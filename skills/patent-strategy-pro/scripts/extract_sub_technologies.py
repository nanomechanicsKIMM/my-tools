#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract 3-5 sub-technologies from an RFP markdown file.

Analyzes (priority order):
  - 연구개발내용 / 개발내용 (highest — actual dev tasks)
  - 과제목표 / 연구목표 (high)
  - 성과지표 / 핵심성과지표 (medium)
  - 기술분류 / 키워드 (medium)
  - 추진배경 (low — background only, not dev tasks)

Handles Korean RFP conventions:
  - ㅇ / · bullet markers (in addition to - * •)
  - Content inside Markdown table cells (PDF→MD tables)
  - Long sentence items → truncated to concise tech names

Domain-agnostic: works with any technology field.
  - Built-in _KO_EXPAND covers 14+ domains as baseline
  - Use --domain-dict <path.json> to add custom domain terms
  - Outputs quality report with key_terms overlap warnings

Usage:
  python extract_sub_technologies.py <rfp.md> -o sub_techs.json [--min 3] [--max 5]
  python extract_sub_technologies.py <rfp.md> -o sub_techs.json --domain-dict my_domain.json
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


# ── Section heading patterns ──────────────────────────────────────────────────

SECTION_PATTERNS = {
    "contents": [
        r"연구개발[\s\S]*?내용", r"개발[\s\S]*?내용", r"기술[\s\S]*?내용",
        r"연구[\s\S]*?내용", r"수행[\s\S]*?내용",
    ],
    "objectives": [
        r"과제[\s\S]*?목표", r"연구[\s\S]*?목표", r"기술[\s\S]*?목표",
        r"개발[\s\S]*?목표", r"연구개발[\s\S]*?목표",
    ],
    "indicators": [
        r"성과[\s\S]*?지표", r"핵심[\s\S]*?지표", r"목표[\s\S]*?지표",
        r"연구[\s\S]*?성과", r"기술[\s\S]*?수준",
    ],
    "keywords": [
        r"키워드", r"keyword", r"기술[\s\S]*?분류", r"핵심[\s\S]*?기술",
    ],
    "background": [
        r"추진[\s\S]*?배경", r"기술[\s\S]*?동향", r"현황[\s\S]*?분석",
    ],
}

# ── Stopwords ─────────────────────────────────────────────────────────────────

STOPWORDS_KO = {
    "기술", "연구", "개발", "시스템", "방법", "장치", "분야", "관련",
    "적용", "활용", "이용", "구현", "설계", "분석", "최적화", "향상",
    "개선", "확보", "제공", "구성", "형성", "수행", "및", "등", "또는",
}

STOPWORDS_EN = {
    "technology", "system", "method", "device", "process", "based",
    "using", "for", "with", "and", "or", "the", "of", "in", "a",
    "performance", "improvement", "optimization", "application",
    "development", "research", "study", "analysis",
}

# ── Domain expansion: Korean tech keyword → English search terms ───────────────
# Used when English co-occurrence search finds nothing (typical for Korean-only PDFs).
# Keys are matched against the Korean sub-tech name; values supplement key_terms.
# Organized by technology domain for maintainability.
# Coverage: flexible display, sensing, battery, semiconductor, AI/ML,
#           communication, biomedical, automotive, optics, power electronics,
#           materials/manufacturing, robotics, environment.
_KO_EXPAND: dict[str, list[str]] = {

    # ── Flexible Display / TFT / Backplane ──────────────────────────────────────
    "백플레인": ["backplane", "LTPS", "oxide TFT"],
    "TFT": ["TFT", "thin film transistor", "LTPS"],
    "LTPS": ["LTPS", "low temperature polysilicon", "backplane"],
    "산화물": ["oxide TFT", "IGZO", "amorphous oxide"],
    "유연": ["flexible", "stretchable", "bendable"],
    "RGB": ["RGB", "color display", "subpixel"],
    "OLED": ["OLED", "organic light emitting", "flexible OLED"],
    "디스플레이": ["display", "OLED display"],
    "화소": ["pixel", "subpixel"],
    "픽셀": ["pixel", "pixel array"],
    "화질": ["image quality", "display quality"],

    # ── Sensing / Deformation ────────────────────────────────────────────────────
    "센서": ["sensor", "sensing", "transducer"],
    "어레이": ["array", "sensor array"],
    "변형": ["deformation", "strain", "bending"],
    "감지": ["sensing", "detection"],
    "압력": ["pressure sensor", "piezoelectric"],
    "진동": ["vibration", "vibration sensor", "piezoelectric"],
    "온도": ["temperature", "thermal sensor", "thermometer"],

    # ── UI / UX / Interaction ────────────────────────────────────────────────────
    "인터페이스": ["interface", "user interface"],
    "상호작용": ["interaction", "gesture recognition"],
    "UI": ["UI", "user interface", "interaction"],
    "UX": ["UX", "user experience", "haptic"],

    # ── Circuit / Compensation ───────────────────────────────────────────────────
    "회로": ["circuit", "driving circuit"],
    "구동": ["driving", "driver circuit"],
    "보상": ["compensation", "correction"],
    "왜곡": ["distortion", "aberration"],
    "기판": ["substrate", "flexible substrate"],

    # ── Battery / Energy Storage ─────────────────────────────────────────────────
    "전지": ["battery", "electrochemical cell", "lithium battery"],
    "배터리": ["battery", "lithium", "energy storage"],
    "양극": ["cathode", "cathode material", "positive electrode"],
    "음극": ["anode", "anode material", "negative electrode"],
    "전극": ["electrode", "active material", "electrochemical"],
    "전해질": ["electrolyte", "ionic conductivity", "solid electrolyte"],
    "고체전지": ["solid-state battery", "all-solid-state", "solid electrolyte"],
    "리튬": ["lithium", "Li-ion", "lithium metal"],
    "분리막": ["separator", "membrane", "ionic membrane"],
    "에너지밀도": ["energy density", "specific capacity", "Wh"],
    "충전": ["charging", "fast charging", "charge cycle"],
    "방전": ["discharge", "capacity retention", "cycle life"],
    "연료전지": ["fuel cell", "PEMFC", "hydrogen fuel"],
    "수소": ["hydrogen", "hydrogen storage", "fuel cell"],

    # ── Semiconductor / Process ──────────────────────────────────────────────────
    "반도체": ["semiconductor", "integrated circuit", "chip"],
    "공정": ["process", "fabrication", "lithography"],
    "식각": ["etching", "dry etch", "plasma etching"],
    "증착": ["deposition", "CVD", "sputtering"],
    "패터닝": ["patterning", "photolithography", "photoresist"],
    "나노": ["nano", "nanoscale", "nanostructure"],
    "집적": ["integration", "chip integration", "wafer"],
    "메모리": ["memory", "DRAM", "NAND flash"],
    "트랜지스터": ["transistor", "FET", "MOSFET"],
    "다이오드": ["diode", "LED", "photodiode"],
    "EUV": ["EUV", "extreme ultraviolet", "lithography"],
    "포토레지스트": ["photoresist", "resist", "EUV resist"],

    # ── Artificial Intelligence / Machine Learning ────────────────────────────────
    "인공지능": ["artificial intelligence", "AI", "machine learning"],
    "딥러닝": ["deep learning", "neural network", "CNN"],
    "기계학습": ["machine learning", "supervised learning", "model training"],
    "신경망": ["neural network", "deep learning", "transformer"],
    "추론": ["inference", "edge inference", "model compression"],
    "인식": ["recognition", "detection", "classification"],
    "모델경량화": ["model compression", "pruning", "quantization"],
    "네트워크압축": ["network compression", "knowledge distillation", "quantization"],
    "언어모델": ["language model", "LLM", "transformer"],
    "컴퓨터비전": ["computer vision", "image recognition", "object detection"],

    # ── Communication / Network ──────────────────────────────────────────────────
    "통신": ["communication", "wireless", "network"],
    "안테나": ["antenna", "beamforming", "phased array"],
    "주파수": ["frequency", "spectrum", "bandwidth"],
    "무선": ["wireless", "radio frequency", "RF"],
    "네트워크": ["network", "protocol", "connectivity"],
    "5G": ["5G", "millimeter wave", "NR"],
    "6G": ["6G", "terahertz", "beyond 5G"],
    "채널": ["channel", "channel estimation", "OFDM"],
    "변조": ["modulation", "MIMO", "beamforming"],
    "레이더": ["radar", "FMCW", "LiDAR"],

    # ── Biomedical / Healthcare ───────────────────────────────────────────────────
    "의료": ["medical", "clinical", "healthcare"],
    "바이오": ["biosensor", "biomarker", "biological"],
    "진단": ["diagnostics", "detection", "bioassay"],
    "치료": ["therapy", "treatment", "drug delivery"],
    "약물": ["drug", "pharmaceutical", "drug delivery"],
    "세포": ["cell", "cellular", "cell culture"],
    "유전자": ["gene", "genomics", "CRISPR"],
    "단백질": ["protein", "proteomics", "antibody"],
    "영상": ["imaging", "medical imaging", "MRI"],
    "생체신호": ["biosignal", "ECG", "EEG"],
    "임플란트": ["implant", "biocompatible", "implantable"],

    # ── Automotive / Electric Vehicle ────────────────────────────────────────────
    "전기차": ["electric vehicle", "EV", "battery electric"],
    "자동차": ["automotive", "vehicle", "car"],
    "모터": ["motor", "electric motor", "powertrain"],
    "자율주행": ["autonomous driving", "ADAS", "self-driving"],
    "BMS": ["BMS", "battery management", "state of charge"],
    "충전인프라": ["charging infrastructure", "EV charger", "fast charger"],
    "인버터": ["inverter", "power inverter", "motor drive"],

    # ── Optics / Photonics ───────────────────────────────────────────────────────
    "광학": ["optical", "optics", "photonic"],
    "레이저": ["laser", "laser beam", "laser diode"],
    "광원": ["light source", "LED", "illumination"],
    "광통신": ["optical communication", "fiber optic", "wavelength"],
    "렌즈": ["lens", "optical lens", "optics"],
    "파장": ["wavelength", "spectrum", "optical band"],
    "편광": ["polarization", "polarizer", "wave plate"],

    # ── Power Electronics ────────────────────────────────────────────────────────
    "전력": ["power", "power electronics", "power conversion"],
    "컨버터": ["converter", "DC-DC converter", "power converter"],
    "변환기": ["converter", "power converter", "rectifier"],
    "절연": ["insulation", "isolation", "dielectric"],

    # ── Materials / Manufacturing ────────────────────────────────────────────────
    "소재": ["material", "advanced material", "functional material"],
    "복합재": ["composite material", "composite", "fiber reinforced"],
    "경량화": ["lightweight", "weight reduction", "model compression"],
    "강도": ["strength", "mechanical strength", "tensile strength"],
    "내열": ["heat resistance", "thermal stability", "refractory"],
    "내식": ["corrosion resistance", "anti-corrosion", "passivation"],
    "코팅": ["coating", "surface coating", "thin film coating"],
    "3D프린팅": ["3D printing", "additive manufacturing", "SLM"],
    "프린팅": ["printing", "additive manufacturing", "inkjet"],
    "주조": ["casting", "die casting", "metal casting"],

    # ── Robotics / Automation ─────────────────────────────────────────────────────
    "로봇": ["robot", "robotic arm", "collaborative robot"],
    "액추에이터": ["actuator", "servo", "pneumatic actuator"],
    "제어": ["control", "feedback control", "PID controller"],
    "자동화": ["automation", "industrial automation", "CNC"],
    "조립": ["assembly", "automated assembly", "pick and place"],

    # ── Environment / Energy Conversion ─────────────────────────────────────────
    "정화": ["purification", "water treatment", "filtration"],
    "필터": ["filter", "membrane filtration", "air filter"],
    "오염": ["pollution", "contaminant removal", "remediation"],
    "태양전지": ["solar cell", "photovoltaic", "perovskite solar"],
    "열전": ["thermoelectric", "Seebeck effect", "TEG"],
    "풍력": ["wind energy", "wind turbine", "generator"],
}


def load_domain_dict(path: Path | None) -> dict[str, list[str]]:
    """
    Load an external domain dictionary (JSON) and merge with built-in _KO_EXPAND.
    External entries override built-in entries for the same Korean key.

    Expected JSON format:
      { "한글키워드": ["english_term1", "english_term2", ...], ... }
    """
    merged = dict(_KO_EXPAND)
    if path is None:
        return merged
    if not path.exists():
        print(f"⚠️  도메인 사전 파일 없음 (무시): {path}", file=sys.stderr)
        return merged
    try:
        ext_dict = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(ext_dict, dict):
            merged.update(ext_dict)
            print(f"  ✓ 외부 도메인 사전 로딩: {len(ext_dict)}개 항목 ({path.name})")
    except (json.JSONDecodeError, OSError) as e:
        print(f"⚠️  도메인 사전 파싱 오류 (무시): {e}", file=sys.stderr)
    return merged


def validate_differentiation(sub_techs: list[dict]) -> list[str]:
    """
    Validate that sub-technologies have differentiated key_terms.
    Returns a list of warning messages for overlapping pairs.

    Criteria:
      - Jaccard similarity between any two sub-techs' key_terms > 0.5 → warning
      - Any sub-tech with < 3 key_terms → warning
      - All sub-techs sharing the same top-2 terms → critical warning
    """
    warnings: list[str] = []

    for st in sub_techs:
        kt = st.get("key_terms", [])
        if len(kt) < 3:
            warnings.append(
                f"⚠️  [{st['id']}] key_terms가 {len(kt)}개로 부족 (최소 3개 권장)"
            )

    # Pairwise Jaccard similarity
    for i in range(len(sub_techs)):
        for j in range(i + 1, len(sub_techs)):
            set_i = {t.lower() for t in sub_techs[i].get("key_terms", [])}
            set_j = {t.lower() for t in sub_techs[j].get("key_terms", [])}
            if not set_i or not set_j:
                continue
            intersection = set_i & set_j
            union = set_i | set_j
            jaccard = len(intersection) / len(union) if union else 0
            if jaccard > 0.5:
                overlap = ", ".join(sorted(intersection))
                warnings.append(
                    f"⚠️  [{sub_techs[i]['id']}] ↔ [{sub_techs[j]['id']}] "
                    f"key_terms 유사도 {jaccard:.0%} (중복: {overlap})"
                )

    # Check if all share same top-2 terms
    if len(sub_techs) >= 3:
        all_top2 = [
            set(t.lower() for t in st.get("key_terms", [])[:2])
            for st in sub_techs
        ]
        if all_top2 and all(s == all_top2[0] for s in all_top2):
            warnings.append(
                "🚨  모든 세부 기술이 동일한 상위 2개 key_terms를 공유 → 검색 결과 중복 우려"
            )

    return warnings

# ── Meta-heading patterns to EXCLUDE from sub-tech candidates ─────────────────

META_HEADING_PATTERNS = [
    r"해결하고자\s*하는",
    r"문제의\s*정의",
    r"기획의\s*주안점",
    r"목표\s*달성을\s*통한",
    r"기대\s*효과",
    r"추진\s*배경",
    r"기술\s*동향",
    r"수요\s*기반",
    r"상용화[\s\S]{0,5}파급",
    r"단계별\s*목표",
]


# ── Helper functions ──────────────────────────────────────────────────────────

def load_rfp(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def strip_table_cell_content(text: str) -> str:
    """
    Convert Markdown table rows to plain text lines.
    Handles `| cell1 | cell2 |` → individual lines for each cell.

    Special handling: pdfplumber often collapses multi-line table cell content
    into a single long string.  We restore bullet structure by splitting on
    Korean bullet markers (ㅇ, ·) within a single cell.
    """
    result_lines = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("|"):
            # Table row: extract each cell as its own line(s)
            cells = stripped.split("|")
            for cell in cells:
                cell = cell.strip()
                if cell and cell != "---" and not re.match(r"^[-:]+$", cell):
                    # Split on embedded Korean bullets that pdfplumber merged onto
                    # one line: "... 기술 ㅇ 다음기술 ..." → restore as separate lines
                    # Split before "ㅇ " or "· " when preceded by whitespace
                    sub_parts = re.split(r"(?<=[\s,])\s*(?=ㅇ\s|·\s)", cell)
                    for part in sub_parts:
                        part = part.strip()
                        if part:
                            result_lines.append(part)
        else:
            result_lines.append(line)
    return "\n".join(result_lines)


def extract_section(text: str, patterns: list[str], max_chars: int = 3000) -> str:
    """
    Extract text following a section heading.
    Also searches inside table cell content (PDF→MD tables).
    """
    # Try heading-based extraction first
    heading_pat = r"(?:#{1,4}\s+|(?:^|\n)[^\n]*?)"
    for pat in patterns:
        full_pat = heading_pat + pat
        m = re.search(full_pat, text, re.IGNORECASE | re.MULTILINE)
        if m:
            start = m.end()
            next_heading = re.search(r"\n#{1,4}\s+", text[start:])
            end = start + next_heading.start() if next_heading else start + max_chars
            return text[start:end].strip()[:max_chars]

    # Fallback: search in table cell content (PDF→MD specific)
    flat = strip_table_cell_content(text)
    for pat in patterns:
        m = re.search(r"(?:^|\n)[^\n]*" + pat + r"[^\n]*\n([\s\S]*?)(?=\n[^\n]*(?:" +
                      "|".join(["연구개발내용", "과제목표", "성과지표", "키워드"]) + r")|$)",
                      flat, re.IGNORECASE)
        if m:
            return m.group(1).strip()[:max_chars]

    return ""


def is_meta_heading(text: str) -> bool:
    """Return True if text is a section label / meta-heading, not a tech name."""
    for pat in META_HEADING_PATTERNS:
        if re.search(pat, text):
            return True
    return False


def truncate_to_tech_name(item: str, max_len: int = 40) -> str | None:
    """
    Shorten a long bullet sentence to a concise technology name.
    Returns None if the item is a meta-heading (should be filtered out).
    """
    item = item.strip()
    # Remove leading bullet chars that weren't caught
    item = re.sub(r"^[·•◦ㅇ▸\-\*]\s*", "", item).strip()

    if not item or len(item) < 5:
        return None
    if is_meta_heading(item):
        return None

    # Pattern 1: extract "X기술", "X시스템", "X센서", ... noun phrases
    tech_suffixes = (
        "기술|시스템|알고리즘|공정|센서|디스플레이|회로|플랫폼|인터페이스"
        "|소자|모듈|구조|백플레인|소재|소자"
    )
    m = re.search(
        r"([가-힣a-zA-Z0-9()/·\-\s]{4,35}(?:" + tech_suffixes + r"))",
        item,
    )
    if m:
        candidate = m.group(1).strip()
        if 6 <= len(candidate) <= max_len:
            return candidate

    # Pattern 2: truncate at first comma / connector
    for sep in [",", "，", " 및 ", " 위해 ", " 위한 ", "을 위한", "를 위한"]:
        idx = item.find(sep)
        if 10 <= idx <= max_len:
            return item[:idx].strip()

    # Pattern 3: just truncate at word boundary
    if len(item) > max_len:
        truncated = item[:max_len]
        last_space = truncated.rfind(" ")
        if last_space > max_len - 10:
            truncated = truncated[:last_space]
        return truncated + "…"

    return item


def extract_bullet_items(section_text: str) -> list[str]:
    """
    Extract bullet list items from section text.
    Supports:
      - Standard Markdown: -, *, •, ◦, ▪, ▸
      - Korean RFP bullets: ㅇ (circle), · (middle dot)
      - Content inside Markdown table cells
    """
    # Strip table markup so we can find bullets inside table cells
    flat_text = strip_table_cell_content(section_text)

    items = []
    for line in flat_text.split("\n"):
        line = line.strip()
        # Match Korean bullets (ㅇ, ·) AND standard Markdown bullets
        m = re.match(
            r"^(?:[-*•◦·▪▸ㅇ]\s+|\d+\.\s+|[가나다라마바사]\.\s+)(.*)",
            line,
        )
        if m:
            item = m.group(1).strip()
            if len(item) > 5:
                items.append(item)
    return items


def extract_rfp_en_keywords(text: str) -> list[str]:
    """
    Extract explicitly listed English keywords from the RFP.
    Matches patterns like: '영문 | Display, Transformable, Deformation sensing...'
    or '영문 키워드: Display, Transformable...'
    """
    # Table cell pattern (PDF→MD output): 영문 | Display, ...
    m = re.search(
        r"영문[^\n|]{0,15}[|：:]\s*([A-Za-z][^|\n]{5,300})",
        text,
        re.IGNORECASE,
    )
    if m:
        terms_str = m.group(1).strip()
        # Remove trailing table pipe
        terms_str = terms_str.split("|")[0].strip()
        terms = [t.strip() for t in re.split(r"[,，、]", terms_str) if t.strip()]
        return [t for t in terms if len(t) >= 2]
    return []


def extract_english_terms(text: str, priority_text: str = "") -> list[str]:
    """Extract English technical terms. Priority text is searched first."""
    stopwords = STOPWORDS_EN

    def _extract(t: str) -> list[str]:
        terms = re.findall(r"\b[A-Z][a-zA-Z\-]{2,20}\b|\b[a-z]{4,20}\b", t)
        return [x for x in terms if x.lower() not in stopwords and len(x) > 3]

    priority = list(dict.fromkeys(_extract(priority_text))) if priority_text else []
    all_terms = list(dict.fromkeys(_extract(text)))
    # Merge: priority first, then CamelCase/hyphenated, then rest
    camel = [t for t in all_terms if re.search(r"[A-Z][a-z]|[-]", t)]
    combined = []
    seen = set()
    for t in priority + camel + all_terms:
        if t not in seen:
            seen.add(t)
            combined.append(t)
    return combined[:20]


def extract_noun_phrases_ko(text: str) -> list[str]:
    """Simple heuristic: extract Korean noun phrases."""
    phrases = []
    tech_suffixes = [
        "기술", "소재", "공정", "소자", "센서", "디스플레이", "모듈",
        "인터페이스", "알고리즘", "시스템", "구조", "구동", "회로", "백플레인",
    ]
    for suffix in tech_suffixes:
        matches = re.findall(r"[가-힣]{2,8}" + suffix, text)
        phrases.extend(matches)
    chunks = re.findall(r"[가-힣]{2,5}(?:\s+[가-힣]{2,5}){0,2}", text)
    for chunk in chunks:
        words = chunk.split()
        if not any(w in STOPWORDS_KO for w in words):
            phrases.append(chunk)
    return list(dict.fromkeys(phrases))


# ── Main extraction logic ─────────────────────────────────────────────────────

def cluster_into_sub_techs(
    contents: str, objectives: str, indicators: str, keywords: str,
    rfp_en_keywords: list[str],
    min_count: int = 3, max_count: int = 5,
    domain_dict: dict[str, list[str]] | None = None,
) -> list[dict]:
    """
    Heuristic clustering of RFP content into sub-technologies.
    Priority: 연구개발내용 > 과제목표 > noun phrase fallback.
    """
    # --- Step 1: collect raw bullet items (priority order) ---
    raw_items = extract_bullet_items(contents)
    if len(raw_items) < min_count:
        raw_items += extract_bullet_items(objectives)
    if len(raw_items) < min_count:
        raw_items += extract_bullet_items(indicators)

    # --- Step 2: apply truncation + meta-heading filter ---
    seen_keys: set[str] = set()
    filtered: list[str] = []
    for item in raw_items:
        name = truncate_to_tech_name(item)
        if name is None:
            continue
        key = re.sub(r"\s+", "", name[:15])
        if key not in seen_keys and len(name) > 4:
            seen_keys.add(key)
            filtered.append(name)
        if len(filtered) >= max_count:
            break

    # --- Step 3: supplement from keyword section ---
    if len(filtered) < min_count:
        for item in extract_bullet_items(keywords):
            name = truncate_to_tech_name(item)
            if name is None:
                continue
            key = re.sub(r"\s+", "", name[:15])
            if key not in seen_keys:
                seen_keys.add(key)
                filtered.append(name)
            if len(filtered) >= max_count:
                break

    # --- Step 4: Korean noun phrase fallback ---
    if len(filtered) < min_count:
        ko_phrases = extract_noun_phrases_ko(contents + "\n" + objectives)
        for phrase in ko_phrases:
            if phrase in seen_keys:
                continue
            if not is_meta_heading(phrase):
                seen_keys.add(phrase)
                filtered.append(phrase)
            if len(filtered) >= min_count:
                break

    # --- Step 5: build English key_terms ---
    # General English pool for fallback (same for all sub-techs)
    all_text = contents + "\n" + objectives + "\n" + keywords
    all_en = extract_english_terms(all_text, priority_text=keywords)

    # Build sub-tech dicts — each uses _build_key_terms() for differentiated terms
    sub_techs = []
    for i, name in enumerate(filtered[:max_count], 1):
        combined_en = _build_key_terms(name, rfp_en_keywords, all_en, domain_dict=domain_dict)

        sub_techs.append({
            "id": f"sub{i}",
            "name_ko": name.strip(),
            "name_en": _make_name_en(name, combined_en),
            "description": f"RFP 세부 기술 {i}: {name.strip()}",
            "key_terms": combined_en[:8],
            "exclude_terms": [],
            "rfp_objectives": [],
            "status": "auto-extracted — please review and edit",
        })

    return sub_techs


def _build_key_terms(
    name_ko: str,
    rfp_en_keywords: list[str],
    fallback_pool: list[str],
    target: int = 8,
    domain_dict: dict[str, list[str]] | None = None,
) -> list[str]:
    """
    Build differentiated English key_terms for a sub-tech from its Korean name.

    Priority:
      1. English terms embedded directly in the Korean name (e.g. "TFT", "RGB", "UI/UX")
      2. Domain expansion from domain_dict (merged _KO_EXPAND + external)
      3. RFP explicit English keywords (unique ones not already included)
      4. General English pool fallback

    Each sub-tech gets a distinct set because steps 1+2 depend on the name itself.
    """
    expand = domain_dict if domain_dict is not None else _KO_EXPAND
    terms: list[str] = []
    seen: set[str] = set()

    def _add(t: str) -> bool:
        tl = t.lower().strip()
        if tl and tl not in seen and len(tl) >= 2:
            seen.add(tl)
            terms.append(t.strip())
            return True
        return False

    # 1. Extract English terms embedded in the Korean name
    #    e.g. "TFT", "RGB", "UI/UX", "100PPI" → capture TFT, RGB, UI, UX
    for tok in re.findall(r"[A-Za-z][A-Za-z0-9\-/]{1,20}", name_ko):
        # Split on "/" for compounds like "UI/UX"
        for part in re.split(r"[/]", tok):
            if part and len(part) >= 2 and part.lower() not in STOPWORDS_EN:
                _add(part)

    # 2. Domain expansion for Korean keywords found in the name
    for ko_key, en_list in expand.items():
        if ko_key in name_ko:
            for t in en_list:
                _add(t)
                if len(terms) >= target:
                    break
        if len(terms) >= target:
            break

    # 3. RFP explicit keywords (unique; avoids exact-lower duplicates)
    for t in rfp_en_keywords:
        _add(t)
        if len(terms) >= target:
            break

    # 4. General fallback pool
    for t in fallback_pool:
        _add(t)
        if len(terms) >= target:
            break

    return terms[:target]


def _make_name_en(name_ko: str, en_terms: list[str]) -> str:
    """Generate an English name for the sub-tech from co-occurring EN terms."""
    if len(en_terms) >= 2:
        return " ".join(en_terms[:2])
    if en_terms:
        return en_terms[0]
    return "Sub-technology"


# ── CLI entry point ───────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Extract 3-5 sub-technologies from RFP markdown for targeted patent search"
    )
    ap.add_argument("rfp_path", help="RFP markdown file path")
    ap.add_argument("-o", "--output", required=True, help="Output JSON path (sub_techs.json)")
    ap.add_argument("--min", type=int, default=3, help="Minimum sub-technologies (default 3)")
    ap.add_argument("--max", type=int, default=5, help="Maximum sub-technologies (default 5)")
    ap.add_argument(
        "--domain-dict", type=str, default=None,
        help="External domain dictionary JSON path (Korean→English term mappings). "
             "Supplements built-in 190+ term dictionary for uncommon domains."
    )
    args = ap.parse_args()

    rfp_path = Path(args.rfp_path)
    out_path = Path(args.output)

    if not rfp_path.exists():
        print(f"RFP not found: {rfp_path}", file=sys.stderr)
        sys.exit(1)

    text = load_rfp(rfp_path)

    # Extract RFP title
    title_match = re.search(r'title:\s*["\']?(.+?)["\']?\s*\n', text)
    rfp_title = title_match.group(1).strip() if title_match else rfp_path.stem

    # Extract sections
    contents = extract_section(text, SECTION_PATTERNS["contents"])
    objectives = extract_section(text, SECTION_PATTERNS["objectives"])
    indicators = extract_section(text, SECTION_PATTERNS["indicators"])
    keywords = extract_section(text, SECTION_PATTERNS["keywords"])
    rfp_en_keywords = extract_rfp_en_keywords(text)

    # Load external domain dictionary if provided
    domain_dict_path = Path(args.domain_dict) if args.domain_dict else None
    merged_dict = load_domain_dict(domain_dict_path)

    # Fallback: if no section content found, use entire stripped-table text
    flat_text = strip_table_cell_content(text)
    if not contents and not objectives:
        contents = flat_text

    sub_techs = cluster_into_sub_techs(
        contents=contents or flat_text,
        objectives=objectives or flat_text,
        indicators=indicators,
        keywords=keywords,
        rfp_en_keywords=rfp_en_keywords,
        min_count=args.min,
        max_count=args.max,
        domain_dict=merged_dict,
    )

    # Validate key_terms differentiation
    quality_warnings = validate_differentiation(sub_techs)

    result = {
        "rfp_title": rfp_title,
        "rfp_path": str(rfp_path),
        "rfp_en_keywords": rfp_en_keywords,
        "sub_tech_count": len(sub_techs),
        "sub_technologies": sub_techs,
        "quality_warnings": quality_warnings,
        "instructions": (
            "아래 세부 기술 목록을 검토하고 필요 시 수정하세요.\n"
            "각 항목의 name_ko, name_en, key_terms, exclude_terms를 정확히 작성하면\n"
            "이후 검색식 생성 및 연관성 점수 계산 품질이 향상됩니다.\n"
            "key_terms: Google Patents 검색에 사용할 영어 핵심 키워드 (3~8개)\n"
            "exclude_terms: 이 세부 기술에서 제외할 단어 (노이즈 방지)\n"
            "\n"
            "⚠️ 자동 추출 결과는 Claude의 RFP 분석 보정을 거친 뒤 사용자 확인을 받아야 합니다.\n"
            "   Claude는 아래 결과를 RFP 원문과 대조하여 기술명·key_terms를 보정하고,\n"
            "   보정된 결과를 사용자에게 제시합니다."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    # Print summary
    print(f"\n{'='*60}")
    print(f"RFP: {rfp_title}")
    if rfp_en_keywords:
        print(f"RFP 영문 키워드: {', '.join(rfp_en_keywords)}")
    print(f"도출된 세부 기술 ({len(sub_techs)}개):")
    print(f"{'='*60}")
    for st in sub_techs:
        print(f"\n  [{st['id']}] {st['name_ko']}")
        print(f"       영문: {st['name_en']}")
        print(f"       키워드: {', '.join(st['key_terms']) if st['key_terms'] else '(미설정)'}")
    # Print quality warnings
    if quality_warnings:
        print(f"\n{'─'*60}")
        print("📋 품질 검증 결과:")
        for w in quality_warnings:
            print(f"  {w}")
        print(f"{'─'*60}")
    else:
        print(f"\n  ✅ 품질 검증 통과: key_terms 간 중복 없음")

    print(f"\n{'='*60}")
    print(f"결과 저장: {out_path}")
    print("\n⚠️  자동 추출 결과입니다. Claude의 RFP 분석 보정 → 사용자 확인 후 사용하세요.")
    print("   (1) Claude가 RFP 원문과 대조하여 기술명·key_terms 보정")
    print("   (2) 보정된 결과를 사용자에게 표 형태로 제시")
    print("   (3) 사용자 승인 후 Phase 2 진행")


if __name__ == "__main__":
    main()
