# MCP Server Setup Guide

새 PC에서 MCP 서버를 사용 가능 상태로 만드는 절차. 인증·키는 PC별 수동 단계 — repo에 저장하지 않는다.

전체 인벤토리는 `mcp-servers.json` 참조.

## Tier A — 자동 (확인만 필요)

다음 서버는 해당 플러그인이 활성화되면 자동으로 동작. 별도 인증 없음.

| 서버 | 활성화 방법 |
|---|---|
| `oh-my-claudecode-t` | `setup.{ps1,sh}` 실행 → oh-my-claudecode 플러그인 등록 |
| `playwright` | 동상. setup이 마켓플레이스에서 등록 |
| `bkit` | 동상 |

확인:
```bash
claude mcp list 2>/dev/null   # CLI에서 등록된 MCP 서버 나열
```
또는 Claude Code UI에서 `/mcp` 명령 실행.

## Tier B — 외부 repo clone (no auth)

### korean-law-mcp

```bash
# 1) Clone
git clone https://github.com/chrisryugj/korean-law-mcp.git ~/korean-law-mcp
cd ~/korean-law-mcp
npm install
npm run build

# 2) Register with Claude Code
claude mcp add korean-law -- node "$(pwd)/build/index.js"
```

Windows PowerShell:
```powershell
git clone https://github.com/chrisryugj/korean-law-mcp.git $env:USERPROFILE\korean-law-mcp
cd $env:USERPROFILE\korean-law-mcp
npm install
npm run build
claude mcp add korean-law -- node "$env:USERPROFILE\korean-law-mcp\build\index.js"
```

> Repo URL은 `mcp/mcp-servers.json`의 `korean-law.repo`에 명시.

## Tier C — Interactive auth

### NotebookLM (`nlm`)

`nlm`은 NotebookLM에 접근하는 자동화 CLI. 새 PC에서 한 번 로그인 필요.

```bash
# Install (refer to NotebookLM MCP upstream — pipx / binary release)
# After install, login:
nlm login           # opens Google OAuth flow in browser

# Verify
nlm status

# Register MCP server with Claude Code:
claude mcp add notebooklm -- nlm mcp serve
```

> `nlm login switch <profile>` 로 다른 Google 계정으로 전환 가능.

### claude.ai Connectors (Gmail / Calendar / Drive)

Claude Code 내장 connector — 첫 호출 시 자동으로 OAuth 진행.

1. Claude Code 실행
2. Gmail/Calendar/Drive 도구를 호출하는 명령 실행 (예: "Gmail 받은편지함 확인")
3. 브라우저로 자동 이동, Google 계정 선택
4. 권한 승인 후 Claude Code로 복귀

`~/.claude/mcp-needs-auth-cache.json`에 인증 대기 상태가 캐시됨. 토큰은 이 파일에 저장되지 않으며, Claude 자체 보안 저장소 사용.

> 새 PC에서는 처음 사용 시 자동 OAuth — 사전 작업 불필요.

## Tier D — API 키 / 환경변수

### KIPRIS (patent-trend-analyzer)

특허 검색용. honeypot 플러그인의 `patent-mcp-setup` 스킬이 안내.

1. https://www.kipris.or.kr 에서 API 키 발급
2. 환경변수 또는 플러그인 설정 파일에 등록 (스킬 가이드 참조)
3. Claude Code 재시작

### GEMINI_API_KEY (visual-generator)

slide-renderer가 Gemini API로 슬라이드 이미지 생성.

1. https://aistudio.google.com/apikey 에서 키 발급
2. 환경변수로 설정:
   ```bash
   # bash / zsh
   export GEMINI_API_KEY="..."

   # Windows (PowerShell)
   [Environment]::SetEnvironmentVariable("GEMINI_API_KEY", "...", "User")
   ```
3. 새 터미널에서 `echo $GEMINI_API_KEY` (또는 `$env:GEMINI_API_KEY`)로 확인

## 등록 확인 (전체)

```bash
claude mcp list
# 또는 Claude Code 세션에서:
/mcp
```

기대 결과 (Tier A·B 모두 활성화 시):
```
oh-my-claudecode  (active)
playwright        (active)
bkit              (active)
korean-law        (active)
notebooklm        (active, after login)
```

## 트러블슈팅

| 증상 | 처방 |
|---|---|
| `claude mcp list`에 서버가 없음 | `claude mcp add ...` 명령 재실행. Claude Code 재시작 |
| `nlm login`이 브라우저를 못 엶 | `~/.local/bin/`이 PATH에 있는지 확인. `nlm login switch <profile>` 시도 |
| Gmail OAuth 무한 대기 | Claude Code 종료 → 재시작. 브라우저 쿠키 정리 후 재시도 |
| KIPRIS API 호출 실패 | API 키 만료 여부 확인. 호스트 측 IP 화이트리스트 정책 확인 |
| `claude` 명령 not found | `npm install -g @anthropic-ai/claude-code` (이미 `bootstrap/npm-globals.txt` 포함) |

## 관련 파일

- `mcp/mcp-servers.json` — 머신 판독 인벤토리 (CI 검증용)
- `bootstrap/clone-marketplaces.{ps1,sh}` — Tier B 자동 clone (korean-law-mcp 포함)
- `claude-config/settings.json.template` — Claude Code 설정 (MCP 인증 캐시는 별도 처리)
