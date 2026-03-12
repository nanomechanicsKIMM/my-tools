#!/usr/bin/env python3
"""build_tor.py - 과업지시서(TOR) HWPX 자동 생성

Usage:
    PYTHONUTF8=1 uv run python build_tor.py --input tor_data.json --output result.hwpx
    PYTHONUTF8=1 uv run python build_tor.py --title "과업명" --dept "부서명" --author "홍길동" --output result.hwpx
"""

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent

SAMPLE_HWPX = str(_SKILL_DIR / "assets" / "TermsOfReference_sample.hwpx")
UNPACK_PY = str(_SCRIPT_DIR / "office" / "unpack.py")
PACK_PY = str(_SCRIPT_DIR / "office" / "pack.py")
VALIDATE_PY = str(_SCRIPT_DIR / "validate.py")

# PREFIX에서 치환할 원본 플레이스홀더 텍스트
PLACEHOLDER_DEPT = "나노디스플레이연구실"
PLACEHOLDER_AUTHOR = "김재현"
PLACEHOLDER_TITLE = "뇌졸중 환자 재활훈련 프로그램 개발"

# PREFIX와 BODY를 구분하는 마커 (페이지 브레이크 단락)
PAGE_BREAK_MARKER = '<hp:p id="0" paraPrIDRef="7" styleIDRef="2" pageBreak="1"'


def p_heading(pid, text):
    """섹션 제목 단락 (paraPrIDRef=21 CENTER, charPrIDRef=16 13pt Bold)"""
    return (
        f'  <hp:p id="{pid}" paraPrIDRef="21" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">\n'
        f'    <hp:run charPrIDRef="16">\n'
        f'      <hp:t>{escape(text)}</hp:t>\n'
        f'    </hp:run>\n'
        f'  </hp:p>'
    )


def p_body(pid, text, para_ref="21"):
    """본문 내용 단락 (charPrIDRef=17 13pt Regular, para_ref 지정 가능)"""
    return (
        f'  <hp:p id="{pid}" paraPrIDRef="{para_ref}" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">\n'
        f'    <hp:run charPrIDRef="17">\n'
        f'      <hp:t>{escape(text)}</hp:t>\n'
        f'    </hp:run>\n'
        f'  </hp:p>'
    )


def p_empty(pid):
    """빈 줄 단락 (paraPrIDRef=34, charPrIDRef=16)"""
    return (
        f'  <hp:p id="{pid}" paraPrIDRef="34" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">\n'
        f'    <hp:run charPrIDRef="16"/>\n'
        f'  </hp:p>'
    )


def p_misc(pid, text):
    """기타 단락 (paraPrIDRef=36, 번호 bold + 내용 regular)"""
    return (
        f'  <hp:p id="{pid}" paraPrIDRef="36" styleIDRef="0" '
        f'pageBreak="0" columnBreak="0" merged="0">\n'
        f'    <hp:run charPrIDRef="16">\n'
        f'      <hp:t>10. </hp:t>\n'
        f'    </hp:run>\n'
        f'    <hp:run charPrIDRef="26">\n'
        f'      <hp:t>{escape(text)}</hp:t>\n'
        f'    </hp:run>\n'
        f'  </hp:p>'
    )


class IdGen:
    def __init__(self, start=1000000100):
        self._n = start

    def next(self):
        v = self._n
        self._n += 1
        return v


def build_body(data):
    """TOR 데이터로부터 10개 섹션 BODY XML 생성"""
    paras = []
    g = IdGen()

    def h(text):
        paras.append(p_heading(g.next(), text))

    def b(text, para_ref="21"):
        paras.append(p_body(g.next(), text, para_ref))

    def e():
        paras.append(p_empty(g.next()))

    # 1. 과업명
    h(f"1. 과 업 명 : {data['title']}")
    e()

    # 2. 목적
    h("2. 목    적")
    b(data.get("purpose", ""))
    e()

    # 3. 과업기간
    h("3. 과업기간")
    b(f"   : {data.get('period', '')}")
    e()

    # 4. 과업범위
    h("4. 과업범위")
    b("  가. 주요내용", "24")
    if data.get("scope_summary"):
        b(f"    ○ {data['scope_summary']}", "24")
    b("  나. 과업의 범위")
    for item in data.get("scope_items", []):
        b(f"    {item}")
    e()

    # 5. 과업내용
    # ○ 항목은 paraPrIDRef=39, 나머지(가./나. 등)는 21
    h("5. 과업내용")
    for item in data.get("content_items", []):
        if item.lstrip().startswith("○"):
            b(item, "39")
        else:
            b(item)
    e()

    # 6. 검수 및 결과물 제출
    # 가.→paraPrIDRef=30, 나.→31, 이후→21
    h("6. 검수 및 결과물 제출")
    sec6_refs = ["30", "31"] + ["21"] * 100
    for i, item in enumerate(data.get("deliverables", [])):
        b(f"   {item}", sec6_refs[i])
    e()

    # 7. 책임 및 의무
    # 가.→paraPrIDRef=32, 나.→33, 이후→21
    h("7. 책임 및 의무")
    sec7_refs = ["32", "33"] + ["21"] * 100
    for i, item in enumerate(data.get("responsibilities", [])):
        b(f"   {item}", sec7_refs[i])
    e()

    # 8. 자격조건
    h('8. "을"은 다음의 자격조건을 갖추어야 한다.')
    for item in data.get("qualifications", []):
        b(f"  {item}")
    e()

    # 9. 계약해지 및 해제조건
    h("9. 계약해지 및 해제조건")
    for item in data.get("termination_conditions", []):
        b(f"  {item}")
    e()

    # 10. 기타
    misc = data.get(
        "misc",
        '기타 계약에 규정되지 않은 사항에 대하여 이의가 발생한 경우에는 "갑"의 결정에 따른다.',
    )
    paras.append(p_misc(g.next(), misc))

    return "\n".join(paras)


def run(cmd):
    result = subprocess.run(cmd, check=True)
    return result


def main():
    parser = argparse.ArgumentParser(description="과업지시서 HWPX 자동 생성")
    parser.add_argument("--input", help="JSON 입력 파일 경로")
    parser.add_argument("--output", required=True, help="출력 HWPX 파일 경로")
    parser.add_argument("--title", help="과업명 (JSON 우선)")
    parser.add_argument("--dept", help="부서명 (JSON 우선)")
    parser.add_argument("--author", help="작성자 (JSON 우선)")
    parser.add_argument("--period", help="과업기간 (JSON 우선)")
    args = parser.parse_args()

    # 데이터 로드
    if args.input:
        with open(args.input, encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {}

    # CLI 인수로 덮어쓰기 (JSON이 없을 때 보완)
    for key, val in [
        ("title", args.title),
        ("department", args.dept),
        ("author", args.author),
        ("period", args.period),
    ]:
        if val and not data.get(key):
            data[key] = val

    # 필수 필드 확인
    for field in ["title", "department", "author"]:
        if not data.get(field):
            print(f"Error: '{field}' 필드가 필요합니다.", file=sys.stderr)
            sys.exit(1)

    output_path = Path(args.output).resolve()

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 샘플 HWPX 언팩
        run([sys.executable, UNPACK_PY, SAMPLE_HWPX, tmpdir])

        # 2. section0.xml 읽기
        sec_path = Path(tmpdir) / "Contents" / "section0.xml"
        content = sec_path.read_text(encoding="utf-8")

        # 3. PREFIX 내 플레이스홀더 치환
        content = content.replace(PLACEHOLDER_DEPT, data["department"])
        content = content.replace(PLACEHOLDER_AUTHOR, data["author"])
        content = content.replace(PLACEHOLDER_TITLE, data["title"])

        # 4. PREFIX / PAGE_BREAK_PARA 추출
        idx = content.find(PAGE_BREAK_MARKER)
        if idx < 0:
            print("Error: 페이지 브레이크 마커를 찾을 수 없습니다.", file=sys.stderr)
            sys.exit(1)

        prefix = content[:idx]
        rest = content[idx:]

        # 페이지 브레이크 단락 (첫 </hp:p> 까지) 추출
        end_pb = rest.find("</hp:p>") + len("</hp:p>")
        page_break_para = rest[:end_pb]

        # 5. 새 BODY 생성
        body_xml = build_body(data)

        # 6. 새 section0.xml 조합: PREFIX + PAGE_BREAK_PARA + BODY + 닫는 태그
        new_content = prefix + page_break_para + "\n" + body_xml + "\n</hs:sec>"
        sec_path.write_text(new_content, encoding="utf-8")

        # 7. HWPX 재조립
        run([sys.executable, PACK_PY, tmpdir, str(output_path)])

    # 8. 구조 검증
    run([sys.executable, VALIDATE_PY, str(output_path)])

    print(f"\n생성 완료: {output_path}")


if __name__ == "__main__":
    main()
