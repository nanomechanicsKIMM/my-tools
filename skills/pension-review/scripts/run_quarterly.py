# -*- coding: utf-8 -*-
"""
P3-2 분기 점검 러너 — 신규 CSV 투입 후 1커맨드로 Phase 0(증분)~7 + IPS 대조 완주.

전제: data_raw/에 최신 (YYYYMMDD)_과기공제회_연금_실적배당형상품.csv 존재
      (sema 엑셀 다운로드→CSV 변환은 수동, SKILL.md Phase 0 참조. collect_nav가 최신 CSV 자동 선택).
동작: 각 단계를 서브프로세스로 실행, 핵심 지표를 파싱해
      reports/{YYYYQn}/(YYYYMMDD)_분기점검_체크리스트.md 자동 생성.
      데이터 단계(update_nav~build_panel) 실패 시 중단, 분석 단계 실패는 기록 후 계속.
      ips_check의 exit 1은 '전환 미완'으로 기록(중단 아님).

사용(작업폴더 루트): python scripts/run_quarterly.py [--only step1,step2] [--skip mc_backtest]
                    [--date YYYYMMDD] [--quarter 2026Q3]
"""
import argparse, datetime, os, re, subprocess, sys

STEPS = [  # (이름, 커맨드, 데이터단계여부, 체크리스트 파싱 패턴)
    ("update_nav",        ["python", "scripts/update_nav.py"],        True,  r"DONE\..*"),
    ("adjust_nav",        ["python", "scripts/adjust_nav.py"],        True,  r"분배락.*"),
    ("build_eligibility", ["python", "scripts/build_eligibility.py"], True,  r".*매매가능.*"),
    ("build_panel",       ["python", "scripts/build_panel.py"],       True,  r"전체 결측률.*"),
    ("verify_vs_csv",     ["python", "scripts/verify_vs_csv.py"],     False, r"기준가 일치.*"),
    ("fix_classification",["python", "scripts/fix_classification.py"],False, r".*gold제거.*"),
    ("diag_dropped_funds",["python", "scripts/diag_dropped_funds.py"],False, r".*"),
    ("recommend_algo",    ["python", "scripts/recommend_algo.py"],    False, r"⑤ 컴플라이언스.*|.*컴플라이언스.*"),
    ("backtest_portfolio",["python", "scripts/backtest_portfolio.py"],False, r"\[정확\].*|.*PASS.*"),
    ("mc_backtest",       ["python", "scripts/mc_backtest.py"],       False, r".*추천65/35.*"),
    ("real_report",       ["python", "scripts/real_report.py"],       False, r".*추천65/35.*"),
    ("fee_drag",          ["python", "scripts/fee_drag.py"],          False, r".*가중TER.*"),
    ("drift_check",       ["python", "scripts/drift_check.py"],       False, r"위험자산비중.*"),
    ("ips_check",         ["python", "scripts/ips_check.py"],         False, r"판정:.*"),
    ("extract_dashboard", ["python", "scripts/extract_dashboard_data.py"], False, r"생성:.*"),
]


def _inject_targets(steps):
    """ips_policy.json의 목표배분 파일을 fee_drag/drift_check에 자동 전달."""
    try:
        import json as _j
        tf = _j.load(open("status/ips_policy.json", encoding="utf-8"))["allocation"]["targets_file"]
        if os.path.exists(tf):
            return [(n, c + ["--targets", tf] if n in ("fee_drag", "drift_check") else c, d, p)
                    for n, c, d, p in steps]
    except Exception:
        pass
    return steps


STEPS = _inject_targets(STEPS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default=None)
    ap.add_argument("--skip", default="")
    ap.add_argument("--date", default=datetime.date.today().strftime("%Y%m%d"))
    ap.add_argument("--quarter", default=None)
    a = ap.parse_args()
    q = a.quarter or "%sQ%d" % (a.date[:4], (int(a.date[4:6]) - 1) // 3 + 1)
    only = set(a.only.split(",")) if a.only else None
    skip = set(a.skip.split(",")) if a.skip else set()
    outdir = os.path.join("reports", q)
    os.makedirs(outdir, exist_ok=True)

    rows = []
    aborted = False
    for name, cmd, is_data, pat in STEPS:
        if (only and name not in only) or name in skip:
            rows.append((name, "SKIP", ""))
            continue
        print(">> %s" % name, flush=True)
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=1800)
        except subprocess.TimeoutExpired:
            rows.append((name, "TIMEOUT", ""))
            if is_data:
                aborted = True
                break
            continue
        out = (r.stdout or "") + ("\n" + r.stderr if r.returncode != 0 else "")
        key = ""
        for line in out.splitlines():
            if re.match(pat, line.strip()):
                key = line.strip()[:120]
        if name == "ips_check":
            status = "PASS" if r.returncode == 0 else "전환미완(FAIL항목 있음)"
        else:
            status = "OK" if r.returncode == 0 else "FAIL(exit %d)" % r.returncode
        rows.append((name, status, key))
        print("   %s %s" % (status, key), flush=True)
        if is_data and r.returncode != 0:
            print(out[-1500:])
            aborted = True
            break

    md = ["---", 'title: "%s 분기점검 체크리스트"' % q, "created: %s-%s-%s" % (a.date[:4], a.date[4:6], a.date[6:]),
          "tags: [퇴직연금, 분기점검, %s]" % q, "---", "",
          "# %s 분기점검 자동 체크리스트 (%s)" % (q, a.date), "",
          "| 단계 | 결과 | 핵심 지표 |", "|---|---|---|"]
    md += ["| %s | %s | %s |" % (n, s, k.replace("|", "/")) for n, s, k in rows]
    md += ["", "## 수동 확인 항목", "",
           "- [ ] 데이터 신선도 = 최신 영업일 (update_nav 말단일 확인)",
           "- [ ] 신규/탈락 펀드가 추천·보유에 영향 주는지 (diag_dropped_funds)",
           "- [ ] 위험비중 포털 공시값 대조 (분류기반 수치와 병기)",
           "- [ ] 밴드 이탈 시 조치 계획 (drift_check 괴리표 → IPS §3 현금흐름 리밸 우선)",
           "- [ ] 부담금·지출 목표 변동 시 lifecycle_sim 재실행",
           "", "> 명목/실질 병기(real_report)·비용 드래그(fee_drag)·IPS 대조 포함 시에만 분기점검 완료로 간주(§15).",
           "", "> 투자 권유 아님. 과거 성과는 미래를 보장하지 않음."]
    path = os.path.join(outdir, "(%s)_분기점검_체크리스트.md" % a.date)
    open(path, "w", encoding="utf-8").write("\n".join(md))
    print("\n체크리스트 저장: %s%s" % (path, "  (데이터 단계 실패로 중단됨)" if aborted else ""))
    sys.exit(1 if aborted else 0)


if __name__ == "__main__":
    main()
