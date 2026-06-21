---
name: fem-cheatsheet
description: FEniCSx/dolfinx 유한요소해석의 누적 함정 레퍼런스를 컨텍스트에 주입하는 스킬. UFL·메쉬·축대칭 잔차·매핑·검증·PETSc 작업 중 '체적 locking', 'quadrature aliasing', '축 hoop nan', 'GAMG 축대칭', 'MUMPS', 'quadrature_degree', 'dolfinx 함정', 'FEM cheatsheet' 등이 언급되면 사용. FEM 작업 전용.
---

# FEM Cheatsheet — 함정 레퍼런스 라이브러리 (FEniCSx 전용)

FEniCSx/dolfinx 해석에서 반복 발생한 함정을 주제별로 정리한 **일반 레퍼런스**다.
구현·디버깅 전 해당 파일을 읽어 같은 함정의 재발을 막는다.

> **레퍼런스 표기 안내**: `references/*.md`의 우측 출처 태그(`W*-P*`, `S*` 등)와 일부 재료(예: PDMS·SMA·Cr)는 **저자 프로젝트에서 어떤 케이스로 그 교훈을 얻었는지 보여주는 예시**다. **기법 자체는 임의의 dolfinx 문제에 일반 적용**되며, 특정 문제로 적용 범위를 한정하지 않는다.

## 사용 시점
- `fem-implementer` 에이전트가 구현 시작 시 해당 주제 파일을 읽는다.
- 발산·이상결과 디버깅 시 증상→파일 매핑으로 진단한다.
- **FEM/FEniCSx 작업에만 사용한다.** 일반 코딩 함정 자료가 아니다.

## references/ 파일 맵 (주제 → 파일)

| 파일 | 다루는 함정(일반) |
|---|---|
| `references/ufl.md` | UFL 약형식·자동미분·`quadrature_degree` 명시·비매끄러움 미분가능 처리 |
| `references/mesh.md` | Gmsh·메쉬태그·경계층/특이점 refinement·다층 stitched 메쉬·cell connectivity NaN |
| `references/axisym_residual.md` | 축대칭 3D Hooke + hoop `ε_θθ=u_r/r` + `r·dx`, r=0 특이, plane stress λ 오용 |
| `references/mapping.md` | ABAQUS/ANSYS↔dolfinx 요소·재료·BC 매핑, shear locking, DG0 per-cell 물성 |
| `references/verification.md` | 해석해·MMS·수렴·극한·평형 검증 패턴 |
| `references/petsc.md` | 직접해(MUMPS LU)·KSP+AMG·전제조건자 선택·강스케일링 측정 |

## 핵심 함정 요약 (일반)
1. **초기 횡강성≈0인 평막/박판** → 첫 하중 step 미소, 적응 하중증분 필수.
2. **quadrature 내부변수 자기참조 aliasing**(경로의존 재료) → 임시함수 경유. quadrature 함수는 자기 quad point에서만 평가.
3. **축대칭 r=0 hoop 특이($1/r$) → nan** → 근축 샘플(예: r≈0.02~0.04·R).
4. **거의비압축 체적 locking**(ν→0.5) → mixed u-p Taylor-Hood. 변위전용은 과강성.
5. **적응증분 하한 `min_dp`가 초기 dp와 같으면** 첫 실패 시 즉시 종료(빈 결과) → `min_dp ≪ 초기 dp`.
6. **`quadrature_degree` 미명시** → 비다항식 form에서 FFCX auto-degree 과대추정 → 큰 감속. form 차수에 맞게 명시.
7. **권장 솔버/병렬도 문제별 검증**: 전제조건자(예: 축대칭에서 기하 AMG 부적합)·강스케일링은 가정 말고 측정.

> 원본 동기화: 저자 작업폴더 `cheatsheet/`. 새 함정 발견 시 원본 갱신 후 이 references/로 복사.
