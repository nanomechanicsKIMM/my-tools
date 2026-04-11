# My Tools

Claude Code / Codex용 스킬·플러그인을 한 레포에 모아 두고, **clone 후 setup**으로 여러 PC에 동일한 도구 환경을 구성합니다.

## 포함된 스킬

`skills/` 디렉터리의 독립 스킬. setup 실행 시 `~/.claude/skills/` 및 `~/.codex/skills/`로 배포됩니다.

| 스킬 | 설명 |
|------|------|
| **patent-draft-review** | 출원 전 특허 명세서 초안 TRIZ 진단 + 청구항 구조 + 오탈자·부호 + 요약서 점검 → Obsidian 호환 개선방안 MD 자동 생성 (Phase 0~7 파이프라인, QC-02 재현율 100%) |
| **patent-defence** | 특허 거절이유 통지 분석 → 당소의견안 업데이트내역·메일 초안 자동 생성 |
| **patent-strategy-pro** | RFP 기반 특허 전략 보고서 (세부기술 분해, 공백 분석, OS 매트릭스, IP 창출 전략) |
| **tor** | 한국기계연구원 과업지시서(TOR) HWPX 자동 생성 (10개 섹션 치환) |

## 포함된 플러그인

`plugins/` 디렉터리의 Claude Code 플러그인. setup 실행 시 `~/.claude/plugins/`에 등록됩니다.

| 플러그인 | 버전 | 설명 |
|---------|:----:|------|
| **hwpx-tools** | 1.0.0 | HWPX 문서 생성·편집 툴킷 (hwpx, hwpx-xml, tor 스킬 포함) |
| **patent-tools** | 1.0.0 | 특허 전략 보고서 자동 생성 툴킷 (patent-strategy-pro 스킬 포함) |
| **visual-generator** | 3.0.0 | 문서 → 슬라이드 이미지 자동 생성 파이프라인 (6종 테마, 24종 레이아웃) |

### hwpx-tools 포함 스킬

| 스킬 | 설명 |
|------|------|
| **hwpx** | HWPX 문서 생성·편집 (python-hwpx API, ZIP-level 치환, 보고서/공문 스타일) |
| **hwpx-xml** | HWPX XML 직접 작성 방식 생성·편집 (5종 템플릿: base/gonmun/report/minutes/proposal) |
| **tor** | 과업지시서 HWPX 자동 생성 (루트 skills/tor와 동일) |

### visual-generator 테마

| 테마 | 스타일 |
|------|--------|
| **gov** | 정부·공공기관 PPT |
| **seminar** | 세미나·발표 자료 |
| **concept** | Kurzgesagt 풍 시각 스토리텔링 |
| **pitch** | Apple Keynote 스타일 피치덱 |
| **whatif** | 미래 비전 스냅샷 |
| **comparison** | Before/After 비교 |

> 렌더링(이미지 생성)에는 `GEMINI_API_KEY` 환경변수가 필요합니다. 프롬프트 생성까지만 실행하는 경우 API 없이 사용 가능합니다.

## 새 PC에서 환경 구성

1. **저장소 클론**
   ```bash
   git clone https://github.com/nanomechanicsKIMM/my-tools.git
   cd my-tools
   ```

2. **도구 배포**
   - **Windows**: PowerShell에서 `.\setup.ps1`
   - **Mac/Linux**: `chmod +x setup.sh && ./setup.sh`

   setup 스크립트가 수행하는 작업:
   - `skills/` → `~/.claude/skills/` 및 `~/.codex/skills/`로 복사
   - `plugins/` → `~/.claude/plugins/`에 등록 (marketplace registry 포함)
   - 외부 플러그인 설치: **bkit**, **playwright**

3. **Claude Code / Codex 재시작**
   새 스킬·플러그인을 인식시키기 위해 재시작합니다.

4. **스킬별 의존성** (해당 스킬을 쓸 때만)

   | 스킬 | 의존성 설치 명령 |
   |------|----------------|
   | patent-strategy-pro | `cd skills/patent-strategy-pro/scripts && uv pip install -r requirements.txt` |
   | tor / hwpx-xml | `uv pip install lxml` |
   | visual-generator (렌더링) | `uv pip install google-genai Pillow` + `GEMINI_API_KEY` 설정 |

   > **Windows 환경**: `uv` 패키지 매니저 사용 권장. `PYTHONUTF8=1` 환경변수 설정 필수 (한국어 인코딩)

## 레포 구조

| 경로 | 설명 |
|------|------|
| `skills/` | 독립 스킬 (각 하위 폴더 = 스킬 하나) |
| `plugins/` | Claude Code 플러그인 (각 하위 폴더 = 플러그인 하나) |
| `docs/` | 구성 가이드 등 문서 |
| `setup.ps1` / `setup.sh` | clone 후 한 번 실행해 스킬·플러그인을 배포 |

## 업데이트

- 레포에서 스킬/플러그인을 수정한 뒤 push합니다.
- 다른 PC에서는 `git pull` 후 `.\setup.ps1`(또는 `./setup.sh`)을 다시 실행하고 Claude Code를 재시작합니다.
