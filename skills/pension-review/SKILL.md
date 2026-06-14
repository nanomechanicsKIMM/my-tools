---
name: pension-review
description: >-
  DC형 퇴직연금(과학기술인공제회 등) 펀드 분석·추천·백테스트·글로벌 분산 전 과정을 자동화하는
  워크플로우 스킬. 사용자가 "퇴직연금 포트폴리오", "연금 펀드 추천", "DC형 자산배분",
  "펀드 백테스트", "포트폴리오 검증", "연금 글로벌 분산", "실적배당형 상품 분석" 등을 언급하거나
  과기공제회 펀드 엑셀(펀드+필터+검색-YYYYMMDD.xlsx)을 다루며 추천·검증을 요청하면 이 스킬을 사용한다.
  KOFIA 일별 NAV 수집→분배락 보정→슬롯 기반 추천→forward-pricing 백테스트(DC제약)→
  부트스트랩 다중경로 강건성→상관/신흥국 글로벌 분산→HTML 대시보드까지 8단계로 처리한다.
---

# pension-review — DC형 퇴직연금 포트폴리오 워크플로우

DC형 퇴직연금 펀드를 **수집→가공→검증→추천→백테스트→비교→글로벌분산→리포트**의 8 Phase로 분석한다.
검증된 방법론(기준가 0% 오차, 슬롯 6/6 재현, 부트스트랩 강세장 편향 제거, 정량+정성 교차검증)을 따른다.

## 사전 준비

**작업 디렉토리**: 분석할 프로젝트 폴더에서 실행한다(스크립트는 상대경로 `panel_adj_nav.csv`, `funds/`, `nav_history/` 등을 참조). `scripts/`의 .py를 작업 폴더로 복사하거나 작업 폴더에서 직접 실행한다.

**투자자 프로필**(필수 입력): 출생연도·은퇴예정·투자성향·투자금액·계좌유형. 예) 1971년생·은퇴 2033·공격투자형·3억·DC형.

## Phase 0 — 데이터 수집 (사용자 수동 다운로드 + 변환)

> [!중요] 펀드 데이터는 사용자가 직접 다운로드해야 한다. 자동 접근 불가(회원 포털·JS 사이트).

1. **사용자에게 수동 다운로드 안내**(반드시 이 절차를 안내):
   - `www.sema.or.kr` 접속 → **연금** → **상품안내** → **실적배당형상품** → **FUNEFT 창에서 `전체 정보 다운로드`** 클릭
   - 다운로드 파일: `펀드+필터+검색-YYYYMMDD.xlsx` (기본 `~/Downloads`)
2. **CSV 변환** (pandas):
   ```python
   import pandas as pd
   pd.read_excel("펀드+필터+검색-YYYYMMDD.xlsx", header=None).to_csv(
       "(YYYYMMDD)_과기공제회_연금_실적배당형상품.csv", index=False, header=False,
       encoding="utf-8-sig", na_rep="")
   ```
   - 34컬럼·2줄 헤더 구조. 직전 파일과 비교해 **신규/탈락 펀드** 점검.
3. **KOFIA 일별 NAV 수집**: `collect_nav.py` (CSV_PATH를 최신 CSV로 지정). dis.kofia.or.kr 무인증 API, 5년치 일별 기준가 → `nav_history/{표준코드}.csv`.
4. **분류/수수료 JSON 생성**: data-updater 스킬 또는 `convert_sema_to_legacy.py` 경유로 `funds/fund_data.json`·`fund_fees.json`·`fund_classification.json`.

## Phase 1 — 데이터 가공
- `adjust_nav.py`: 분배락(1000 리셋) 후방조정 → 수정기준가 `adjusted_nav/`
- `build_eligibility.py`: 펀드별 자격 타임라인(생존편향 차단) → `eligibility.csv`
- `build_panel.py`: 날짜×코드 패널(NaN 정책, ffill 금지) → `panel_adj_nav.csv`, `panel_ret.csv`

## Phase 2 — 무결성 검증
- `verify_vs_csv.py`: 수집 NAV vs 원본 CSV 공시수익률 교차검증. 기준가 0% 오차 확인.
- `diag_tail_error.py`: 1년/3년 꼬리오차 진단(분배락 탐지 한계는 기준가 데이터의 본질적 한계 — 휴리스틱으로 완전 해결 불가).

## Phase 3 — 추천 생성 (슬롯 5단계 규칙)
- `recommend_algo.py`: 결정적 규칙으로 추천 도출.
  - ① 안전자산 게이트(bestBond 실질<예금+0.5%p→예금100%)
  - ② 연령 위험비중(cap70%−보수5%p=65%)
  - ③ 핵심-위성 슬롯(S&P22/나스닥13/KOSPI15/반도체8/고배당7)
  - ④ 슬롯별 랭킹(핵심4+반도체=최저보수, 고배당=최대순자산) — 시점별 동적 선택
  - ⑤ 컴플라이언스(위험70/단일40/지역50)

## Phase 4 — 백테스트 (DC제약 + 다중경로)
- `backtester.py`: forward-pricing(룩어헤드 차단)·거래비용·일1회 체결 엔진
- `constraints.py`: DC 제약(위험70/단일40), `dc_constrained()` 래퍼
- `backtest_portfolio.py`: 추천 포트폴리오 단일경로(2.5y 정확/5y proxy)·글라이드패스
- `mc_backtest.py`: 구간벡터화 경량엔진 + Stationary Block Bootstrap **다중경로**(강세장 편향 제거). `fast_run`은 NaN 안전(0×NaN 차단).

## Phase 5 — 알고리즘 비교
- `algos.py`(10종: 모멘텀/듀얼/트렌드/역변동성/리스크패리티/최소분산/최대샤프/HRP/HERC/Mean-CVaR)
- `algos_new.py`(커스텀: 모멘텀가속/단기반전/섹터로테이션, 분기·월간 15일 리밸)
- `backtest_algos.py`·`mc_hybrid.py`: 추천 vs 알고리즘 비교. **단순 고정비중 > 복잡 최적화** 일관 확인.

## Phase 6 — 글로벌 분산
- `screen_global.py`:
  - `correlation_matrix({label:code})`: 상관매트릭스·평균·중복(0.85+)·저상관쌍
  - `screen_emerging()`: 신흥국 펀드 메트릭(CAGR·Sharpe·미국/한국 상관)
  - `backtest_cases({label:weights}, N, extra_codes)`: 재구성안 단일+다중경로
- **정성 교차검증**: 인도/중국 등 신흥국 거시는 `/deep-research`로 고평가·환율·상관 과대평가 검증(백테스트 과적합 방지). 백테스트 일별상관 < 실제 장기상관임에 유의 → 신흥국 비중 보수적(≤8%), 환헤지·DCA 권장.

## Phase 7 — 리포트
- `scripts/extract_dashboard_data.py`: 핵심 펀드(미국/한국/인도/중국/아세안) 월말 NAV → `dashboard_data.js` 생성.
- `templates/portfolio_dashboard.html`: 인터랙티브 대시보드.
  - **투자 알고리즘 선택** + 텍스트 규칙 표시(원본추천/글로벌분산/모멘텀Top5/역변동성/사용자정의)
  - **JS 백테스트 + 수익률 그래프**(선택 포트 vs KOSPI200 vs S&P500, CAGR/Sharpe/MDD) — 분기 리밸·동적 펀드선택을 브라우저에서 계산
  - 총액 입력→배분금액, 현재 보유→리밸런싱 변동(매수/매도), 로그 저장(txt/CSV)
  - 실행: `extract_dashboard_data.py`로 `dashboard_data.js` 생성 → 같은 폴더에서 **로컬 서버**로 열기(`python -m http.server`; file:// 프로토콜은 차단됨).
- Obsidian md 종합보고서(YAML 프론트매터·Mermaid·콜아웃). 추천 근거·백테스트·글로벌분산·한계 포함.

## 산출물
- `portfolio_recommendation.md` (추천 + 컴플라이언스 + Devil's Advocate)
- 백테스트 검증 보고서·글로벌 분산 보고서 (Obsidian md)
- `portfolio_dashboard.html` (인터랙티브 대시보드)
- 리밸런싱 로그 (사용자 저장)

## 주의사항
- 모든 보고서는 **투자 권유 아님** 면책 포함. 과거 성과는 미래 보장 안 함.
- 분배락 탐지는 휴리스틱(1000±1.5 밴드) — 1년+ 누적수익에 ±수%p 오차 가능, 백테스트(일일수익률)엔 영향 제한적.
- 신흥국 분산효과는 일별 백테스트가 과대평가 가능 → 정성 리서치로 보정.
- 방법론 상세: `references/methodology.md` 참조.
