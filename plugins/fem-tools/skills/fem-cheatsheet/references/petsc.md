---
title: PETSc 옵션 사전 — FEniCSx 학습 누적
date: 2026-05-16
tags:
  - FEM
  - FEniCSx
  - PETSc
  - cheatsheet
status: active
---

# PETSc 옵션 사전

> 누적 원칙: 시도한 옵션 + 증상 + 결론을 매주 기록. 효과 없거나 역효과인 것도 남긴다 (재시도 방지).

## 솔버 선택 가이드 (요약)

| 문제 규모 | 종류 | 권장 KSP | 권장 PC | 비고 |
|----------|------|---------|---------|------|
| <50k DOF, 대칭/비대칭 | 직접 | `preonly` | `lu` (MUMPS) | 메모리 여유 시 가장 안정 |
| 50k~500k 대칭 | 반복 | `cg` | `gamg`/`hypre` | AMG 옵션 튜닝 필요 |
| >500k | 반복 | `cg`/`gmres` | `gamg` + multi-grid | MPI 병렬과 결합 |

## 시도 로그

| 날짜 | 문제 | 옵션 | 증상 | 결론 | 출처 |
|------|------|------|------|------|------|
| 2026-05-16 | 1D 봉 P1/P2, DOF ≤ 257 | `{"ksp_type":"preonly","pc_type":"lu"}` | 즉시 수렴, 머신 정밀도 | 1D 소형 문제 디폴트로 채택 | W1-P1 |
| 2026-05-18 | 2D 평면응력 Kirsch, DOF ≤ 41k | `{"ksp_type":"preonly","pc_type":"lu"}` | 4단계 메시 합쳐 ~수 초, 메모리 여유 | 50k 이하 2D는 LU 직접이 여전히 디폴트 | W1-P2 |
| 2026-05-25 | 3D hex 캔틸레버 P2, DOF ≤ 49k ($L/h{=}50$) | `{"ksp_type":"preonly","pc_type":"lu"}` | 6 케이스 총 수 초, 메모리 여유 | 50k 이하 3D도 LU 직접 OK. 다음 임계는 ~200k에서 평가 예정 | W1-P3 |

## SNES (비선형) 옵션 — dolfinx NewtonSolver 경유

dolfinx 0.9.0의 `NewtonSolver` (`dolfinx.nls.petsc`)는 PETSc SNES `newtonls`의 얇은 래퍼. SNES를 직접 쓸 수도 있지만 W2-P1 단계에선 NewtonSolver가 충분.

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 문제 구성 | `problem = NonlinearProblem(R, u, bcs=bcs, J=Jacobian)` | `dolfinx.fem.petsc` | W2-P1 |
| 솔버 생성 | `solver = NewtonSolver(comm, problem)` | `dolfinx.nls.petsc` | W2-P1 |
| 절대 허용오차 | `solver.atol = 1e-8` | $\|R\| < $ atol 시 수렴 | W2-P1 |
| 상대 허용오차 | `solver.rtol = 1e-8` | $\|R_k\|/\|R_0\| < $ rtol | W2-P1 |
| 최대 반복 | `solver.max_it = 30` | 비수렴 시 RuntimeError | W2-P1 |
| 수렴 기준 | `solver.convergence_criterion = "incremental"` 또는 `"residual"` | "incremental" = $\|\Delta u\|$, 권장 | W2-P1 |
| 보고 출력 | `solver.report = True` | 매 iter 잔차 노름 stdout | W2-P1 |
| 내부 KSP 선택 | `ksp = solver.krylov_solver` → PETSc Options 사용 | dict 인터페이스 없음 | W2-P1 |
| 풀이 | `n_iter, converged = solver.solve(u)` | `u` in-place 갱신 | W2-P1 |

### Inner KSP 설정 (`NewtonSolver`에 dict 인터페이스 없음)

```python
from petsc4py import PETSc
ksp = solver.krylov_solver
opts = ksp.getOptionsPrefix() or ""
P = PETSc.Options()
P[f"{opts}ksp_type"] = "preonly"
P[f"{opts}pc_type"]  = "lu"
ksp.setFromOptions()
```

### Load stepping 패턴

```python
for lam in stretch_steps:
    u_prescribed.x.array[:] = (lam - 1.0) * L         # BC 갱신
    n_iter, converged = solver.solve(u)                # Warm-start (u가 이전 step 해)
    if not converged:
        # Δλ를 절반으로 줄여 재시도 (1차 복구)
        ...
```

## 시도 로그 (SNES/NewtonSolver)

| 날짜 | 문제 | 옵션 | 증상 | 결론 | 출처 |
|------|------|------|------|------|------|
| 2026-05-25 | NH P2 hex $8^3$ uniaxial, 21 load step, $\lambda$ 1→2 | NewtonSolver atol=rtol=1e-8, "incremental", 내부 KSP `preonly/lu` | 모든 step Newton 4 iter, 머신 정밀도 잔차 | NH compressible Bonet-Wood는 strongly convex → Newton quadratic 수렴 안정 | W2-P1 |
| 2026-05-25 | NH Taylor-Hood mixed P2-P1 hex $6^3$ equibiaxial, 11 load step, $\lambda_b$ 1→1.5 | 동일 (preonly/lu on mixed block system) | 모든 step 수렴, σ 오차 0.19% | Mixed system 도 작은 DOF (~5k 변위 + ~1k 압력)에선 monolithic LU OK. 대형은 fieldsplit + block PC 필요 | W2-P2a |

## 트랩

| 증상 | 원인 | 회피 | 출처 |
|------|------|------|------|
| `petsc_options` 키가 안 먹음 | dash prefix 사용 (`-ksp_type`) | dash 없는 키 (`"ksp_type"`) | W1-P1 |
| `ld: warning: duplicate -rpath ...` (macOS) | JIT 빌드가 동일 rpath 중복 추가 | 무해. 무시 | W1-P1 |
| MUMPS LU 단일 노드 strong scaling **anti-scaling** (n↑ 시 wall time ↑) | 1M DOFs는 single-node MPI에 너무 작음. supernode factorization 효율 < communication overhead. axisymmetric narrow mesh가 partition imbalance 악화 | baseline n=1 측정 후 sweep으로 sweet spot 확인. 단일 노드 + 작은 문제 + 직접 솔버는 **serial이 종종 최적**. 큰 문제 (≥ 10M) 또는 multi-node cluster에서 의미 있는 strong scaling | W4-P3 |
| CG + GAMG 가 axisymmetric NH에서 NewtonSolver max_it 도달 | CG는 SPD 가정 — axisymmetric tangent ($\varepsilon_{\theta\theta}=u_r/r$ 항) 이 $r \to 0$ 근처에서 ill-conditioned, SPD 보장 안 됨 | KSP를 `gmres`로 (indefinite 허용). 그러나 GAMG 자체가 hoop coupling 표현 못 함 → 다음 행 | W4-P3 |
| GMRES + GAMG 가 "converged" 하지만 u = 0 (false convergence) | AMG agg algorithm은 standard isotropic Laplacian 가정. axisymmetric $1/r$ singularity + hoop modes 가 strong-of-influence 그래프 왜곡 → coarse grid가 wrong null space | (a) `MatSetNearNullSpace`로 rigid body 등록, (b) `pc_type fieldsplit` block PC, (c) hypre BoomerAMG, (d) **fallback to MUMPS** (W4-P3 채택) | W4-P3 |
| Mesh aspect ratio가 매우 클 때 (thin film: h_f/L ~ 1/50000) MPI partition 불균형 | ParMETIS auto-partition도 narrow long strip은 잘 못 분할 → halo communication 큼 | **thin film 문제는 single-rank 가 종종 최적**. 또는 3D로 z 방향에 충분 cells | W4-P3 |

## Strong scaling 측정 가이드 (W4-P3 경험, 1.2M DOFs M5 Max)

실측: MUMPS LU, n=1 (11.6s, η=100%) → n=4 (51.7s, 5.6%) → n=6 (74.4s, 2.6%) → n=12 (179s, 0.54%). **단조 anti-scaling, sweet spot n=1**.

1. **baseline n=1 측정 필수** — 절대 wall time 기준
2. n=4, 6, 12 sweep — efficiency $\eta = T_1 / (n \cdot T_n)$
3. acceptable threshold: η ≥ 50%
4. anti-scaling 발견 시: problem size + mesh aspect + hardware (single-node vs cluster) 진단

| Problem size | Single-node sweet spot (경험적) |
|---|---|
| ≤ 1M DOFs (W4-P3) | **n=1 (serial)** |
| 1-10M DOFs | n=4-6 (case dependent) |
| ≥ 10M DOFs | n=12 또는 multi-node |
