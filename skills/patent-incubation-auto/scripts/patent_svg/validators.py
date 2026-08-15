# -*- coding: utf-8 -*-
"""patent_svg QA 게이트 — 완료 보고 전 issues 0건이 통과 조건.

검사: V-A 라벨 bbox 상호 충돌 / V-B 지시선-구조선 교차(대상 접점 제외) /
V-C viewBox 포함성 / V-D 텍스트 글리프 안전성(NFC, 허용 문자군).
"""
import re
import unicodedata


def _seg_intersect(p, q, a, b):
    def ccw(o, u, v):
        return (u[0] - o[0]) * (v[1] - o[1]) - (u[1] - o[1]) * (v[0] - o[0])
    d1, d2 = ccw(a, b, p), ccw(a, b, q)
    d3, d4 = ccw(p, q, a), ccw(p, q, b)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


_SAFE = re.compile(
    r"[ -~가-힣±×–≤≥∼"  # µ(U+00B5)는 렌더러 미지원 실측으로 제외 — mm 표기 권장
    r"λθφπΔ°′″]")


def validate(svg_path, ledger, viewbox):
    """ledger: LabelLedger.export() dict, viewbox: (x, y, w, h). 반환: issue 목록."""
    issues = []
    boxes = ledger["boxes"]
    # V-A 라벨 충돌 (배치기 실패 감시 — 넉지 한도 초과 등)
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            a, b = boxes[i], boxes[j]
            if a[0] < b[2] and a[2] > b[0] and a[1] < b[3] and a[3] > b[1]:
                issues.append(f"V-A 라벨 충돌: '{a[4]}' vs '{b[4]}'")
    # V-B 지시선이 구조선/광선을 관통하는지 (svgpathtools, 대상 접점 3px 제외)
    try:
        from svgpathtools import svg2paths2
        paths, attrs, _ = svg2paths2(svg_path)
        prim, leaders = [], []
        for p, at in zip(paths, attrs):
            c = at.get("class", "")
            (leaders if c == "leader" else prim if c in ("primitive", "beam") else []).append(p)
        for k, lp in enumerate(leaders):
            s, e = lp.start, lp.end
            hits = 0
            for pp in prim:
                # intersect 반환: [((T1, seg1, t1), (T2, seg2, t2)), ...]
                for pair in pp.intersect(lp):
                    T1 = pair[0][0] if isinstance(pair[0], (tuple, list)) else pair[0]
                    ix = pp.point(T1)
                    if abs(ix - e) > 3.0 and abs(ix - s) > 3.0:
                        hits += 1
            if hits > 0:
                issues.append(f"V-B 지시선 {k + 1} 구조 관통 {hits}건")
    except Exception as ex:  # svgpathtools 실패는 게이트 실패로 취급
        issues.append(f"V-B 검사 실행 실패: {ex}")
    # V-C viewBox 포함성 (라벨 bbox 기준 + 여백 4px)
    x0, y0, w, h = viewbox
    for (a0, b0, a1, b1, t) in boxes:
        if a0 < x0 + 4 or b0 < y0 + 4 or a1 > x0 + w - 4 or b1 > y0 + h - 4:
            issues.append(f"V-C viewBox 이탈: '{t}'")
    # V-D 글리프 안전성
    for (_, _, _, _, t) in boxes:
        if unicodedata.normalize("NFC", t) != t:
            issues.append(f"V-D NFD 한글: '{t}'")
        bad = [ch for ch in t if not _SAFE.match(ch)]
        if bad:
            issues.append(f"V-D 비허용 문자 {bad}: '{t}'")
    return issues
