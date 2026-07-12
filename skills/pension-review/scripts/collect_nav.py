# -*- coding: utf-8 -*-
"""
KOFIA 전자공시 일별 기준가(NAV) 5년치 수집기.
소스 검증: dis.kofia.or.kr proframeWeb/XMLSERVICES (COMFundPriceModSO.priceModSrch)
- 인증 불필요(표준코드만), 일별은 요청당 최근 120영업일 캡 -> to 이동 페이지네이션
- 출력: nav_history/{표준코드}.csv  (date,nav,tax_nav,kospi,kospi200,kosdaq)
        nav_history/_metadata.json, nav_history/_failed.txt
"""
import csv, os, re, json, time, sys
from datetime import datetime, timedelta
import requests

def _latest_csv():
    import glob
    c = glob.glob("data_raw/*_과기공제회_연금_실적배당형상품.csv")
    return max(c, key=lambda p: re.search(r"(20\d{6})", os.path.basename(p)).group(1)) if c else None

CSV_PATH = _latest_csv() or "data_raw/(20260711)_과기공제회_연금_실적배당형상품.csv"
OUT_DIR = "nav_history"
START = "20210613"          # 5년 시작(목표)
END = datetime.now().strftime("%Y%m%d")
URL = "https://dis.kofia.or.kr/proframeWeb/XMLSERVICES/"
HEADERS = {"Content-Type": "application/xml; charset=UTF-8",
           "User-Agent": "Mozilla/5.0", "Referer": "https://dis.kofia.or.kr/"}
SLEEP = 0.25               # 레이트리밋 (서버 예의)
RETRY = 3
PAGE_CAP = 120            # 서버 일별 캡

BODY = ('<?xml version="1.0" encoding="utf-8"?>'
        '<message><proframeHeader><pfmAppName>FS-COM</pfmAppName>'
        '<pfmSvcName>COMFundPriceModSO</pfmSvcName>'
        '<pfmFnName>priceModSrch</pfmFnName></proframeHeader><systemHeader></systemHeader>'
        '<COMFundUnityInfoInputDTO><standardCd>{cd}</standardCd><companyCd></companyCd>'
        '<vSrchTrmFrom>{f}</vSrchTrmFrom><vSrchTrmTo>{t}</vSrchTrmTo>'
        '<vSrchStd>1</vSrchStd></COMFundUnityInfoInputDTO></message>')

ROW_RE = re.compile(r"<priceModList>(.*?)</priceModList>", re.S)
def tag(block, name):
    m = re.search(r"<%s>(.*?)</%s>" % (name, name), block, re.S)
    return m.group(1).strip() if m else ""

def fetch_page(code, frm, to):
    body = BODY.format(cd=code, f=frm, t=to).encode("utf-8")
    for attempt in range(RETRY):
        try:
            r = requests.post(URL, data=body, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
        except requests.RequestException:
            pass
        time.sleep(1.5 * (attempt + 1))
    return None

def collect_fund(code, set_date=None):
    """to를 과거로 이동하며 전체 일별 시계열 수집. {date: (nav,tax,kospi,kospi200,kosdaq)}
    floor=max(START,설정일)까지 수집. 중간 데이터 공백(빈 페이지)을 만나도 floor까지 후퇴."""
    floor = max(START, set_date) if set_date else START
    rows = {}
    to = END
    prev_oldest = None
    while True:
        txt = fetch_page(code, floor, to)
        if txt is None:
            raise RuntimeError("HTTP fail")
        blocks = ROW_RE.findall(txt)
        if not blocks:                                    # 공백 구간: floor까지 더 후퇴
            nxt = datetime.strptime(to, "%Y%m%d") - timedelta(days=180)
            if nxt.strftime("%Y%m%d") < floor:
                break
            to = nxt.strftime("%Y%m%d")
            time.sleep(SLEEP)
            continue
        page_dates = []
        for b in blocks:
            d = tag(b, "standardDt")
            if not d:
                continue
            page_dates.append(d)
            rows[d] = (tag(b, "standardCot"), tag(b, "standardassStdCot"),
                       tag(b, "kospiEpn"), tag(b, "kospi200Epn"), tag(b, "kosdaqEpn"))
        oldest = min(page_dates)
        # 서버 일별 캡 = 달력 6개월(페이지당 건수 변동). 목표 도달 또는 진전없음(신생펀드/끝)이면 종료.
        if oldest <= floor or oldest == prev_oldest:
            break
        prev_oldest = oldest
        nxt = datetime.strptime(oldest, "%Y%m%d") - timedelta(days=1)
        to = nxt.strftime("%Y%m%d")
        time.sleep(SLEEP)
    return rows

def load_universe():
    with open(CSV_PATH, encoding="utf-8") as f:
        data = list(csv.reader(f))[2:]
    return [(r[0].strip(), r[1].strip(), r[2].strip(), r[21].strip())
            for r in data if r and r[0].strip()]

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    funds = load_universe()
    meta_path = os.path.join(OUT_DIR, "_metadata.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    failed = []
    for i, (code, name, typ, setdt) in enumerate(funds, 1):
        out = os.path.join(OUT_DIR, code + ".csv")
        if os.path.exists(out) and code in meta:          # resume
            print("[%3d/%d] skip %s (cached)" % (i, len(funds), code)); continue
        try:
            rows = collect_fund(code, setdt)
        except Exception as e:
            print("[%3d/%d] FAIL %s : %s" % (i, len(funds), code, e))
            failed.append(code); continue
        if not rows:
            print("[%3d/%d] EMPTY %s" % (i, len(funds), code))
            failed.append(code); continue
        dates = sorted(rows)
        with open(out, "w", newline="", encoding="utf-8") as w:
            cw = csv.writer(w)
            cw.writerow(["date", "nav", "tax_nav", "kospi", "kospi200", "kosdaq"])
            for d in dates:
                cw.writerow([d, *rows[d]])
        meta[code] = {"name": name, "type": typ, "set_date": setdt,
                      "start": dates[0], "end": dates[-1], "rows": len(dates)}
        json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print("[%3d/%d] OK   %s  %s~%s  %d rows" % (i, len(funds), code, dates[0], dates[-1], len(dates)))
        time.sleep(SLEEP)
    if failed:
        open(os.path.join(OUT_DIR, "_failed.txt"), "w").write("\n".join(failed))
    print("DONE. funds=%d failed=%d" % (len(funds), len(failed)))

if __name__ == "__main__":
    main()
