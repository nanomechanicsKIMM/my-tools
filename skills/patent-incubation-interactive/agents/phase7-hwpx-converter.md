---
name: phase7-hwpx-converter
description: "HWPX 변환 에이전트. 완성된 발명내용설명서 MD를 KIMM 양식 HWPX로 변환한다. 전체 셀 내용 교체 방식(전략 A)."
model: sonnet
---

# Phase 7: HWPX 변환

## 입력

1. Phase 6 출력 MD 파일 `(YYYYMMDD 발명자) 발명명칭vN.md` — 9개 섹션 MD
2. `reference/kimm-template-mapping.md` — 셀별 고유키 매핑
3. `assets/[KIMM]직무발명내용설명서_양식.hwpx` — 원본 양식

## 의존 스크립트

- **convert_hwpx.py**: `{SHARED_SKILL_ROOT}/scripts/convert_hwpx.py` — 메인 변환 스크립트 (auto 스킬 공유; auto의 `assets/` 양식 템플릿에 의존하므로 SHARED 경로 필수)
- **fix_namespaces.py**: `C:/Users/JHKIM/.claude/skills/hwpx/scripts/fix_namespaces.py`
- **validate.py**: `C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/validate.py`

## 권장 실행 방법 (스크립트 직접 호출)

> [!important] 아래 스크립트를 직접 실행하는 것이 가장 안정적이다. Python 코드를 에이전트가 재구현하지 말 것.

```bash
python "{SHARED_SKILL_ROOT}/scripts/convert_hwpx.py" \
  --disclosure "{output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.md" \
  --output "{output_dir}/{발명명칭}_발명내용설명서.hwpx" \
  --diagrams "{output_dir}/diagrams"
```

스크립트가 수행하는 작업:
1. Phase 6 출력 MD에서 §1~§9 추출 (부록 제외, 마크다운 서식 제거)
2. 템플릿 HWPX 해제 → section0.xml 파싱
3. 각 셀의 모든 hp:p 제거 후 새 단락 삽입 (lineseg vertpos 누적 계산)
4. §9에 diagrams/*.png 삽입 (hp:pic + BinData + content.hpf 업데이트)
5. 템플릿 image1.bmp 제외
6. fix_namespaces + validate 실행

스크립트 실행이 성공하면 Phase 7 완료. 실패 시 아래 수동 절차 참조.

---

## 수동 절차 (스크립트 실패 시 fallback)

### Step 1: MD 파싱

Phase 6 출력 MD 파일에서 `## §N` 헤더로 9개 섹션 본문을 추출:

```python
import re

sections = {}
current = None
for line in md_text.split('\n'):
    m = re.match(r'^## §(\d+)\s', line)
    if m:
        current = int(m.group(1))
        sections[current] = []
    elif current is not None:
        sections[current].append(line)

# 각 섹션 본문을 정리 (Obsidian 콜아웃 등 제거)
for k in sections:
    text = '\n'.join(sections[k]).strip()
    # > [!note] 블록 제거
    text = re.sub(r'> \[!.*?\].*?\n(?:>.*?\n)*', '', text).strip()
    # ### 하위 헤더를 일반 텍스트로 변환
    text = re.sub(r'^###?\s+', '', text, flags=re.MULTILINE)
    # 마크다운 볼드/이탤릭 제거
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    sections[k] = text
```

### Step 2: XML 이스케이프

HWPX XML에 삽입하기 전에 특수문자 이스케이프:

```python
from xml.sax.saxutils import escape
for k in sections:
    sections[k] = escape(sections[k])
```

### Step 3: 전체 셀 내용 교체 (전략 A — 필수)

> [!warning] 중요: 단순 텍스트 치환(zip_replace)은 사용 금지
> 기존 zip_replace()는 첫 번째 hp:t만 교체하고 나머지 hp:p 블록이 남아 텍스트가 겹치는 버그를 발생시킨다.
> 반드시 **전체 셀 내용 교체 방식**을 사용해야 한다.

#### 핵심 원리

각 섹션 셀(`<hp:tc>`) 내부의 **모든 `<hp:p>` 요소를 제거**하고, 새 내용을 줄바꿈(`\n\n` 또는 `\n`) 기준으로 분할하여 **개별 `<hp:p>` 요소로 재생성**한다.

#### Python 구현

```python
import zipfile, shutil, copy
import xml.etree.ElementTree as ET

# HWPX 네임스페이스 등록
NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hp2': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
}
for prefix, uri in NS.items():
    ET.register_namespace(prefix, uri)

# 섹션별 스타일 참조 (kimm-template-mapping.md에서 추출)
SECTION_STYLES = {
    1: {'paraPrIDRef': '12', 'charPrIDRef': '16'},  # §1 발명 명칭
    2: {'paraPrIDRef': '12', 'charPrIDRef': '11'},  # §2 논문발표
    3: {'paraPrIDRef': '14', 'charPrIDRef': '11'},  # §3 배경
    4: {'paraPrIDRef': '14', 'charPrIDRef': '11'},  # §4 종래기술
    5: {'paraPrIDRef': '14', 'charPrIDRef': '11'},  # §5 목적
    6: {'paraPrIDRef': '14', 'charPrIDRef': '11'},  # §6 구성
    7: {'paraPrIDRef': '14', 'charPrIDRef': '11'},  # §7 효과
    8: {'paraPrIDRef': '14', 'charPrIDRef': '11'},  # §8 청구범위
    9: {'paraPrIDRef': '12', 'charPrIDRef': '6'},   # §9 추가자료
}

# 셀 위치 매핑 (테이블 인덱스, 행 인덱스, 셀 인덱스)
SECTION_CELLS = {
    1: (0, 2, 0),   # Table 0, Row 2, Cell 0
    2: (0, 4, 0),   # Table 0, Row 4, Cell 0
    3: (0, 6, 0),   # Table 0, Row 6, Cell 0
    4: (0, 8, 0),   # Table 0, Row 8, Cell 0
    5: (1, 1, 0),   # Table 1, Row 1, Cell 0
    6: (1, 3, 0),   # Table 1, Row 3, Cell 0
    7: (1, 5, 0),   # Table 1, Row 5, Cell 0
    8: (1, 7, 0),   # Table 1, Row 7, Cell 0
    9: (1, 9, 0),   # Table 1, Row 9, Cell 0
}

def make_paragraph(text, para_id_ref, char_id_ref):
    """단일 hp:p 요소를 생성한다."""
    hp_ns = NS['hp']
    p = ET.Element(f'{{{hp_ns}}}p')
    p.set('id', '0')
    p.set('paraPrIDRef', para_id_ref)
    p.set('styleIDRef', '0')
    p.set('pageBreak', '0')
    p.set('columnBreak', '0')
    p.set('merged', '0')

    run = ET.SubElement(p, f'{{{hp_ns}}}run')
    run.set('charPrIDRef', char_id_ref)

    t = ET.SubElement(run, f'{{{hp_ns}}}t')
    t.text = text

    lsa = ET.SubElement(p, f'{{{hp_ns}}}linesegarray')
    ls = ET.SubElement(lsa, f'{{{hp_ns}}}lineseg')
    ls.set('textpos', '0')
    ls.set('vertpos', '0')
    ls.set('vertsize', '1000')
    ls.set('textheight', '1000')
    ls.set('baseline', '850')
    ls.set('spacing', '600')
    ls.set('horzpos', '0')
    ls.set('horzsize', '41672')
    ls.set('flags', '2490368')

    return p

def replace_cell_content(tree, table_idx, row_idx, cell_idx, new_text, styles):
    """특정 셀의 전체 내용을 새 텍스트로 교체한다."""
    root = tree.getroot()
    hp_ns = NS['hp']

    # 테이블 찾기 (hp:tbl)
    tables = root.findall(f'.//{{{hp_ns}}}tbl')
    if table_idx >= len(tables):
        # subList 내부의 테이블도 검색
        tables = []
        for elem in root.iter():
            if elem.tag.endswith('}tbl') or elem.tag == 'hp:tbl':
                tables.append(elem)

    tbl = tables[table_idx]

    # 행 찾기 (hp:tr)
    rows = tbl.findall(f'{{{hp_ns}}}tr')
    row = rows[row_idx]

    # 셀 찾기 (hp:tc)
    cells = row.findall(f'{{{hp_ns}}}tc')
    cell = cells[cell_idx]

    # 셀 내부의 기존 hp:p 요소 모두 제거
    # subList가 있으면 그 안의 hp:p를 제거
    sublist = cell.find(f'{{{hp_ns}}}subList')
    if sublist is None:
        # subList 없이 직접 hp:p가 있는 경우
        container = cell
    else:
        container = sublist

    # 기존 hp:p 요소 모두 제거 (hp:pic 포함 요소도 제거)
    paras_to_remove = []
    for child in list(container):
        if child.tag.endswith('}p') or child.tag == 'hp:p':
            paras_to_remove.append(child)
    for p in paras_to_remove:
        container.remove(p)

    # 새 텍스트를 단락 단위로 분할
    # 빈 줄(\n\n)은 단락 구분, 단일 줄바꿈(\n)도 단락 구분
    paragraphs = [p.strip() for p in new_text.split('\n') if p.strip()]

    if not paragraphs:
        paragraphs = [' ']  # 빈 셀 방지

    # 새 hp:p 요소들을 생성하여 삽입
    for para_text in paragraphs:
        new_p = make_paragraph(
            para_text,
            styles['paraPrIDRef'],
            styles['charPrIDRef']
        )
        container.append(new_p)

def remove_images_from_cell(tree, table_idx, row_idx, cell_idx):
    """특정 셀에서 hp:pic 요소(이미지)를 모두 제거한다."""
    root = tree.getroot()
    hp_ns = NS['hp']

    tables = root.findall(f'.//{{{hp_ns}}}tbl')
    if table_idx >= len(tables):
        tables = []
        for elem in root.iter():
            if elem.tag.endswith('}tbl') or elem.tag == 'hp:tbl':
                tables.append(elem)

    tbl = tables[table_idx]
    rows = tbl.findall(f'{{{hp_ns}}}tr')
    row = rows[row_idx]
    cells = row.findall(f'{{{hp_ns}}}tc')
    cell = cells[cell_idx]

    # 재귀적으로 hp:pic 요소 제거
    for parent in cell.iter():
        pics_to_remove = []
        for child in parent:
            if child.tag.endswith('}pic') or child.tag == 'hp:pic':
                pics_to_remove.append(child)
        for pic in pics_to_remove:
            parent.remove(pic)

def convert_hwpx(template_path, output_path, sections):
    """HWPX 변환 메인 함수"""
    tmp_dir = output_path + '_tmp'

    # 1. ZIP 해제
    with zipfile.ZipFile(template_path, 'r') as z:
        z.extractall(tmp_dir)

    # 2. section0.xml 파싱
    section_xml = os.path.join(tmp_dir, 'Contents', 'section0.xml')
    tree = ET.parse(section_xml)

    # 3. 각 섹션 셀 내용 교체
    for sec_num, content in sections.items():
        tbl_idx, row_idx, cell_idx = SECTION_CELLS[sec_num]
        styles = SECTION_STYLES[sec_num]
        replace_cell_content(tree, tbl_idx, row_idx, cell_idx, content, styles)

    # 4. §9 셀에서 기존 템플릿 이미지 삭제
    tbl_idx, row_idx, cell_idx = SECTION_CELLS[9]
    remove_images_from_cell(tree, tbl_idx, row_idx, cell_idx)

    # 5. BinData/image1.bmp 파일도 ZIP에서 제거 (선택적)

    # 6. 수정된 XML 저장
    tree.write(section_xml, encoding='utf-8', xml_declaration=True)

    # 7. 다시 ZIP으로 압축
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zout:
        for root_dir, dirs, files in os.walk(tmp_dir):
            for f in files:
                file_path = os.path.join(root_dir, f)
                arcname = os.path.relpath(file_path, tmp_dir)
                # image1.bmp 제외 (§9 기존 이미지 삭제)
                if arcname == os.path.join('BinData', 'image1.bmp'):
                    continue
                zout.write(file_path, arcname)

    # 8. 임시 디렉토리 정리
    shutil.rmtree(tmp_dir)
```

### Step 4: 네임스페이스 수정

```bash
python3 "C:/Users/JHKIM/.claude/skills/hwpx/scripts/fix_namespaces.py" "$OUTPUT_HWPX"
```

### Step 5: 검증

```bash
python3 "C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/validate.py" "$OUTPUT_HWPX"
```

검증 실패 시:
- 에러 메시지 확인
- XML 구조 오류면 이스케이프 재확인
- 복구 불가 시 MD 파일만 최종 출력 (fallback)

## 출력

- `(YYYYMMDD 발명자) {발명명칭}v1.hwpx` — KIMM 양식 HWPX
- `(YYYYMMDD 발명자) {발명명칭}vN.md` — Phase 6에서 이미 이 형식으로 생성됨
- manifest 업데이트: `"phase7": {"status": "completed", "output": "(YYYYMMDD 발명자) {발명명칭}v1.hwpx"}`

> [!important] 파일명 규칙: `(YYYYMMDD 발명자) 발명명칭vN.hwpx` 형식. 수정본 생성 시 v2, v3으로 버전 증가.

## §8 청구범위 특별 규칙 (검증됨 — 2026-03-31)

§8은 **청구항 단위로 문단을 분할**해야 한다. 줄 단위로 분할하면 안 된다.

- Phase 6 출력 MD의 §8에서 `**[청구항 N]**`로 시작하는 각 청구항 블록을 식별
- 각 청구항의 헤더(`[청구항 N] (유형)`)와 본문을 공백으로 합쳐 **하나의 hp:p 요소**로 생성
- 예: 6개 청구항 → 6개 hp:p 요소 (27개가 아님)

```python
# §8 청구항 단위 분할
import re
claims = re.split(r'\n\n(?=\*\*\[청구항)', section8_text)
for claim in claims:
    claim_oneline = ' '.join(line.strip() for line in claim.strip().split('\n') if line.strip())
    claim_oneline = claim_oneline.replace('**', '')  # 마크다운 볼드 제거
    # → 이 claim_oneline을 하나의 hp:p로 생성
```

## §9 도면 삽입 규칙 (검증됨 — 2026-03-31)

### hp:pic 필수 구조

> [!warning] `hc:` 네임스페이스 요소 (transMatrix, scaMatrix, rotMatrix) 사용 금지
> `<hp:renderingInfo>` 블록 전체를 생략해야 한다. 포함 시 `validate.py`가 네임스페이스 미선언 오류로 실패한다.

```xml
<hp:p id="0" paraPrIDRef="12" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="6">
    <hp:ctrl>
      <hp:pic id="{pic_id}" zOrder="{idx+3}"
        numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES"
        lock="0" dropcapstyle="None" href="" groupLevel="0" instid="{inst_id}" reverse="0">
        <hp:offset x="0" y="0"/>
        <hp:orgSz width="{w}" height="{h}"/>
        <hp:curSz width="{w}" height="{h}"/>
        <hp:flip horizontal="0" vertical="0"/>
        <hp:rotationInfo angle="0" centerX="{w//2}" centerY="{h//2}" rotateimage="1"/>
        <!-- renderingInfo 생략 (hc: 네임스페이스 문제) -->
        <hp:lineShape color="0" width="0" style="None" endCap="Flat"
          headStyle="ARROW_NONE" tailStyle="ARROW_NONE"
          headSz="MEDIUM_MEDIUM" tailSz="MEDIUM_MEDIUM"
          outlineStyle="NORMAL" alpha="0"/>
        <hp:imgRect x="0" y="0" x2="{w}" y2="{h}"/>
        <hp:imgClip left="0" top="0" right="0" bottom="0"/>
        <hp:img bright="0" contrast="0" effect="RealPic" binItemIDRef="{fig_id}"/>
      </hp:pic>
    </hp:ctrl>
  </hp:run>
</hp:p>
```

### 도면 파일명 매핑

diagrams/ 폴더의 실제 파일명과 HWPX 내부 ID를 매핑해야 한다:

| 실제 파일명 | BinData 저장명 | binItemIDRef | content.hpf id |
|------------|---------------|-------------|----------------|
| fig1_system_overview.png | BinData/fig1.png | fig1 | fig1 |
| fig2_process_flow.png | BinData/fig2.png | fig2 | fig2 |
| ... | ... | ... | ... |

### content.hpf 필수 처리

1. **image1 참조 제거**: 템플릿의 `<opf:item id="image1" href="BinData/image1.bmp" .../>` 삭제 (파일 미포함 시 한/글 크래시 발생)
2. **fig 항목 등록**: 각 도면에 대해 `<opf:item id="fig1" href="BinData/fig1.png" media-type="image/png" isEmbeded="1"/>` 추가

### Windows 경로 주의사항

`os.path.join()`으로 경로 조합 시 실제 파일 존재 여부를 `os.listdir()`로 확인할 것. Windows에서 forward/backslash 혼합으로 `os.path.exists()`가 False를 반환할 수 있다. 절대 경로를 사용하는 것을 권장.

## 주의사항

### 절대 금지 사항

- **zip_replace()로 텍스트만 치환하는 방식 사용 금지** — 이 방식은 첫 번째 `hp:t`만 교체하고 나머지 `hp:p` 블록(템플릿 원문)이 남아 한/글에서 열었을 때 글자가 겹쳐 보이는 치명적 버그를 발생시킨다.
- **단일 `hp:t`에 `\n`을 포함한 전체 텍스트를 넣는 방식 금지** — HWPX는 `\n`을 단락 구분으로 인식하지 않는다. 각 단락은 별도의 `<hp:p>` 요소여야 한다.

### 필수 수행 사항

1. **전체 셀 내용 교체**: `replace_cell_content()` 함수로 셀 내 모든 `<hp:p>`를 제거 후 새 단락들을 생성
2. **§9 이미지 삭제**: `remove_images_from_cell()`로 템플릿에 포함된 예시 이미지(`image1.bmp`) 제거
3. **BinData/image1.bmp 제외**: ZIP 재압축 시 해당 파일 미포함
4. **단락 분할**: 새 내용의 각 줄(`\n` 기준)을 개별 `<hp:p>` 요소로 생성
5. **스타일 보존**: 각 섹션의 `paraPrIDRef`, `charPrIDRef` 값을 정확히 적용

### XML 이스케이프 규칙

| 문자 | 이스케이프 |
|------|-----------|
| `&` | `&amp;` |
| `<` | `&lt;` |
| `>` | `&gt;` |
| `"` | `&quot;` |

### 스타일 참조 보존

| 속성 | 설명 | 주요 값 |
|------|------|---------|
| `paraPrIDRef` | 단락 서식 ID | `12` (§1,§2,§9), `14` (§3~§8) |
| `charPrIDRef` | 글자 서식 ID | `16` (§1 명칭), `11` (본문), `6` (§9) |
| `styleIDRef` | 스타일 ID | 모든 셀에서 `0` |
