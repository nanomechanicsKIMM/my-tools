# -*- coding: utf-8 -*-
"""KEIT 첨단나노상용화(2026-08) 기술수요조사서 양식 채움 — 검증된 참조 구현.

⚠️ 이 스크립트는 특정 양식에 맞춘 구현이다. 새 양식에는 다음 부분을 반드시 수정:
  - 표 id (get_tbl 인자: 이 양식은 §1=1161504823, §2=1161504833, 안내박스=1164427360)
  - 체크박스 좌표 map (type_map/detail_map/mega_map 의 (colAddr, rowAddr))
  - 라벨 문자열 (find_label_tc 인자), 예시 문구 anchor (replace_text_once 인자)
  - 견본 체크 정리 로직 (CHK 문자와 기존 체크 위치는 양식마다 다름 — repr 로 확인)
일반 재사용 가능한 부분: weighted_len / rebuild_lineseg / grow_cell_height /
rebuild_cell / insert_figure / register_binitem (SKILL.md Phase 6 규칙의 구현).

사용: python fill_survey_template.py <content.json> <out_dir>
  (스크립트와 같은 폴더 기준 form_unpacked/ 를 원본 언팩본으로 사용)
"""
import sys, json, shutil, copy, re, math
from pathlib import Path
from lxml import etree

HP = 'http://www.hancom.co.kr/hwpml/2011/paragraph'
def q(tag): return f'{{{HP}}}{tag}'

BASE = Path(__file__).parent
SRC = BASE / 'form_unpacked'

def norm(s):
    return re.sub(r'\s+', '', s or '')

def cell_norm_text(tc):
    return norm(''.join(tc.itertext()))

DEFAULT_SEG = {'vertsize': '1100', 'textheight': '1100', 'baseline': '935',
               'spacing': '384', 'horzpos': '0', 'horzsize': '39040'}

def weighted_len(text):
    """한글 1.0, ASCII 0.55, 기타 0.6 가중 길이 (vault HWPX 수정 패턴 §4.1)."""
    total = 0.0
    for ch in text:
        o = ord(ch)
        if o < 128:
            total += 0.55
        elif 0xAC00 <= o <= 0xD7A3:
            total += 1.0
        else:
            total += 0.6
    return total

def para_text(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))

def seg_attrs_of(p):
    """문단의 기존 첫 lineseg 속성 회수 (없으면 기본값)."""
    lsa = p.find(q('linesegarray'))
    if lsa is not None:
        seg = lsa.find(q('lineseg'))
        if seg is not None:
            return {k: seg.get(k, DEFAULT_SEG[k]) for k in DEFAULT_SEG}
    return dict(DEFAULT_SEG)

def rebuild_lineseg(p, attrs, start_vert=0, horzsize=None):
    """문단 linesegarray 를 명시적으로 재생성 (계층 bullet paraPr 는 lineseg 필수).
    flags: 첫 줄 393216, 연속 줄 1441792 (2490368 금지). 사용 줄 수 반환."""
    for lsa in p.findall(q('linesegarray')):
        p.remove(lsa)
    hs = int(horzsize if horzsize else attrs['horzsize'])
    unit = int(attrs['textheight'])  # 한글 1자 폭 ≈ textheight
    per_line = max(1.0, hs / unit)
    text = para_text(p)
    n = max(1, math.ceil(weighted_len(text) / per_line))
    step = int(attrs['vertsize']) + int(attrs['spacing'])
    tlen = max(1, len(text))
    lsa = etree.SubElement(p, q('linesegarray'))
    for i in range(n):
        seg = etree.SubElement(lsa, q('lineseg'))
        seg.set('textpos', str(min(round(i * tlen / n), tlen - 1)))
        seg.set('vertpos', str(start_vert + i * step))
        seg.set('vertsize', attrs['vertsize'])
        seg.set('textheight', attrs['textheight'])
        seg.set('baseline', attrs['baseline'])
        seg.set('spacing', attrs['spacing'])
        seg.set('horzpos', attrs['horzpos'])
        seg.set('horzsize', str(hs))
        seg.set('flags', '393216' if i == 0 else '1441792')
    return n, step

def cell_horzsize(tc):
    sz = tc.find(q('cellSz'))
    mg = tc.find(q('cellMargin'))
    return int(sz.get('width')) - int(mg.get('left')) - int(mg.get('right'))

def grow_cell_height(tc, needed):
    """콘텐츠가 넘치면 같은 행의 rowSpan=1 셀 높이와 tbl 전체 높이를 키운다."""
    sz = tc.find(q('cellSz'))
    cur = int(sz.get('height'))
    if needed <= cur:
        return
    delta = needed - cur
    tr = tc.getparent()
    for c in tr.findall(q('tc')):
        span = c.find(q('cellSpan'))
        if span is not None and span.get('rowSpan') == '1':
            csz = c.find(q('cellSz'))
            csz.set('height', str(int(csz.get('height')) + delta))
    tbl = tr.getparent()
    tsz = tbl.find(q('sz'))
    if tsz is not None:
        tsz.set('height', str(int(tsz.get('height')) + delta))

def set_cell_text(tc, text):
    """첫 문단 첫 run 에 텍스트 설정 (기존 스타일 유지) + lineseg 재생성."""
    sub = tc.find(q('subList'))
    p = sub.find(q('p'))
    run = p.find(q('run'))
    t = run.find(q('t'))
    if t is None:
        t = etree.SubElement(run, q('t'))
    t.text = text
    attrs = seg_attrs_of(p)
    n, step = rebuild_lineseg(p, attrs, 0, cell_horzsize(tc))
    grow_cell_height(tc, n * step + 282)

def find_label_tc(root, label):
    """정규화 텍스트가 label 과 일치하는 tc (중첩 테이블 셀 포함) 반환."""
    for tc in root.iter(q('tc')):
        if cell_norm_text(tc) == norm(label):
            return tc
    raise KeyError(f'label cell not found: {label}')

def next_tc(tc):
    tr = tc.getparent()
    tcs = [c for c in tr if c.tag == q('tc')]
    i = tcs.index(tc)
    return tcs[i + 1]

def get_tbl(root, tbl_id):
    for tbl in root.iter(q('tbl')):
        if tbl.get('id') == tbl_id:
            return tbl
    raise KeyError(f'table {tbl_id} not found')

def tc_at(tbl, col, row):
    for tr in tbl.findall(q('tr')):
        for tc in tr.findall(q('tc')):
            addr = tc.find(q('cellAddr'))
            if int(addr.get('colAddr')) == col and int(addr.get('rowAddr')) == row:
                return tc
    raise KeyError(f'cell ({col},{row}) not found')

def make_para(tmpl, text):
    p = copy.deepcopy(tmpl)
    runs = p.findall(q('run'))
    # 첫 run 만 남김 (기존 linesegarray 는 rebuild_cell 에서 재생성)
    for r in runs[1:]:
        p.remove(r)
    t = runs[0].find(q('t'))
    if t is None:
        t = etree.SubElement(runs[0], q('t'))
    t.text = text
    return p

def rebuild_cell(tc, lines, tmpl_o, tmpl_sub):
    """content cell 의 subList 문단을 lines 로 재구성 + 누적 lineseg 생성.
    lines: [(level, text)] level: 'o'(ㅇ), 'd'(-), 's'(*)"""
    sub = tc.find(q('subList'))
    for p in sub.findall(q('p')):
        sub.remove(p)
    hs = cell_horzsize(tc)
    vert = 0
    step_last = 1484
    for level, text in lines:
        if level == 'o':
            p = make_para(tmpl_o, 'ㅇ ' + text)
        elif level == 'd':
            p = make_para(tmpl_sub, ' - ' + text)
        else:
            p = make_para(tmpl_sub, '  * ' + text)
        attrs = seg_attrs_of(p)
        n, step = rebuild_lineseg(p, attrs, vert, hs)
        vert += n * step
        step_last = step
        sub.append(p)
    grow_cell_height(tc, vert + 282)

HC = 'http://www.hancom.co.kr/hwpml/2011/core'

def png_size(path):
    import struct
    with open(path, 'rb') as f:
        head = f.read(24)
    w, h = struct.unpack('>II', head[16:24])
    return w, h

def insert_figure(tc, png_path, item_id):
    """content cell 끝에 그림 문단(hp:pic) 추가. 기존 image1 구조를 복제."""
    pw, ph = png_size(png_path)
    orgw, orgh = pw * 30, ph * 30
    dimw, dimh = pw * 75, ph * 75
    w = cell_horzsize(tc) - 200
    h = round(w * ph / pw)
    sca = w / orgw
    xml = f'''<wrap xmlns:hp="{HP}" xmlns:hc="{HC}">
<hp:p id="1900000001" paraPrIDRef="21" styleIDRef="0" pageBreak="0" columnBreak="0" merged="0">
  <hp:run charPrIDRef="23">
    <hp:pic id="1900000002" zOrder="20" numberingType="PICTURE" textWrap="TOP_AND_BOTTOM" textFlow="BOTH_SIDES" lock="0" dropcapstyle="None" href="" groupLevel="0" instid="1900000003" reverse="0">
      <hp:offset x="0" y="0"/>
      <hp:orgSz width="{orgw}" height="{orgh}"/>
      <hp:curSz width="{w}" height="{h}"/>
      <hp:flip horizontal="0" vertical="0"/>
      <hp:rotationInfo angle="0" centerX="{w//2}" centerY="{h//2}" rotateimage="1"/>
      <hp:renderingInfo>
        <hc:transMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
        <hc:scaMatrix e1="{sca:.6f}" e2="0" e3="0" e4="0" e5="{sca:.6f}" e6="0"/>
        <hc:rotMatrix e1="1" e2="0" e3="0" e4="0" e5="1" e6="0"/>
      </hp:renderingInfo>
      <hc:img binaryItemIDRef="{item_id}" bright="0" contrast="0" effect="REAL_PIC" alpha="0"/>
      <hp:imgRect>
        <hc:pt0 x="0" y="0"/><hc:pt1 x="{orgw}" y="0"/><hc:pt2 x="{orgw}" y="{orgh}"/><hc:pt3 x="0" y="{orgh}"/>
      </hp:imgRect>
      <hp:imgClip left="0" right="{dimw}" top="0" bottom="{dimh}"/>
      <hp:inMargin left="0" right="0" top="0" bottom="0"/>
      <hp:imgDim dimwidth="{dimw}" dimheight="{dimh}"/>
      <hp:effects/>
      <hp:sz width="{w}" widthRelTo="ABSOLUTE" height="{h}" heightRelTo="ABSOLUTE" protect="0"/>
      <hp:pos treatAsChar="1" affectLSpacing="0" flowWithText="1" allowOverlap="0" holdAnchorAndSO="0" vertRelTo="PARA" horzRelTo="COLUMN" vertAlign="TOP" horzAlign="LEFT" vertOffset="0" horzOffset="0"/>
      <hp:outMargin left="0" right="0" top="0" bottom="0"/>
      <hp:shapeComment>기술 핵심 아이디어 개념도</hp:shapeComment>
    </hp:pic>
    <hp:t/>
  </hp:run>
</hp:p></wrap>'''
    p = etree.fromstring(xml.encode('utf-8')).find(q('p'))
    sub = tc.find(q('subList'))
    # 기존 문단들의 누적 높이 계산
    vert = 0
    for ep in sub.findall(q('p')):
        lsa = ep.find(q('linesegarray'))
        if lsa is None:
            continue
        for seg in lsa.findall(q('lineseg')):
            vert = max(vert, int(seg.get('vertpos')) + int(seg.get('vertsize')) + int(seg.get('spacing')))
    lsa = etree.SubElement(p, q('linesegarray'))
    seg = etree.SubElement(lsa, q('lineseg'))
    for k, v in [('textpos', '0'), ('vertpos', str(vert)), ('vertsize', str(h)),
                 ('textheight', str(h)), ('baseline', str(round(h * 0.85))), ('spacing', '160'),
                 ('horzpos', '0'), ('horzsize', str(cell_horzsize(tc))), ('flags', '393216')]:
        seg.set(k, v)
    sub.append(p)
    grow_cell_height(tc, vert + h + 442)

def register_binitem(out_dir, png_path, item_id):
    import shutil as sh
    bin_dir = out_dir / 'BinData'
    bin_dir.mkdir(exist_ok=True)
    sh.copy(png_path, bin_dir / f'{item_id}.png')
    hpf = out_dir / 'Contents' / 'content.hpf'
    s = hpf.read_text(encoding='utf-8')
    if f'id="{item_id}"' not in s:
        s = s.replace('<opf:item id="section0"',
                      f'<opf:item id="{item_id}" href="BinData/{item_id}.png" media-type="image/png" isEmbeded="1"/>\n    <opf:item id="section0"', 1)
        hpf.write_text(s, encoding='utf-8')

def replace_text_once(root, old, new, nth=1, refresh=False):
    """텍스트 치환. refresh=True 면 소속 문단 lineseg 재생성 (긴 텍스트 치환용)."""
    n = 0
    for t in root.iter(q('t')):
        if t.text == old:
            n += 1
            if n == nth:
                t.text = new
                if refresh:
                    p = t.getparent().getparent()  # t < run < p
                    attrs = seg_attrs_of(p)
                    tc = p.getparent().getparent()  # p < subList < tc
                    hs = cell_horzsize(tc) if tc.tag == q('tc') else None
                    n_lines, step = rebuild_lineseg(p, attrs, 0, hs)
                    if tc.tag == q('tc'):
                        grow_cell_height(tc, n_lines * step + 282)
                return True
    raise KeyError(f'text not found (occurrence {nth}): {old}')

def main():
    content = json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    out_dir = Path(sys.argv[2])
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(SRC, out_dir)
    sec_path = out_dir / 'Contents' / 'section0.xml'
    tree = etree.parse(str(sec_path))
    root = tree.getroot()

    # ── 템플릿 문단 확보 (기술개발 목표 셀의 ㅇ / - 문단)
    goal_label = find_label_tc(root, '기술개발 목표')
    goal_cell = next_tc(goal_label)
    goal_ps = goal_cell.find(q('subList')).findall(q('p'))
    tmpl_o = copy.deepcopy(goal_ps[0])   # 'ㅇ ' paraPr 68
    tmpl_sub = copy.deepcopy(goal_ps[1]) # ' - ' paraPr 33

    # ── 0. 제안자 정보
    pr = content['proposer']
    set_cell_text(next_tc(find_label_tc(root, '성명(직위)')), pr['name'])
    if pr.get('phone'):
        set_cell_text(next_tc(find_label_tc(root, '휴대전화')), pr['phone'])
    set_cell_text(next_tc(find_label_tc(root, '소속기관(부서명)')), pr['org'])
    set_cell_text(next_tc(find_label_tc(root, '이메일')), pr['email'])
    CHK = ''
    for t in root.iter(q('t')):
        if t.text and '중견기업' in t.text:
            t.text = ('대기업(  ), 중견기업(  ), 중소기업(  ), 대학(  ), '
                      f'연구소({CHK}), 학회(  ), 기타(  )')
            break
    for t in root.iter(q('t')):
        if t.text and '대전( )' in t.text:
            t.text = (t.text.replace(f'서울({CHK})', '서울( )')
                            .replace('대전( )', f'대전({CHK})'))
            break

    # ── 1. 제안기술 정보
    replace_text_once(root, '(예) ±3℃ 이내 온도 제어가 가능한 ~~', content['tech_name'], refresh=True)
    set_cell_text(next_tc(find_label_tc(root, '최종 산출물')), content['final_output'])
    replace_text_once(root, 'ex. 화학', content['class_major'])
    replace_text_once(root, 'ex. 고분자 재료 ', content['class_middle'])
    replace_text_once(root, 'ex. 나노소재기술', content['class_minor'])

    tbl1 = get_tbl(root, '1161504823')
    # 제안기술 유형: 혁신제품형 check=(4,6), 원천기술형 check=(12,6)
    type_map = {'innov': (4, 6), 'fundamental': (12, 6)}
    set_cell_text(tc_at(tbl1, *type_map[content['type_check']]), '√')
    # 내역사업: 1→(2,9), 2→(6,9), 3→(10,9)
    detail_map = {1: (2, 9), 2: (6, 9), 3: (10, 9)}
    set_cell_text(tc_at(tbl1, *detail_map[content['detail_check']]), '√')
    # 3대 메가: 반도체(2,12) 피지컬AI(3,12) AI데이터센터(7,12) 기타(11,12)
    mega_map = {'semi': (2, 12), 'pai': (3, 12), 'aidc': (7, 12), 'etc': (11, 12)}
    set_cell_text(tc_at(tbl1, *mega_map[content['mega_check']]), '√')

    # 적용 대상 및 개발기술
    replace_text_once(root, '(예) HBM 패키지 → 접합부 열저항 저감 필요 → 고열전도 나노계면소재 개발',
                      content['apply_line'], refresh=True)
    # 참고사항 중첩 테이블(id 1164427360) 을 감싼 문단만 제거
    ref_tbl = get_tbl(root, '1164427360')
    ref_p = ref_tbl.getparent().getparent()  # tbl < run < p
    ref_p.getparent().remove(ref_p)

    # ── 2. 개발목표 및 내용
    replace_text_once(root, '(   ) 년', f"( {content['years']} ) 년")
    tbl2 = get_tbl(root, '1161504833')
    for col, val in zip([1, 2, 4, 5, 7, 9], content['budget']):
        set_cell_text(tc_at(tbl2, col, 2), val)
    replace_text_once(root, '(    )단계', f"( {content['trl_start']} )단계", nth=1)
    replace_text_once(root, '(    )단계', f"( {content['trl_end']} )단계", nth=1)

    sections = content['sections']
    rebuild_cell(goal_cell, sections['목표'], tmpl_o, tmpl_sub)
    overview_cell = next_tc(find_label_tc(root, '기술개발 개요'))
    rebuild_cell(overview_cell, sections['개요'], tmpl_o, tmpl_sub)
    if content.get('figure'):
        register_binitem(out_dir, content['figure'], 'image3')
        insert_figure(overview_cell, content['figure'], 'image3')
    rebuild_cell(next_tc(find_label_tc(root, '기술개발주요내용')), sections['주요내용'], tmpl_o, tmpl_sub)
    rebuild_cell(next_tc(find_label_tc(root, '지원 필요성')), sections['지원필요성'], tmpl_o, tmpl_sub)
    rebuild_cell(next_tc(find_label_tc(root, '기대효과')), sections['기대효과'], tmpl_o, tmpl_sub)

    # ── 3. 국내외 동향
    rebuild_cell(next_tc(find_label_tc(root, '국내')), sections['국내'], tmpl_o, tmpl_sub)
    rebuild_cell(next_tc(find_label_tc(root, '해외')), sections['해외'], tmpl_o, tmpl_sub)

    # ── 4. 보유기술 / 공통기술
    rebuild_cell(next_tc(find_label_tc(root, '보유기술')), sections['보유기술'], tmpl_o, tmpl_sub)
    rebuild_cell(next_tc(find_label_tc(root, '공통기술·지원 필요사항')), sections['공통기술'], tmpl_o, tmpl_sub)

    tree.write(str(sec_path), xml_declaration=True, encoding='UTF-8')
    print('filled:', sec_path)

if __name__ == '__main__':
    main()
