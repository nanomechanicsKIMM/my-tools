# My Tools

KIMM 연구 업무(특허 창출·논문·연구행정)를 자동화하는 Claude Code / Codex용 스킬·플러그인 모음.
**clone 후 setup** 한 번으로 여러 PC(Windows/macOS)에 동일한 도구 환경을 구성합니다.

```bash
git clone https://github.com/nanomechanicsKIMM/my-tools.git
cd my-tools
./setup.sh        # Mac/Linux  (Windows: .\setup.ps1)
```

setup은 `skills/`와 각 플러그인의 스킬을 `~/.claude/skills/`·`~/.codex/skills/`에 복사하고, `plugins/`를 `~/.claude/plugins/`에 등록합니다. 이후 Claude Code를 재시작하면 스킬이 인식됩니다. 업데이트는 `git pull` 후 setup 재실행.

> 모든 스킬은 크로스플랫폼 경로(`~`, `$HOME`, `Path.home()`) + `python3` PATH 우선 규약을 따릅니다.
> KIPRIS 등 API 키는 `~/Claude_Work/.env`에 둡니다 (없으면 해당 단계는 degraded 모드로 진행).

---

## 업무 영역별 스킬 카탈로그

### 1. 특허 — 창출 → 출원 전 검토 → 거절 대응 → 전략

발명 아이디어에서 특허청 대응까지의 전체 수명주기를 커버합니다.

```
아이디어 ─▶ patent-incubation-{auto,interactive} ─▶ 발명내용설명서(HWPX)
                     │
출원 초안 ─▶ patent-draft-review ─▶ 개선방안 보고서
                     │
거절이유통지 ─▶ patent-defence ─▶ 당소의견안 업데이트내역 + 메일 초안
                     │
과제 기획  ─▶ patent-strategy-report / patent-strategy-pro ─▶ 특허 landscape·전략 보고서
```

| 스킬 | 기능 | 이렇게 말하면 실행 |
|------|------|------------------|
| **patent-incubation-auto** | 기술분야·해결과제·핵심아이디어만 주면 TRIZ 모순 분석→IFR 도출→KIPRIS·국제 선행조사(자기공지 점검 포함)→특허성 재채점→발명내용설명서 작성→청구항 하드닝→컬러 도면→인용 정합 기계 게이트→등록가능성·사업화 이중 critic→KIMM 직무발명신고서 HWPX까지 완전 자동 생성 | "이 아이디어로 TRIZ 기반 발명내용설명서 자동으로 써줘" |
| **patent-incubation-interactive** | 같은 파이프라인을 각 Phase마다 사용자가 검토·선택·승인하며 진행하는 대화형 버전. 아이디어가 아직 유동적일 때 적합 | "발명 아이디어 단계별로 같이 발전시키자" |
| **patent-draft-review** | 출원 전 명세서 초안(HWPX/MD)을 TRIZ 진단 + 청구항 구조 분석 + 오탈자·도면부호 검출 + 요약서·도면 점검으로 통합 검토, Obsidian 개선방안 MD 생성 | "이 명세서 초안 출원 전에 검토해줘" |
| **patent-defence** | 의견제출통지서·명세서·당소의견안 3종을 교차 분석해 권리 최대화 방향의 업데이트내역과 변리사 회신 메일 초안 생성. 제출 전 심사관 페르소나 critic이 원문 전수 대조·재반박 시뮬레이션 | "이 거절이유통지에 대한 당소의견안 업데이트 도출해줘" |
| **patent-strategy-report** | RFP 마크다운 + Google Patents CSV로 TF-IDF 상관성 점수 기반 상위 특허를 추려 연도·출원인·국가 통계와 핵심특허 10건 분석이 담긴 landscape 보고서(Obsidian MD) 생성 | "이 RFP로 특허 현황 분석 보고서 만들어줘" |
| **patent-strategy-pro** (plugin) | PDF RFP 지원 + 세부기술 분해, 공백기술 분석, Objective-Solution 매트릭스, IP 창출 전략까지 포함한 심층 전략 보고서 | "세부기술 분해와 공백기술까지 IP 전략 보고서로" |
| `_shared` | KIPRIS·Google Patents 공보 PDF 다운로드, EPO OPS 검색 등 특허 스킬 공용 스크립트 (단독 사용 아님) | — |

### 2. 논문·학술 — 문헌 수집 → 변환 → 집필 → 그림 → 리뷰

```
문헌 발견(/lit-search·/research-gap) ─▶ paper-pdf-download(수집) ─▶ pdf-to-md(변환) ─▶ Zettelkasten
집필(/abstract·/academic-humanize) ─▶ figure-polish(그림) ─▶ paper-review·/peer-review·/cite-verify(검증) ─▶ /journal-match(투고)
```

| 스킬 | 기능 | 이렇게 말하면 실행 |
|------|------|------------------|
| **paper-review** | 논문 원고(docx/pdf)를 MD로 변환하고 참고문헌 PDF를 자동 수집한 뒤, 인용 정확성·독창성·초록-결론 정합 등 5개 항목을 심각도(CRITICAL/MAJOR/MINOR)로 리뷰. haiku 분류→sonnet 병렬 PDF 분석→opus 종합의 3단 모델 배정 | "이 논문 원고 리뷰해줘" |
| **paper-pdf-download** | LLM이 직접 못 받는 봇차단·기관구독 저널 PDF를 실제 인증 Chromium 브라우저로 다운로드. 라이브러리 dedup→고속 HTTP(OA)→브라우저 3단 사다리, `(연도 저자) 제목.pdf`로 References 이중 보관. 페이월 우회는 하지 않음 | "이 DOI 목록 논문 PDF 받아줘" |
| **pdf-to-md** | opendataloader-pdf로 PDF를 표·이미지·읽기순서 보존 Obsidian MD로 변환(로컬 결정론). 여러 PDF를 한 호출로 묶어 JVM 비용 절감 | "이 PDF들 마크다운으로 변환해줘" |
| **abstract-evaluation** | 학회 초록 PDF 폴더를 일괄 MD 변환 후 4축(창의성·체계성·난제해결·가중치, 총 4~20점)으로 정량 채점, 순위·통계·그룹 강점이 담긴 Obsidian 보고서 생성 | "IMID 초록들 평가 보고서 만들어줘" |
| **paper-code-reproduce** | 논문 PDF 한 편만으로 figure를 재현. 값 날조를 provenance 태그·missing-info 게이트·instrument 테스트로 차단하고 1:1 고해상도 비교, 3회 실패 시 unprimed critic 교차검증 | "이 논문 Fig.3 코드로 재현해줘" |
| **figure-polish** | matplotlib 과학 도표를 Pretendard 폰트·인쇄 가독 크기·순수 원색 팔레트로 다듬고 편집 가능한 PPTX로 변환. 폰트 외 좌표·데이터 불변 원칙으로 회귀 없음 | "논문 그림 폰트 키우고 pptx로 다듬어줘" |
| **research-prompt** | 막연한 조사 요구를 딥리서치용 1문단 프롬프트(번호 매긴 세부질문 + finding별 출력형식)로 변환 | "이 주제 리서치 브리프 써줘" |
| **teach** | 다세션 학습 워크스페이스(용어집·간격 반복·미션) — 논문·이론 정독 학습 보조 | "/teach로 이 논문 학습하자" |
| **grill-me** | 계획·설계·논리를 소크라테스식으로 심문해 약점 노출 — 제안서·청구항·논문 논리 사전 검증 | "/grill-me 내 제안서 약점 짚어줘" |

**슬래시 커맨드** (`commands/`, KatmerCode 계열은 영문 HTML 보고서 산출):

| 커맨드 | 기능 |
|--------|------|
| `/lit-search` | 질의 변형 3~5개로 Semantic Scholar·OpenAlex 등 병렬 문헌검색 → 관련도 랭킹 |
| `/research-gap` | 문헌 landscape에서 6종 연구 공백(시간·방법·주제·응용·인구·모순) 식별 |
| `/citation-network` | DOI 시드로 인용 네트워크 시각화(HTML, 클러스터·seminal·bridge 논문) |
| `/cite-verify` | 원고의 모든 인용을 CrossRef·S2·OpenAlex로 존재·서지 정확성 검증, 날조 인용 플래그 |
| `/peer-review` | 8기준 1~5점 동료심사 + 누락 참고문헌 탐색 (영문 HTML; 국문 MD 리뷰는 paper-review 스킬) |
| `/abstract` | 원고에서 초록 5변형 생성(구조/비구조/확장/단문/이중언어) |
| `/journal-match` | 원고 프로파일 → 유사 논문 게재지 분포 → 티어별 투고 저널 추천 |
| `/academic-humanize` | 논문·제안서·특허 산출물에서 AI 문체 제거 + 주장-근거 규율 편집 (국문 특화) |
| `/report-template` | 위 HTML 커맨드들이 공유하는 디자인 시스템(규약 문서) |

### 3. 연구행정 — HWPX 공문서 자동 생성

| 스킬 | 기능 | 이렇게 말하면 실행 |
|------|------|------------------|
| **purchase-requisition** | 견적서 PDF + 컨텍스트로 KIMM 구매요구서 부속 양식(규격서 + 용도설명서) HWPX 생성. 자금코드 등 필수값 2회 확인 절차 내장 | "이 견적서로 구매요구서 양식 만들어줘" |
| **overseas-trip-plan** | 국외출장계획서 HWPX 자동 생성 — 기관방문·회담형(meeting)과 학회·전시회형(conference) 2종. conference 모드는 학회 홈페이지 정보 자동 수집 | "Display Week 출장계획서 작성해줘" |
| **nrf-tech-survey** | NRF 미래개척융합 기술수요조사서 HWPX 자동 생성. 심사자 에이전트 8기준 80점 게이트(최대 3회 반복)로 품질 보증 | "NRF 기술수요조사서 작성해줘" |
| **tor** (plugin) | KIMM 과업지시서(TOR) HWPX 자동 생성 (10개 섹션 치환) | "과업지시서 hwpx로 만들어줘" |
| **hwpx** (plugin) | HWPX 문서 생성·편집 엔진 — python-hwpx API, ZIP-level 치환, 보고서/공문 템플릿 | "이 내용 한글 보고서로" |
| **hwpx-xml** (plugin) | HWPX를 XML 직접 작성으로 생성·편집 — 세밀한 서식 제어용, 5종 템플릿(base/gonmun/report/minutes/proposal) | (서식 버그 우회가 필요할 때) |

### 4. 발표·자산관리·기타

| 스킬 | 기능 | 이렇게 말하면 실행 |
|------|------|------------------|
| **frontend-slides** | 무의존성 애니메이션 HTML 프레젠테이션 제작·PPTX 변환·PDF export | "이 내용으로 웹 슬라이드 만들어줘" |
| **pptx-layout-kits** | PptxGenJS 재사용 레이아웃 10종(minimal~datasheet)으로 편집 가능한 네이티브 PPTX 덱을 코드로 생성. 콘텐츠 한 번 작성 후 이름 문자열 하나로 룩 전환, 색 토큰으로 라이트/다크 자동 적응 | "datasheet 레이아웃으로 보고 덱 만들어줘" |
| **pension-review** | DC형 퇴직연금 전 과정 자동화 — KOFIA NAV 수집→분배락 보정→슬롯 추천→forward-pricing 백테스트→부트스트랩 강건성→글로벌 분산→HTML 대시보드 (8단계, 분기 러너 `run_quarterly.py`) | "퇴직연금 포트폴리오 분기 점검해줘" |

## 플러그인

| 플러그인 | 설명 |
|---------|------|
| **hwpx-tools** | HWPX 엔진 툴킷 (hwpx, hwpx-xml, tor 스킬 포함) |
| **patent-tools** | 특허 심층 전략 보고서 (patent-strategy-pro 스킬 포함) |
| **visual-generator** | 문서 → 슬라이드 이미지 자동 생성 (6종 테마·24종 레이아웃, 렌더링에 `GEMINI_API_KEY` 필요) |
| **fem-tools** | FEniCSx/dolfinx FEM 해석 에이전트 |
| **mineru-tools** | MinerU 기반 PDF→MD 변환 커맨드 (표 구조 보존 강함) |

## 스킬별 의존성 (해당 스킬 사용 시에만)

| 스킬 | 의존성 |
|------|--------|
| patent-incubation-* | `requests` (+선택: `scikit-learn`, `fontTools`, `svglib`, `reportlab`, `matplotlib`, Inkscape) · KIPRIS 키 `~/Claude_Work/.env` |
| paper-review | `python-docx`, `PyMuPDF`, `requests` |
| paper-pdf-download | dev-browser CLI (npm), bash (+선택: `UNPAYWALL_EMAIL`) |
| pdf-to-md / abstract-evaluation | Java 11+, `opendataloader-pdf` |
| paper-code-reproduce | `numpy`, `scipy`, `matplotlib` (+`PyMuPDF` 또는 poppler) |
| figure-polish | `matplotlib`, `adjustText`, `python-pptx` (Pretendard 폰트 동봉) |
| hwpx / tor / purchase-requisition 등 HWPX 계열 | `python-hwpx`, `lxml` |
| patent-strategy-report / -pro | `pandas`, `scikit-learn`, `requests`, `beautifulsoup4` |
| pension-review | `pandas`, `numpy`, `openpyxl` |
| pptx-layout-kits | Node.js + `pptxgenjs` 4.x (+선택: LibreOffice·poppler — 이미지 QA용) |
| visual-generator 렌더링 | `google-genai`, `Pillow` + `GEMINI_API_KEY` |

> Windows에서는 `PYTHONUTF8=1` 환경변수 필수(한국어 인코딩). python 호출은 전 스킬 `python3` PATH 우선.

## 레포 구조

| 경로 | 설명 |
|------|------|
| `skills/` | 독립 스킬 (어느 플러그인에도 속하지 않는 것만) |
| `skills/_shared/` | 특허 스킬 공용 스크립트 (KIPRIS·EPO·공보 PDF) |
| `plugins/` | Claude Code 플러그인 (각자 자체 `skills/` 보유 가능) |
| `commands/` | 사용자 슬래시 커맨드 |
| `bootstrap/` | OS 부트스트랩 — winget/brew + npm globals + pip |
| `claude-config/` | `settings.json`·`CLAUDE.md` 템플릿 + apply-config |
| `mcp/` | MCP 서버 등록 가이드 |
| `snapshots/` | PC별 환경 스냅샷 |
| `docs/` | 가이드·개선전략 문서 |
| `setup.sh` / `setup.ps1` | 메인 설치 — skills + plugins + commands + config |

### Source of Truth 정책

- 플러그인에 묶인 스킬은 플러그인 내부에만 보관 (예: `tor` → `plugins/hwpx-tools/skills/tor/`).
- 루트 `skills/`는 독립 스킬만 보관. setup은 루트 → 플러그인 순 복사(플러그인이 이김).
- 유사 스킬 라우팅: "특허 전략 보고서"는 CSV landscape 통계면 `patent-strategy-report`, 공백기술·OS 매트릭스 포함 심층이면 `patent-strategy-pro`. 논문 리뷰는 국문 MD면 `paper-review` 스킬, 영문 HTML 8기준이면 `/peer-review` 커맨드.
