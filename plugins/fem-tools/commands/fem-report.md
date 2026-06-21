---
description: FEM 해석 결과 디렉터리를 Obsidian 보고서(문제그림→결과→검증표→한계)로 초안 (FEniCSx 전용)
---

# /fem-report — FEM 보고서 초안

FEniCSx/dolfinx 해석 결과 dir을 **fem-report** 스킬로 Obsidian 보고서(.md)로 초안한다.

## 동작
1. `fem-report` 스킬을 로드하고 `templates/fem_report.md`를 사용한다.
2. **문제 설명 그림 먼저** → FEM 방법 → 결과 그림 → 검증표(`fem-verify`) → 핵심 메시지 → 한계.
3. frontmatter(status·tags), 수식 LaTeX, `![[...png]]` 참조, `<단계>_report.md` 명명.
4. 검증표 없으면 "초안(미검증)"으로 표시.

> FEM/FEniCSx 해석 보고서 전용.

입력: `$ARGUMENTS` (결과 dir `results/<단계>` + 단계 ID).
