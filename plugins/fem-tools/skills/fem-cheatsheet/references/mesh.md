---
title: Mesh 치트시트 — dolfinx + Gmsh 누적 트랩
date: 2026-05-28
tags:
  - FEM
  - FEniCSx
  - mesh
  - Gmsh
  - cheatsheet
status: active
---

# Mesh 치트시트

> 누적 원칙: 메시 생성·연결·tag 관련 트랩을 학습 sprint에서 만날 때마다 추가.

## 목차

- [Mesh 생성 (dolfinx 내장)](#mesh-생성-dolfinx-내장)
- [Custom stitched mesh](#custom-stitched-mesh)
- [Gmsh 통합](#gmsh-통합)
- [트랩 (자주 틀리는 것)](#트랩-자주-틀리는-것)

## Mesh 생성 (dolfinx 내장)

| 항목 | 표현 | 비고 | 출처 |
|---|---|---|---|
| 2D 사각형 | `mesh.create_rectangle(comm, [(x0,y0), (x1,y1)], [nx, ny], cell_type=CellType.quadrilateral)` | quad 권장. tri는 `triangle` | W1-P2 |
| 3D 박스 | `mesh.create_box(comm, [pmin, pmax], [nx, ny, nz], cell_type=CellType.hexahedron)` | hex 권장 (P2면 cubic 변위 표현, bending 효율) | W1-P3 |
| Custom mesh (manual nodes+cells) | `mesh.create_mesh(comm, cells, x, coord_elem)` | nodes shape (n,gdim), cells shape (n_cells, n_per_cell). coord_elem = `basix.ufl.element("Lagrange", "quadrilateral", 1, shape=(2,))` | W3-P1 |
| 한 노드의 셀 중점 추출 | `mesh.compute_midpoints(domain, tdim, cell_indices)` → shape (n_cells, 3) | DG0 재료 할당용 | W3-P1 |

## Custom stitched mesh

두 층 별도 분할 후 노드 stitching — interface 강제 정렬 (예: bimetal `y=0`, wafer-film `z=h_s`).

```python
def build_stitched_quad_mesh(L, h_bot, h_top, nx, ny_per_layer, comm):
    if comm.rank == 0:
        x = np.linspace(0.0, L, nx + 1)
        y_bot = np.linspace(-h_bot, 0.0, ny_per_layer + 1)[:-1]   # exclude y=0
        y_top = np.linspace(0.0, h_top, ny_per_layer + 1)         # include y=0
        y = np.concatenate([y_bot, y_top])
        ny = 2 * ny_per_layer
        X, Y = np.meshgrid(x, y, indexing="xy")
        nodes = np.stack([X.ravel(), Y.ravel()], axis=-1).astype(np.float64)
        # dolfinx quadrilateral 노드 순서: tensor-product (i,j),(i+1,j),(i,j+1),(i+1,j+1)
        cells = []
        for j in range(ny):
            for i in range(nx):
                n00 = j*(nx+1) + i
                n10 = j*(nx+1) + (i+1)
                n01 = (j+1)*(nx+1) + i
                n11 = (j+1)*(nx+1) + (i+1)
                cells.append([n00, n10, n01, n11])
        cells = np.asarray(cells, dtype=np.int64)
    else:
        nodes = np.empty((0, 2), dtype=np.float64)
        cells = np.empty((0, 4), dtype=np.int64)
    coord_elem = basix.ufl.element("Lagrange", "quadrilateral", 1, shape=(2,))
    return mesh.create_mesh(comm, cells, nodes, coord_elem)
```

W3-P1 `build_bimetal_mesh`, W3-P2 `build_axisym_mesh` 패턴. 두 다른 두께 층에 interface가 cell 경계와 정확히 일치 → centroid-based 재료 할당 안전.

## Gmsh 통합

```python
import gmsh
gmsh.initialize()
gmsh.option.setNumber("General.Terminal", 0)
gmsh.model.add("name")

# Points + Lines + Surface (geo kernel)
p1 = gmsh.model.geo.addPoint(x, y, z, lc)       # lc = local mesh size
l1 = gmsh.model.geo.addLine(p1, p2)
loop = gmsh.model.geo.addCurveLoop([l1, l2, ...])  # closed loop (end-of-seg = start-of-next)
surf = gmsh.model.geo.addPlaneSurface([loop])

gmsh.model.geo.synchronize()

# Physical tags (cell + facet + point)
gmsh.model.addPhysicalGroup(2, [surf], tag=1)      # cell tag
gmsh.model.addPhysicalGroup(1, [l1, l2], tag=10)   # facet tag
gmsh.model.addPhysicalGroup(0, [p_pin], tag=20)    # point tag

# Embed point inside surface (single-DOF BC 위치 보장)
gmsh.model.mesh.embed(0, [p_pin], 2, surf)

gmsh.model.mesh.generate(2)
mesh_data = gmshio.model_to_mesh(gmsh.model, comm, 0, gdim=2)  # (mesh, cell_tags, facet_tags)
gmsh.finalize()
```

180° 호는 setOrder 한계로 두 90° split 권장 (W2-P3a).

## 트랩 (자주 틀리는 것)

### T1. dolfinx quadrilateral 노드 순서 = tensor-product (Z-order), NOT CCW

| 잘못 (CCW) | 올바른 (Z-order) |
|---|---|
| `[n00, n10, n11, n01]` (반시계) | `[n00, n10, n01, n11]` (tensor-product) |
| Jacobian 음수 → 솔루션 **NaN** | 정상 |

**디버깅 단서**: BC dof 정상 잡히지만 솔루션 NaN → cell connectivity 의심. W3-P1 v1에서 모든 케이스 NaN → cell 순서 수정 후 즉시 PASS.

### T2. 비대칭 두께 + `create_rectangle` 균등 분할 → 인터페이스 어긋남

`create_rectangle([(0, -h_bot), (L, h_top)], [nx, ny])` 에서 ny 균등 분할은 두 층 두께가 다르면 인터페이스 `y=0` 이 cell 경계가 **아님**. centroid-based 재료 할당이 오분류.

**증상**: 대칭 케이스 (h_bot=h_top) PASS, 비대칭 (m≠1) 큰 오차 (30%+).
**해결**: custom stitched mesh (위 §Custom stitched mesh 패턴) 또는 Gmsh.

### T3. Gmsh shared edge direction

두 surface가 edge 공유 시 **양쪽 loop가 같은 direction의 edge 사용해도 OK** (gmsh는 connectivity로 loop 검증, orientation은 surface normal 별도).

```python
# Loop 1 (surface A)
loop_A = gmsh.model.geo.addCurveLoop([l1, l2, l_shared])

# Loop 2 (surface B): shared edge 같은 방향 + 그 외 edges로 닫기
loop_B = gmsh.model.geo.addCurveLoop([l3, l4, l5, l_shared])  # NOT -l_shared
#                                                    ↑↑↑↑↑↑↑↑
#                                                    같은 방향 OK
```

**에러 메시지**: "Curve loop N is wrong" → 첫 의심은 **연결성** (end of seg = start of next), 방향 reverse 시도는 두 번째.

### T4. Gmsh pin point + embed

Single-DOF BC (예: `u_z=0` at corner) 위해 메쉬에 정확한 노드 필요. Point를 surface에 embed:
```python
p_pin = gmsh.model.geo.addPoint(x, y, z, lc)
gmsh.model.geo.synchronize()
gmsh.model.mesh.embed(0, [p_pin], 2, surf)   # 0=point dim, 2=surface dim
gmsh.model.addPhysicalGroup(0, [p_pin], tag=20)
```
**embed 안 하면** mesh generation 시 그 위치에 노드 없을 수 있음 → BC `locate_dofs_geometrical` 실패.

## 출처

- W1-P2/P3, W2-P3a, W3-P1, W3-P2, W3-P3 v2, W4-P2 미니프로젝트
- jsdokken DOLFINx tutorial — mesh creation, Gmsh integration
- gmsh Python API docs
