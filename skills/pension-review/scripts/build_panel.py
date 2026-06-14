# -*- coding: utf-8 -*-
"""
백테스트용 통합 패널(wide) 생성.
- 인덱스: 전 펀드 거래일 합집합(한국 영업일 캘린더, 1228일)
- 컬럼: 282 펀드 표준코드
- 값: 수정기준가(adj_nav). 결측은 NaN 유지(ffill 미적용)
      결측 의미 = ⓐ자격밖(설정전/데이터끝후) ⓑ내부공백(휴면) ⓒ산발누락 — 모두 백테스터가 정책 결정

산출:
  panel_adj_nav.csv  — 날짜(ISO) × 표준코드, 수정기준가  [메인]
  panel_ret.csv      — 날짜 × 표준코드, 일일수익률(=마스터 정렬 adj_nav의 pct_change)
                        공백/자격경계는 자동 NaN(공백 건너뛴 가짜 점프 수익률 방지)

백테스터 사용:
  nav = pd.read_csv('panel_adj_nav.csv', index_col=0, parse_dates=True)
  tradeable = nav.notna()            # 시점별 매매가능 유니버스
  ret = pd.read_csv('panel_ret.csv', index_col=0, parse_dates=True)
"""
import glob, os, csv
import pandas as pd

SRC = "adjusted_nav"

def main():
    files = sorted(set(f for f in glob.glob(os.path.join(SRC, "*.csv"))
                       if os.path.basename(f)[0] == "K" and "_" not in os.path.basename(f)))
    series = {}
    for f in files:
        code = os.path.basename(f)[:-4]
        rows = [r for r in list(csv.reader(open(f, encoding="utf-8")))[1:] if r]
        s = pd.Series({r[0]: float(r[2]) for r in rows})   # col2 = adj_nav
        series[code] = s
    nav = pd.DataFrame(series)                              # index=YYYYMMDD str(합집합), cols=code
    nav.index = pd.to_datetime(nav.index, format="%Y%m%d")
    nav = nav.sort_index().reindex(sorted(nav.columns), axis=1)
    nav = nav.round(4)

    ret = nav.pct_change(fill_method=None).round(6)         # fill 금지 → 공백/경계 자동 NaN(가짜 점프 방지)

    nav.to_csv("panel_adj_nav.csv", index_label="date")
    ret.to_csv("panel_ret.csv", index_label="date")

    # ---- 검증 ----
    elig = {r["code"]: int(r["n_days"]) for r in csv.DictReader(open("eligibility.csv", encoding="utf-8"))}
    mismatch = [c for c in nav.columns if int(nav[c].notna().sum()) != elig.get(c)]
    print("패널 차원: %d 거래일 × %d 펀드" % nav.shape)
    print("기간: %s ~ %s" % (nav.index[0].date(), nav.index[-1].date()))
    print("eligibility n_days 불일치:", len(mismatch), mismatch[:5])
    print("전체 결측률: %.1f%% (자격밖+공백 포함)" % (nav.isna().mean().mean() * 100))
    # 월말 활성 펀드수 (universe_timeline 정합성 스팟)
    for ym in ["2021-06", "2023-06", "2025-12"]:
        sub = nav.loc[nav.index.to_period("M").astype(str) == ym]
        if len(sub):
            print("  %s 말 활성펀드:" % ym, int(sub.iloc[-1].notna().sum()))
    # 공백펀드 ret 경계 NaN 확인
    gap = "K55301CG2721"
    if gap in ret.columns:
        seg = ret[gap].dropna()
        print("공백펀드 %s: ret 유효 %d개 (공백 양끝 NaN 분리 정상)" % (gap, len(seg)))

if __name__ == "__main__":
    main()
