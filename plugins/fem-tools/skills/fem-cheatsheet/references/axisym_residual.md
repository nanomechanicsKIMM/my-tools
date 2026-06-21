---
title: Axisymmetric + 박막 잔류응력 치트시트
date: 2026-05-28
tags:
  - FEM
  - FEniCSx
  - axisymmetric
  - residual-stress
  - eigenstrain
  - Hooke
  - cheatsheet
status: active
---

# Axisymmetric + 박막 잔류응력 치트시트

> W3-P2/P3 + W4-P1 누적. axisymmetric kinematics + 3D Hooke + eigenstrain (thermal·intrinsic) + multiplicative finite strain.

## 목차

- [Axisymmetric kinematics](#axisymmetric-kinematics)
- [3D Hooke (등방 등온)](#3d-hooke-등방-등온)
- [Eigenstrain — thermal vs intrinsic](#eigenstrain--thermal-vs-intrinsic)
- [Multiplicative decomposition (finite strain)](#multiplicative-decomposition-finite-strain)
- [트랩](#트랩)

## Axisymmetric kinematics

회전 대칭: $u_\theta = 0$, 모든 양이 $\theta$ 독립. 변위 $\mathbf u = (u_r, u_z)$, 2D 메쉬 (r, z) 평면.

**Linearized strain (4 성분)**:
$$\varepsilon_{rr} = \partial u_r/\partial r,\quad \varepsilon_{zz} = \partial u_z/\partial z,\quad
\varepsilon_{rz} = \tfrac{1}{2}(\partial u_r/\partial z + \partial u_z/\partial r),\quad
\boxed{\varepsilon_{\theta\theta} = u_r / r}$$

UFL:
```python
def eps_axi(u, r):
    """3x3 strain tensor for axisymmetric kinematics."""
    grad_u = ufl.grad(u)            # 2x2 (u = u_r, u_z)
    e_rr = grad_u[0, 0]
    e_zz = grad_u[1, 1]
    e_rz = 0.5 * (grad_u[0, 1] + grad_u[1, 0])
    e_th = u[0] / r                 # hoop (★ key, r=0 singular handled by BC)
    return ufl.as_tensor([
        [e_rr, e_rz, 0.0],
        [e_rz, e_zz, 0.0],
        [0.0,  0.0,  e_th],
    ])
```

**Finite strain F (3×3)**: hoop = `1 + u_r/r`
```python
def F_axi(u, r):
    grad_u = ufl.grad(u)
    return ufl.as_tensor([
        [1.0 + grad_u[0, 0], grad_u[0, 1],       0.0],
        [grad_u[1, 0],       1.0 + grad_u[1, 1], 0.0],
        [0.0,                0.0,                1.0 + u[0] / r],
    ])
```

**약형식 measure**: $2\pi r\, dr\, dz$. $2\pi$ 약분, **`r·dx`** 사용:
```python
x_sp = ufl.SpatialCoordinate(domain)
r_sym = x_sp[0]
dx_q = ufl.dx(metadata={"quadrature_degree": 2*degree})
a = ufl.inner(sigma, eps_axi(v, r_sym)) * r_sym * dx_q
```

## 3D Hooke (등방 등온)

$$\boldsymbol\sigma = 2\mu\,\boldsymbol\varepsilon + \lambda\,\mathrm{tr}(\boldsymbol\varepsilon)\,\mathbf I_3$$
- $\mu = E / [2(1+\nu)]$ (shear modulus)
- $\lambda = E\nu / [(1+\nu)(1-2\nu)]$ (Lamé 1st parameter, **3D**)

```python
def sigma_iso_3D(eps_3d, E, nu):
    """등방 3D Hooke (★ plane stress 아님, full 3D Lamé)."""
    mu = E / (2.0 * (1.0 + nu))
    lam = E * nu / ((1.0 + nu) * (1.0 - 2.0 * nu))
    return 2.0 * mu * eps_3d + lam * ufl.tr(eps_3d) * ufl.Identity(3)
```

**Plane stress vs 3D 비교**:

| 가정 | $\lambda$ | 적용 |
|---|---|---|
| 3D Hooke | $E\nu/[(1+\nu)(1-2\nu)]$ | axisymmetric, full 3D |
| Plane stress | $E\nu/(1-\nu^2)$ | thin plate (out-of-plane free) |
| Plane strain | 3D Lamé (위와 동일) + $\sigma_{zz}=\nu(\sigma_{xx}+\sigma_{yy})$ | infinite extrusion |

**Stoney 공식의 $(1-\nu_s)$ factor**: 3D Hooke + axisymmetric으로 풀면 plate biaxial modulus $M_s = E_s/(1-\nu_s)$ 가 **자동 발생**. 별도 도입 없이 결과가 Stoney와 일치.

## Eigenstrain — thermal vs intrinsic

**선형 탄성**: $\boldsymbol\sigma = \mathsf{C} : (\boldsymbol\varepsilon - \boldsymbol\varepsilon^{\rm eig})$, eigenstrain은 stress-free reference 변형.

**약형식**:
$$\int_\Omega \boldsymbol\sigma(\boldsymbol\varepsilon(\mathbf u)) : \boldsymbol\varepsilon(\mathbf v)\,dV = \underbrace{\int_\Omega \boldsymbol\sigma(\boldsymbol\varepsilon^{\rm eig}) : \boldsymbol\varepsilon(\mathbf v)\,dV}_{\text{RHS (eigenstrain source)}}$$

### Thermal (3D isotropic)

$$\boldsymbol\varepsilon^{\rm eig}_{\rm thermal} = \alpha \cdot \Delta T \cdot \mathbf I_3$$
모든 3 normal 성분이 같은 값으로 팽창/수축.

### Intrinsic stress (in-plane biaxial only)

Sputter deposition 등 microstructure 기원 — **in-plane만**, z 자유:
$$\boldsymbol\varepsilon^{\rm eig}_{\rm intrinsic} = \begin{pmatrix} -\sigma_{\rm int}/M_f & 0 & 0 \\ 0 & 0 & 0 \\ 0 & 0 & -\sigma_{\rm int}/M_f \end{pmatrix}$$
- $M_f = E_f/(1-\nu_f)$ (박막 biaxial modulus)
- **부호**: σ_int > 0 (tensile film) → ε_eig < 0 (수축 방향)
- z 성분 0 (intrinsic은 deposition 평면 phenomena)

### 합성 (thermal + intrinsic)

```python
eps_planar = alpha_fn * DT + (-sig_int_fn / M_fn)  # thermal isotropic + intrinsic biaxial
eps_zz = alpha_fn * DT                              # thermal only (intrinsic은 z 0)
eps_eigen = ufl.as_tensor([
    [eps_planar, 0.0,       0.0],
    [0.0,        eps_zz,    0.0],
    [0.0,        0.0,       eps_planar],
])
```

DG0 per-cell field로 박막 영역만 σ_int 부여:
```python
sig_int_fn.x.array[is_film] = sigma_intrinsic
sig_int_fn.x.array[~is_film] = 0.0
M_fn.x.array[is_film] = M_film
M_fn.x.array[~is_film] = M_substrate
```

## Multiplicative decomposition (finite strain)

Lee 1969: $\mathbf F = \mathbf F_{\rm el} \cdot \mathbf F_{\rm eig}$
- $\mathbf F_{\rm eig}$ = stress-free reference deformation (eigenstrain)
- $\mathbf F_{\rm el} = \mathbf F \cdot \mathbf F_{\rm eig}^{-1}$
- Neo-Hookean energy on **F_el**: $\Psi(\mathbf F_{\rm el})$

박막 (biaxial + thermal):
```python
lambda_p = 1 + alpha_f * DT - sigma_int / M_f
lambda_z = 1 + alpha_f * DT
F_eig = ufl.as_tensor([[lambda_p, 0, 0], [0, lambda_z, 0], [0, 0, lambda_p]])
F_eig_inv = ufl.as_tensor([[1/lambda_p, 0, 0], [0, 1/lambda_z, 0], [0, 0, 1/lambda_p]])  # diagonal trivial
F_el = F * F_eig_inv
```

기판 (3D isotropic thermal):
```python
lambda_s = 1 + alpha_s * DT
F_eig_sub = lambda_s * ufl.Identity(3)
```

**Cauchy stress on F_el**:
$$\boldsymbol\sigma = \frac{\mu}{J_{\rm el}}(\mathbf B_{\rm el} - \mathbf I) + \frac{\lambda}{J_{\rm el}} \ln J_{\rm el}\,\mathbf I,\quad \mathbf B_{\rm el} = \mathbf F_{\rm el}\mathbf F_{\rm el}^\top$$

## 트랩

### T1. F_axi hoop 성분 = 1 + u_r/r (NOT u_r/r)

Linearized ε_θθ = u_r/r 와 1차 일치하지만 finite strain F 에는 **+1 필수**. 잘못하면 결과 완전히 틀림.

### T2. 3D Hooke vs plane stress (axisymmetric 케이스)

Axisymmetric은 hoop ε_θθ ≠ 0 + σ_zz 자유 → **3D Hooke 필수**.
- plane stress λ_ps = Eν/(1-ν²) 잘못 쓰면 hoop coupling 누락
- Stoney $(1-\nu_s)$ factor 실종 → 큰 deviation
- plane strain 강제는 ε_zz=0 → wafer top/bottom 자유 z-수축 막아 잘못

**핵심**: axisymmetric kinematics ↔ 3D Hooke 는 짝 (W3-P2/P3, W4-P1 모두 적용).

### T3. ε_θθ = u_r/r 의 r=0 singularity

UFL 식에 `u_r/r` 등장하지만:
1. **BC**: r=0에서 `u_r=0` 강제 → 극한 finite
2. **Quadrature point**: P2 Gauss point는 cell 내부, r=0 boundary에 절대 위치 안 함 → r>0
3. **r·dx weighting**: (u_r/r) · r · dx = u_r · dx → r 약분, 적분 안정

⇒ 별도 처리 (max(r, ε) 등) 불요. **predicate-based BC `np.isclose(x[0], 0.0)` 를 r=0에 정확히 주는 게 결정적**.

### T4. Thermal vs intrinsic eigenstrain tensor 형태 차이

| Source | rr, θθ | zz | 잘못 시 결과 |
|---|---|---|---|
| Thermal | α ΔT | α ΔT | (정상) |
| Intrinsic | -σ/M | **0** | isotropic 잘못 주면 σ_zz 발생 → biaxial 깨짐 → Stoney와 큰 deviation |

자체 검증: σ_zz_film ≈ 0 (입력 σ의 < 0.005%) 확인 → biaxial 가정 자동 검증.

## Stoney 공식 (참고)

$$\sigma_f = \frac{E_s h_s^2 \kappa}{6(1-\nu_s) h_f} = \frac{M_s h_s^2 \kappa}{6 h_f}$$

- M_s = E_s/(1-ν_s) (substrate plate biaxial modulus)
- 유효 범위: $h_f/h_s \ll 1$ + $\sigma_f h_f \ll E_s h_s$
- W3-P2 실측 한계: M_f/M_s 비율 ~ 2 일 때 유효 범위 ~ $h_f/h_s \leq 0.004$ (이론 0.05 보다 엄격)

곡률 측정 (axisymmetric, spherical cap approx):
$$\kappa_{\rm FEM} = \frac{2\,u_z(R_{\rm wafer}, 0)}{R_{\rm wafer}^2}$$

## 출처

- W3-P1 (Timoshenko bimetal), W3-P2 (Stoney axisym), W3-P3 v2 (Cr 실측), W4-P1 v2 (finite strain)
- Stoney 1909, Timoshenko 1925, Lee 1969, Bonet-Wood 2008
- jsdokken DOLFINx — Hyperelasticity, axisymmetric examples
