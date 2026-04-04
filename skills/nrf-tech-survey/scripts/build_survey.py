#!/usr/bin/env python3
"""NRF 기술수요조사서 HWPX 빌드 스크립트.

원본 양식 HWPX를 템플릿으로 사용하여, JSON 입력 데이터로 동적 필드를 채운
기술수요조사서 HWPX 파일을 생성한다.

Usage:
    PYTHONUTF8=1 uv run python build_survey.py --input data.json --output result.hwpx
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from xml.sax.saxutils import escape

from lxml import etree

# ── 경로 설정 ──────────────────────────────────────────────
_SCRIPT_DIR = Path(__file__).resolve().parent
_SKILL_DIR = _SCRIPT_DIR.parent
TEMPLATE_HWPX = _SKILL_DIR / "assets" / "NRF_기술수요조사서_양식.hwpx"
UNPACK_PY = Path("C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/office/unpack.py")
PACK_PY = Path("C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/office/pack.py")
FIX_NS_PY = Path("C:/Users/JHKIM/.claude/skills/hwpx/scripts/fix_namespaces.py")
VALIDATE_PY = Path("C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/validate.py")

# ── 네임스페이스 ───────────────────────────────────────────
HP = "http://www.hancom.co.kr/hwpml/2011/paragraph"
NS = {"hp": HP}

# ── 테이블 인덱스 (section0.xml 기준, v2 양식) ────────────
TBL_MAIN = 1       # 기본정보 36행
TBL_TECH = 2       # 핵심기술 내용/기능 2행
TBL_GOAL = 3       # 목표 및 내용 4행
TBL_NEED = 4       # 제안취지 1행
TBL_TREND = 5      # 국내외 동향 2행
TBL_EFFECT = 6     # 파급효과/특이사항 2행
TBL_BUDGET = 7     # 예산 2행

# ── 기술후보군 매핑: 기술명 → (checkbox_row, checkbox_col) in tbl[4] ──
TECH_CANDIDATES = {
    # 도전형 (r4~r17)
    "환경 적응형 자율연산 플랫폼":          (5, 0),
    "글래스 프리 공간 지능 플랫폼":          (5, 1),
    "정보 저장‧처리용 바이오 컴퓨팅":        (7, 0),
    "상황 이해형 차세대 감각 입력‧해석":      (7, 1),
    "다중감각-인간증강 센서-인터페이스":      (9, 0),
    "극한 환경 제조":                       (9, 1),
    "그린 희토류 자원화":                    (11, 0),
    "단백질 미세구동체 집단 행동 설계":       (11, 1),
    "구조 설계 기반 스마트 메타물질":         (13, 0),
    "솔리드 스테이트 냉각":                  (13, 1),
    "협력형 에너지 하베스팅":                (15, 0),
    "양자에너지 전송(QET)":                  (15, 1),
    "도전형 자율주제":                       (17, 0),
    # 유망신기술형 (r18~r23)
    "상태유지형 뉴로모픽 컴퓨팅":            (19, 0),
    "인공근육 액츄에이터":                   (19, 1),
    "제로 파워 모션 디스플레이":              (21, 0),
    "구조형 배터리 복합 소재":               (21, 1),
    "해수 기반 에너지 저장‧전환":            (23, 0),
    "유망신기술형 자율주제":                  (23, 1),
}

# ── 지원유형 체크박스 매핑 ─────────────────────────────────
SUPPORT_TYPE_MAP = {
    "도전형": (1, 0),       # tbl[4] r1 c0
    "유망신기술형": (3, 0),  # tbl[4] r3 c0
}


# ══════════════════════════════════════════════════════════
#  헬퍼 함수
# ══════════════════════════════════════════════════════════

def run_cmd(cmd):
    """subprocess 실행, 실패 시 종료."""
    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {' '.join(str(c) for c in cmd)}", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        sys.exit(1)
    return result


def find_cell(tables, tbl_idx, row_idx, col_idx):
    """테이블/행/열 인덱스로 hp:tc 요소를 찾는다."""
    tbl = tables[tbl_idx]
    rows = tbl.findall("hp:tr", NS)
    if row_idx >= len(rows):
        raise IndexError(f"tbl[{tbl_idx}] has {len(rows)} rows, requested r{row_idx}")
    cells = rows[row_idx].findall("hp:tc", NS)
    if col_idx >= len(cells):
        raise IndexError(f"tbl[{tbl_idx}] r{row_idx} has {len(cells)} cells, requested c{col_idx}")
    return cells[col_idx]


def get_first_run(cell):
    """셀의 첫 번째 hp:run 요소를 반환."""
    return cell.find(f".//{{{HP}}}run")


def set_simple_text(cell, text, char_pr_override=None, para_pr_override=None):
    """셀을 단일 단락/단일 run으로 재구성하여 텍스트를 설정한다.

    - char_pr_override: 폰트 스타일 변경 (charPrIDRef)
    - para_pr_override: 문단 정렬 변경 (paraPrIDRef, 예: "20"=가운데)
    """
    sublist = cell.find(f"{{{HP}}}subList")
    if sublist is None:
        raise ValueError("Cell has no hp:subList element")

    first_p = sublist.find(f"{{{HP}}}p")
    para_pr = para_pr_override or (first_p.get("paraPrIDRef", "21") if first_p is not None else "21")
    style_id = first_p.get("styleIDRef", "22") if first_p is not None else "22"
    first_run = first_p.find(f"{{{HP}}}run") if first_p is not None else None
    char_pr = char_pr_override or (first_run.get("charPrIDRef", "8") if first_run is not None else "8")

    for p in list(sublist.findall(f"{{{HP}}}p")):
        sublist.remove(p)

    p = etree.SubElement(sublist, f"{{{HP}}}p")
    p.set("id", "2147483648")
    p.set("paraPrIDRef", para_pr)
    p.set("styleIDRef", style_id)
    p.set("pageBreak", "0")
    p.set("columnBreak", "0")
    p.set("merged", "0")

    run_el = etree.SubElement(p, f"{{{HP}}}run")
    run_el.set("charPrIDRef", char_pr)
    t_el = etree.SubElement(run_el, f"{{{HP}}}t")
    t_el.text = text


def set_cell_height(cell, height):
    """셀의 높이(hp:cellSz height)를 변경한다."""
    cell_sz = cell.find(f"{{{HP}}}cellSz")
    if cell_sz is not None:
        cell_sz.set("height", str(height))


def set_cell_margin(cell, left=None, right=None, top=None, bottom=None):
    """셀의 내부 여백(hp:cellMargin)을 변경한다. 단위: HWP (1mm ≈ 283)."""
    margin = cell.find(f"{{{HP}}}cellMargin")
    if margin is None:
        return
    if left is not None:
        margin.set("left", str(left))
    if right is not None:
        margin.set("right", str(right))
    if top is not None:
        margin.set("top", str(top))
    if bottom is not None:
        margin.set("bottom", str(bottom))


def set_row_height(tables, tbl_idx, row_idx, height):
    """행 내 모든 셀의 높이를 일괄 변경한다."""
    tbl = tables[tbl_idx]
    rows = tbl.findall("hp:tr", NS)
    if row_idx >= len(rows):
        return
    for tc in rows[row_idx].findall("hp:tc", NS):
        cell_sz = tc.find(f"{{{HP}}}cellSz")
        if cell_sz is not None:
            cell_sz.set("height", str(height))


def replace_checkbox(cell, checked=True):
    """셀 내 □(U+25A1)를 ■(U+25A0)로 교체."""
    for t_el in cell.iter(f"{{{HP}}}t"):
        if t_el.text and "□" in t_el.text:
            t_el.text = t_el.text.replace("□", "■" if checked else "□")
            return True
    return False


def set_multiline_text(cell, text, para_pr_override=None):
    """멀티라인 텍스트를 셀에 삽입한다.
    입력 텍스트의 각 줄이 별도 hp:p 요소가 된다.
    줄바꿈(\\n)으로 구분.
    para_pr_override: 문단 스타일 오버라이드 (예: 내어쓰기 적용)
    """
    sublist = cell.find(f"{{{HP}}}subList")
    if sublist is None:
        return

    # 첫 번째 기존 단락에서 스타일 참조 추출
    first_p = sublist.find(f"{{{HP}}}p")
    para_pr = para_pr_override or (first_p.get("paraPrIDRef", "21") if first_p is not None else "21")
    style_id = first_p.get("styleIDRef", "22") if first_p is not None else "22"
    first_run = first_p.find(f"{{{HP}}}run") if first_p is not None else None
    char_pr = first_run.get("charPrIDRef", "17") if first_run is not None else "17"

    # 기존 단락 모두 제거
    for p in list(sublist.findall(f"{{{HP}}}p")):
        sublist.remove(p)

    # 새 단락 생성 (lineseg 없이 — HWP가 열 때 자동 계산)
    lines = text.split("\n") if text else [""]
    for line in lines:
        p = etree.SubElement(sublist, f"{{{HP}}}p")
        p.set("id", "2147483648")
        p.set("paraPrIDRef", para_pr)
        p.set("styleIDRef", style_id)
        p.set("pageBreak", "0")
        p.set("columnBreak", "0")
        p.set("merged", "0")

        run_el = etree.SubElement(p, f"{{{HP}}}run")
        run_el.set("charPrIDRef", char_pr)
        t_el = etree.SubElement(run_el, f"{{{HP}}}t")
        t_el.text = line


# ══════════════════════════════════════════════════════════
#  메인 빌드 로직
# ══════════════════════════════════════════════════════════

def build(data: dict, output_path: Path):
    """JSON 데이터를 기반으로 기술수요조사서 HWPX를 생성한다."""

    with tempfile.TemporaryDirectory() as tmpdir:
        # 1. 템플릿 언팩
        run_cmd([sys.executable, str(UNPACK_PY), str(TEMPLATE_HWPX), tmpdir])

        # 2. header.xml에 내어쓰기 25pt paraPr 추가 (id=50)
        HH = "http://www.hancom.co.kr/hwpml/2011/head"
        HC = "http://www.hancom.co.kr/hwpml/2011/core"
        hdr_path = Path(tmpdir) / "Contents" / "header.xml"
        hdr_tree = etree.parse(str(hdr_path))
        hdr_root = hdr_tree.getroot()
        # paraPrs 컨테이너 찾기 (hp:switch/hp:case 내부 또는 직접)
        para_prs = None
        for el in hdr_root.iter():
            if el.tag.endswith("}paraPr") and el.get("id") == "0":
                para_prs = el.getparent()
                break
        if para_prs is not None:
            # 기존 paraPr id=0 (JUSTIFY, 160%) 복제 후 내어쓰기 추가
            new_pr = etree.SubElement(para_prs, f"{{{HH}}}paraPr")
            new_pr.set("id", "50")
            new_pr.set("tabPrIDRef", "0")
            new_pr.set("condense", "0")
            new_pr.set("fontLineHeight", "0")
            new_pr.set("snapToGrid", "1")
            new_pr.set("suppressLineNumbers", "0")
            new_pr.set("checked", "0")
            align = etree.SubElement(new_pr, f"{{{HH}}}align")
            align.set("horizontal", "JUSTIFY")
            align.set("vertical", "BASELINE")
            heading = etree.SubElement(new_pr, f"{{{HH}}}heading")
            heading.set("type", "NONE")
            heading.set("idRef", "0")
            heading.set("level", "0")
            brk = etree.SubElement(new_pr, f"{{{HH}}}breakSetting")
            brk.set("breakLatinWord", "KEEP_WORD")
            brk.set("breakNonLatinWord", "KEEP_WORD")
            brk.set("widowOrphan", "0")
            brk.set("keepWithNext", "0")
            brk.set("keepLines", "0")
            brk.set("pageBreakBefore", "0")
            brk.set("lineWrap", "BREAK")
            auto_sp = etree.SubElement(new_pr, f"{{{HH}}}autoSpacing")
            auto_sp.set("eAsianEng", "0")
            auto_sp.set("eAsianNum", "0")
            # 내어쓰기 25pt(intent=-2500), 좌우여백 5pt(500)
            margin = etree.SubElement(new_pr, f"{{{HH}}}margin")
            for tag, val in [("intent", "-2500"), ("left", "500"),
                             ("right", "500"), ("prev", "0"), ("next", "0")]:
                m = etree.SubElement(margin, f"{{{HC}}}{tag}")
                m.set("value", val)
                m.set("unit", "HWPUNIT")
            ls = etree.SubElement(new_pr, f"{{{HH}}}lineSpacing")
            ls.set("type", "PERCENT")
            ls.set("value", "130")
            ls.set("unit", "HWPUNIT")
            border = etree.SubElement(new_pr, f"{{{HH}}}border")
            border.set("borderFillIDRef", "2")
            for a in ["offsetLeft", "offsetRight", "offsetTop", "offsetBottom"]:
                border.set(a, "0")
            border.set("connect", "0")
            border.set("ignoreMargin", "0")
            # itemCnt 업데이트
            para_prs.set("itemCnt", str(len(para_prs.findall(f"{{{HH}}}paraPr"))))
            hdr_tree.write(str(hdr_path), encoding="utf-8",
                           xml_declaration=True, pretty_print=True)
        HANGING_PARA_PR = "50"

        # 3. section0.xml 파싱
        sec_path = Path(tmpdir) / "Contents" / "section0.xml"
        tree = etree.parse(str(sec_path))
        root = tree.getroot()
        tables = root.findall(f".//{{{HP}}}tbl")

        # ── tbl[4]: 기본정보 ──────────────────────────────

        # 지원유형 체크박스
        support_type = data.get("지원유형", "")
        if support_type in SUPPORT_TYPE_MAP:
            r, c = SUPPORT_TYPE_MAP[support_type]
            cell = find_cell(tables, TBL_MAIN, r, c)
            replace_checkbox(cell, checked=True)

        # 기술후보군 체크박스
        for tech_name in data.get("기술후보군", []):
            if tech_name in TECH_CANDIDATES:
                r, c = TECH_CANDIDATES[tech_name]
                cell = find_cell(tables, TBL_MAIN, r, c)
                replace_checkbox(cell, checked=True)

        # 융합 분야 대분류 (r25 c2, c3)
        fus = data.get("융합분야", {})
        for i, val in enumerate(fus.get("대분류", [])[:2]):
            cell = find_cell(tables, TBL_MAIN, 25, 2 + i)
            set_simple_text(cell, val)

        # 융합 분야 중분류 (r26 c1~c3)
        for i, val in enumerate(fus.get("중분류", [])[:4]):
            cell = find_cell(tables, TBL_MAIN, 26, 1 + i)
            set_simple_text(cell, val)

        # 기술명 (r28 c1) — 행 높이 1/3 축소 + 가운데 맞춤
        if data.get("기술명"):
            cell = find_cell(tables, TBL_MAIN, 28, 1)
            set_simple_text(cell, data["기술명"], para_pr_override="20")
            set_row_height(tables, TBL_MAIN, 28, 3300)

        # 핵심키워드 국문 (r29 c2) — 기울임 제거
        if data.get("키워드_국문"):
            cell = find_cell(tables, TBL_MAIN, 29, 2)
            set_simple_text(cell, data["키워드_국문"], char_pr_override="8")

        # 핵심키워드 영문 (r30 c1) — 기울임 제거
        if data.get("키워드_영문"):
            cell = find_cell(tables, TBL_MAIN, 30, 1)
            set_simple_text(cell, data["키워드_영문"], char_pr_override="8")

        # 연구개발개요 (r31 c1) — 양쪽 맞춤(paraPr "0") + 좌우 여백 5mm
        if data.get("연구개발개요"):
            cell = find_cell(tables, TBL_MAIN, 31, 1)
            set_simple_text(cell, data["연구개발개요"], para_pr_override="0")
            set_cell_margin(cell, left=1417, right=1417)

        # TRL 착수/종료 (r32 c1, c2) — 가운데 맞춤
        trl = data.get("TRL", {})
        if trl.get("착수") is not None:
            cell = find_cell(tables, TBL_MAIN, 32, 1)
            set_simple_text(cell, f"TRL {trl['착수']}", para_pr_override="20")
        if trl.get("종료") is not None:
            cell = find_cell(tables, TBL_MAIN, 32, 2)
            set_simple_text(cell, f"TRL {trl['종료']}", para_pr_override="20")

        # 제안자 정보
        proposer = data.get("제안자", {})
        proposer_fields = [
            ("기관명",     33, 2),
            ("성명",       34, 1),
            ("직장전화",   34, 3),
            ("이메일",     35, 1),
            ("휴대전화",   35, 3),
        ]
        for key, row, col in proposer_fields:
            val = proposer.get(key, "")
            if val:
                cell = find_cell(tables, TBL_MAIN, row, col)
                set_simple_text(cell, val)

        # 부서/직급은 '/'로 분리하여 줄바꿈 처리
        dept_val = proposer.get("부서직급", "")
        if dept_val:
            cell = find_cell(tables, TBL_MAIN, 33, 4)
            if "/" in dept_val:
                parts = dept_val.split("/")
                set_multiline_text(cell, "\n".join(parts))
            else:
                set_simple_text(cell, dept_val)

        # ── tbl[5]: 핵심기술 내용 / 기능범위 ─────────────

        # ── 규칙5: "1.기술개요" 이후 모든 내용 셀에 위아래 0.5줄 여백 ──
        # 0.5줄 ≈ 650 HWP단위 (10pt × 130% lineSpacing × 0.5)
        CELL_PAD = 650

        if data.get("핵심기술내용"):
            cell = find_cell(tables, TBL_TECH, 0, 0)
            set_multiline_text(cell, data["핵심기술내용"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        if data.get("기술기능범위"):
            cell = find_cell(tables, TBL_TECH, 1, 0)
            set_multiline_text(cell, data["기술기능범위"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        # ── tbl[3]: 목표 및 내용 ─────────────────────────

        if data.get("최종목표"):
            row0_cells = tables[TBL_GOAL].findall("hp:tr", NS)[0].findall("hp:tc", NS)
            last_cell = row0_cells[-1]
            set_simple_text(last_cell, data["최종목표"])
            set_cell_margin(last_cell, top=CELL_PAD, bottom=CELL_PAD)

        if data.get("1단계목표"):
            row1_cells = tables[TBL_GOAL].findall("hp:tr", NS)[1].findall("hp:tc", NS)
            target = row1_cells[-1]
            set_simple_text(target, f"(1단계) {data['1단계목표']}")
            set_cell_margin(target, top=CELL_PAD, bottom=CELL_PAD)

        if data.get("2단계목표"):
            row2_cells = tables[TBL_GOAL].findall("hp:tr", NS)[2].findall("hp:tc", NS)
            target = row2_cells[-1] if len(row2_cells) > 1 else row2_cells[0]
            set_simple_text(target, f"(2단계) {data['2단계목표']}")
            set_cell_margin(target, top=CELL_PAD, bottom=CELL_PAD)

        if data.get("연구개발내용"):
            row3_cells = tables[TBL_GOAL].findall("hp:tr", NS)[3].findall("hp:tc", NS)
            target = row3_cells[-1]
            set_multiline_text(target, data["연구개발내용"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(target, top=CELL_PAD, bottom=CELL_PAD)

        # ── tbl[4]: 제안취지 ─────────────────────────────

        if data.get("제안취지"):
            cell = find_cell(tables, TBL_NEED, 0, 0)
            set_multiline_text(cell, data["제안취지"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        # ── tbl[5]: 국내외 동향 ──────────────────────────

        if data.get("국내동향"):
            cell = find_cell(tables, TBL_TREND, 0, 1)
            set_multiline_text(cell, data["국내동향"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        if data.get("해외동향"):
            cell = find_cell(tables, TBL_TREND, 1, 1)
            set_multiline_text(cell, data["해외동향"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        # ── tbl[6]: 파급효과 / 특이사항 ──────────────────

        if data.get("파급효과"):
            cell = find_cell(tables, TBL_EFFECT, 0, 1)
            set_multiline_text(cell, data["파급효과"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        if data.get("특이사항"):
            cell = find_cell(tables, TBL_EFFECT, 1, 1)
            set_multiline_text(cell, data["특이사항"], para_pr_override=HANGING_PARA_PR)
            set_cell_margin(cell, top=CELL_PAD, bottom=CELL_PAD)

        # ── tbl[7]: 예산 ─────────────────────────────────

        budget = data.get("예산", {})
        budget_fields = [
            ("1단계", 1, 1),
            ("2단계", 1, 2),
            ("합계",  1, 3),
        ]
        for key, row, col in budget_fields:
            val = budget.get(key)
            if val is not None:
                cell = find_cell(tables, TBL_BUDGET, row, col)
                set_simple_text(cell, f"{val}억원")

        # 3. 수정된 XML 저장
        tree.write(
            str(sec_path),
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=True,
        )

        # 4. 팩
        run_cmd([sys.executable, str(PACK_PY), tmpdir, str(output_path)])

    # 5. 네임스페이스 후처리
    run_cmd([sys.executable, str(FIX_NS_PY), str(output_path)])

    # 6. 검증
    result = run_cmd([sys.executable, str(VALIDATE_PY), str(output_path)])
    print(result.stdout)

    print(f"✅ 생성 완료: {output_path}")


# ══════════════════════════════════════════════════════════
#  CLI
# ══════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="NRF 기술수요조사서 HWPX 생성"
    )
    parser.add_argument("--input", "-i", required=True, help="JSON 입력 파일 경로")
    parser.add_argument("--output", "-o", required=True, help="출력 HWPX 파일 경로")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: 입력 파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    if not TEMPLATE_HWPX.exists():
        print(f"ERROR: 템플릿을 찾을 수 없습니다: {TEMPLATE_HWPX}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    # _context, _scholar 메타데이터는 빌드에 사용하지 않음
    data.pop("_context", None)
    data.pop("_scholar", None)

    output_path = Path(args.output)
    build(data, output_path)


if __name__ == "__main__":
    main()
