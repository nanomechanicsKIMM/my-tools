#!/usr/bin/env python
"""
HWPX 변환 스크립트 — 전체 셀 내용 교체 + lineseg 계산 + 이미지 삽입
발명내용설명서 disclosure.md → KIMM 양식 HWPX

Usage:
    python convert_hwpx.py --disclosure <md_path> --output <hwpx_path> [--diagrams <dir>]

환경변수 또는 인자로 경로를 지정한다. 기본값은 SKILL_ROOT 기준.
"""
import zipfile
import shutil
import os
import re
import math
import sys
import argparse
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from copy import deepcopy
import glob
import random

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ─── 기본 경로 (스킬 기준) ─────────────────────────────
SKILL_ROOT = os.environ.get(
    "SKILL_ROOT",
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
TEMPLATE_PATH = os.path.join(SKILL_ROOT, "assets", "[KIMM]직무발명내용설명서_양식.hwpx")

HWPX_SKILL = os.environ.get("HWPX_SKILL", os.path.expanduser("~/.codex/skills/hwpx"))
HWPX_XML_SKILL = os.environ.get("HWPX_XML_SKILL", os.path.expanduser("~/.codex/skills/hwpx-xml"))
FIX_NS_SCRIPT = os.path.join(HWPX_SKILL, "scripts", "fix_namespaces.py")
VALIDATE_SCRIPT = os.path.join(HWPX_XML_SKILL, "scripts", "validate.py")

# ─── HWPX 네임스페이스 ──────────────────────────────────
HP_NS = "http://www.hancom.co.kr/hwpml/2011/paragraph"
HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"
HS_NS = "http://www.hancom.co.kr/hwpml/2011/section"
OPF_NS = "http://www.idpf.org/2007/opf/"

# ─── 셀 위치 매핑 (table_idx, row_idx, cell_idx) ────────
SECTION_CELLS = {
    1: (0, 2, 0), 2: (0, 4, 0), 3: (0, 6, 0), 4: (0, 8, 0),
    5: (1, 1, 0), 6: (1, 3, 0), 7: (1, 5, 0), 8: (1, 7, 0), 9: (1, 9, 0),
}

# 스타일 매핑 (paraPrIDRef, charPrIDRef)
SECTION_STYLES = {
    1: ("12", "16"), 2: ("12", "11"), 3: ("14", "11"), 4: ("14", "11"),
    5: ("14", "11"), 6: ("14", "11"), 7: ("14", "11"), 8: ("14", "11"),
    9: ("12", "6"),
}

# HWPX 렌더링 상수 (v10_user.hwpx 역공학 결과)
LINE_HEIGHT = 1600       # vertpos 간격 (한 줄 높이, hwp unit)
CHAR_WIDTH_AVG = 850     # 평균 한글 글자 폭 (cell width 41672 / 48 chars ≈ 868)
FIRST_LINE_FLAGS = "393216"    # 0x60000 — 한/글 에디터가 저장하는 first line 플래그
CONT_LINE_FLAGS = "1441792"    # 0x160000 — continuation line 플래그

# ─── 계층적 글머리기호 상수 ─────────────────────────────
BULLET_CHARS = {0: "●", 1: "○", 2: "▪", 3: "-"}
# paraPrIDRef는 paraProperties 배열 인덱스로 조회되므로 IDs가 순차적이어야 함.
# 기존 템플릿 paraPr(0..max) 뒤에 이어붙일 시작 ID는 ensure_bullet_parapr_defs에서 동적 결정.
BULLET_PARA_PR_BASE = None  # 동적 계산 — 전역 변수로 ensure_bullet_parapr_defs에서 설정
HH_NS = "http://www.hancom.co.kr/hwpml/2011/head"
# 텍스트 수준 들여쓰기 (전각 공백 U+3000 — 한글 테이블 셀에서 유일하게 작동하는 들여쓰기)
BULLET_INDENT_TEXT = {0: "", 1: "\u3000\u3000", 2: "\u3000\u3000\u3000\u3000", 3: "\u3000\u3000\u3000\u3000\u3000\u3000"}
# paraPr 기반 내어쓰기 (v10_user.hwpx 역공학 결과 — 사용자가 한/글에서 수동 설정한 값)
# 형식: {level: (left, intent_case_HwpUnitChar, intent_default_HWPUNIT_legacy)}
# case는 2016 HwpUnitChar 네임스페이스용, default는 2011 HWPUNIT 레거시용 (비율 1:2)
# left=0 유지, intent 음수 → 연속줄이 left-intent 위치로 밀려 내어쓰기 형성
BULLET_MARGIN = {
    0: (0,      0,     0),        # L0 ●: 짧은 제목용, 내어쓰기 없음
    1: (0,  -3072,  -6144),       # L1 ○: 2 full-width + bullet 폭 만큼 hang (user paraPr 15)
    2: (0,  -4572,  -9144),       # L2 ▪: 4 full-width + bullet (user paraPr 17)
    3: (0,  -6072, -12144),       # L3 -: 6 full-width + bullet (선형 보간)
}


# ─── MD 파싱 ─────────────────────────────────────────
def parse_disclosure(md_path):
    """disclosure.md에서 §1~§9 섹션 본문 추출 (부록 제외).
    markdown bullet(`- `, `* `) 구조는 들여쓰기를 포함하여 그대로 보존한다."""
    with open(md_path, "r", encoding="utf-8") as f:
        text = f.read()

    sections = {}
    current = None
    for line in text.split("\n"):
        m = re.match(r"^## §(\d+)\s", line)
        if m:
            current = int(m.group(1))
            sections[current] = []
            continue
        if re.match(r"^## 부록", line):
            current = None
            continue
        if current is not None:
            sections[current].append(line)

    for k in sections:
        txt = "\n".join(sections[k]).strip()
        txt = re.sub(r"> \[!.*?\].*?\n(?:>.*?\n)*", "", txt).strip()
        txt = re.sub(r"^#{1,4}\s+", "", txt, flags=re.MULTILINE)
        txt = re.sub(r"\*\*([^*]+)\*\*", r"\1", txt)
        txt = re.sub(r"\*([^*]+)\*", r"\1", txt)
        txt = re.sub(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]",
                      lambda m: m.group(2) or m.group(1), txt)
        txt = re.sub(r"^---+\s*$", "", txt, flags=re.MULTILINE)
        # Strip mermaid code blocks (rendered as PNG separately)
        txt = re.sub(r"```mermaid\n.*?```", "", txt, flags=re.DOTALL)
        # Strip markdown tables (rendered as PNG separately)
        txt = re.sub(r"(?:^\|.*\|$\n?)+", "", txt, flags=re.MULTILINE)
        # Strip blockquote lines
        txt = re.sub(r"^>.*$\n?", "", txt, flags=re.MULTILINE)
        sections[k] = txt

    return sections


# ─── 계층적 글머리기호 처리 ────────────────────────────
def has_bullet_structure(text):
    """텍스트에 markdown 글머리기호가 하나라도 있는지 확인."""
    return bool(re.search(r"^\s*[-*•]\s+\S", text, re.MULTILINE))


def parse_bullet_lines(text):
    """텍스트에서 markdown 계층적 글머리기호를 파싱한다.
    규칙:
      - 공백 2칸 = 1 레벨 (최대 3 레벨)
      - 기호: `-`, `*`, `•`
      - bullet 아닌 줄은 직전 bullet의 레벨로 연속 문단(본문) 처리하여
        글머리기호 위치에 맞춘 들여쓰기를 유지한다.
    Returns: list of (level: int 0~3, is_bullet: bool, content: str)
    """
    result = []
    bullet_re = re.compile(r"^(\s*)[-*•]\s+(.+)$")
    current_level = 0
    has_context = False

    for raw in text.split("\n"):
        if not raw.strip():
            continue
        m = bullet_re.match(raw)
        if m:
            level = min(len(m.group(1)) // 2, 3)
            content = m.group(2).strip()
            result.append((level, True, content))
            current_level = level
            has_context = True
        else:
            level = current_level if has_context else 0
            result.append((level, False, raw.strip()))
    return result


def ensure_bullet_parapr_defs(header_path):
    """header.xml에 계층적 글머리기호용 paraPr id=100~103이 없으면 추가한다.
    paraPr id=14(BULLET)를 템플릿으로 복제 후 margin.left만 단계별로 조정.
    글머리기호 문자는 텍스트로 삽입하므로 heading type을 NONE으로 변경한다."""
    ET.register_namespace("hh", HH_NS)

    # 원본 XML에서 다른 네임스페이스도 보존하기 위해 수동 등록
    for event, elem in ET.iterparse(header_path, events=["start-ns"]):
        prefix, uri = elem
        if prefix and prefix != "hh":
            try:
                ET.register_namespace(prefix, uri)
            except ValueError:
                pass

    tree = ET.parse(header_path)
    root = tree.getroot()

    # paraProperties 컨테이너 찾기
    container = None
    for elem in root.iter():
        if elem.tag.endswith("}paraProperties"):
            container = elem
            break
    if container is None:
        print("   [경고] paraProperties 컨테이너 없음 — bullet paraPr 생성 생략")
        return False

    existing_paraprs = container.findall(f"{{{HH_NS}}}paraPr")
    existing_ids = {p.get("id") for p in existing_paraprs}
    # paraPrIDRef가 배열 인덱스로 조회되므로 기존 ID 다음부터 순차 할당
    existing_int_ids = [int(p.get("id")) for p in existing_paraprs if p.get("id", "").isdigit()]
    base = max(existing_int_ids) + 1 if existing_int_ids else 0

    global BULLET_PARA_PR_BASE
    BULLET_PARA_PR_BASE = base

    # 템플릿 paraPr id=14 (BULLET level=0) 찾기
    template_pp = None
    for p in existing_paraprs:
        if p.get("id") == "14":
            template_pp = p
            break
    if template_pp is None:
        print("   [경고] 템플릿 paraPr id=14 없음 — bullet paraPr 생성 생략")
        return False

    added = 0
    for level in range(4):
        new_id = str(base + level)
        if new_id in existing_ids:
            continue
        new_pp = deepcopy(template_pp)
        new_pp.set("id", new_id)
        # v10_user.hwpx 분석 결과: 사용자 paraPr 15/17은 snapToGrid="1" 사용
        # snapToGrid="1"이 한/글이 paraPr.intent를 렌더링 시 적용하도록 트리거
        new_pp.set("snapToGrid", "1")
        # 자동 bullet 렌더링 비활성화 (문자는 텍스트로 삽입)
        heading = new_pp.find(f"{{{HH_NS}}}heading")
        if heading is not None:
            heading.set("type", "NONE")
            heading.set("idRef", "0")
            heading.set("level", "0")
        # margin 조정: case(HwpUnitChar 2016) vs default(legacy HWPUNIT) 구분 설정
        # user paraPr 15/17 패턴: case = default/2 (HwpUnitChar : legacy = 1 : 2)
        left_val, intent_case, intent_default = BULLET_MARGIN[level]
        switch = new_pp.find(f"{{{HP_NS}}}switch")
        if switch is None:
            for child in new_pp:
                if child.tag.endswith("}switch"):
                    switch = child
                    break
        blocks = []
        if switch is not None:
            case_blk = None
            default_blk = None
            for child in switch:
                if child.tag.endswith("}case"):
                    case_blk = child
                elif child.tag.endswith("}default"):
                    default_blk = child
            blocks = [(case_blk, intent_case), (default_blk, intent_default)]
        for blk, intent_val in blocks:
            if blk is None:
                continue
            margin = None
            for ch in blk:
                if ch.tag.endswith("}margin"):
                    margin = ch
                    break
            if margin is None:
                continue
            for mchild in margin:
                tag = mchild.tag.split("}")[-1] if "}" in mchild.tag else mchild.tag
                if tag == "left":
                    mchild.set("value", str(left_val))
                elif tag == "intent":
                    mchild.set("value", str(intent_val))
        container.append(new_pp)
        added += 1

    if added:
        # itemCnt 업데이트
        try:
            current_cnt = int(container.get("itemCnt", "0"))
            container.set("itemCnt", str(current_cnt + added))
        except ValueError:
            pass
        tree.write(header_path, encoding="utf-8", xml_declaration=True)
        print(f"   bullet paraPr {added}개 추가 (id={BULLET_PARA_PR_BASE}..{BULLET_PARA_PR_BASE+3})")
    return True


def replace_cell_with_bullets(cell, text, base_char_pr="11"):
    """셀 내용을 계층적 글머리기호 구조로 채운다.
    한글 테이블 셀은 paraPr margin을 무시하므로 순수 텍스트 수준에서
    들여쓰기(BULLET_INDENT_TEXT)와 내어쓰기(긴 텍스트 분할 + BULLET_CONT_TEXT)를
    구현한다. 연속 줄은 글머리기호 뒤 텍스트 시작 위치에 정렬된다."""
    sublist = cell.find(f"{{{HP_NS}}}subList")
    if sublist is None:
        return 0

    horzsize = get_cell_horzsize(cell)

    to_remove = []
    for child in list(sublist):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("p", "pic"):
            to_remove.append(child)
    for elem in to_remove:
        sublist.remove(elem)

    parsed = parse_bullet_lines(text)
    if not parsed:
        parsed = [(0, False, " ")]

    cumulative_vert = 0
    for level, is_bullet, content in parsed:
        para_pr_id = str(BULLET_PARA_PR_BASE + level)
        left_val = BULLET_MARGIN[level][0]
        available_horz = max(5000, horzsize - left_val)

        indent = BULLET_INDENT_TEXT.get(level, "")
        if is_bullet:
            marker = BULLET_CHARS.get(level, "-")
            display = f"{indent}{marker} {content}"
        else:
            display = f"{indent}{content}"
        if not display.strip():
            display = " "

        escaped = escape(display)
        p_elem, num_lines = make_paragraph(
            escaped, para_pr_id, base_char_pr,
            vert_offset=cumulative_vert,
            horzsize=available_horz,
        )
        sublist.append(p_elem)
        cumulative_vert += num_lines * LINE_HEIGHT

    csz = cell.find(f"{{{HP_NS}}}cellSz")
    if csz is not None:
        new_height = max(cumulative_vert + LINE_HEIGHT, int(csz.get("height", "0")))
        csz.set("height", str(new_height))
    return cumulative_vert


# ─── lineseg 계산 ─────────────────────────────────────
def calc_linesegs(text, horzsize=41672):
    """텍스트에 필요한 lineseg 목록을 계산한다."""
    chars_per_line = max(1, horzsize // CHAR_WIDTH_AVG)
    num_lines = max(1, math.ceil(len(text) / chars_per_line))

    segs = []
    textpos = 0
    for i in range(num_lines):
        flags = FIRST_LINE_FLAGS if i == 0 else CONT_LINE_FLAGS
        segs.append({
            "textpos": str(textpos),
            "vertpos": str(i * LINE_HEIGHT),
            "vertsize": "1000",
            "textheight": "1000",
            "baseline": "850",
            "spacing": "600",
            "horzpos": "0",
            "horzsize": str(horzsize),
            "flags": flags,
        })
        textpos += chars_per_line
    return segs, num_lines


# ─── XML 빌더 ─────────────────────────────────────────
def make_paragraph(text, para_pr, char_pr, vert_offset=0, horzsize=41672):
    """hp:p 요소를 올바른 lineseg와 함께 생성한다."""
    p = ET.Element(f"{{{HP_NS}}}p")
    p.set("id", "0")
    p.set("paraPrIDRef", para_pr)
    p.set("styleIDRef", "0")
    p.set("pageBreak", "0")
    p.set("columnBreak", "0")
    p.set("merged", "0")

    run = ET.SubElement(p, f"{{{HP_NS}}}run")
    run.set("charPrIDRef", char_pr)
    t = ET.SubElement(run, f"{{{HP_NS}}}t")
    t.text = text

    segs, num_lines = calc_linesegs(text, horzsize)

    lsa = ET.SubElement(p, f"{{{HP_NS}}}linesegarray")
    for seg_data in segs:
        ls = ET.SubElement(lsa, f"{{{HP_NS}}}lineseg")
        adjusted_vertpos = int(seg_data["vertpos"]) + vert_offset
        seg_data["vertpos"] = str(adjusted_vertpos)
        for attr, val in seg_data.items():
            ls.set(attr, val)

    return p, num_lines


def get_cell_horzsize(cell):
    """셀의 가로 크기를 cellSz에서 추출한다."""
    csz = cell.find(f"{{{HP_NS}}}cellSz")
    if csz is not None:
        w = csz.get("width")
        if w:
            return int(w) - 1700
    return 41672


def replace_section9_styled(cell, new_text):
    """§9 셀 내용을 패턴별 다른 스타일로 교체한다.
    - '도면 목록' → CENTER + bold (paraPr=12, charPr=12)
    - 도 설명, 참고문헌 → JUSTIFY + normal (paraPr=14, charPr=11)
    - '참고문헌' 위에 빈 줄 삽입
    """
    sublist = cell.find(f"{{{HP_NS}}}subList")
    if sublist is None:
        return 0

    horzsize = get_cell_horzsize(cell)

    # 기존 내용 제거
    to_remove = []
    for child in list(sublist):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("p", "pic"):
            to_remove.append(child)
    for elem in to_remove:
        sublist.remove(elem)

    paragraphs = [line for line in new_text.split("\n")]
    # 연속 빈 줄 제거하되 1개는 유지
    cleaned = []
    prev_empty = False
    for line in paragraphs:
        if not line.strip():
            if not prev_empty:
                cleaned.append("")
            prev_empty = True
        else:
            cleaned.append(line)
            prev_empty = False
    paragraphs = cleaned if cleaned else [" "]

    cumulative_vert = 0

    for para_text in paragraphs:
        stripped = para_text.strip()

        # 스타일 결정
        if stripped == "도면 목록":
            # 볼드 + 가운데 맞춤
            p_pr, c_pr = "12", "12"
        else:
            # JUSTIFY + 일반 본문
            p_pr, c_pr = "14", "11"

        if not stripped:
            # 빈 줄
            display_text = " "
        else:
            display_text = stripped

        escaped_text = escape(display_text)
        p_elem, num_lines = make_paragraph(
            escaped_text, p_pr, c_pr,
            vert_offset=cumulative_vert,
            horzsize=horzsize,
        )
        sublist.append(p_elem)
        cumulative_vert += num_lines * LINE_HEIGHT

    csz = cell.find(f"{{{HP_NS}}}cellSz")
    if csz is not None:
        new_height = max(cumulative_vert + LINE_HEIGHT, int(csz.get("height", "0")))
        csz.set("height", str(new_height))

    return cumulative_vert


def replace_cell_content(cell, new_text, para_pr, char_pr):
    """셀 내용을 교체하고 올바른 lineseg를 생성한다."""
    sublist = cell.find(f"{{{HP_NS}}}subList")
    if sublist is None:
        return 0

    horzsize = get_cell_horzsize(cell)

    to_remove = []
    for child in list(sublist):
        tag = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if tag in ("p", "pic"):
            to_remove.append(child)
    for elem in to_remove:
        sublist.remove(elem)

    paragraphs = [line.strip() for line in new_text.split("\n") if line.strip()]
    if not paragraphs:
        paragraphs = [" "]

    cumulative_vert = 0

    for para_text in paragraphs:
        escaped_text = escape(para_text)
        p_elem, num_lines = make_paragraph(
            escaped_text, para_pr, char_pr,
            vert_offset=cumulative_vert,
            horzsize=horzsize,
        )
        sublist.append(p_elem)
        cumulative_vert += num_lines * LINE_HEIGHT

    csz = cell.find(f"{{{HP_NS}}}cellSz")
    if csz is not None:
        new_height = max(cumulative_vert + LINE_HEIGHT, int(csz.get("height", "0")))
        csz.set("height", str(new_height))

    return cumulative_vert


# ─── 이미지 삽입 ──────────────────────────────────────
def get_png_size_hwpunits(png_path):
    """PNG 파일의 크기를 HWPX 단위(1/7200 inch 기준)로 반환한다."""
    if not HAS_PIL:
        return 36000, 24000  # 기본 크기 fallback
    with Image.open(png_path) as img:
        px_w, px_h = img.size
        dpi = img.info.get("dpi", (150, 150))
        dpi_x = dpi[0] if dpi[0] > 0 else 150
        dpi_y = dpi[1] if dpi[1] > 0 else 150
        hwp_w = int(px_w / dpi_x * 7200)
        hwp_h = int(px_h / dpi_y * 7200)
    return hwp_w, hwp_h


def make_pic_paragraph(image_id, org_w, org_h, cur_w, cur_h,
                       para_pr, char_pr, vert_offset=0):
    """이미지를 포함하는 hp:p 요소를 생성한다."""
    p = ET.Element(f"{{{HP_NS}}}p")
    p.set("id", "0")
    p.set("paraPrIDRef", para_pr)
    p.set("styleIDRef", "0")
    p.set("pageBreak", "0")
    p.set("columnBreak", "0")
    p.set("merged", "0")

    run = ET.SubElement(p, f"{{{HP_NS}}}run")
    run.set("charPrIDRef", char_pr)

    pic = ET.SubElement(run, f"{{{HP_NS}}}pic")
    pic.set("id", str(random.randint(100000000, 2000000000)))
    pic.set("zOrder", "2")
    pic.set("numberingType", "PICTURE")
    pic.set("textWrap", "TOP_AND_BOTTOM")
    pic.set("textFlow", "BOTH_SIDES")
    pic.set("lock", "0")
    pic.set("dropcapstyle", "None")
    pic.set("href", "")
    pic.set("groupLevel", "0")
    pic.set("instid", str(random.randint(100000000, 999999999)))
    pic.set("reverse", "0")

    offset = ET.SubElement(pic, f"{{{HP_NS}}}offset")
    offset.set("x", "0"); offset.set("y", "0")

    orgsz = ET.SubElement(pic, f"{{{HP_NS}}}orgSz")
    orgsz.set("width", str(org_w)); orgsz.set("height", str(org_h))

    cursz = ET.SubElement(pic, f"{{{HP_NS}}}curSz")
    cursz.set("width", str(cur_w)); cursz.set("height", str(cur_h))

    flip = ET.SubElement(pic, f"{{{HP_NS}}}flip")
    flip.set("horizontal", "0"); flip.set("vertical", "0")

    rot = ET.SubElement(pic, f"{{{HP_NS}}}rotationInfo")
    rot.set("angle", "0")
    rot.set("centerX", str(cur_w // 2))
    rot.set("centerY", str(cur_h // 2))
    rot.set("rotateimage", "1")

    ri = ET.SubElement(pic, f"{{{HP_NS}}}renderingInfo")
    scale_x = cur_w / org_w if org_w > 0 else 1.0
    scale_y = cur_h / org_h if org_h > 0 else 1.0

    trans = ET.SubElement(ri, f"{{{HC_NS}}}transMatrix")
    trans.set("e1", "1"); trans.set("e2", "0"); trans.set("e3", "0")
    trans.set("e4", "0"); trans.set("e5", "1"); trans.set("e6", "0")

    sca = ET.SubElement(ri, f"{{{HC_NS}}}scaMatrix")
    sca.set("e1", f"{scale_x:.6f}"); sca.set("e2", "0"); sca.set("e3", "0")
    sca.set("e4", "0"); sca.set("e5", f"{scale_y:.6f}"); sca.set("e6", "0")

    rotm = ET.SubElement(ri, f"{{{HC_NS}}}rotMatrix")
    rotm.set("e1", "1"); rotm.set("e2", "0"); rotm.set("e3", "0")
    rotm.set("e4", "0"); rotm.set("e5", "1"); rotm.set("e6", "0")

    ir = ET.SubElement(pic, f"{{{HP_NS}}}imgRect")
    for name, x, y in [("pt0",0,0), ("pt1",org_w,0), ("pt2",org_w,org_h), ("pt3",0,org_h)]:
        pt = ET.SubElement(ir, f"{{{HC_NS}}}{name}")
        pt.set("x", str(x)); pt.set("y", str(y))

    ic = ET.SubElement(pic, f"{{{HP_NS}}}imgClip")
    ic.set("left", "0"); ic.set("right", str(org_w))
    ic.set("top", "0"); ic.set("bottom", str(org_h))

    inm = ET.SubElement(pic, f"{{{HP_NS}}}inMargin")
    inm.set("left", "0"); inm.set("right", "0")
    inm.set("top", "0"); inm.set("bottom", "0")

    imd = ET.SubElement(pic, f"{{{HP_NS}}}imgDim")
    imd.set("dimwidth", str(org_w)); imd.set("dimheight", str(org_h))

    img_elem = ET.SubElement(pic, f"{{{HC_NS}}}img")
    img_elem.set("binaryItemIDRef", image_id)
    img_elem.set("bright", "0")
    img_elem.set("contrast", "0")
    img_elem.set("effect", "REAL_PIC")
    img_elem.set("alpha", "0")

    ET.SubElement(pic, f"{{{HP_NS}}}effects")

    sz = ET.SubElement(pic, f"{{{HP_NS}}}sz")
    sz.set("width", str(cur_w)); sz.set("widthRelTo", "ABSOLUTE")
    sz.set("height", str(cur_h)); sz.set("heightRelTo", "ABSOLUTE")
    sz.set("protect", "0")

    pos = ET.SubElement(pic, f"{{{HP_NS}}}pos")
    pos.set("treatAsChar", "1"); pos.set("affectLSpacing", "0")
    pos.set("flowWithText", "1"); pos.set("allowOverlap", "0")
    pos.set("holdAnchorAndSO", "0")
    pos.set("vertRelTo", "PARA"); pos.set("horzRelTo", "PARA")
    pos.set("vertAlign", "TOP"); pos.set("horzAlign", "LEFT")
    pos.set("vertOffset", "0"); pos.set("horzOffset", "0")

    outm = ET.SubElement(pic, f"{{{HP_NS}}}outMargin")
    outm.set("left", "0"); outm.set("right", "0")
    outm.set("top", "0"); outm.set("bottom", "0")

    lsa = ET.SubElement(p, f"{{{HP_NS}}}linesegarray")
    ls = ET.SubElement(lsa, f"{{{HP_NS}}}lineseg")
    ls.set("textpos", "0")
    ls.set("vertpos", str(vert_offset))
    ls.set("vertsize", str(cur_h))
    ls.set("textheight", str(cur_h))
    ls.set("baseline", str(cur_h))
    ls.set("spacing", "600")
    ls.set("horzpos", "0")
    ls.set("horzsize", "41672")
    ls.set("flags", FIRST_LINE_FLAGS)

    return p, cur_h


def insert_diagrams_to_section9(cell, diagrams_dir, tmp_dir, cumulative_vert):
    """§9 셀에 도면 PNG 파일들을 삽입한다."""
    if not diagrams_dir or not os.path.isdir(diagrams_dir):
        print("   도면 디렉토리 없음 — 건너뜀")
        return cumulative_vert, []

    # 자연 정렬: fig10이 fig2보다 앞에 오는 알파벳 정렬 버그 방지
    def _natural_key(path):
        return [int(t) if t.isdigit() else t.lower()
                for t in re.split(r"(\d+)", os.path.basename(path))]

    png_files = sorted(glob.glob(os.path.join(diagrams_dir, "*.png")), key=_natural_key)
    if not png_files:
        print("   도면 PNG 파일 없음 — 건너뜀")
        return cumulative_vert, []

    # 도면 번호·부호 미사용 정책 (2026-07-13): 캡션은 내용 기반 제목만 사용.
    # diagrams_dir/captions.json ({"fig1_x.png": "제목", ...}) 이 있으면 그 제목을,
    # 없으면 파일명 stem 을 캡션으로 쓴다. "[도 N]" 번호는 부여하지 않는다
    # (출원용 정식 도면·번호 체계는 변리사가 별도 작성 — 내부 번호는 오해 유발).
    caption_map = {}
    cap_file = os.path.join(diagrams_dir, "captions.json")
    if os.path.isfile(cap_file):
        import json as _json
        with open(cap_file, encoding="utf-8") as _f:
            caption_map = _json.load(_f)

    sublist = cell.find(f"{{{HP_NS}}}subList")
    if sublist is None:
        return cumulative_vert, []

    horzsize = get_cell_horzsize(cell)
    max_width = horzsize
    image_items = []

    for i, png_path in enumerate(png_files):
        fname = os.path.basename(png_path)
        image_id = f"diagram{i+1}"
        bin_name = f"BinData/{image_id}.png"

        org_w, org_h = get_png_size_hwpunits(png_path)

        if org_w > max_width:
            scale = max_width / org_w
            cur_w = max_width
            cur_h = int(org_h * scale)
        else:
            cur_w = org_w
            cur_h = org_h

        caption = caption_map.get(fname) or fname.replace('.png', '').replace('_', ' ')
        cap_p, cap_lines = make_paragraph(
            escape(caption), "12", "6",
            vert_offset=cumulative_vert, horzsize=horzsize
        )
        sublist.append(cap_p)
        cumulative_vert += cap_lines * LINE_HEIGHT

        pic_p, pic_height = make_pic_paragraph(
            image_id, org_w, org_h, cur_w, cur_h,
            "12", "6", vert_offset=cumulative_vert
        )
        sublist.append(pic_p)
        cumulative_vert += pic_height + LINE_HEIGHT

        bindata_dir = os.path.join(tmp_dir, "BinData")
        os.makedirs(bindata_dir, exist_ok=True)
        shutil.copy2(png_path, os.path.join(bindata_dir, f"{image_id}.png"))

        image_items.append((image_id, bin_name, "image/png"))
        print(f"   {fname} -> {image_id}.png ({cur_w}x{cur_h}) 캡션: {caption}")

    csz = cell.find(f"{{{HP_NS}}}cellSz")
    if csz is not None:
        new_height = max(cumulative_vert + LINE_HEIGHT, int(csz.get("height", "0")))
        csz.set("height", str(new_height))

    return cumulative_vert, image_items


def update_content_hpf(tmp_dir, image_items):
    """content.hpf에 새 이미지 항목을 추가한다."""
    hpf_path = os.path.join(tmp_dir, "Contents", "content.hpf")
    with open(hpf_path, "r", encoding="utf-8") as f:
        hpf_text = f.read()

    new_items = ""
    for image_id, href, media_type in image_items:
        new_items += f'<opf:item id="{image_id}" href="{href}" media-type="{media_type}" isEmbeded="1"/>'

    hpf_text = hpf_text.replace("</opf:manifest>", new_items + "</opf:manifest>")
    hpf_text = re.sub(r'<opf:item[^>]*id="image1"[^>]*/>', '', hpf_text)

    with open(hpf_path, "w", encoding="utf-8") as f:
        f.write(hpf_text)


# ─── 메인 ────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="disclosure.md → KIMM HWPX 변환")
    parser.add_argument("--disclosure", required=True, help="disclosure.md 경로")
    parser.add_argument("--output", required=True, help="출력 HWPX 경로")
    parser.add_argument("--diagrams", default=None, help="도면 PNG 디렉토리 (선택)")
    parser.add_argument("--template", default=TEMPLATE_PATH, help="KIMM 양식 HWPX 템플릿 경로")
    args = parser.parse_args()

    print("1. disclosure.md 파싱...")
    sections = parse_disclosure(args.disclosure)
    print(f"   §1~§9 추출 완료 ({sum(len(v) for v in sections.values())} chars)")

    print("2. 템플릿 HWPX 해제...")
    tmp_dir = args.output + "_tmp"
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    with zipfile.ZipFile(args.template, "r") as z:
        z.extractall(tmp_dir)

    print("3. 네임스페이스 등록 및 XML 파싱...")
    section_xml = os.path.join(tmp_dir, "Contents", "section0.xml")
    header_xml = os.path.join(tmp_dir, "Contents", "header.xml")

    namespaces = {}
    for event, elem in ET.iterparse(section_xml, events=["start-ns"]):
        namespaces[elem[0]] = elem[1]
    if "hc" not in namespaces:
        namespaces["hc"] = HC_NS
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)

    print("3b. 계층적 글머리기호용 paraPr(100~103) 추가...")
    ensure_bullet_parapr_defs(header_xml)

    tree = ET.parse(section_xml)
    root = tree.getroot()
    tables = root.findall(f".//{{{HP_NS}}}tbl")
    print(f"   테이블 {len(tables)}개 발견")

    print("4. 각 섹션 셀 내용 교체...")
    for sec_num in range(1, 10):
        tbl_idx, row_idx, cell_idx = SECTION_CELLS[sec_num]
        para_pr, char_pr = SECTION_STYLES[sec_num]

        tbl = tables[tbl_idx]
        rows = tbl.findall(f"{{{HP_NS}}}tr")
        row = rows[row_idx]
        cells = row.findall(f"{{{HP_NS}}}tc")
        cell = cells[cell_idx]

        content = sections.get(sec_num, " ")

        if sec_num != 1 and sec_num != 2 and has_bullet_structure(content):
            # 계층적 글머리기호 구조 감지 → bullet 렌더러 사용 (§9 포함)
            total_vert = replace_cell_with_bullets(cell, content, base_char_pr=char_pr)
        elif sec_num == 9:
            total_vert = replace_section9_styled(cell, content)
        else:
            total_vert = replace_cell_content(cell, content, para_pr, char_pr)

        sublist = cell.find(f"{{{HP_NS}}}subList")
        p_count = len(sublist.findall(f"{{{HP_NS}}}p")) if sublist is not None else 0
        print(f"   §{sec_num}: {p_count}개 단락, vert_total={total_vert}")

    print("5. §9에 도면 삽입...")
    sec9_cell = tables[1].findall(f"{{{HP_NS}}}tr")[9].findall(f"{{{HP_NS}}}tc")[0]
    sec9_sublist = sec9_cell.find(f"{{{HP_NS}}}subList")
    sec9_paras = sec9_sublist.findall(f"{{{HP_NS}}}p") if sec9_sublist is not None else []
    sec9_vert = 0
    for p in sec9_paras:
        for ls in p.iter(f"{{{HP_NS}}}lineseg"):
            vp = int(ls.get("vertpos", "0"))
            vs = int(ls.get("vertsize", "1000"))
            sec9_vert = max(sec9_vert, vp + vs + 600)

    sec9_vert, image_items = insert_diagrams_to_section9(
        sec9_cell, args.diagrams, tmp_dir, sec9_vert
    )
    print(f"   도면 {len(image_items)}개 삽입 완료")

    if image_items:
        print("5b. content.hpf 업데이트...")
        update_content_hpf(tmp_dir, image_items)

    print("6. XML 저장...")
    tree.write(section_xml, encoding="utf-8", xml_declaration=True)

    print("7. ZIP 재압축...")
    if os.path.exists(args.output):
        os.remove(args.output)
    with zipfile.ZipFile(args.output, "w", zipfile.ZIP_DEFLATED) as zout:
        for dirpath, dirnames, filenames in os.walk(tmp_dir):
            for fname in filenames:
                fpath = os.path.join(dirpath, fname)
                arcname = os.path.relpath(fpath, tmp_dir)
                if "image1.bmp" in arcname:
                    print(f"   [제외] {arcname}")
                    continue
                compress = zipfile.ZIP_STORED if fname == "mimetype" else zipfile.ZIP_DEFLATED
                zout.write(fpath, arcname, compress_type=compress)

    shutil.rmtree(tmp_dir)
    print(f"   출력: {args.output}")

    if os.path.isfile(FIX_NS_SCRIPT):
        print("8. fix_namespaces 실행...")
        ret = os.system(f'python "{FIX_NS_SCRIPT}" "{args.output}"')
        print(f"   반환 코드: {ret}")

    if os.path.isfile(VALIDATE_SCRIPT):
        print("9. validate 실행...")
        ret = os.system(f'python "{VALIDATE_SCRIPT}" "{args.output}"')
        print(f"   반환 코드: {ret}")

    print("\n완료!")


if __name__ == "__main__":
    main()
