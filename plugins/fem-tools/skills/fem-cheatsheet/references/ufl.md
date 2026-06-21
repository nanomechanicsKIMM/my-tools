---
title: UFL 치트시트 — FEniCSx 학습 누적
date: 2026-05-16
tags:
  - FEM
  - FEniCSx
  - UFL
  - cheatsheet
status: active
---

# UFL 치트시트

> 누적 원칙: 새로 만난 UFL 연산·이디엄을 1건 이상 매주 추가. 출처(주차·미니프로젝트·튜토리얼 URL) 표기.

## 목차

- [기본 객체](#기본-객체)
- [측도와 적분](#측도와-적분)
- [미분 연산](#미분-연산)
- [텐서 연산](#텐서-연산)
- [경계조건](#경계조건)
- [자동미분 (`derivative`)](#자동미분-derivative)
- [솔버 인터페이스](#솔버-인터페이스)
- [트랩 (자주 틀리는 것)](#트랩-자주-틀리는-것)

## 기본 객체

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 시도/시험 함수 | `u = TrialFunction(V)`, `v = TestFunction(V)` | 같은 공간이어도 둘 다 필요 | W1-P1 |
| 상수 | `fem.Constant(domain, default_scalar_type(c))` | PETSc complex 빌드 호환 | W1-P1 |
| 공간 좌표 | `x = ufl.SpatialCoordinate(domain)`; 성분은 `x[0]`, `x[1]` | 해석해 비교용 | W1-P1 |
| 함수 공간 (스칼라) | `fem.functionspace(domain, ("Lagrange", p))` | p=1,2 | W1-P1 |
| 함수 공간 (벡터 nD) | `fem.functionspace(domain, ("Lagrange", p, (n,)))` | 2D=`(2,)`, 3D=`(3,)` | W1-P2·P3 |
| 함수 공간 (텐서) | `fem.functionspace(domain, ("Lagrange"\|"DG", p, (n,n)))` | 응력 보간용 | W1-P2 |
| Mixed element (Taylor-Hood) | `elem_u = basix.ufl.element("Lagrange", domain.basix_cell(), 2, shape=(3,))`<br>`elem_p = basix.ufl.element("Lagrange", domain.basix_cell(), 1)`<br>`me = basix.ufl.mixed_element([elem_u, elem_p])` | `import basix.ufl`. 0.9.0 권장 API | W2-P2a |
| Mixed function space | `W = fem.functionspace(domain, me)` | | W2-P2a |
| Mixed Function 심볼 분리 | `u, p = ufl.split(w)` | symbolic (UFL 식 만들 때). 실제 array는 `w.sub(i).collapse()` | W2-P2a |
| Mixed TestFunctions | `v_u, v_p = ufl.TestFunctions(W)` 또는 `derivative(Pi, w, TestFunction(W))` | | W2-P2a |
| 벡터 상수 | `fem.Constant(domain, np.array([Tx,Ty], dtype=default_scalar_type))` | 튜플 직접 전달 금지 (스칼라 캐스트됨) | W1-P2 |
| 식 보간 | `expr = fem.Expression(ufl_expr, V.element.interpolation_points())`; `f.interpolate(expr)` | UFL 식 → Function | W1-P2 |
| 3D 박스 메시 | `mesh.create_box(comm, [p_min, p_max], [nx, ny, nz], cell_type=CellType.hexahedron)` | hex 권장; tet은 `tetrahedron` | W1-P3 |
| Plane strain 2D→3D F embedding | `F2 = Identity(2) + grad(u)`<br>`F = as_tensor([[F2[0,0], F2[0,1], 0], [F2[1,0], F2[1,1], 0], [0,0,1]])` | out-of-plane stretch = 1. 3D NH/SVK 식 그대로 사용 가능 | W2-P3a |
| Reaction force 추출 (prescribed disp BC) | `b = assemble_vector(form(R_form))` (BC zero-out 전); `F_x = b.array[parent_dofs].sum()` | parent_dofs = `locate_dofs_topological((sub, sub_space), ...)[0]` | W2-P3a |

## 측도와 적분

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 영역 적분 | `... * ufl.dx` | | W1-P1 |
| 경계 적분 (전체) | `... * ufl.ds` | | — |
| 경계 적분 (태그 1) | `ds = Measure("ds", domain=domain, subdomain_data=facet_tags)` 후 `... * ds(1)` | `mesh.meshtags`로 facet에 marker 부여 | W1-P1 |
| 스칼라 적분 평가 | `fem.assemble_scalar(fem.form(expr * dx))` | float 반환 | W1-P1 |

## 미분 연산

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 1D 미분 | `u.dx(0)` | 0번째 좌표 방향 | W1-P1 |
| 다차원 그래디언트 | `ufl.grad(u)` | 스칼라 → 벡터 | — |
| 발산 | `ufl.div(sigma)` | 텐서 → 벡터 | — |

## 텐서 연산

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 변형률 | `eps = ufl.sym(ufl.grad(u))` | 벡터장 → 대칭 2-텐서 | W1-P2 |
| 항등 텐서 | `ufl.Identity(n)` | n=2 or 3 | W1-P2 |
| 트레이스 | `ufl.tr(T)` | | W1-P2 |
| 텐서 내적 | `ufl.inner(A, B)` ($A_{ij}B_{ij}$) | 약형식 좌변 `inner(sigma, eps(v))` | W1-P2 |
| 등방 응력 (3D 또는 plane strain) | `lam*tr(eps)*Identity(d) + 2*mu*eps` | $\lambda=E\nu/((1+\nu)(1-2\nu))$ | W1-P3 |
| 등방 응력 (plane stress) | 위 식 + **유효** $\lambda^{*}=E\nu/(1-\nu^2)$ | 그대로 $\lambda$ 쓰면 $\sigma_{zz}\neq 0$ 발생 | W1-P2 |
| 3D 텐서 공간 → reshape | `W=fem.functionspace(domain,("Lagrange",1,(3,3)))`<br>`s_arr=sigma.x.array.reshape(-1,9)` (row-major: sxx,sxy,sxz,syx,syy,syz,szx,szy,szz) | 3D 응력 노드값 추출 | W1-P3 |

## 경계조건

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| Dirichlet 상수값 | `dofs = locate_dofs_geometrical(V, fn)` + `dirichletbc(Constant(domain, 0.), dofs, V)` | 시험함수가 자동으로 0이 됨 | W1-P1 |
| 컴포넌트 Dirichlet (대칭 BC) | `sub=V.sub(i); sub_space,_=sub.collapse()`<br>`dofs=locate_dofs_topological((sub, sub_space), fdim, facets)`<br>`bc=dirichletbc(Function(sub_space), dofs, sub)` | $u_i=0$만 잠그고 다른 성분은 자유 | W1-P2 |
| 면 전체 잠금 (벡터) | `dofs=locate_dofs_topological(V, fdim, facets); u0=fem.Function(V); bc=dirichletbc(u0, dofs)` | 컴포넌트 분리 불필요. 모든 성분 = 0 | W1-P3 |
| 다중 facet tag (`create_box` 등) | facet 인덱스·값을 concat → **`np.argsort`로 인덱스 오름차순 정렬 후** `meshtags(...)` | meshtags는 정렬된 인덱스 가정 — 안 하면 silent 오류 | W1-P3 |
| Mixed 서브-서브 컴포넌트 BC | `sub = W.sub(0).sub(comp_idx); sub_space, _ = sub.collapse()`<br>`dofs = locate_dofs_topological((sub, sub_space), fdim, facets)`<br>`bc = dirichletbc(Function(sub_space), dofs, sub)` | 변위 블록(W.sub(0))의 한 성분만 잠금 — Taylor-Hood 대칭 BC | W2-P2a |
| facet → ds(tag) | `gmshio.model_to_mesh` 가 physical group 태그를 facet_tags로 변환 → `Measure("ds", subdomain_data=facet_tags)` | facet_tags.find(tag)으로 해당 facets 검색 | W1-P2 |
| 점에서 Function 평가 | `bb=geometry.bb_tree(domain, tdim)`<br>`cand=compute_collisions_points(bb, pts)`<br>`coll=compute_colliding_cells(domain, cand, pts)`<br>`f.eval(pts, [coll.links(0)[0]])` | 점 외부 셀 인덱스 필수. 텐서면 flatten 후 reshape | W1-P2 |
| Neumann | 약형식 우변 `T * v * ds(tag)` 항으로 추가 | "안 적으면 자유면" — 상용 SW 디폴트와 같지만 명시 안 함이 의도임을 본인이 알아야 | W1-P1 |
| Robin | 좌변 `h*u*v*ds + ...` AND 우변 `h*u_inf*v*ds + ...` 둘 다 | 한쪽만 빼먹는 게 흔한 버그 | L1 노트 |

## 자동미분 (`derivative`)

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 변분 잔차 (퍼텐셜 → 약형식) | `R = ufl.derivative(Pi, u, v)` | $\Pi = \int\Psi\,d\mathbf{X}$ 일 때 $R = \delta\Pi$ | W2-P1 |
| 접선강성 (Newton) | `Jacobian = ufl.derivative(R, u, du)` | 손유도 $\partial R/\partial u$ 30+ 줄을 자동 | W2-P1 |
| 형식 변수 | `v=TestFunction(V), du=TrialFunction(V)` | `derivative`의 2·3번째 인자 | W2-P1 |
| 끊긴 변수 체크 | `print(Pi.signature())` 또는 `len(Pi.coefficients())>0` | `derivative(Pi, u, v) == 0`이면 `Pi`가 `u`를 추적 못 함 | W2-P1 |

## 초탄성 (Hyperelasticity, Total Lagrangian)

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 변형 경사 | `F = ufl.Identity(d) + ufl.grad(u)` | 참조 좌표계 기준 (Lagrangian) | W2-P1 |
| 우측 Cauchy-Green | `C = F.T * F` | 대칭, 양정값 | W2-P1 |
| Green-Lagrange | `E = 0.5*(C - Identity(d))` | 회전 불변 | W2-P1 |
| Jacobian (체적비) | `J = ufl.det(F)` | **변수명 충돌 주의**: 접선강성도 보통 J — `Jacobian` 권장 | W2-P1 |
| 1st invariant | `Ic = ufl.tr(C)` | NH 등에 사용 | W2-P1 |
| Neo-Hookean (Bonet-Wood) | `psi = mu/2*(Ic-3) - mu*ln(J) + lam/2*ln(J)**2` | 압축성. $J\to 0$ 안정 | W2-P1 |
| NH perturbed Lagrangian (mixed) | `psi_mix = mu/2*(Ic-3) - mu*ln(J) + p*(J-1) - p**2/(2*kappa)` | **`-mu*ln(J)` 보정 필수** — 없으면 자명해 깨짐 | W2-P2a |
| Isochoric invariant $\bar I_p$ | `Ibar_p = J**(-p/3.0) * sum_lambda_p` | $\sum\lambda^p$ 계산 후 isochoric 변환 | W2-P2b |
| Newton's identity α=2 | `sum_lam_2 = ufl.tr(C)` | $\sum\lambda^2 = I_1$ | W2-P2b |
| Newton's identity α=4 | `sum_lam_4 = ufl.tr(C)**2 - 2*I2` ($I_2 = \tfrac12((tr C)^2 - tr(C^2))$) | $\sum\lambda^4 = \mathrm{tr}\,C^2$ | W2-P2b |
| Newton's identity α=6 | `sum_lam_6 = ufl.tr(C)**3 - 3*ufl.tr(C)*I2 + 3*ufl.det(C)` | $\sum\lambda^6 = \mathrm{tr}\,C^3$. α 짝수 정수 한정 | W2-P2b |
| Ogden 일반 (mixed + perturbed Lagrangian) | `psi = Σ_p (mu_p/alpha_p)*(Ibar_alpha_p - 3) + p*(J-1) - p**2/(2*kappa)` | 1-term α=2 가 incompressible NH 와 동치 | W2-P2b |
| Ogden 1st PK / Cauchy (손유도) | $\sigma = (2/J)\,F\,(\partial\Psi/\partial C)\,F^\top + p I$, $\partial\bar I_\alpha/\partial C = J^{-\alpha/3}[\partial(\sum\lambda^\alpha)/\partial C - (\alpha/6)\sum\lambda^\alpha\,C^{-1}]$ | $\partial(\sum\lambda^2)/\partial C = I$, $\partial(\sum\lambda^4)/\partial C = 2C$, $\partial(\sum\lambda^6)/\partial C = 3C^2$ | W2-P2b |
| SVK | `psi = lam/2*tr(E)**2 + mu*inner(E,E)` | 큰 압축에서 비물리 — NH 권장 | L6 노트 |
| 1st PK (NH, 손유도) | `P = mu*F + (lam*ln(J)-mu)*inv(F).T` | UFL 자동미분 검증용으로만 | W2-P1 |
| Cauchy stress | `sigma = (1.0/J) * P * F.T` | 실험·문헌 비교용 (현재 단면) | W2-P1 |
| 총 퍼텐셜 | `Pi = psi * ufl.dx` | 우변 (T·u·ds, b·u·dx) 포함 시 추가 | W2-P1 |

## 솔버 인터페이스

| 항목 | 표현 | 비고 | 출처 |
|------|------|------|------|
| 선형 문제 | `LinearProblem(a, L, bcs=[bc], petsc_options={...})` + `.solve()` | `Function` 반환 | W1-P1 |
| 비선형 문제 | `NonlinearProblem(R, u, bcs=bcs, J=Jacobian)` (`dolfinx.fem.petsc`) | `u`는 `Function` (in-place 갱신), `R`은 약형식 잔차 | W2-P1 |
| Newton 솔버 | `solver = NewtonSolver(comm, problem)`, 속성 `atol/rtol/max_it/convergence_criterion/report` | PETSc SNES 래퍼 | W2-P1 |
| Newton 내부 KSP | `ksp = solver.krylov_solver`; PETSc Options 로 `ksp_type/pc_type` 설정 후 `ksp.setFromOptions()` | NewtonSolver는 `petsc_options` dict 미지원 → Options 객체 사용 | W2-P1 |
| Newton 풀이 | `n_iter, converged = solver.solve(u)` | `u` 반환 안 됨 — `u`가 in-place 갱신됨 | W2-P1 |
| Load stepping | `u_prescribed.x.array[:] = U_load`; `solver.solve(u)` 반복 | prescribed BC `Function`을 step마다 갱신 | W2-P1 |
| DOF 좌표 (P1) | `V.tabulate_dof_coordinates()` | P2+에서는 DOF≠노드 의미 다름 — 주의 | W1-P1 |
| L2 오차 | `sqrt(assemble_scalar(form((uh - u_ex)**2 * dx)))` | UFL 정밀 적분 | W1-P1 |
| 균질 변형 응력 평균 | `assemble_scalar(form(sigma[0,0]*dx)) / V_total` | $V_{\text{total}}$ = $\int 1\,dx$ | W2-P1 |

## 트랩 (자주 틀리는 것)

| 증상 | 원인 | 회피 | 출처 |
|------|------|------|------|
| `Constant` 타입 에러 (PETSc complex 빌드) | 파이썬 float을 그대로 전달 | `default_scalar_type(val)`로 감싸기 | W1-P1 |
| `petsc_options`이 무시됨 | dash prefix (`-ksp_type`) 사용 | dash 없이 키-밸류 (`"ksp_type": "preonly"`) | W1-P1 |
| 자연 BC가 "조용히" 빠짐 | 우변 ds 항을 안 적음 | T=0 이라도 일관성 위해 항을 적어두면 코드 의도가 명확 | W1-P1 |
| Robin BC 행렬이 비대칭/잘못된 값 | 좌·우변 중 한쪽만 적음 | 항상 쌍으로 추가 | L1 노트 |
| 트랙션 BC가 적용 안 됨 (변위 ≈ 0) | `Constant(domain, default_scalar_type((Tx,Ty)))` 가 튜플을 스칼라로 캐스트 | `Constant(domain, np.array([Tx,Ty], dtype=default_scalar_type))` | W1-P2 |
| 평면응력에서 잘못된 응력장 | 3D Lamé $\lambda$를 그대로 사용 | $\lambda^{*}=E\nu/(1-\nu^2)$ 로 교체 | W1-P2 |
| 응력집중에서 $\sigma_{\theta\theta}\neq\sigma_{yy}$ | 점 $(0,a)$는 $\theta=\pi/2$에서 $\hat\theta=(-1,0)$ → $\sigma_{\theta\theta}=\sigma_{xx}$ | 점 평가 전에 $\hat\theta$를 그려 확인 | W1-P2 |
| P1 hex로 휨 변위 -5~10% 과소 | shear/trapezoidal locking (P1 trilinear가 휨 변형 표현 못 함) | **P2 hex로 차수 ↑** — 메시 세밀화로는 안 풀림. 상용 SW: C3D8 → C3D20 | W1-P3 |
| 3D 완전 클램프 코너에서 $\sigma$ 발산 | Williams-type 응력 특이점, 메시 세밀화 시 단조 증가 | EB·analytical 비교는 **빔 중간 단면** 또는 클램프에서 한 요소 안쪽 | W1-P3 |
| 평면응력 식($\lambda^{*}$)을 3D 빔에 쓰면 응력 ≈12% 작게 | 3D 등방엔 정식 $\lambda=E\nu/((1+\nu)(1-2\nu))$ | 차원 다르면 $\lambda$ 식부터 다시 확인 (W1-P2 vs W1-P3 혼동 금지) | W1-P3 |
| `derivative(Pi, u, v)` 잔차가 0 | `Pi`에 `u`가 통하지 않음 (UFL 객체 끊김) | `Pi = psi * dx`, `psi`가 `F = I + grad(u)` 까지 추적되는지 확인 | W2-P1 |
| 변수명 `J` 충돌 (det F vs 자코비안) | `J = det(F)` 와 `J = derivative(R, u, du)` 둘 다 흔한 이름 | det F는 `J`, 접선강성은 `Jacobian`(또는 `K_mat`) — 한 코드에서 분리 | W2-P1 |
| SVK 큰 압축에서 응력 폭주/비물리 | $J\to 0$에서 $\Psi$ 유한 → 에너지 우물 없음 | NH 사용 (Bonet-Wood $\Psi$가 $-\mu\ln J$ 항 포함) | L6 노트 |
| Newton 첫 step 잔차는 작지만 안 풀림 | Prescribed displacement BC `Function`을 step마다 갱신 안 함 | load step 루프 첫 줄에서 `u_prescribed.x.array[:] = U_load` 강제 | W2-P1 |
| Cauchy ↔ 1st PK 혼동 (응력 1.13× 차이) | 인장에서 $\sigma = J^{-1}\mathbf{P}\mathbf{F}^\top$ 변환 필요 | 보고서·해석해 모두 Cauchy로 통일, 변환 한 줄 명시 | W2-P1 |
| NewtonSolver `petsc_options` 인자 없음 | NewtonSolver는 dict 미지원 — Options 객체 필요 | `petsc4py.PETSc.Options()`에 `f"{prefix}ksp_type"` 형식으로 설정 | W2-P1 |
| Mixed 자명해 ($\mathbf{F}=\mathbf{I}, p=0$)에서 σ ≠ 0, p ≈ -μ | perturbed Lagrangian에 isochoric 보정($-\mu\ln J$) 빠짐 | $\Psi_{\text{mix}} = \mu/2(I_C-3) \mathbf{- \mu\ln J} + p(J-1) - p^2/(2\kappa)$ — `-mu*ln(J)` 빠뜨리지 말 것 | W2-P2a |
| Prescribed-disp 균질 deformation에서 disp-only ≡ mixed (locking 안 보임) | volumetric locking 은 *요소별 제약 충돌* — 균질이면 글로벌 1자유도라 충돌 없음 | Locking demo는 **굽힘/traction/heterogeneous**로 가야. 균질 prescribed-disp는 mixed 구현 검증용 | W2-P2a |
| Mixed의 ⟨p⟩가 해석해 hydrostatic pressure와 부호·스케일 다름 | $p$는 Lagrange 다중자 (formulation 의존), physical pressure는 $-\sigma_{\text{trace}}/3$ | physical pressure 비교 시 $\sigma_{\text{trace}}$ 별도 계산 | W2-P2a |
| Ogden α=3, fractional 시도 → invariant 닫힌형식 없음 | Cayley-Hamilton 은 $\sum\lambda^{2k}$ (짝수만) | Cardano spectral decomposition 필요 (`dolfinx_materials` 참조) | W2-P2b |
| Ogden $\sum\lambda^\alpha$ 만 쓰고 isochoric 안 함 → 자명해 깨짐 | pure $\sum\lambda^\alpha$ 는 J=1 가정 (incompressible) | $\bar I_p = J^{-p/3}\sum\lambda^p$ 항상 사용 (perturbed Lagrangian 결합 시) | W2-P2b |
| Ogden α=4,6 항이 "큰 stretch 에서만" 효과적 ? | 거짓 — small strain 에서도 $\mu_p$ 가 effective shear modulus 에 합산 | small strain $\mu_{\text{eff}} = \sum_p \mu_p$ — fit 시 모든 $\mu_p$ 고려 | W2-P2b |
| Ogden 다항식 ⟨J⟩ 가 NH 보다 큼 (3-term: 1.0039 vs 1-term: 1.0016) | Ogden 더 stiff → $p$ 더 큼 → $J-1=p/\kappa$ 비례 증가 (finite $\kappa$ 효과, 비물리 아님) | $\kappa \to \infty$ 극한에서 사라짐 | W2-P2b |
| 굽힘 + 거의 비압축 disp-only P1 이 4× 강성 | **volumetric locking** — P1 trilinear/tri 자유도가 incompressibility 제약 + 굽힘 모드 동시 표현 부족 | P2 또는 Taylor-Hood mixed. 상용: C3D8H/C3D20H 같은 hybrid 요소 | W2-P3a |
| Gmsh `setOrder(2)` 가 180° 호에서 실패 | `addCircleArc(p_start, c, p_end)` 의 short-way 한계 (≤ π) | 두 90° 호로 split (top point 중간 추가) | W2-P3a |
| Plane strain 에서 3D NH 식 못 씀 | `F_2D` 만 쓰면 out-of-plane stretch 정보 없음 | `as_tensor` 로 명시적 3×3 embedding, out-of-plane = 1 | W2-P3a |
| `dirichletbc(Function, dofs, V)` TypeError | sub-space 가 아닌 일반 V 에 4th-arg V 전달 | 일반 공간: `dirichletbc(Function, dofs)` (2-arg). sub-space: `dirichletbc(Function, dofs, sub)` (3-arg) | W2-P3a |
| 비다항식 form (NH `ln J`, Ogden `λ^α`) 솔버 60-134× slowdown | UFL/FFCX가 polynomial degree 추정 실패 → 보수적 high `q` (≥ 8) 채택 | `dx_q = ufl.dx(metadata={"quadrature_degree": 2*degree})` 명시. P2면 q=4 default starting point. 정확도 회귀 테스트로 q 상향 결정. [[fenicsx_speed_analysis]] §5 | W2-P1·이후 모든 솔버 |
| `XDMFFile.write_function` Runtime Error "degree of output Function must be same as mesh degree" | mesh degree=1 (P1 geom) + 함수 degree=P2 mismatch | P1 공간으로 interpolation 후 저장: `V_out = functionspace(dom, ("Lagrange", 1, shape))`; `u_out.interpolate(u_p2)` | W3-P1 |
| Cauchy ↔ PK1 수동 변환 (작은 사례에서 정합 안 됨) | UFL `derivative(Pi, u, v)` 가 **자동으로 PK1 잔차** 생성 (Total Lagrangian) | 약형식·솔버에는 그대로 `derivative(Pi, u, v)` 사용. **Cauchy 는 후처리 전용** $\sigma = (1/J)\,\partial\Psi/\partial F \cdot F^\top$ 한 줄 별도 (`cauchy_NH(F_el, mu, lam)` 헬퍼) | W4-P1 |
| 4-inch Si + σ=500MPa 입력으로 R=7.7m 결과 (사용자 직관과 다름) | 구두 정보 만으로 셋업, 실측 doc 자료 미읽음 → h_s, σ, ΔT 모두 잘못 | **doc 1차 자료 read 후 입력값 확정**. K_Stoney invariant check + R/L 비율 reasonable check가 빠른 진단 도구. [[verification]] | W3-P3 v1→v2 |
| Finite strain vs small strain 2.5% κ 차이 — 코드 버그? | strain ~10⁻³ 영역에서 의외로 큰 차이 | **Small-strain limit test**: 모든 미스매치 ×0.01 → ratio·slope 측정. quadratic (slope ≈ 2) → finite strain geometric nonlinearity (membrane-bending coupling), 코드 정확. [[verification]] | W4-P1 v1 |

> 추가 누적 cheatsheet (학습 sprint 2026-05): [[mesh]] (Gmsh, custom stitched), [[axisym_residual]] (axisymmetric kinematics, 3D Hooke, eigenstrain, multiplicative F), [[verification]] (실험매칭·부호 통일·limit test), [[petsc]], [[mapping]]
