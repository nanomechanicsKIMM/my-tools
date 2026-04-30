# Environment Snapshot — DESKTOP-L0USAAE — 2026-04-30

> Phase 1 갭 측정 결과. 새 PC 부트스트랩 시 이 스냅샷이 재현 목표.

## 시스템

| 항목 | 버전 |
|---|---|
| OS | Windows 11 Pro 10.0.22631 |
| Shell | bash (Git Bash) + PowerShell |
| Node.js | v24.13.0 |
| Python (miniconda3) | 3.13.9 |
| Java | OpenJDK 21.0.6 (2025-01-21) |

## ~/.claude/skills/ 인벤토리 (26개)

```
_shared
abstract-evaluation
hwpx
hwpx-xml
layout-types
omc-learned
overseas-trip-plan
paper-review
patent-defence
patent-draft-review
patent-incubation-auto
patent-incubation-interactive
patent-report
patent-report-workspace
patent-strategy-pro
patent-strategy-report
pdf-to-md
purchase-requisition
slide-renderer
theme-comparison
theme-concept
theme-gov
theme-pitch
theme-seminar
theme-whatif
tor
```

## my-tools 커버리지

### skills/ (13)

```
_shared, abstract-evaluation, nrf-tech-survey, overseas-trip-plan,
paper-review, patent-defence, patent-draft-review,
patent-incubation-auto, patent-incubation-interactive,
patent-strategy-pro, pdf-to-md, purchase-requisition, tor
```

### plugins/*/skills/

| 플러그인 | 포함 스킬 |
|---|---|
| hwpx-tools | hwpx, hwpx-xml, tor |
| patent-tools | patent-report, patent-strategy-pro |
| visual-generator | layout-types, slide-renderer, theme-comparison, theme-concept, theme-gov, theme-pitch, theme-seminar, theme-whatif |
| mineru-tools | (skills/ 없음 — pdf 변환만) |

**합집합 (my-tools 전체)**: 22개 스킬

## 갭 분석

### 누락 스킬 (~/.claude에는 있고 my-tools에는 없음)

| 스킬 | 출처 추정 | 처리 |
|---|---|---|
| `omc-learned` | oh-my-claudecode 외부 marketplace에서 자동 생성 | clone-marketplaces로 충당 — my-tools 직접 저장 X |
| `patent-report-workspace` | 사용자 작업 폴더? | 점검 후 결정 |
| `patent-strategy-report` | 별도 스킬 | **my-tools/skills/에 추가 필요** |

### 중복 (skills/ + plugins/*/skills/ 양쪽 존재)

| 스킬 | 위치 |
|---|---|
| `patent-strategy-pro` | skills/ + patent-tools/ |
| `tor` | skills/ + hwpx-tools/ |

→ **결정**: 플러그인에 묶이지 않은 스킬만 루트 `skills/`, 묶인 것은 플러그인에서만 관리하는 단일 source of truth 정책 적용 (Phase 4)

### my-tools에만 있고 현 PC에 없음

| 스킬 | 처리 |
|---|---|
| `nrf-tech-survey` | 의도적 보존 — 다른 PC에서 사용 가능 |

## 외부 Marketplace (clone 대상)

| 디렉토리 | git remote |
|---|---|
| `~/honeypot/` | `https://github.com/orientpine/honeypot` |
| `~/oh-my-claudecode/` | `https://github.com/yeachan-heo/oh-my-claudecode` |
| `~/Claude-Patent-Creator/` | `https://github.com/RobThePCGuy/Claude-Patent-Creator.git` |

> `~/.claude/settings.json`의 `extraKnownMarketplaces`가 위 디렉토리를 가리킴 → bootstrap 단계에서 clone + 경로 매칭 필요.

## Node.js 글로벌 패키지

```
@anthropic-ai/claude-code@2.1.89    ← Claude Code CLI 본체
@tobilu/qmd@2.1.0                    ← Vault semantic search
dev-browser@0.2.7
pnpm@10.33.0
```

## Python 핵심 패키지

```
beautifulsoup4==4.14.3
lxml==5.4.0
matplotlib==3.10.8
numpy==2.4.3
opendataloader-pdf==2.2.1   ← pdf-to-md 의존성
pandas==3.0.1
pillow==12.1.1
pypdfium2==5.6.0
python-hwpx==2.1            ← hwpx, tor, purchase-requisition 의존성
requests==2.32.5
requests-toolbelt==1.0.0
uvicorn==0.44.0
```

> `google-genai`, `defuddle`, `uv`, `playwright`는 grep 결과 미발견 — 필요 시 별도 설치하거나, 사용자가 사용하지 않는 상태일 수 있음. Phase 4에서 스킬별 사용처를 검증.

## ~/.claude/commands/ (8개)

KatmerCode 슬래시 명령:
```
abstract.md, citation-network.md, cite-verify.md,
journal-match.md, lit-search.md, peer-review.md,
report-template.md, research-gap.md
```

→ Phase 2에서 my-tools/commands/로 백업.

## ~/.claude/settings.json 핵심

```json
{
  "permissions": { "allow": [...8 entries...], "defaultMode": "plan" },
  "enabledPlugins": {
    "skill-creator@claude-plugins-official": true,
    "hwpx-generator@honeypot": true,
    "visual-generator@honeypot": true,
    "patent-trend-analyzer@honeypot": true,
    "oh-my-claudecode@omc": true,
    "investments-portfolio@honeypot": true,
    "claude-patent-creator-standalone@claude-patent-creator": true
  },
  "extraKnownMarketplaces": {
    "my-tools": "C:/Users/JHKIM/my-tools",
    "honeypot": "C:/Users/JHKIM/honeypot",
    "omc": "C:/Users/JHKIM/oh-my-claudecode",
    "claude-patent-creator": "C:\\Users\\JHKIM\\Claude-Patent-Creator"
  },
  "effortLevel": "high",
  "theme": "light",
  "skipDangerousModePermissionPrompt": true
}
```

→ `extraKnownMarketplaces`의 절대 경로가 PC 의존적 → Phase 2 템플릿화 필수.

## ~/.claude/CLAUDE.md (개인 글로벌 가이드라인)

크기: 14,520 bytes (대용량). 내용:
- oh-my-claudecode 운영 원칙
- Token Efficiency Rules
- AI Coding Agent Guidelines (Update: 20260315)
- Plan Mode / Subagent Strategy / Task Management

→ Phase 2에서 `claude-config/CLAUDE.md.template`으로 백업 (PC 종속 정보 없음, 그대로 복사 가능).

## 활성화된 플러그인 출처 매핑

| 플러그인 ID | 마켓플레이스 | clone 위치 |
|---|---|---|
| skill-creator | claude-plugins-official | (Anthropic 공식, npm 또는 git) |
| hwpx-generator | honeypot | `~/honeypot/` |
| visual-generator | honeypot | `~/honeypot/` |
| patent-trend-analyzer | honeypot | `~/honeypot/` |
| oh-my-claudecode | omc | `~/oh-my-claudecode/` |
| investments-portfolio | honeypot | `~/honeypot/` |
| claude-patent-creator-standalone | claude-patent-creator | `~/Claude-Patent-Creator/` |

> 주의: `visual-generator`는 `honeypot`에서 활성화되었으나 my-tools/plugins에도 동명의 폴더가 있음. **두 출처가 다른 코드일 가능성** — Phase 4에서 충돌 검증 필요.

## Phase 1 결론 (다음 단계 입력)

1. **Phase 4 누락 스킬 추가 대상**: `patent-strategy-report` (단 1건)
2. **Phase 2 settings 템플릿화 시 placeholder**: `{{USER_HOME}}` (`C:/Users/JHKIM` 치환)
3. **Phase 3 clone-marketplaces 대상**: 3개 외부 repo
4. **Python 의존성**: 위 12개로 충분 (Phase 1 시점). Phase 4 검증 시 추가 항목 발생 가능
5. **검증 미완 항목**:
   - `google-genai` 미발견 — visual-generator 렌더링 미사용 상태?
   - `defuddle` 미발견 — Python 패키지가 아닌 npm CLI일 수 있음
   - `uv` 미발견 — winget 또는 pipx 설치 필요할 수 있음
