# 환경 동기화 검증 체크리스트

부트스트랩(`docs/NEW-PC-BOOTSTRAP.md`) 완료 후 모든 구성 요소가 동작하는지 확인. 항목별 1줄 명령으로 빠르게 OK/NG 판정.

## 1. 시스템 의존성

| 항목 | 확인 명령 | 기대 |
|---|---|---|
| Git | `git --version` | `git version 2.x` 이상 |
| Node.js | `node --version` | `v20.x` 또는 `v24.x` |
| Python | `python --version` | `Python 3.10` 이상 |
| Java | `java -version` 2>&1 | `openjdk 21` |
| Claude Code CLI | `claude --version` | `2.x.x` |

## 2. 글로벌 npm 패키지

```bash
npm list -g --depth=0
```

| 항목 | 확인 |
|---|---|
| `@anthropic-ai/claude-code` | 존재 |
| `@tobilu/qmd` | 존재 (vault 검색 시 필요) |
| `pnpm` | 존재 |
| `dev-browser` | 존재 |

## 3. Python 패키지 (핵심 13종)

```bash
python -m pip list | grep -iE "opendataloader|python-hwpx|lxml|pandas|google-genai|pillow"
```

| 항목 | 사용 스킬 |
|---|---|
| `opendataloader-pdf` | pdf-to-md |
| `python-hwpx` | hwpx, tor, purchase-requisition |
| `lxml` | hwpx-xml |
| `pandas` / `numpy` / `matplotlib` | patent-strategy-* |
| `google-genai` | visual-generator slide rendering |
| `pillow` | visual-generator |
| `uv` | 다수 스킬의 venv 관리 |

## 4. ~/.claude/ 구조

```bash
ls ~/.claude/
```

| 파일/디렉토리 | 확인 |
|---|---|
| `settings.json` | 존재; `extraKnownMarketplaces`의 경로가 실재 |
| `CLAUDE.md` | 14 KB 가량 |
| `skills/` | 25+ 디렉토리 (`abstract-evaluation`, `pdf-to-md`, ... 포함) |
| `commands/` | 8개 .md (abstract, citation-network, …, research-gap) |
| `plugins/installed_plugins.json` | bkit, playwright, my-tools 플러그인 등록됨 |

## 5. 외부 marketplace clone 상태

```bash
for d in honeypot oh-my-claudecode Claude-Patent-Creator korean-law-mcp; do
    [[ -d ~/$d/.git ]] && echo "OK $d" || echo "MISSING $d"
done
```

(Windows PowerShell):
```powershell
@("honeypot","oh-my-claudecode","Claude-Patent-Creator","korean-law-mcp") | ForEach-Object {
    if (Test-Path "$env:USERPROFILE\$_\.git") { "OK $_" } else { "MISSING $_" }
}
```

## 6. 활성 플러그인

Claude Code 세션에서:
```
/plugins
```

다음 7개가 enabled여야 함:
- skill-creator@claude-plugins-official
- hwpx-generator@honeypot
- visual-generator@honeypot
- patent-trend-analyzer@honeypot
- oh-my-claudecode@omc
- investments-portfolio@honeypot
- claude-patent-creator-standalone@claude-patent-creator

## 7. 슬래시 명령 동작

Claude Code 세션에서 `/`만 입력 → 자동완성 메뉴에 다음이 보여야 함:
- `/abstract`, `/citation-network`, `/cite-verify`, `/journal-match`,
- `/lit-search`, `/peer-review`, `/report-template`, `/research-gap`
- 플러그인 제공 명령들 (`/standup`, `/wrap-up`, `/dump`, `/loop`, `/schedule` 등)

## 8. 스킬 트리거 테스트

각 스킬은 키워드로 자동 트리거. 빠른 ping:

| 트리거 발화 | 기대 동작 |
|---|---|
| "PDF를 MD로 변환해줘" | `pdf-to-md` 스킬 자동 invoke |
| "초록 평가" | `abstract-evaluation` 스킬 invoke |
| "한글 보고서 만들어줘" | `hwpx` 스킬 invoke |
| "출장계획서" | `overseas-trip-plan` invoke |
| "특허 분석 보고서" | `patent-strategy-pro`/`patent-strategy-report` 후보 제시 |

## 9. MCP 서버

```bash
claude mcp list
```

| 서버 | 기대 |
|---|---|
| oh-my-claudecode (`t`) | active |
| playwright | active |
| bkit | active |
| korean-law | active (Step 6 등록 후) |
| notebooklm | active (Step 7 nlm login 후) |
| claude.ai gmail/calendar/drive | 사용 시 OAuth 자동 트리거 |

## 10. apply-config dry-run

설정 파일이 손상돼 보일 때 진단:
```bash
python ~/my-tools/claude-config/apply-config.py --dry-run
```

기대 출력:
```
[apply-config] USER_HOME       = ...
[apply-config] USER_HOME_BS    = ...
[apply-config] USER_HOME_POSIX = ...
[apply-config] DRY RUN -- no files will be written
[apply-config] settings.json: rendered + JSON-valid
[apply-config] CLAUDE.md: would copy from ...
[apply-config] command -> abstract.md
... (8 commands)
[apply-config] done.
```

## 11. Vault (선택)

```bash
ls ~/LLM_wiki/.git
```

별도 git repo이므로 부트스트랩과 무관. 사용자 본인 vault repo URL로 clone.

## 합격 기준

- **MUST**: 1~7번 모두 OK. (없으면 부트스트랩 재시도)
- **SHOULD**: 8~10번 OK. (한두 개 NG는 사용 빈도 따라 무시 가능)
- **OPTIONAL**: 11번. (vault 미사용 시 skip)

## NG 발생 시

1. `docs/NEW-PC-BOOTSTRAP.md`의 "트러블슈팅 빠른 참조" 표 확인
2. 해당 Phase 산출물의 README 확인 (`bootstrap/`, `claude-config/`, `mcp/`)
3. `apply-config.py --dry-run`으로 설정 진단
4. 그래도 막히면: `git log --oneline -- snapshots/` 확인 후 가장 최근 동작 PC와 비교
