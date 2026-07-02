#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_citations.py — 참고문헌 클린 게이트 (Phase 6c)

정책(2026-07 개정): 발명신고서 §9 참고문헌 리스트에는 **검증된 실제 문헌의 서지
정보만** 기재한다. (정합 확인!)/[정정:...]/(삭제) 등 마커·편집문구는 리스트에
넣지 않으며, 검증 이력은 reference_verification.json(audit trail)에만 남긴다.

이 게이트가 강제하는 것:
  1. 참고문헌 리스트에 편집문구(정합 확인/정정/삭제/불일치/확인 불가/수동 확인)가
     없을 것 (Rule 1 클린 리스트).
  2. 모든 참고문헌이 reference_verification.json의 검증된 항목과 DOI 또는 특허번호로
     매칭될 것 (실제 검증된 문헌만).
  3. json에서 removed 로 표기된 문헌의 키가 리스트에 나타나지 않을 것.

사용법:
  python verify_citations.py --md <disclosure.md> --verification <reference_verification.json>

종료 코드: 0 통과 / 1 위반 / 2 구조 오류(파일 부재·참고문헌 미검출)
"""
from __future__ import annotations
import argparse
import json
import re
import sys

EDIT_PHRASES = ("정합 확인", "정정", "삭제", "정합 불일치", "확인 불가", "수동 확인", "정합 부분")
BACKED = {"verified", "corrected", "corrected_title", "partial"}
REMOVED = {"removed", "unverifiable", "mismatch"}

REF_LINE = re.compile(r"^\s*-\s*\[(\d+)\]\s*(.+)$")
DOI_RE = re.compile(r"10\.\d{4,}/[^\s\"\)\],]+")
KR_RE = re.compile(r"10-\d{4}-\d{6,7}|10-\d{5,7}")


def norm_doi(d: str) -> str:
    return d.lower().rstrip(".,);]")


def extract_keys(text: str) -> set[str]:
    keys = set()
    for d in DOI_RE.findall(text):
        keys.add("doi:" + norm_doi(d))
    for k in KR_RE.findall(text):
        keys.add("kr:" + k.replace("-", ""))
    return keys


def main() -> int:
    ap = argparse.ArgumentParser(description="참고문헌 클린 게이트")
    ap.add_argument("--md", required=True)
    ap.add_argument("--verification", required=True)
    args = ap.parse_args()

    try:
        with open(args.verification, encoding="utf-8") as f:
            vj = json.load(f)
    except FileNotFoundError:
        print(f"FAIL(2): reference_verification.json 없음 ({args.verification}) — Phase 6c 미실행")
        return 2
    except json.JSONDecodeError as e:
        print(f"FAIL(2): verification JSON 파싱 실패 — {e}")
        return 2

    verified_keys, removed_keys = set(), set()
    for c in vj.get("citations", []):
        blob = json.dumps(c, ensure_ascii=False)
        ks = extract_keys(blob)
        st = c.get("status")
        if st in BACKED:
            verified_keys |= ks
        elif st in REMOVED:
            removed_keys |= ks

    try:
        with open(args.md, encoding="utf-8") as f:
            md_lines = f.read().split("\n")
    except FileNotFoundError:
        print(f"FAIL(2): MD 파일 없음 ({args.md})")
        return 2

    refs = [(m.group(1), m.group(2)) for l in md_lines if (m := REF_LINE.match(l))]
    if not refs:
        print("FAIL(2): 참고문헌('- [N] ...') 미검출")
        return 2

    errors = []
    for rid, body in refs:
        # 1. 편집문구 금지
        found = [p for p in EDIT_PHRASES if p in body]
        if found:
            errors.append(f"[{rid}] 편집문구 잔존 {found} → 클린 리스트 위반")
        # 2. 검증 매칭
        ks = extract_keys(body)
        if not ks:
            errors.append(f"[{rid}] DOI/특허번호 미검출 → 서지 식별 불가(검증 매칭 불능)")
        elif not (ks & verified_keys):
            errors.append(f"[{rid}] 검증된 문헌과 매칭 안 됨(keys={sorted(ks)}) → 미검증 문헌 의심")
        # 3. removed 문헌 키 재등장 금지
        if ks & removed_keys:
            errors.append(f"[{rid}] removed 처리된 문헌 키가 리스트에 존재")

    if errors:
        print(f"FAIL(1): 참고문헌 클린 게이트 위반 ({len(errors)}건)")
        for e in errors:
            print("  -", e)
        return 1

    print(f"PASS: 참고문헌 {len(refs)}건 모두 클린(편집문구 없음) + 검증 문헌과 매칭됨")
    return 0


if __name__ == "__main__":
    sys.exit(main())
