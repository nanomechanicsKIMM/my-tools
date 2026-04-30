# Claude Code 환경 동기화 마스터 플랜

> 새 PC에서 현재 PC와 동일한 Claude Code 환경(스킬·플러그인·명령·MCP·설정·의존성)을 재현하기 위한 my-tools 레포 확장 계획서.
>
> **작성일**: 2026-04-30
> **현 PC**: Windows 11 Pro · Claude Opus 4.7 · LLM_wiki Vault

## 1. 현황 진단

### 1.1 my-tools 이미 보유 (truth)

| 영역 | 상태 |
|---|---|
| `skills/` | 13개 (abstract-evaluation 포함) |
| `plugins/` | 4개 (hwpx-tools, mineru-tools, patent-tools, visual-generator) |
| `setup.ps1` / `setup.sh` | skills 복사 + bkit/playwright/local plugin 등록 |
| `docs/` | 구성 가이드 1종 |

### 1.2 갭 (현 PC ⊃ my-tools)

| 카테고리 | 항목 |
|---|---|
| 시스템 | OpenJDK 21, miniconda3, Node.js, Git, Obsidian |
| Python pkg | opendataloader-pdf, lxml, google-genai, Pillow, pyhwpx, defuddle, uv |
| Node pkg | @playwright/mcp 등 |
| 사용자 글로벌 설정 | `~/.claude/settings.json`, `~/.claude/CLAUDE.md` |
| 외부 marketplace | `~/honeypot/`, `~/oh-my-claudecode/`, `~/Claude-Patent-Creator/` |
| 사용자 슬래시 명령 | abstract, citation-network, cite-verify, journal-match, lit-search, peer-review, report-template, research-gap |
| 누락 스킬 | Phase 1에서 측정 |
| MCP 서버 | Gmail, NotebookLM, Korean Law 등 (인증 별도) |

### 1.3 비대상 (절대 커밋 X)

- `.credentials.json`, OAuth 토큰, GEMINI_API_KEY 등 비밀
- `history.jsonl`, `sessions/`, `projects/`, `file-history/`, `telemetry/`, `statsig/`
- 사용자 vault (`LLM_wiki/`)
- 외부 marketplace 코드 자체 (각자 git clone)

## 2. 추가 저장 항목

### 2.1 `bootstrap/` (신규)

| 파일 | 역할 |
|---|---|
| `install-prereqs.ps1` / `.sh` | OS 의존성 (winget/brew/apt) |
| `winget-packages.json` | 선언적 매니페스트 |
| `python-requirements.txt` | pip 통합 의존성 |
| `npm-globals.txt` | npm -g 대상 |
| `clone-marketplaces.ps1` / `.sh` | 외부 marketplace clone |

### 2.2 `claude-config/` (신규)

| 파일 | 역할 |
|---|---|
| `settings.json.template` | 경로 placeholder 적용 |
| `CLAUDE.md.template` | 글로벌 가이드라인 |
| `apply-config.ps1` / `.sh` | 템플릿 렌더링 → `~/.claude/`에 배치 |

### 2.3 `commands/` (신규)

`~/.claude/commands/`의 사용자 슬래시 명령 8개 백업.

### 2.4 `mcp/` (신규)

| 파일 | 역할 |
|---|---|
| `mcp-servers.json` | 메타데이터 (인증 제외) |
| `setup-mcp.md` | OAuth/API key 절차 가이드 |

### 2.5 `scripts/` (신규)

| 파일 | 역할 |
|---|---|
| `diff-skills.ps1` / `.sh` | 누락 스킬 진단 |
| `diff-config.ps1` / `.sh` | settings 비교 |
| `export-snapshot.ps1` / `.sh` | 현 PC 환경 스냅샷 |

### 2.6 `snapshots/` (신규, gitignore 검토)

PC별 환경 dump (`<hostname>-<YYYYMMDD>.md`).

### 2.7 `docs/` 확장

- `NEW-PC-BOOTSTRAP.md`: zero→full 가이드
- `SKILLS-CATALOG.md`: 스킬 트리거·의존성 일람
- `ENV-SYNC-CHECKLIST.md`: 동기화 검증
- `ENV-SYNC-PLAN.md` (이 문서)

## 3. 권장 디렉토리 구조

```
my-tools/
├── README.md
├── CLAUDE.md
├── setup.ps1 / setup.sh
├── bootstrap/                 ★ 신규
├── claude-config/             ★ 신규
├── commands/                  ★ 신규
├── skills/
├── plugins/
├── mcp/                       ★ 신규
├── scripts/                   ★ 신규
├── snapshots/                 ★ 신규
└── docs/
    ├── 도구_레포지토리_구성_가이드.md
    ├── ENV-SYNC-PLAN.md       ← 본 문서
    ├── NEW-PC-BOOTSTRAP.md    ★ 신규
    ├── SKILLS-CATALOG.md      ★ 신규
    └── ENV-SYNC-CHECKLIST.md  ★ 신규
```

## 4. 단계별 실행 계획

### Phase 1 — 갭 정밀 측정 (30분) **✅ 완료 (2026-04-30)**

- [x] `~/.claude/skills/` vs `my-tools/skills/` 비교 → 누락 명단 (단 1건: `patent-strategy-report`)
- [x] `pip list` → 핵심 12개 패키지 식별 (opendataloader-pdf, lxml, python-hwpx 등)
- [x] `npm list -g --depth=0` → 4개 (claude-code CLI, qmd, dev-browser, pnpm)
- [ ] `winget export` → Phase 3에서 winget configure용 매니페스트 생성 시 수행
- [x] 외부 marketplace 디렉토리 `git remote -v` 수집 (3개)
- [x] 결과를 `snapshots/DESKTOP-L0USAAE-20260430.md`에 저장

### Phase 2 — 설정 템플릿화 (30분)

- [ ] settings.json → 템플릿 변환 (placeholder 도입)
- [ ] CLAUDE.md → 템플릿
- [ ] `apply-config.ps1` 작성
- [ ] 슬래시 명령 8개 → `commands/` 복사

### Phase 3 — 부트스트랩 스크립트 (60분)

- [ ] `install-prereqs.ps1` (winget 기반)
- [ ] `clone-marketplaces.ps1`
- [ ] `setup.ps1`/`.sh`에 `install_commands` + `apply_config` 단계 추가
- [ ] idempotency 보장

### Phase 4 — 누락 스킬 보강 (1~2시간)

- [ ] Phase 1 diff 결과 기반 일괄 복사
- [ ] 의존성 통합
- [ ] 플러그인 vs 루트 스킬 source of truth 정립

### Phase 5 — MCP 가이드 (30분)

- [ ] 등록된 MCP 서버 목록 추출
- [ ] 인증 절차 문서화

### Phase 6 — 문서·검증 (1시간)

- [ ] `NEW-PC-BOOTSTRAP.md`
- [ ] `ENV-SYNC-CHECKLIST.md`
- [ ] dry-run 검증

### Phase 7 — 자동화 (선택, 향후)

- [ ] 정기 스냅샷
- [ ] pre-commit hook

## 5. 리스크와 대응

| 리스크 | 대응 |
|---|---|
| Credentials 유출 | `.gitignore` + secret scanner |
| 경로 하드코딩 | 템플릿 + placeholder 렌더링 |
| 마켓플레이스 vendored 코드 | submodule 대신 정식 clone 스크립트 |
| skill 중복 (플러그인 vs 루트) | source of truth 1곳 결정 |
| Win/Mac 호환 | 양 버전 스크립트 |
| MCP 수동 인증 | 자동화 불가 — README 명시 |

## 6. 진행 로그

| 일자 | Phase | 산출물 |
|---|---|---|
| 2026-04-30 | 0 | 본 plan 작성 + 커밋 |
| 2026-04-30 | 1 ✅ | `snapshots/DESKTOP-L0USAAE-20260430.md` — 갭 측정, 외부 marketplace 3개 식별, 누락 스킬 1건 (`patent-strategy-report`) |
