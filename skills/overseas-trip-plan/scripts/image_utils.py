#!/usr/bin/env python3
"""image_utils.py — HWPX 이미지 삽입 유틸리티 (v0.6)

HWPX 에 PNG/JPG 이미지를 안전하게 삽입하기 위한 helper 모음.

3단계 삽입 패턴:
  1. BinData/{imageN}.png 로 파일 복사
  2. Contents/content.hpf 에 <opf:item> 등록 (idempotent)
  3. section0.xml 에 <hp:pic> 포함 <hp:p> 삽입 (기존 이미지 wrapper deepcopy)

HWPUNIT 변환:
  - 1 pixel @ 96 DPI = 0.75 pt = 75 HWPUNIT
  - A4 본문 폭 약 48188 HWPUNIT (약 17cm) — 15cm 표시 시 42520 HWPUNIT 권장

사용 예:
  from image_utils import (
      register_image_in_hpf,
      clone_pic_paragraph,
      HWPUNIT_PER_PX,
  )

  # 1. BinData 복사
  shutil.copy(png, unpacked / "BinData" / "image9.png")

  # 2. content.hpf 등록
  register_image_in_hpf(
      unpacked / "Contents" / "content.hpf",
      img_id="image9", href="BinData/image9.png", media_type="image/png",
  )

  # 3. section0.xml 에 <hp:pic> 삽입 (기존 이미지 wrapper 를 템플릿으로)
  template_wrapper = find_pic_wrapper_by_binary_id(root, "image5")
  new_wrap = clone_pic_paragraph(
      template_wrapper,
      binary_id="image9",
      orig_px=(1280, 720),
      display_w_hwpunit=42520,
      pic_id=1900000009, instid=800000009, zorder=20,
  )
  target_paragraph.addnext(new_wrap)
"""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Optional

from lxml import etree

from table_utils import hp, strip_linesegarray

HC_NS = "http://www.hancom.co.kr/hwpml/2011/core"


def hc(tag: str) -> str:
    return f"{{{HC_NS}}}{tag}"


# ===========================================================================
# 상수
# ===========================================================================

HWPUNIT_PER_PX = 75
"""1 pixel @ 96 DPI = 0.75pt = 75 HWPUNIT."""

DEFAULT_DISPLAY_WIDTH = 42520
"""본문 내 이미지 권장 폭 (~15cm). A4 본문 폭 48188 HWPUNIT 대비 88%."""


# ===========================================================================
# content.hpf — manifest 등록
# ===========================================================================

def register_image_in_hpf(
    hpf_path: Path,
    img_id: str,
    href: str,
    media_type: str,
    anchor_item_id: Optional[str] = None,
) -> bool:
    """content.hpf 에 `<opf:item>` 을 idempotent 추가.

    Args:
        hpf_path: Contents/content.hpf 경로
        img_id: 새 이미지 id (예: "image9")
        href: "BinData/image9.png" 같은 상대 경로
        media_type: "image/png", "image/jpeg", "image/bmp" 등
        anchor_item_id: 이 id 뒤에 삽입. None 이면 **마지막 image item** 뒤에 자동 배치.

    Returns:
        True = 새로 등록, False = 이미 등록되어 있었음.
    """
    hpf_path = Path(hpf_path)
    txt = hpf_path.read_text(encoding="utf-8")

    if f'id="{img_id}"' in txt:
        return False

    line = f'<opf:item id="{img_id}" href="{href}" media-type="{media_type}" isEmbeded="1"/>'

    if anchor_item_id is None:
        # 마지막 image item (imageN) 찾기 — 가장 큰 숫자
        import re
        matches = re.findall(r'<opf:item id="image(\d+)" [^/]+/>', txt)
        if matches:
            last_n = max(int(m) for m in matches)
            anchor_item_id = f"image{last_n}"
        else:
            raise RuntimeError("content.hpf 에 기존 image item 없음 — anchor_item_id 명시 필요")

    # anchor 라인 검색
    import re
    pattern = re.compile(
        rf'(<opf:item id="{re.escape(anchor_item_id)}"[^/]+/>)'
    )
    m = pattern.search(txt)
    if m is None:
        raise RuntimeError(f"content.hpf 에 anchor item '{anchor_item_id}' 없음")

    anchor_line = m.group(1)
    # anchor 라인 뒤 (같은 들여쓰기 유지)
    idx = m.end()
    # 앞 line 의 들여쓰기 추정
    line_start = txt.rfind("\n", 0, m.start()) + 1
    indent = txt[line_start : m.start()]

    new_txt = txt[:idx] + "\n" + indent + line + txt[idx:]
    hpf_path.write_text(new_txt, encoding="utf-8")
    return True


# ===========================================================================
# <hp:pic> wrapper paragraph 탐색·생성
# ===========================================================================

def find_pic_wrapper_by_binary_id(root, binary_id: str):
    """주어진 `binaryItemIDRef` 를 참조하는 `<hp:pic>` 을 포함한 `<hp:p>` 반환.

    기존 이미지 삽입 구조를 **템플릿으로 deepcopy 하여 재사용** 할 때 앵커.

    Args:
        root: section XML root
        binary_id: "image5" 같은 기존 이미지 id

    Returns:
        wrapper `<hp:p>` 또는 None
    """
    for p in root.iter(hp("p")):
        for pic in p.iter(hp("pic")):
            img = pic.find(hc("img"))
            if img is not None and img.get("binaryItemIDRef") == binary_id:
                return p
    return None


def clone_pic_paragraph(
    template_p,
    binary_id: str,
    orig_px: tuple[int, int],
    display_w_hwpunit: int = DEFAULT_DISPLAY_WIDTH,
    pic_id: int = 0,
    instid: int = 0,
    zorder: int = 0,
    keep_aspect: bool = True,
):
    """기존 `<hp:p>` (이미지 포함) 을 deepcopy → 새 이미지용으로 속성 재설정.

    처리:
      - `<hp:linesegarray>` 제거 (HWP 재계산)
      - `<hp:pic>` 의 id/instid/zOrder 변경
      - `<hp:orgSz>` = 원본 픽셀 × 75
      - `<hp:curSz>` / `<hp:sz>` = display_w_hwpunit × 비례 높이
      - `<hp:renderingInfo>` 의 `<hc:scaMatrix e1/e5>` 갱신
      - `<hp:imgRect>`, `<hp:imgClip>`, `<hp:imgDim>` 원본 크기로 재설정
      - `<hc:img binaryItemIDRef>` 새 이미지 id 로 교체
      - `<hp:shapeComment>` 제거 (원본 파일명 누설 방지)

    Args:
        template_p: `<hp:pic>` 을 포함한 기존 `<hp:p>` (`find_pic_wrapper_by_binary_id` 결과)
        binary_id: 새 바이너리 id (예: "image9")
        orig_px: 원본 PNG/JPG 픽셀 크기 (W, H)
        display_w_hwpunit: 문서 내 표시 폭 (기본 42520 ≈ 15cm)
        pic_id / instid / zorder: 고유값 (기존 값과 충돌 금지)
        keep_aspect: True 이면 display 높이 = display_w × (orig_h / orig_w)

    Returns:
        deepcopy 된 `<hp:p>` — caller 가 `anchor.addnext(result)` 로 삽입.
    """
    orig_w_px, orig_h_px = orig_px
    orig_w = orig_w_px * HWPUNIT_PER_PX
    orig_h = orig_h_px * HWPUNIT_PER_PX
    disp_w = display_w_hwpunit
    disp_h = (
        int(disp_w * orig_h_px / orig_w_px) if keep_aspect
        else int(disp_w * orig_h / orig_w)
    )
    scale = disp_w / orig_w

    new_p = deepcopy(template_p)
    strip_linesegarray(new_p)

    pic = next(new_p.iter(hp("pic")), None)
    if pic is None:
        raise RuntimeError("template 내 <hp:pic> 없음")

    if pic_id:
        pic.set("id", str(pic_id))
    if instid:
        pic.set("instid", str(instid))
    if zorder:
        pic.set("zOrder", str(zorder))

    # orgSz
    orgsz = pic.find(hp("orgSz"))
    if orgsz is not None:
        orgsz.set("width", str(orig_w))
        orgsz.set("height", str(orig_h))

    # curSz
    cursz = pic.find(hp("curSz"))
    if cursz is not None:
        cursz.set("width", str(disp_w))
        cursz.set("height", str(disp_h))

    # rotationInfo
    rot = pic.find(hp("rotationInfo"))
    if rot is not None:
        rot.set("centerX", str(disp_w // 2))
        rot.set("centerY", str(disp_h // 2))

    # renderingInfo scaMatrix
    rendering = pic.find(hp("renderingInfo"))
    if rendering is not None:
        scamat = rendering.find(hc("scaMatrix"))
        if scamat is not None:
            scamat.set("e1", f"{scale:.6f}")
            scamat.set("e5", f"{scale:.6f}")

    # imgRect
    imgrect = pic.find(hp("imgRect"))
    if imgrect is not None:
        pts = [(0, 0), (orig_w, 0), (orig_w, orig_h), (0, orig_h)]
        for i, (x, y) in enumerate(pts):
            pt = imgrect.find(hc(f"pt{i}"))
            if pt is not None:
                pt.set("x", str(x))
                pt.set("y", str(y))

    # imgClip / imgDim
    imgclip = pic.find(hp("imgClip"))
    if imgclip is not None:
        imgclip.set("left", "0")
        imgclip.set("right", str(orig_w))
        imgclip.set("top", "0")
        imgclip.set("bottom", str(orig_h))

    imgdim = pic.find(hp("imgDim"))
    if imgdim is not None:
        imgdim.set("dimwidth", str(orig_w))
        imgdim.set("dimheight", str(orig_h))

    # hc:img binaryItemIDRef
    img = pic.find(hc("img"))
    if img is not None:
        img.set("binaryItemIDRef", binary_id)

    # hp:sz (display)
    psz = pic.find(hp("sz"))
    if psz is not None:
        psz.set("width", str(disp_w))
        psz.set("height", str(disp_h))

    # shapeComment 제거 (원본 파일명 방지)
    sc = pic.find(hp("shapeComment"))
    if sc is not None:
        pic.remove(sc)

    return new_p
