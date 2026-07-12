# -*- coding: utf-8 -*-
"""
KOFIA NAV 증분 갱신기 — collect_nav.py 보조.
기존 nav_history/{코드}.csv 말단 이후 구간만 수집해 append, 신규 펀드는 전체 수집.
collect_nav.py의 검증된 fetch/collect 로직을 재사용한다(CSV_PATH 유니버스 기준).
"""
import csv, os, json
from datetime import datetime, timedelta
import collect_nav as cn

OUT_DIR = cn.OUT_DIR

def read_last_date(path):
    with open(path, encoding="utf-8") as f:
        rows = [r for r in csv.reader(f) if r]
    return rows[-1][0] if len(rows) > 1 else None

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    funds = cn.load_universe()
    meta_path = os.path.join(OUT_DIR, "_metadata.json")
    meta = json.load(open(meta_path, encoding="utf-8")) if os.path.exists(meta_path) else {}
    failed, new_funds, updated, unchanged = [], 0, 0, 0
    for i, (code, name, typ, setdt) in enumerate(funds, 1):
        out = os.path.join(OUT_DIR, code + ".csv")
        try:
            if os.path.exists(out):
                last = read_last_date(out)
                frm = (datetime.strptime(last, "%Y%m%d") + timedelta(days=1)).strftime("%Y%m%d")
                if frm > cn.END:
                    unchanged += 1; continue
                rows = cn.collect_fund(code, frm)   # floor=frm 이후만
                rows = {d: v for d, v in rows.items() if d > last}
                if not rows:
                    unchanged += 1; continue
                with open(out, "a", newline="", encoding="utf-8") as w:
                    cw = csv.writer(w)
                    for d in sorted(rows):
                        cw.writerow([d, *rows[d]])
                updated += 1
                tag = "UPD "
            else:
                rows = cn.collect_fund(code, setdt)
                if not rows:
                    print("[%3d/%d] EMPTY %s" % (i, len(funds), code))
                    failed.append(code); continue
                with open(out, "w", newline="", encoding="utf-8") as w:
                    cw = csv.writer(w)
                    cw.writerow(["date", "nav", "tax_nav", "kospi", "kospi200", "kosdaq"])
                    for d in sorted(rows):
                        cw.writerow([d, *rows[d]])
                new_funds += 1
                tag = "NEW "
        except Exception as e:
            print("[%3d/%d] FAIL %s : %s" % (i, len(funds), code, e))
            failed.append(code); continue
        # 메타 갱신(전체 파일 기준 start/end/rows 재계산)
        with open(out, encoding="utf-8") as f:
            n = sum(1 for r in csv.reader(f) if r) - 1
        first = None
        with open(out, encoding="utf-8") as f:
            rd = csv.reader(f); next(rd)
            for r in rd:
                first = r[0]; break
        meta[code] = {"name": name, "type": typ, "set_date": setdt,
                      "start": first, "end": read_last_date(out), "rows": n}
        print("[%3d/%d] %s %s  ~%s  +%d rows" % (i, len(funds), tag, code,
              meta[code]["end"], len(rows)))
    json.dump(meta, open(meta_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    if failed:
        open(os.path.join(OUT_DIR, "_failed.txt"), "w").write("\n".join(failed))
    print("DONE. funds=%d updated=%d new=%d unchanged=%d failed=%d" %
          (len(funds), updated, new_funds, unchanged, len(failed)))

if __name__ == "__main__":
    main()
