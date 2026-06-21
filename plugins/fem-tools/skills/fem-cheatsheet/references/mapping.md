---
title: 상용 FEA ↔ FEniCSx/UFL 용어 매핑표
date: 2026-05-16
tags:
  - FEM
  - FEniCSx
  - ABAQUS
  - ANSYS
  - mapping
status: active
---

# 상용 FEA ↔ FEniCSx/UFL 매핑표

> Week 1 검증 기준 산출물. 새로 발견한 대응 관계를 매주 추가.

## 모델 구조

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| 메시 | `*PART`/`*INSTANCE` | Mesh body | `dolfinx.mesh.Mesh` | |
| 재료 영역 | Section assignment | Material assignment | `meshtags` + subdomain integration | |
| 절점 변수 | Node | Node | `Function` (DOF) | |

## 요소·기저

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| 선형 사면체 | C3D4 | SOLID185 (degen.) | `("Lagrange", 1)` on tetra | |
| 2차 사면체 | C3D10 | SOLID187 | `("Lagrange", 2)` on tetra | |
| 선형 hex | C3D8 | SOLID185 | `("Lagrange", 1)` on hexahedron | **shear locking** — 휨 정확도 낮음. P1 trilinear가 휨 변형 표현 못 함 [W1-P3] |
| 2차 hex | C3D20 (또는 C3D20R) | SOLID186 | `("Lagrange", 2)` on hexahedron | 휨 정확. $L/h{=}50$ 캔틸레버에서 P1 오차 −10% → P2 오차 −0.15% [W1-P3] |
| Hybrid (비압축) hex | C3D8H, C3D20H | SOLID185/186 with mixed u-p | Taylor-Hood: `basix.ufl.mixed_element([elem_u_P2, elem_p_P1])` | 거의비압축 PDMS/고무. 굽힘에선 disp-only가 locking [W2-P2a] |
| Hybrid tet | C3D4H, C3D10H | — | Taylor-Hood on tetra (P2 vector + P1 scalar) | tet은 P2도 약간의 locking 잔존 — hex 권장 |
| 평면응력 | CPS4 | PLANE182 (plane stress) | UFL 2D + **유효** $\lambda^{*}=E\nu/(1-\nu^2)$ | 3D $\lambda$ 그대로 쓰면 $\sigma_{zz}\neq 0$ 잡힘 [W1-P2] |
| 평면변형 | CPE4 | PLANE182 (plane strain) | UFL 2D + 정식 $\lambda=E\nu/((1+\nu)(1-2\nu))$ | 같은 식, $\lambda$ 만 차이 |
| 곡선 경계 (2차 기하) | C3D10 등 (자동) | SOLID187 (자동) | Gmsh `setOrder(2)` + dolfinx 고차 메시 | P2 변위와 isoparametric 일치 [W1-P2] |

## 재료 모델

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| 선형 탄성 | `*ELASTIC` | MP, EX/PRXY | UFL `sigma = lam*tr(eps)*I + 2*mu*eps` | |
| 사용자 정의 | UMAT | USERMAT | UFL 직접 작성 또는 `dolfinx_materials` | |
| Neo-Hookean (압축성) | `*HYPERELASTIC, NEO HOOKE`<br>`*NLGEOM, YES` | TB,HYPER,NEO | `psi = mu/2*(Ic-3) - mu*ln(J) + lam/2*ln(J)^2`<br>Total Lagrangian, `F=I+grad(u)` | Bonet-Wood 형 — $J\to 0$ 안정. ABAQUS `NLGEOM=YES` 가 dolfinx의 디폴트(Total Lagrangian + Newton) [W2-P1] |
| SVK (Saint Venant-Kirchhoff) | `*ELASTIC` + `*NLGEOM,YES` (자동) | 직접 지원 안 함 | `psi = lam/2*tr(E)**2 + mu*inner(E,E)`,  `E=(C-I)/2` | 큰 압축에서 비물리 — 작은 변형(<5%) 또는 인장 only [L6 노트] |
| Mooney-Rivlin | `*HYPERELASTIC, MOONEY-RIVLIN` | TB,HYPER,MOONEY | `psi = c1*(Ic-3) + c2*(IIc-3) + kappa/2*(J-1)^2` | 고무 (작은~중간 변형) |
| Ogden 3-term (α ∈ {2,4,6}, invariant) | `*HYPERELASTIC, OGDEN, N=3`<br>(α 짝수 정수만) | TB,HYPER,OGDEN | $\sum_p (\mu_p/\alpha_p)(\bar I_{\alpha_p} - 3)$, $\bar I_\alpha = J^{-\alpha/3}\sum\lambda^\alpha$, Newton's identities 사용 | thin slice 시제. 1-term α=2 가 incompressible NH 와 동치. fractional α 안 됨 [W2-P2b] |
| Ogden 3-term (fractional α) | `*HYPERELASTIC, OGDEN, N=3`<br>(Treloar/PDMS fit) | TB,HYPER,OGDEN | Cardano spectral decomposition 필요 → $\lambda_i = \sqrt{\text{eig}_i(C)}$ | 실제 PDMS fit ($\alpha \approx 1.3, 5.0, -2.0$). `dolfinx_materials` 라이브러리 또는 직접 구현 [W2-P2 후속 옵션] |

## 메시 생성·가져오기

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| 파티션/물성영역 | `*ELSET` | NSEL/ESEL component | Gmsh `addPhysicalGroup(2, [surf], tag=N)` → cell_tags | [W1-P2] |
| 경계면 그룹 | `*SURFACE` | SF area | Gmsh `addPhysicalGroup(1, [line], tag=N)` → facet_tags | [W1-P2] |
| 메시 세밀화 (지역) | Bias seeding / mesh control | Sphere of influence | Gmsh `Field "Distance" + "Threshold"` | [W1-P2] |
| 메시 가져오기 | (CAE 내부) | (Workbench 내부) | `dolfinx.io.gmshio.model_to_mesh(model, comm, rank=0, gdim=d)` | 반환 (mesh, cell_tags, facet_tags) [W1-P2] |

## 경계조건·하중

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| Dirichlet | `*BOUNDARY` | D | `dirichletbc` | |
| Traction | `*DSLOAD` | SF | UFL `dot(T, v)*ds` | |
| 체적력 | `*DLOAD` | BF | UFL `dot(b, v)*dx` | |
| 대칭 BC | `*BOUNDARY, ENCASTRE`/XSYMM | `D, , UX/UY/UZ`, symm | `V.sub(i).collapse()` + `dirichletbc` 한 성분만 | 다른 성분은 자유; 자연 BC $\sigma_{n\tau}=0$ 묵시 [W1-P2] |
| 완전 클램프 (`*BOUNDARY ENCASTRE`) | `*BOUNDARY, ENCASTRE` | `D, , ALL` | `locate_dofs_topological(V, fdim, facets)` + zero `Function` (컴포넌트 분리 X) | 코너에 Williams 응력 특이점 — $\sigma^{\max}$ 메시 의존 [W1-P3] |

## 솔버·수렴

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| 직접 솔버 | Direct | Sparse | PETSc `lu` (MUMPS) | |
| 반복 솔버 | Iterative | PCG | PETSc `cg`/`gmres` | |
| Newton (비선형) | 내장 자동 (`*STATIC`+`*NLGEOM,YES`) | Auto (Nonlinear) | `NonlinearProblem(R, u, bcs, J=Jacobian)` + `NewtonSolver` (dolfinx.nls.petsc) | NewtonSolver는 PETSc SNES `newtonls` 래퍼. atol/rtol/max_it 속성 [W2-P1] |
| Load step | `*STEP` 내 `*INCREMENTATION` (자동/수동) | LSTEP/SUBST | Python 루프 + `u_prescribed.x.array[:]=U` + `solver.solve(u)` | 자동 load step·증분 줄이기는 본인 구현 [W2-P1] |
| Arc-length | `*RIKS` | Arc-length | `fenics_arclength` (외부) | Limit point/snap-through 통과 |

## 후처리

| 개념 | ABAQUS | ANSYS | FEniCSx | 비고 |
|------|--------|-------|---------|------|
| 응력 시각화 | Viewer (.odb) | PostProc (.rst) | PyVista + VTKHDF | |
| 적분점 응력 | IP output | ETABLE | `Function`을 DG 공간에 project | |

## 트랩

| 항목 | 상용 SW 거동 | FEniCSx 차이 | 출처 |
|------|-------------|-------------|------|
| 자동 단위 | 일부 SW가 SI 가정 | UFL은 단위 무차원 — 사용자가 일관성 책임 | |
| C3D8R (reduced integration) | hourglass control 자동 | 명시적으로 quadrature 줄이거나 EAS 요소 별도 구현 필요 | — |
| C3D8 shear locking 경고 | ABAQUS는 종종 자동 경고/대안 권장 | FEniCSx는 조용히 잘못된(작은) 변위 반환 — P2 hex로 자체 검증 | W1-P3 |
| ENCASTRE 자동 corner 응력 처리 | 일부 후처리에서 코너 평균 | dolfinx 노드 평균은 코너 특이점 그대로 반영 → 평가 위치를 의도적으로 선택 | W1-P3 |
