---
name: pension-review
description: >-
  DC형 퇴직연금(과학기술인공제회 등) 펀드 분석·추천·백테스트·글로벌 분산 전 과정을 자동화하는
  워크플로우 스킬. 사용자가 "퇴직연금 포트폴리오", "연금 펀드 추천", "DC형 자산배분",
  "펀드 백테스트", "포트폴리오 검증", "연금 글로벌 분산", "실적배당형 상품 분석",
  "섹터 로테이션", "퀀트 알고리즘 도출·검증" 등을 언급하거나
  과기공제회 펀드 엑셀(펀드+필터+검색-YYYYMMDD.xlsx)을 다루며 추천·검증을 요청하면 이 스킬을 사용한다.
  KOFIA 일별 NAV 수집→분배락 보정→슬롯 기반 추천→forward-pricing 백테스트(DC제약)→
  부트스트랩 다중경로 강건성→상관/신흥국 글로벌 분산→HTML 대시보드까지 8단계로 처리하며,
  퀀트 알고리즘 도출(3-에이전트·페어 부트스트랩 심판·과적합 가드)·섹터 로테이션 분석도 지원한다.
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
3. **KOFIA 일별 NAV 수집**: 최초 전체 수집은 `collect_nav.py` (CSV_PATH를 최신 CSV로 지정). dis.kofia.or.kr 무인증 API, 5년치 일별 기준가 → `nav_history/{표준코드}.csv`.
   **분기 증분 갱신은 `update_nav.py`** — 기존 시계열 말단 이후만 fetch·append하고 신규 펀드는 전체 수집(collect_nav의 resume는 캐시 펀드를 스킵하므로 증분 갱신 불가). CSV_PATH는 collect_nav.py에서 갱신 후 실행.
4. **분류/수수료 JSON 생성**: data-updater 스킬 또는 `convert_sema_to_legacy.py` 경유로 `funds/fund_data.json`·`fund_fees.json`·`fund_classification.json`.
   생성 직후 **`fix_classification.py` 필수 실행** — 알려진 자동분류 오류(펀드명에 없는 'gold' 테마 false-positive, (UH)/(H) hedged 필드)를 정정한다(멱등, 분류 JSON의 키=펀드명·name 필드 없음에 주의).

## Phase 1 — 데이터 가공
- `adjust_nav.py`: 분배락(1000 리셋) 후방조정 → 수정기준가 `adjusted_nav/`
- `build_eligibility.py`: 펀드별 자격 타임라인(생존편향 차단) → `eligibility.csv`
- `build_panel.py`: 날짜×코드 패널(NaN 정책, ffill 금지) → `panel_adj_nav.csv`, `panel_ret.csv`

## Phase 2 — 무결성 검증
- `verify_vs_csv.py`: 수집 NAV vs 원본 CSV 공시수익률 교차검증. 기준가 0% 오차 확인. 인자 없이 실행하면 `data_raw/` 최신 CSV와 기준일(파일명 날짜의 직전 영업일, 포털 '전영업일 결제기준')을 자동 선택 — `--csv`/`--date`로 오버라이드(한국 공휴일이 낀 주는 `--date` 명시).
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
- **`fetch_index_history.py` — FDR 장기 실지수 백테스트(직교 강건성)**: 5년 펀드 패널·부트스트랩이 못 보는 *실제 약세장*(2008·2011·2015·2018·2020·2022)에서 정책 아키타입을 검증. FinanceDataReader로 US500(1979~)·IXIC(1979~)·KS200(2010~)·USD/KRW(2003~) 수집→**월간 KRW 언헤지·TR근사** 패널(`index_panel.csv`). 가드: SOX미제공→반도체는 IXIC흡수, 나스닥은 IXIC(종합)대용, US+KR 일별혼합 금지(ME 리샘플), 가격지수+배당수익률 가산(TR근사), 월간 전용 `sim`(ppy=12, forward). 산출: ①아키타입 vs 벤치마크(다자산 2010~/US-only 2003~) ②**위기별 MDD 표**(GFC 추천 −15.0% vs 주식100% −23.3%, 전위기 방어 +2.5~8.3%p) ③**장기 walk-forward(fold 12·18개)**로 WF 통계력 보강 — 위험슬리브 4종 선택이 OOS에서 고정 추천에 동률/패배(FAIL) 재확인. 실행: 작업폴더에서 `python <skill>/scripts/fetch_index_history.py [--refresh]`. **레이블 주의: '추천 펀드'가 아니라 '정책 아키타입의 실약세장 스트레스' — 펀드단위 결론과 구분.**

## Phase 5 — 알고리즘 비교 + 엄밀 평가
- `algos.py`(10종: 모멘텀/듀얼/트렌드/역변동성/리스크패리티/최소분산/최대샤프/HRP/HERC/Mean-CVaR)
- `algos_new.py`(커스텀): 모멘텀가속·단기반전·섹터로테이션 + **TradingAgents 수집 3종**(`regime_gate` 200SMA레짐·`vol_target` 변동성타게팅·`ensemble_vote` MACD+SMA+RSI 앙상블) + `diversified_riskbudget`(분산 inverse-vol 리스크버짓).
- `backtest_algos.py`·`backtest_tradingagents.py`·`mc_hybrid.py`: 추천 vs 알고리즘 단일+다중경로 비교.
- **`algo_eval.py` — 페어 부트스트랩 심판**: 동일 경로에서 추천vs후보 페어 비교 + 게이트(CAGR≥1.10× AND |MDD|≤0.90×) 자동판정. 신규 알고리즘 평가의 단일 객관 기준.
- **`walkforward_oos.py` — Walk-Forward 표본외(OOS) 검증**: 부트스트랩이 못 보는 *알고리즘 선택의 과적합*을 시간순 전진으로 측정. anchored 학습 `[0,t)`→OOS 테스트 `[t,t+126)`를 126일씩 전진하며, 매 fold마다 후보 10종을 학습 Sharpe로 선택→테스트 적용. WF-Select(메타)·추천65/35·개별algo고정·동일가중을 동일 fold로 stitch 비교, 전환 fold엔 전환비용 차감. 게이트는 `algo_eval`과 동일. 검증된 `fast_run` 엔진 재사용(skfolio 미사용 — DC제약·예금쿠션·forward-pricing 수치체계 일관성). 실행: 작업폴더에서 `PYTHONPATH=<skill>/scripts python <skill>/scripts/walkforward_oos.py [TEST] [STEP] [FREQ]` → `wf_oos_results.json`. **실증(5y·6fold): WF-Select FAIL**(OOS Sharpe 1.81 vs 추천 2.45, MDD −12.2% vs −6.7%, fold승률 3/6) — *선택은 과적합, 고정 추천65/35가 표본외 우위* 재확인. ⚠ 5년 일별→fold 적음(통계력 낮음). FDR 장기 실지수 백테스트 병행 권장.
- **3-에이전트 엄밀평가 프로토콜**(도출→백테스트→비평): GitHub 퀀트레포(Riskfolio-Lib·PyPortfolioOpt·HRP·TradingAgents) 조사→구현→**독립 critic 감사**(룩어헤드·DC·과적합·아티팩트). 과적합 가드(주의사항) 필수.
- **결론(검증됨)**: **단순 고정비중(추천65/35) > 복잡 최적화·타이밍** 일관. 부트스트랩이 추세형 타이밍에 불리. 분산은 **MDD/Sharpe만 견고 개선, 수익(CAGR) 우위는 사후편향**으로 표본외 불가.
- **섹터 로테이션(보조 분석)** `sector_rotation.py`: 분기별 최고수익 섹터 변천 bar chart(섹터=region+테마 반도체/바이오의료/국방우주/에너지이차전지/금, MIN_N=2 단일펀드·브라질 제외) → 시장 국면 진단·정성 보조.

## Phase 6 — 글로벌 분산
- `screen_global.py`:
  - `correlation_matrix({label:code})`: 상관매트릭스·평균·중복(0.85+)·저상관쌍
  - `screen_emerging()`: 신흥국 펀드 메트릭(CAGR·Sharpe·미국/한국 상관)
  - `backtest_cases({label:weights}, N, extra_codes)`: 재구성안 단일+다중경로
- **정성 교차검증**: 인도/중국 등 신흥국 거시는 `/deep-research`로 고평가·환율·상관 과대평가 검증(백테스트 과적합 방지). 백테스트 일별상관 < 실제 장기상관임에 유의 → 신흥국 비중 보수적(≤8%), 환헤지·DCA 권장.

## Phase 7 — 리포트
- **`drift_check.py` — 보유 드리프트 점검**: 사용자 보유내역을 `status/holdings_YYYYMMDD.json`(`{"asof","holdings":[{"name","code","value","kind":"fund|deposit|cash"}]}`)으로 구조화한 뒤 실행. 비중표·위험자산비중·DC 한도(위험70/단일40) 판정, `--targets` JSON(코드→비중%)을 주면 목표 대비 괴리(±5%p 밴드이탈 플래그)까지 출력. ⚠ '기타' 분류(골드·TDF)가 안전으로 집계되어 포털 공시 위험비중과 다를 수 있음 — 포털값 병기 확인.
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
- **알고리즘 도출 과적합 가드(필수)**: ①**사후편향** — 풀을 실현수익 기준으로 큐레이션 금지(부트스트랩이 실현수익을 baked-in). 승자 상위2종 제거 + ex-ante(수익무관 AUM/카테고리) 풀로 재검증해 CAGR 우위 진위 확인. ②**비동기 NAV** — 아시아펀드 對미국 일별상관 과소측정 → 분산/MDD 개선 과대평가(0.5~1%p 차감). ③**데이터 스누핑** — 다변형·다시드 반복은 거짓양성. **음성 결론 후 추가 탐색 금지**. ④홀드아웃 다중시드 교차검증 의무.
- **추천65/35는 표본외 효율적 벤치마크** — 적대적 탐색에도 수익 우위 안 깨짐. 개선 여지는 "수익↑"이 아니라 "분산으로 MDD↓"(이마저 비동기NAV 과제 잔존). walk-forward OOS(`walkforward_oos.py`)로도 *알고리즘 선택*이 표본외에서 추천에 패배 확인(과적합) — 단 5y·소수 fold라 통계력 낮음, FDR 장기 실지수 백테스트로 보강 필요.
- 방법론 상세: `references/methodology.md` 참조.
