# 새 PC 부트스트랩 가이드

zero→full Claude Code 환경을 약 30~60분 안에 재현. 본 문서는 단일 페이지로 끝까지 따라할 수 있도록 구성한다.

> **전제**: Windows 10/11 또는 macOS 또는 Debian/Ubuntu 계열 Linux. 인터넷 연결과 관리자 권한 필요.

## TL;DR (요약 명령 시퀀스)

### Windows (PowerShell, 관리자 권장)

```powershell
git clone https://github.com/nanomechanicsKIMM/my-tools.git $env:USERPROFILE\my-tools
cd $env:USERPROFILE\my-tools
.\bootstrap\install-prereqs.ps1            # OS deps
# --- 새 터미널 열기 (PATH 갱신 반영) ---
.\bootstrap\clone-marketplaces.ps1          # 외부 marketplace + korean-law-mcp
.\setup.ps1                                  # skills + plugins + commands + apply-config
# --- Claude Code 재시작 ---
# Tier C/D 인증은 mcp/setup-mcp.md 참조
```

### macOS / Linux (bash)

```bash
git clone https://github.com/nanomechanicsKIMM/my-tools.git ~/my-tools
cd ~/my-tools
./bootstrap/install-prereqs.sh
# --- 새 터미널 열기 ---
./bootstrap/clone-marketplaces.sh
./setup.sh
# --- Claude Code 재시작 ---
# Tier C/D 인증은 mcp/setup-mcp.md 참조
```

## Step 1. Repository clone

```bash
git clone https://github.com/nanomechanicsKIMM/my-tools.git ~/my-tools
cd ~/my-tools
```

Windows: `git clone https://github.com/nanomechanicsKIMM/my-tools.git $env:USERPROFILE\my-tools`

## Step 2. OS-level prerequisites

`bootstrap/install-prereqs.{ps1,sh}` 실행:

설치 항목:
- Git
- Node.js LTS
- OpenJDK 21 (Temurin) — `pdf-to-md` 스킬의 `opendataloader-pdf` 의존성
- Miniconda3 (Python)
- Obsidian (선택)
- npm globals: `@anthropic-ai/claude-code`, `@tobilu/qmd`, `dev-browser`, `pnpm`
- pip: `python-requirements.txt`의 13개 패키지

> **중요**: 설치 후 **반드시 새 터미널을 열어야** PATH 변경이 반영됨. Miniconda 초기화 미완 시 `conda init powershell` 또는 `conda init bash` 1회 실행 후 재시작.

검증:
```bash
git --version
node --version       # v20+ 권장
java -version        # OpenJDK 21
python --version     # 3.10+
claude --version     # Claude Code CLI
```

## Step 3. 외부 marketplace clone

`bootstrap/clone-marketplaces.{ps1,sh}` 실행. idempotent — 이미 존재하면 `git pull --ff-only`만 시도.

clone 대상:
- `~/honeypot` — Claude 플러그인 5개 (hwpx-generator, visual-generator, patent-trend-analyzer, investments-portfolio, …)
- `~/oh-my-claudecode` — OMC 본체
- `~/Claude-Patent-Creator` — 특허 작성 plugin
- `~/korean-law-mcp` — 한국 법령 MCP 서버

검증:
```bash
ls ~/honeypot ~/oh-my-claudecode ~/Claude-Patent-Creator ~/korean-law-mcp
```

## Step 4. 메인 setup

`setup.{ps1,sh}` 실행. 다음을 순차 수행:

1. `install_claude_skills` — `skills/` → `~/.claude/skills/`
2. `install_codex_skills` — `skills/` → `~/.codex/skills/` (Codex 동시 사용 시)
3. `install_commands` — `commands/*.md` → `~/.claude/commands/` (8개 슬래시 명령)
4. 외부 plugin 등록: bkit, playwright + my-tools 로컬 플러그인 (visual-generator, hwpx-tools, patent-tools)
5. `apply_config` — `claude-config/` 템플릿을 `~/.claude/`에 배치 (백업 자동)

> **백업**: 기존 `~/.claude/settings.json`, `CLAUDE.md`는 `<file>.backup-<YYYYMMDD-HHMMSS>` 형태로 보존됨.

## Step 5. Claude Code 재시작

새 스킬·플러그인·명령·설정을 로드하려면 **Claude Code 종료 후 재시작 필수**.

```bash
claude --version  # CLI 정상 응답 확인
claude            # 세션 시작 후 / 입력으로 슬래시 명령 자동완성 확인
```

## Step 6. Korean-law MCP 빌드 + 등록

```bash
cd ~/korean-law-mcp
npm install
npm run build
claude mcp add korean-law -- node "$(pwd)/build/index.js"
```

Windows:
```powershell
cd $env:USERPROFILE\korean-law-mcp
npm install; npm run build
claude mcp add korean-law -- node "$env:USERPROFILE\korean-law-mcp\build\index.js"
```

## Step 7. Tier C/D 인증 (수동, PC당 1회)

전체 절차는 `mcp/setup-mcp.md` 참조. 요약:

| 항목 | 명령 |
|---|---|
| NotebookLM 로그인 | `nlm login` (브라우저 OAuth) |
| Gmail / Calendar / Drive | Claude Code 첫 호출 시 자동 OAuth |
| KIPRIS API 키 | `~/honeypot/plugins/patent-trend-analyzer`의 `patent-mcp-setup` 스킬 안내대로 설정 |
| Gemini API 키 | `setx GEMINI_API_KEY "..."` (Win) / `export GEMINI_API_KEY=...` 후 `~/.bashrc` 추가 |

## Step 8. (선택) Vault clone

Obsidian Vault `LLM_wiki`는 별도 git repository — 사용자 본인 환경 정보 포함이라 my-tools에 포함 안 됨.

```bash
git clone <your-vault-repo> ~/LLM_wiki
```

## 동작 검증

`docs/ENV-SYNC-CHECKLIST.md` 참조.

## 트러블슈팅 빠른 참조

| 증상 | 해결 |
|---|---|
| `winget` not found | Windows 11이 아니면 https://aka.ms/getwinget 에서 설치 |
| `python` 명령 없음 | Miniconda 초기화 (`conda init powershell` 또는 `conda init bash`) → 새 터미널 |
| `claude` 명령 없음 | `npm install -g @anthropic-ai/claude-code` 재실행 |
| `apply-config.py` 한글 깨짐 | Python 3.7+ 확인. cp949 환경에서도 reconfigure로 자동 처리됨 |
| 외부 marketplace 미인식 | `~/.claude/settings.json`의 `extraKnownMarketplaces` 경로가 실재하는지 확인 |
| 슬래시 명령 안 보임 | `~/.claude/commands/`에 8개 .md 파일 존재 확인 + Claude Code 재시작 |
| MCP 서버가 `claude mcp list`에 없음 | `claude mcp add` 명령 재실행 |

## 관련 문서

- [`bootstrap/README.md`](../bootstrap/README.md) — 부트스트랩 스크립트 상세
- [`claude-config/README.md`](../claude-config/README.md) — 설정 템플릿화 메커니즘
- [`mcp/setup-mcp.md`](../mcp/setup-mcp.md) — MCP 서버 인증 절차
- [`docs/ENV-SYNC-PLAN.md`](./ENV-SYNC-PLAN.md) — 7-Phase 마스터 플랜과 진행 로그
- [`docs/ENV-SYNC-CHECKLIST.md`](./ENV-SYNC-CHECKLIST.md) — 동작 검증 체크리스트
