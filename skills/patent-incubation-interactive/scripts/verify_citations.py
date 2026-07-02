#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_citations.py — Phase 6c 정합 마커 강제 게이트

발명내용설명서 MD의 모든 (정합 확인!) 마커가 reference_verification.json의
실제 검증 레코드로 뒷받침되는지 결정적으로 검사한다. 하나라도 위조/불일치면
비정상 종료(exit != 0)한다.

이 스크립트의 존재 이유:
  최초 patent-incubation run에서 Phase 6c(인용 검증)가 실행되지 않았는데도
  Phase 6 작성 에이전트가 참고문헌 20건 전부에 (정합 확인!) 마커를 임의로
  부착했다. CrossRef 재검증 결과 6개 학술 DOI가 전부 404/무관논문/제목오류였다.
  즉 "마커=검증"이라는 신뢰가 깨진 것. 이 스크립트는 마커를 JSON 증거에
  묶어 그 신뢰를 결정적으로 복원한다.

사용법:
  python verify_citations.py --md <disclosure.md> --verification <reference_verification.json>

종료 코드:
  0  모든 마커가 검증 레코드와 정합 (PASS)
  1  마커-레코드 불일치 존재 (FAIL)
  2  검증 파일 부재 또는 MD에 참고문헌 없음 (Phase 6c 미실행 신호)
"""
from __future__ import annotations
import argparse
import json
import re
import sys

CONFIRMED_KEY = "정합 확인"          # (정합 확인!) / (정합 확인!, CrossRef) ...
UNVERIFIED_KEYS = ("정합 불일치", "확인 불가")
PARTIAL_KEY = "정합 부분 확인"

# reference_verification.json status 값 중 "검증됨(마커 허용)" 부류
BACKED = {"verified", "corrected", "corrected_title", "partial"}
# "검증 안 됨(마커 불허)" 부류
UNBACKED = {"removed", "unverifiable", "mismatch", "manual_review", "skipped"}

# 참고문헌 리스트 항목: 줄 시작(공백 허용) + "- [N] ..." (인라인 인용 [N] 은 제외)
REF_LINE = re.compile(r"^\s*-\s*\[(\d+)\]\s*(.+)$")


def classify_marker(body: str) -> str:
    has_confirmed = CONFIRMED_KEY in body
    has_unverified = any(k in body for k in UNVERIFIED_KEYS)
    if has_unverified:            # 불일치/확인불가 가 있으면 우선 (혼재 시 보수적)
        return "unverified"
    if has_confirmed:
        return "confirmed"
    if PARTIAL_KEY in body:
        return "partial"
    return "none"


def parse_refs(md_text: str) -> dict[str, str]:
    refs: dict[str, str] = {}
    for line in md_text.splitlines():
        m = REF_LINE.match(line)
        if not m:
            continue
        rid, body = m.group(1), m.group(2)
        refs[rid] = classify_marker(body)
    return refs


def main() -> int:
    ap = argparse.ArgumentParser(description="Phase 6c 정합 마커 강제 게이트")
    ap.add_argument("--md", required=True, help="발명내용설명서 MD 경로")
    ap.add_argument("--verification", required=True, help="reference_verification.json 경로")
    args = ap.parse_args()

    try:
        with open(args.verification, encoding="utf-8") as f:
            vj = json.load(f)
    except FileNotFoundError:
        print(f"FAIL(2): reference_verification.json 없음 ({args.verification}) — Phase 6c 미실행")
        return 2
    except json.JSONDecodeError as e:
        print(f"FAIL(2): reference_verification.json 파싱 실패 — {e}")
        return 2

    vmap = {str(c.get("id")): c for c in vj.get("citations", [])}

    try:
        with open(args.md, encoding="utf-8") as f:
            refs = parse_refs(f.read())
    except FileNotFoundError:
        print(f"FAIL(2): MD 파일 없음 ({args.md})")
        return 2

    if not refs:
        print("FAIL(2): MD에서 참고문헌 항목('- [N] ...')을 찾지 못함 — Phase 6c 대상 없음")
        return 2

    errors: list[str] = []
    for rid, marker in sorted(refs.items(), key=lambda x: int(x[0])):
        entry = vmap.get(rid)
        status = (entry or {}).get("status", None)
        source = (entry or {}).get("source", "none")
        if marker == "confirmed":
            if entry is None:
                errors.append(f"[{rid}] (정합 확인!)인데 검증 레코드 없음 → 마커 위조")
            elif status in UNBACKED:
                errors.append(f"[{rid}] (정합 확인!)인데 status={status} → 검증되지 않음")
            elif source in (None, "none", ""):
                errors.append(f"[{rid}] (정합 확인!)인데 source={source!r} → 검증 근거 없음")
        elif marker == "unverified":
            if entry is not None and status in BACKED and source not in (None, "none", ""):
                errors.append(f"[{rid}] (정합 불일치/확인 불가)인데 검증은 status={status} → 마커 과소표기")
        elif marker == "none":
            errors.append(f"[{rid}] 정합 마커 없음 → Phase 6c 마커 누락")

    # 커버리지: 검증 레코드에는 있으나 MD 참고문헌에 없는 항목
    for rid in vmap:
        if rid not in refs:
            errors.append(f"[{rid}] 검증 레코드에는 있으나 MD 참고문헌에 없음")

    if errors:
        print(f"FAIL(1): 인용 정합 마커 검증 실패 ({len(errors)}건)")
        for e in errors:
            print("  -", e)
        return 1

    print(f"PASS: 참고문헌 {len(refs)}건 모두 검증 레코드와 정합")
    return 0


if __name__ == "__main__":
    sys.exit(main())
