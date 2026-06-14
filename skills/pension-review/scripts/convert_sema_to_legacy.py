#!/usr/bin/env python3
"""sema.or.kr 실적배당형 상품 CSV → 미래에셋증권 상품제안서 형식 CSV 변환기.

data-updater 스킬의 update_fund_data.py가 기대하는 legacy 형식으로 sema.or.kr
직접 다운로드 CSV를 변환한다. 동시에 모든 펀드 코드를 포함한
investable_codes.json을 생성하여 필터링이 no-op이 되도록 한다.
"""

import csv
import json
import re
import sys
from datetime import date
from pathlib import Path

RISK_NAMES = {
    1: "매우높은위험",
    2: "높은위험",
    3: "다소높은위험",
    4: "보통위험",
    5: "낮은위험",
    6: "매우낮은위험",
}

LEGACY_HEADER = [
    "펀드코드", "펀드명", "운용회사명", "위험등급", "순자산총액(억원)",
    "수익률(6M)", "수익률(1Y)", "수익률(3Y)", "수익률(5Y)", "수익률(7Y)", "수익률(10Y)",
    "설정일", "비율(%)", "1년투자비용(원)", "계열사 여부", "비고",
]


def extract_base_date_from_filename(path: Path) -> str:
    m = re.search(r"(20\d{6})", path.name)
    if m:
        s = m.group(1)
        return f"{s[:4]}-{s[4:6]}-{s[6:8]}"
    return date.today().isoformat()


def convert(sema_path: Path, legacy_path: Path, codes_path: Path) -> int:
    with open(sema_path, "r", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if len(rows) < 3:
        raise ValueError("CSV에 데이터가 부족합니다 (최소 3행 필요)")

    sema_header = [c.strip() for c in rows[0]]
    sub_header_present = bool(rows[1]) and any(
        ("%순위" in c or "지표" in c) for c in rows[1]
    )
    data_start = 2 if sub_header_present else 1
    data_rows = rows[data_start:]

    idx = {name: i for i, name in enumerate(sema_header)}

    def cell(row, name):
        i = idx.get(name)
        if i is not None and i < len(row):
            return row[i].strip()
        return ""

    base_date = extract_base_date_from_filename(sema_path)

    out_rows = [
        ["사업자명", "과학기술인공제회"],
        ["제도유형", "DC/IRP"],
        ["상품유형", "실적배당형 상품(펀드/ETF)"],
        ["기준일", f"{base_date}, 과학기술인공제회"],
        [], [], [],
        LEGACY_HEADER,
    ]

    fund_codes = []
    skipped = 0

    for row in data_rows:
        if not row or not any(c.strip() for c in row):
            continue
        fund_code = cell(row, "펀드코드")
        if not fund_code:
            skipped += 1
            continue

        risk_raw = cell(row, "위험등급")
        try:
            n = int(risk_raw)
            risk_legacy = f"{n}등급({RISK_NAMES.get(n, '')})"
        except (ValueError, TypeError):
            risk_legacy = ""

        total_fee = cell(row, "총보수(%)")
        try:
            annual_cost = str(int(round(float(total_fee) * 100)))
        except (ValueError, TypeError):
            annual_cost = ""

        out_rows.append([
            fund_code,
            cell(row, "펀드명"),
            cell(row, "운용사명"),
            risk_legacy,
            cell(row, "운용규모(억원)"),
            cell(row, "6개월(%)"),
            cell(row, "1년(%)"),
            cell(row, "3년(%)"),
            "", "", "",  # 5Y, 7Y, 10Y — sema 데이터에 없음
            cell(row, "설정일"),
            total_fee,
            annual_cost,
            "",
            cell(row, "펀드 대유형"),
        ])
        fund_codes.append(fund_code)

    with open(legacy_path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f).writerows(out_rows)

    with open(codes_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "_meta": {
                    "version": base_date,
                    "source": "sema.or.kr 실적배당형 상품 (전체)",
                    "note": "no-op filtering: sema CSV 전체 펀드 코드",
                    "recordCount": len(fund_codes),
                },
                "codes": fund_codes,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"[OK] Legacy CSV: {legacy_path}")
    print(f"[OK] Codes JSON: {codes_path}")
    print(f"[INFO] Funds converted: {len(fund_codes)}")
    print(f"[INFO] Skipped (no fundCode): {skipped}")
    print(f"[INFO] Base date: {base_date}")
    return len(fund_codes)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python convert_sema_to_legacy.py <sema_csv> [legacy_csv] [codes_json]")
        sys.exit(1)

    sema = Path(sys.argv[1])
    legacy = Path(sys.argv[2]) if len(sys.argv) > 2 else sema.with_name(sema.stem + "_legacy.csv")
    codes = Path(sys.argv[3]) if len(sys.argv) > 3 else Path("funds/investable_codes.json")
    codes.parent.mkdir(parents=True, exist_ok=True)
    convert(sema, legacy, codes)
