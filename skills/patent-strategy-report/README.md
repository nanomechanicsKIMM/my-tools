# Patent Strategy Report Skill

Claude Code용 특허 전략 보고서 작성 스킬. **다양한 연구·기술 분야**에 적용 가능.  
RFP(MD) → 검색식·URL 생성 → **사용자가 Google Patents에서 CSV 다운로드 후 제공** → **(경로 A)** 노이즈 필터링(제거율 ≤10%) 또는 **(경로 B)** 제목/초록 연관성 상위 N건 → 집계(출원인 영어 통일·동일 회사 합산) → 보고서 MD 생성.

## Quick start

1. **검색식·URL 생성**  
   `python scripts/generate_query.py <RFP.md> [기술분류] [--years 10]`  
   **검색 기간**: 기본값 **10년**(`--years 10`). 사용자가 `--years 12`, `--years 15` 등으로 지정하면 **그 값이 우선** 적용된다. 보고서는 **CSV에 포함된 전체 기간**을 연도별로 분석하므로, 원하는 기간만큼 URL로 다운로드한 CSV를 사용한다.  
   **현재 폴더 RFP**: 첫 인자를 `"."`로 주면 현재 디렉터리에서 `*RFP*.md`를 자동 탐색한다.  
   기본적으로 **필수 개념 그룹을 AND로 묶어** 검색 건수를 5000건 이하 수준으로 줄인 검색식을 생성한다. 출력된 **SEARCH_URL**을 복사.  
   **검색 결과가 여전히 많을 때**: 사용자가 정한 **핵심 키워드(필수 단어)**를 넣어 더 축소할 수 있다.  
   - `--required-terms "stretchable,sensor,display"` 처럼 쉼표 구분으로 핵심 키워드를 넘기거나,  
   - `--required-all` 로 **모든 핵심 키워드가 AND**로 들어가게 할 수 있다.  
   - `--ask-required` 로 실행하면 **핵심 키워드(필수 단어, 쉼표 구분)** 입력을 요청한다.  
   **필수 제외 단어**: `--exclude-terms "rigid substrate,drug"` 또는 `--ask-exclude` 로 검색에서 빼야 할 단어를 지정하면 `NOT (...)` 블록이 추가된다.  
   기존처럼 단일 OR 블록만 쓰려면 `--no-and-groups`를 붙인다.

2. **CSV 준비 (사용자)**  
   브라우저에서 위 URL로 Google Patents 검색 실행 → 결과 페이지에서 **Download (CSV)** 클릭 → 저장한 CSV 파일 경로를 확보 (예: `output/xxx.csv`).

3. **경로 A: 노이즈 필터**  
   `python scripts/filter_noise.py <CSV경로> <RFP.md> -o output/filtered.csv`  
   REMOVAL_RATIO가 0.10 이하가 될 때까지 필요 시 검색식 보정 후 사용자가 새 CSV를 받아 다시 반복.

   **경로 B: 연관성 상위 N건** (검색 결과가 많을 때)  
   v1 CSV → **제목–RFP 연관성 상위 5000건** → (선택) 초록 크롤링 → **초록–RFP 연관성 상위 2500건** → 집계·보고서.  
   - `filter_title_top_n.py <v1.csv> <RFP.md> -o v1_top5000.csv --top 5000`  
   - (선택) `fetch_abstracts.py` → `filter_abstract_top_n.py` → v2.csv  
   - 일괄: `run_v1_to_v2_pipeline.py <v1_csv> <RFP.md> -o output`  
   상세는 `output/실행가이드_v1_to_v2_파이프라인.md` 참고.

4. **집계**  
   `python scripts/aggregate_csv_report.py output/filtered.csv -o output --report-title "제목" --search-query "..." --search-url "..." --rfp-path <RFP.md>`  
   한글 경로 문제 시: `run_aggregate_5000_inprocess.py` 또는 `run_report_from_5000.py`처럼 스크립트 내부에서 경로를 지정하는 러너 사용.

5. **보고서 채우기**  
   `python scripts/fill_report.py output/aggregate_report_data.json -o output/보고서.md --topic <주제슬러그>`

6. 생성된 보고서에서 `[ ... ]` 안의 서술문을 LLM으로 채워 최종 저장. **기술 단계**(도입기/성장기/성숙기)는 RFP·도메인에 맞게 해석하고, 최근년도 감소가 공개 지연·표본 한계 때문인지 구분하여 서술.

## 스크립트 목록

| 용도 | 스크립트 |
|------|----------|
| 검색식·URL | `generate_query.py` |
| 노이즈 필터(경로 A) | `filter_noise.py` |
| 제목 연관성 상위 N | `filter_title_top_n.py` |
| 초록 추가 | `fetch_abstracts.py` |
| 초록 연관성 상위 N | `filter_abstract_top_n.py` |
| v1→v2 일괄 | `run_v1_to_v2_pipeline.py` |
| 집계 | `aggregate_csv_report.py` |
| 보고서 채우기 | `fill_report.py` |
| 전체 파이프라인(경로 A) | `run_full_pipeline.py` |
| 5000건 기준 집계·보고서 | `run_aggregate_5000_inprocess.py`, `run_report_from_5000.py` |

## 파일

- **SKILL.md**: 워크플로(경로 A/B), 출원인 통일·기술 단계 해석 등.
- **reference.md**: 쿼리 문법, **출원인 집계(영어 통일·동일 회사 합산)**, **기술 단계 해석**, v1→v2 파이프라인, 노이즈 기준, 보고서 템플릿 요약.
- **templates/report-template.md**: Obsidian 보고서 템플릿.
- **scripts/**: 위 표 참고. Playwright 기반 자동 다운로드는 **보류**; CSV는 사용자 제공.

## 의존성

- Python 3.9+
- **pandas** (집계·필터). **scikit-learn** (제목/초록 연관성). **requests**, **beautifulsoup4** (초록 크롤링).  
  uv 사용 시:
  ```bash
  cd .codex/skills/patent-strategy-report/scripts
  uv venv
  uv pip install -r requirements.txt
  ```
  Playwright는 메인 워크플로에 사용하지 않음.

## GitHub 배포 및 다른 PC 설치

- **GitHub에 올리는 방법**과 **다른 컴퓨터에 설치하는 방법**(Codex skill-installer / 수동 clone)은 [INSTALL.md](INSTALL.md)를 참고하세요.
- **스킬·플러그인을 한 레포에 모아 여러 PC에 동일 환경 구성**하려면 [docs/도구_레포지토리_구성_가이드.md](docs/도구_레포지토리_구성_가이드.md)를 참고하세요.
