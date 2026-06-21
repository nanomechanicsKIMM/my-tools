---
name: fem-report
description: FEniCSx/dolfinx 해석 결과 디렉터리(results/<단계>)를 받아 '문제설명 그림→결과 그림→검증표→한계' 순서의 Obsidian 호환 보고서(.md)를 자동 초안하는 스킬. 'FEM 보고서', 'FEM report', '해석 보고서', 'results 보고서', '검증표 포함 보고서' 등이 언급되면 사용. FEM 해석 보고서 전용.
---

# fem-report — FEM 해석 보고서 초안 (Obsidian .md, FEniCSx 전용)

유한요소해석 결과 dir을 받아 '문제그림 먼저→결과그림→검증표→한계' 순서의 Obsidian 보고서 초안을 만든다.
**임의의 FEM 문제**에 적용된다.

## 사용 시점
- 한 해석 단계가 끝나 결과를 보고서로 남길 때.
- **FEniCSx/dolfinx 해석 보고서에만 사용한다.** 일반 문서 작성은 다른 스킬을 쓴다.

## 입력
- 결과 dir: `results/<단계>/` (`*_setup.png`/`*_diagram.png` = 문제설명, `*_curves.png`/`*_deformed.png`/`*.gif` = 결과)
- (선택) `fem-verify` 검증표, 솔버 로그(Newton 반복·수렴).

## 절차
1. `templates/fem_report.md`를 복사해 frontmatter(status·tags) 채운다.
2. **문제 설명 그림 먼저** 배치 → 문제 정의·가정.
3. FEM 방법(정식화·요소·솔버·증분).
4. **결과 그림/그래프** + 핵심 수치.
5. `fem-verify` **검증표 삽입**(항상 포함).
6. **핵심 메시지** + **한계**(robust/material지배 구분).

## 명명·형식 규칙
- 파일: `<단계>_report.md`. 그림 참조는 Obsidian `![[...png]]`.
- frontmatter `status`·`tags` 필수. 수식은 LaTeX `$...$`/`$$...$$` (`$$` 짝수 확인).
- 비ASCII 라벨 그림은 폰트 설정된 환경에서 생성 가정(DEPENDENCIES.md).
- **검증 전 완료 주장 금지** — 검증표 없는 보고서는 "초안(미검증)"으로 표시.

## 골격 상태
- `templates/fem_report.md` — 보고서 골격(채워짐).
- 그림 자동 수집·삽입 스크립트는 다음 실해석에서 점진 추출(현재 수동 배치).
