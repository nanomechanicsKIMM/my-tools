---
title: Verification / 검증 치트시트 — FEM 결과 검산·매칭·진단
date: 2026-05-28
tags:
  - FEM
  - FEniCSx
  - verification
  - validation
  - debugging
  - cheatsheet
status: active
---

# Verification 치트시트

> FEM 솔버 작성 후 결과 검증·실험 매칭·트랩 진단을 위한 도구 모음.

## 목차

- [부호 규약 통일 (sign convention)](#부호-규약-통일-sign-convention)
- [실험 매칭 (doc 1차 자료 우선)](#실험-매칭-doc-1차-자료-우선)
- [Small-strain limit test (nonlinearity 진단)](#small-strain-limit-test-nonlinearity-진단)
- [Invariant constant check (셋업 1차 검증)](#invariant-constant-check-셋업-1차-검증)
- [PyVista 시각화 트랩](#pyvista-시각화-트랩)
- [Verification 체크리스트](#verification-체크리스트)

## 부호 규약 통일 (sign convention)

해석해 (closed-form formula) 의 부호 규약은 source마다 다름 (Timoshenko vs Hyer vs Stoney). **FEM 좌표·BC·변위 규약에 맞춰 한 번 통일** 하는 게 매번 abs() 우회보다 디버깅·시각화에 명확.

### 예시 (W3-P1 bimetal):

원논문 Timoshenko 1925: $\kappa = 6(\alpha_2 - \alpha_1) \Delta T \cdot \ldots / \ldots$  
FEM 좌표 규약: $\alpha_1$ (top) > $\alpha_2$ (bot) + $\Delta T > 0$ ⇒ ∩ 모양 ⇒ bottom midspan up ⇒ $\delta_y > 0$ ⇒ $\kappa_{\rm FEM} > 0$

**해결**: 원식 $(\alpha_2 - \alpha_1)$ 을 **$(\alpha_1 - \alpha_2)$** 로 코드에서 뒤집어 부호까지 매칭. 비교는 단순 `rel.err = (kFEM - kT) / kT * 100` 한 줄.

```python
def timoshenko_curvature(*, alpha1, alpha2, ...):
    """본 코드 규약: FEM δ_y > 0 ↔ κ > 0. 원식 부호 뒤집어 매칭."""
    num = 6.0 * (alpha1 - alpha2) * deltaT * (1 + m)**2  # ← 원식은 (α₂-α₁)
    den = h * (3*(1+m)**2 + (1+m*n)*(m**2 + 1/(m*n)))
    return num / den
```

> **트랩**: 문헌·교과서·논문의 closed-form 식은 좌표 규약·기호 정의가 각자 다름. **첫 비교에서 부호 한 번 통일** > 매번 abs() 우회.

## 실험 매칭 (doc 1차 자료 우선)

사용자 구두 정보 (대략값, 메모리 회상) 만 기반으로 솔버 셋업하면 잘못된 가정 누적. **doc/실험 보고서 1차 자료를 가장 먼저 read** 후 입력값 확정.

### W3-P3 v1→v2 트랩 (실제 사례)

| 항목 | v1 (구두 정보) | v2 (doc 실측) |
|---|---|---|
| Wafer | 4-inch Si | **2-inch Si** |
| h_s | 0.5 mm | **280 μm** |
| σ_residual | +500 MPa 단일 | **case별 215/212/148** |
| ΔT | -200 K (cooling) | **0 K (RT 증착)** |
| 결과 R | 7.7 m | 12-27 m |
| 사용자 직관 | "R 예상보다 작다" | reasonable |

⇒ doc/(20260317) 보고서 read 후 모든 입력값 수정 → 실측 매칭 ≤ 4%.

### 검산 단계 (Reasonable check)

| 검산 | 조건 | 대상 |
|---|---|---|
| **R 값 vs domain scale** | R/L 또는 R/R_wafer 비율이 expected range 안? | bimetal beam, wafer 곡률 |
| **wafer bow vs h_s** | bow가 wafer thickness 의 1-5%면 small strain 안전 | Stoney case |
| **σ 값 vs material strength** | 박막 σ < yield/strength? | metal stressor |
| **F = σ·h_f vs Ni target** | 박리 driving force 비교 | Cr stressor |

## Small-strain limit test (nonlinearity 진단)

비교 차이가 작을 때 (≤ 5%) 그것이 **실제 nonlinearity 인지 또는 코드 버그인지 진단** — strain magnitude scaling으로 order 측정.

### 절차

1. baseline 케이스 풀이 → 차이 Δ_baseline 측정
2. 모든 미스매치 (σ, ΔT, ε 등) 를 **× 0.01** 스케일로 줄임 → Δ_small 측정
3. **비율 R = Δ_baseline / Δ_small** 측정
4. log scale slope: `slope = log(R) / log(100)`

| Slope | 의미 |
|---|---|
| ≈ 0 | constant offset (코드 버그 또는 systematic error) |
| ≈ 1 | linear nonlinearity (1차 효과) |
| ≈ 2 | **quadratic geometric coupling** (finite strain 표준) |
| > 2 | higher-order nonlinearity |

### 예시 (W4-P1 v1, v2):

| 셋업 | baseline Δκ | × 0.01 Δκ | R | slope | 진단 |
|---|---|---|---|---|---|
| v1 (ΔT=-200K) | 2.49% | 0.001% | 2553 | **1.7** | finite strain geometric coupling (substrate membrane-bending) |
| v2 (RT, ΔT=0) | 0.013% | 0.0053% | 2.4 | 0.19 | noise level (no thermal contraction = no coupling) |

⇒ v1의 2.5% 차이가 코드 버그가 아닌 **substrate thermal contraction** 의 finite strain 효과임을 v2 cross-check로 확정.

```python
# Small-strain limit test 코드 패턴
res_base = solve(**p_baseline)
p_small = {k: v * 0.01 if k in ('deltaT', 'sigma_intrinsic') else v
           for k, v in p_baseline.items()}
res_small = solve(**p_small)
rel_base = (res_base['kappa'] - kS_base) / kS_base * 100
rel_small = (res_small['kappa'] - kS_small) / kS_small * 100
ratio = abs(rel_base) / abs(rel_small)
slope = np.log(ratio) / np.log(100)
print(f"baseline {rel_base:.3f}%, small {rel_small:.5f}%, slope {slope:.2f}")
```

## Invariant constant check (셋업 1차 검증)

새 솔버 작성 시 **invariant constant** (K, modulus 등) 를 입력으로부터 재계산해 보고서 명시값과 비교 → 빠른 셋업 검증.

### 예시 (Stoney K = M_s h_s²/6):

```python
# 보고서 §1.1 K = 2358 Pa·m² (Si 2-inch 280μm)
K_FEM = E_s / (1 - nu_s) * h_s**2 / 6
print(f"K_FEM = {K_FEM:.2f}, 보고서 = 2358 Pa·m²")
# 일치 < 0.1% → (E_s, ν_s, h_s) 입력 OK
# case별 σ 입력 → F 결과는 자동으로 보고서와 일치 (Stoney back-calc 역과정)
```

다른 invariants:
- Stoney K = M_s h_s²/6 (박막 잔류응력)
- D = Eh³/[12(1-ν²)] (plate bending rigidity)
- E_b = E h /(1-ν²) (membrane stretching stiffness)

> **best practice**: 새 셋업 첫 case는 invariant check 만 통과시키고 본 계산 진입. 셋업 오류를 case 1에서 잡으면 sweep 다시 안 함.

## PyVista 시각화 트랩

### T1. 두께 비 200×인 박막+기판

박막 0.5 μm + 기판 100 μm → 전체 view에서 박막은 1% 차지, 핫스팟 가시화 어려움.

**해결 옵션**:
1. **Corner zoom-in plot** 별도 (e.g., $x \in [40, 60]$ μm, $z \in [95, 102]$ μm)
   ```python
   plotter.camera.focal_point = (x_center, z_center, 0)
   plotter.camera.parallel_scale = view_height / 2
   plotter.enable_parallel_projection()
   ```
2. **변형 over-warp**: `warp_by_vector(scale=N)` 으로 박막 변형 시각적 과장
3. **Cr/PDMS 별도 plot**: filter by cell tag, 각각 zoom

### T2. cmap 선택 (low-value visibility)

- `"hot"`, `"viridis"`: vM ≈ 0 영역이 dark (PDMS의 substrate 응력 ~0.5 MPa 보이지 않음)
- `"plasma"`, `"inferno"`: 약간 더 visible at low
- `clim=[0.1, vM_max]` 으로 0 cutoff 설정 가능

### T3. mathtext 한계 — Greek 문자

`add_text()` 에서 σ, κ 등 mathtext가 일부 환경에서 "_" 로 표시. 명시적 `\\sigma`, `\\kappa` 또는 영문 대체 ("sigma", "kappa") 권장.

### T4. PyVista vs VTK Camera API 차이

PyVista 새 API:
- `plotter.camera.focal_point = (x, y, z)`
- `plotter.camera.parallel_scale = h`
- `plotter.enable_parallel_projection()`

VTK old style (`SetFocalPoint`, `SetParallelProjection`) 일부 호환되나 PyVista 명시 권장.

## Verification 체크리스트

새 솔버 / 새 케이스 진입 시:

```
□ 1. doc/실험 보고서 1차 read → 입력값 확정
□ 2. Invariant constant (K, D, E_b 등) FEM vs 보고서 0.1% 일치
□ 3. 작은 deformation case 먼저 (linear regime) → 해석해 비교
□ 4. 부호 규약 closed-form vs FEM 통일
□ 5. R 값 / strain 크기 reasonable (R/L, strain/material 비교)
□ 6. Mesh refinement 2-3 단계 → 솔루션 수렴 확인 (deviation은 수치 vs 물리 진단)
□ 7. Biaxial 가정 자동 검증 (σ_zz_film ≈ 0)
□ 8. 부수 결과 (Newton iter, KSP residual) 합리적
□ 9. Sweep (parameter variation) — trend 물리적 의미
□ 10. Small strain limit test (≤ 5% 차이 진단)
```

## 출처

- W1-W4 모든 미니프로젝트 (특히 W3-P1 부호, W3-P3 v1→v2, W4-P1 small strain limit)
- doc/(20260317), doc/(20260414) 실험 보고서
- doc/fenicsx_speed_analysis.md
