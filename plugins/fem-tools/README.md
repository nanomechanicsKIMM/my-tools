# fem-tools

**FEniCSx/dolfinx 유한요소해석 범용 도구 모음.** 정식화 설계 → 구현 → 검증 → 보고의 FEM 워크플로우를, 작성과 검증을 분리한 역할별 에이전트와 재사용 스킬로 자산화한다.

> 적용 범위는 **임의의 FEniCSx/dolfinx 유한요소문제**(선형/비선형 고체·열·유체·다물리, 정적/동적, 접촉·소성·상변태 등)다. 문서 곳곳의 구체 사례(예: Stoney·shear-lag·접촉·SMA)는 **예시**일 뿐 적용 범위를 한정하지 않는다.
>
> **범용(비-FEM) 사용 금지.** 모든 에이전트는 SCOPE GUARD로 비-FEM 과업을 거부하고 OMC 기본 에이전트로 안내한다.

## 구성

### 에이전트 (OMC 원본 기반, FEM 도메인 한정)
| 에이전트 | OMC 기반 | 역할 | 모델 |
|---|---|---|---|
| `fem-formulator` | `architect` (READ-ONLY) | 정식화·솔버·검증전략 설계 (comet-fenicsx/dolfinx-tutorial 패턴) | opus |
| `fem-implementer` | `executor` | solver/plot/diagram 구현 (quadrature 명시·적응증분·자동 Jacobian) | sonnet (복잡 시 opus) |
| `fem-verifier` | `verifier` | 해석해·수렴·극한 증거 수집 (별도 lane, self-approve 금지) | opus |

### 스킬
| 스킬 | 기능 |
|---|---|
| `fem-cheatsheet` | dolfinx 함정 트랩 라이브러리 주입 (`references/{ufl,mesh,axisym_residual,mapping,verification,petsc}.md`) |
| `fem-verify` | 7항목 검증 체크리스트 → 표준 검증표 (`analytic_solutions.md` 벤치마크 인덱스 + 표 템플릿) |
| `fem-report` | `results/<단계>` → Obsidian 보고서 초안 (문제그림→결과→검증표→한계) |
| `fem-sweep` | 파라미터 스윕 JSON → 백그라운드 병렬 → 수집 → 곡선 |

### 커맨드
`/fem-verify`, `/fem-report`, `/fem-sweep` — 각 스킬 진입점.

## 표준 워크플로우
```
fem-formulator(설계) → fem-implementer(구현, fem-cheatsheet 주입) → fem-verifier(검증, 별도 lane) → fem-report(보고)
                                          ↑ 스윕은 fem-sweep로 병렬 fan-out
```
핵심 원칙: **레퍼런스(comet-fenicsx/dolfinx-tutorial) 먼저 → 가정 명시 → quadrature_degree 명시 → 적응증분 → 2~3개 독립 검증 → 정직 보고(fail loud).**

## 의존성
이 플러그인은 **FEniCSx/dolfinx 런타임을 직접 호출**한다. 실행에는 dolfinx·PETSc(MUMPS)·MPI·gmsh·pyvista·matplotlib 등이 필요하다. **dolfinx는 pip 풀스택 설치가 어렵고 conda-forge/Docker가 권장**된다. 설치·인터프리터 탐지·플랫폼 주의는 **[`DEPENDENCIES.md`](./DEPENDENCIES.md)** 참조.

## 골격 상태 (1차)
- 에이전트 3종·스킬 SKILL.md·템플릿·트랩 라이브러리 완료.
- `fem-verify`/`fem-sweep`의 Python 러너는 **stub** — 실해석에서 점진 추출(skillify).

## 비고
- `shared/fem_figures.py`, `skills/fem-cheatsheet/references/*.md`는 저자 작업폴더에서 **복사**된 자산(포터블). `references/`의 사례 ID(`W*-P*`/`S*`)·일부 재료명은 교훈 출처를 보여주는 **예시 태그**이며 기법은 일반 적용된다. `fem_figures.py`의 한글 폰트(`AppleGothic`)는 macOS 예시 — 타 OS에선 교체.
