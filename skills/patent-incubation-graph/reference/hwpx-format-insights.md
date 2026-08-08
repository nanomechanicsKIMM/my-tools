---
title: "HWPX 포맷 구현 인사이트 — 내어쓰기·계층 글머리기호"
created: 2026-04-16
tags: [hwpx, owpml, reference, hanword, paragraph, indent, hanging-indent, 한글]
related: ["[[convert_hwpx.py]]", "[[kimm-template-mapping.md]]"]
---

# HWPX 포맷 구현 인사이트

> KIMM 직무발명내용설명서 HWPX 생성 파이프라인(v1~v15)에서 역공학으로 확인한 핵심 규칙. 특히 **테이블 셀 내부**의 계층 글머리기호 + 내어쓰기 구현에 필요한 정보.

---

## 1. 핵심 결론 (TL;DR)

테이블 셀 내부 bullet 문단에서 **"계층 들여쓰기 + 내어쓰기(hanging indent)"**를 구현하려면 5가지 조건이 모두 충족되어야 함:

| 조건 | 값/방식 | 근거 |
|------|--------|------|
| **paraPrIDRef가 순차 ID** | 기존 paraPr(0..max) 바로 다음 번호 사용 | 한/글은 **배열 인덱스로 조회** → 범위 초과 시 paraPr[0] fallback |
| **paraPr.margin.intent 음수** | case=-3072·-4572·-6072, default=case×2 | 2016 HwpUnitChar : 2011 legacy HWPUNIT = 1:2 비율 |
| **paraPr.snapToGrid="1"** | 1 (기본 0 아님) | 한/글이 intent를 렌더링 시 적용하려면 grid snap 필요 |
| **lineseg.flags** | 첫줄 `393216`, 연속줄 `1441792` | `2490368`(0x260000)은 "wrap 없음" 신호로 intent 무시 |
| **텍스트 전각 공백 접두** | 레벨별 `\u3000`×(level×2) + bullet 문자 | 첫줄의 시각적 들여쓰기는 텍스트로 구현 (cell 내 paraPr.left 미적용) |

---

## 2. HWPX 파일 구조 개요

HWPX는 ZIP 컨테이너 안에 XML 파일들이 담긴 구조 (OWPML 기반, KS X 6101 표준).

```
document.hwpx (ZIP)
├─ mimetype               (고정 "application/hwp+zip")
├─ META-INF/container.xml (루트 참조)
├─ Contents/
│  ├─ content.hpf         (문서 매니페스트, OPF 형식)
│  ├─ header.xml          (스타일·폰트·문단모양 정의)
│  └─ section0.xml        (본문 컨텐츠)
├─ BinData/               (임베디드 이미지/바이너리)
└─ Preview/               (썸네일, 선택)
```

### 주요 네임스페이스

| 접두사 | URI | 용도 |
|--------|-----|------|
| `hp` | `http://www.hancom.co.kr/hwpml/2011/paragraph` | 문단·본문 요소 (hp:p, hp:run, hp:t, hp:tbl 등) |
| `hh` | `http://www.hancom.co.kr/hwpml/2011/head` | 헤더 요소 (hh:paraPr, hh:charPr 등) |
| `hc` | `http://www.hancom.co.kr/hwpml/2011/core` | 공통 원시 속성 (hc:left, hc:intent, hc:right 등) |
| `hs` | `http://www.hancom.co.kr/hwpml/2011/section` | 섹션 설정 |
| `opf` | `http://www.idpf.org/2007/opf/` | OPF 매니페스트 (content.hpf) |

---

## 3. paraPr 구조와 내어쓰기 규칙

### 3.1 paraPr의 위치와 참조

- `header.xml`의 `<hh:refList><hh:paraProperties itemCnt="N">` 아래에 `<hh:paraPr id="0..N-1">` 형태로 정의
- `section0.xml`의 각 `<hp:p paraPrIDRef="X">`가 이 ID를 참조

### 3.2 **[치명적 함정] paraPrIDRef는 배열 인덱스로 조회된다**

한/글 렌더러는 paraPrIDRef 값을 **paraProperties 배열의 인덱스**로 해석한다. ID가 속성값이지만 실제 동작은 배열 순서를 따름.

```python
# 잘못된 방식 ❌
# template paraPr 0..14 + 새 paraPr 100, 101, 102, 103 추가
# → paraPrIDRef="101"이 itemCnt=19를 초과하여 paraPr[0]로 fallback
#    → intent=0이 적용되어 내어쓰기 없음

# 올바른 방식 ✓
# template paraPr 0..14 뒤에 순차적으로 15, 16, 17, 18 추가
# → paraPrIDRef="15"가 paraProperties[15]에 정확히 매핑
```

**규칙**:
- 새 paraPr 추가 시 `id = max(existing_ids) + 1`부터 순차 할당
- `paraProperties` 컨테이너의 `itemCnt` 속성을 실제 개수로 업데이트
- 배열 순서와 ID 순서가 일치해야 함

### 3.3 paraPr 내어쓰기 구조 (switch/case/default)

```xml
<hh:paraPr id="15" tabPrIDRef="0" condense="0" fontLineHeight="0"
           snapToGrid="1"  <!-- 반드시 1 -->
           suppressLineNumbers="0" checked="0">
  <hh:align horizontal="JUSTIFY" vertical="BASELINE"/>
  <hh:heading type="NONE" idRef="0" level="0"/>
  <hh:breakSetting breakLatinWord="KEEP_WORD" breakNonLatinWord="KEEP_WORD"
                   widowOrphan="0" keepWithNext="0" keepLines="0"
                   pageBreakBefore="0" lineWrap="BREAK"/>
  <hh:autoSpacing eAsianEng="0" eAsianNum="0"/>
  <hp:switch>
    <!-- 2016 HwpUnitChar (새 단위 시스템) -->
    <hp:case required-namespace="http://www.hancom.co.kr/hwpml/2016/HwpUnitChar">
      <hh:margin>
        <hc:intent value="-3072" unit="HWPUNIT"/>  <!-- 음수 = 내어쓰기 -->
        <hc:left value="0" unit="HWPUNIT"/>
        <hc:right value="0" unit="HWPUNIT"/>
        <hc:prev value="0" unit="HWPUNIT"/>
        <hc:next value="0" unit="HWPUNIT"/>
      </hh:margin>
      <hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>
    </hp:case>
    <!-- 2011 legacy HWPUNIT -->
    <hp:default>
      <hh:margin>
        <hc:intent value="-6144" unit="HWPUNIT"/>  <!-- case × 2 -->
        <hc:left value="0" unit="HWPUNIT"/>
        ...
      </hh:margin>
      <hh:lineSpacing type="PERCENT" value="160" unit="HWPUNIT"/>
    </hp:default>
  </hp:switch>
  <hh:border borderFillIDRef="2" offsetLeft="0" offsetRight="0"
             offsetTop="0" offsetBottom="0" connect="0" ignoreMargin="0"/>
</hh:paraPr>
```

### 3.4 단위 체계 (HWPUNIT vs HwpUnitChar)

| 속성값 | 단위 | 값 해석 |
|--------|------|---------|
| case 블록 내부 | HwpUnitChar (2016) | 실제 문자 폭 기반 |
| default 블록 내부 | legacy HWPUNIT (2011) | 1 HWPUNIT = 1/7200 inch |
| **case : default 비율** | **1 : 2** | case 값의 2배가 default 값 |

**실험 검증값** (10pt 한글 본문 기준):
- L1 bullet 내어쓰기: case=-3072 / default=-6144 (≈ 3 Korean char widths)
- L2 bullet 내어쓰기: case=-4572 / default=-9144 (≈ 4.5 Korean char widths)
- L3 bullet 내어쓰기: case=-6072 / default=-12144 (선형 보간)

### 3.5 snapToGrid의 역할

- `snapToGrid="0"` (기본 템플릿 값): 한/글이 stored lineseg을 그대로 사용 → **intent 무시**
- `snapToGrid="1"` (사용자 에디터 편집 시 자동 설정): 한/글이 grid 정렬 수행 → **intent 적용됨**

새 paraPr을 만들 때 반드시 `snapToGrid="1"`로 설정.

---

## 4. lineseg 구조와 flags

### 4.1 linesegarray의 역할

- **레이아웃 캐시가 아닌 필수 정보**: 한/글은 linesegarray의 flags와 textpos로 wrap 구조를 판단
- 단순히 linesegarray를 비우면 Hanword가 레이아웃 재계산 하지 않음 (v13 실패)
- 올바른 lineseg 생성이 필수

### 4.2 lineseg 속성

```xml
<hp:lineseg
  textpos="0"        <!-- 이 lineseg이 시작하는 텍스트 문자 인덱스 -->
  vertpos="8000"     <!-- 수직 위치 (HWPUNIT, 줄 간격 1600) -->
  vertsize="1000"    <!-- 줄 높이 -->
  textheight="1000"  <!-- 글자 높이 -->
  baseline="850"     <!-- 베이스라인 오프셋 -->
  spacing="600"      <!-- 줄 간격 -->
  horzpos="0"        <!-- 수평 시작 위치 (보통 0, intent로 조정) -->
  horzsize="41672"   <!-- 수평 폭 (cellSz.width - 약 282) -->
  flags="393216"/>   <!-- 위치·wrap 속성 플래그 -->
```

### 4.3 flags 값 의미

`flags`는 32비트 플래그로, 상위 비트가 줄 속성을 나타냄.

| 10진 | 16진 | 의미 | 사용 위치 |
|------|------|------|-----------|
| **393216** | 0x60000 | **첫 줄** (wrap 가능) | 모든 paragraph의 첫 lineseg |
| **1441792** | 0x160000 | **연속 줄** (wrap 발생 후) | 두 번째 이후 lineseg |
| ~~2490368~~ | ~~0x260000~~ | ~~"단일 줄, wrap 없음"~~ | **사용 금지** — 한/글 에디터가 저장하지 않는 값, intent 무시됨 |

> **핵심**: 한/글 에디터가 직접 저장한 파일에는 `2490368` flag이 **전혀 등장하지 않음**. 이 값은 Hanword가 렌더 시 "wrap 재계산 불필요"로 해석하여 intent를 무시하게 만듦.

### 4.4 wrap 위치 계산

한/글 10pt 본문에서 Korean 문자의 실측 폭 ≈ **850 HWPUNIT/char**.

```python
chars_per_line = cell_horzsize // 850   # 41672 / 850 ≈ 49 chars
```

긴 텍스트에 대해:
- `textpos=0`에서 `flags=393216`으로 첫 lineseg
- `textpos=wrap_pos`에서 `flags=1441792`로 연속 lineseg
- 각 줄 `vertpos`는 `LINE_HEIGHT=1600`씩 증가

---

## 5. 테이블 셀 내부 렌더링 특이사항

### 5.1 paraPr.margin.left는 테이블 셀에서 무시됨

- 일반 문서 영역에서는 `margin.left`가 왼쪽 들여쓰기로 동작
- **테이블 셀 내부에서는 `left` 값이 시각적으로 반영되지 않음** (v4/v7 실험 결과)
- 대안: **텍스트 내부의 전각 공백(U+3000)**으로 들여쓰기 구현

### 5.2 계층 들여쓰기 구현 (텍스트 레벨)

```python
BULLET_INDENT_TEXT = {
    0: "",                                          # ● 좌측 정렬
    1: "\u3000\u3000",                              # ○ 2 전각 공백
    2: "\u3000\u3000\u3000\u3000",                  # ▪ 4 전각 공백
    3: "\u3000\u3000\u3000\u3000\u3000\u3000",      # - 6 전각 공백
}
# 텍스트 = indent + marker + " " + content
# 예: "\u3000\u3000○ 본 발명의 전체 시스템은..."
```

### 5.3 내어쓰기는 paraPr.intent로 구현

- 텍스트 수준 공백은 **첫 줄의 위치만** 결정 (wrap 후 연속줄은 position 0)
- 연속줄을 첫 줄에 맞춰 정렬하려면 **paraPr.intent 음수값**이 필요
- 한/글이 연속줄을 렌더링할 때 `left + |intent|` 위치에서 시작

---

## 6. v1~v15 구현 여정 (실험 기록)

| 버전 | 변경점 | 결과 |
|------|--------|------|
| v1~v2 | 평문 렌더링 (bullet parser 도입 전) | 계층 구조 없음 |
| v3 | paraPr margin.left 설정, 네임스페이스 버그 | ❌ intent=0 효과 |
| v4 | 네임스페이스 수정 (hh:margin + **hc:left**) | ❌ paraPr.left는 셀 내부 무시됨 발견 |
| v5 | 전각 공백(U+3000)으로 시각적 들여쓰기 | ✓ 계층 들여쓰기 성공 |
| v6 | 긴 텍스트 수동 분할 + 연속줄 prefix | △ 들여쓰기 OK, 분할이 추가 단락으로 보임 |
| v7 | paraPr left+intent만 사용(텍스트 분할 없음) | ❌ 셀 내 paraPr 전체 무시 |
| v8 | v5 + v7 결합 (paraPr intent + 전각 공백) | ✓ 계층 OK, ❌ 내어쓰기 실패 |
| v9~v10 | bullet 렌더러 §9에도 적용 | ✓ 전 섹션 일관성 |
| v11 | paraPr intent 정확히 설정 (case/default 구분) | ❌ intent 여전히 미적용 |
| v12 | snapToGrid="1" 추가 | ❌ 여전히 내어쓰기 실패 |
| v13 | linesegarray 제거 시도 | ❌ 재계산 안됨 |
| v14 | lineseg flags 수정 (2490368 → 393216) | ❌ 여전히 실패 |
| **v15** | **paraPrIDRef 순차 ID (100~103 → 15~18)** | **✓ 내어쓰기 성공** |

### 핵심 교훈

1. **paraPrIDRef는 배열 인덱스** — 건너뛰는 ID 사용 금지
2. **snapToGrid=1** + **intent 음수** + **flags 393216/1441792** 세트 필수
3. 테이블 셀 내 `paraPr.left`는 무시 → 텍스트 전각 공백으로 보완
4. linesegarray는 필수 (캐시 아님)

---

## 7. 최종 구현 요약 (v15 기준)

### 7.1 header.xml 수정

```python
# 기존 paraPr 다음 ID부터 순차 할당
existing_int_ids = [int(p.get("id")) for p in existing_paraprs]
base = max(existing_int_ids) + 1  # template의 max가 14면 base=15

for level in range(4):
    new_id = str(base + level)  # 15, 16, 17, 18
    new_pp = deepcopy(template_pp)
    new_pp.set("id", new_id)
    new_pp.set("snapToGrid", "1")                    # ← 필수
    # heading type=NONE (bullet char는 텍스트로 삽입)
    heading = new_pp.find(f"{{{HH_NS}}}heading")
    heading.set("type", "NONE")
    heading.set("idRef", "0")
    heading.set("level", "0")
    # switch 내부 case/default 각각 intent 설정
    switch = new_pp.find(f"{{{HP_NS}}}switch")
    for blk, intent_val in [(case_blk, intent_case), (default_blk, intent_default)]:
        margin = blk.find(f"{{{HH_NS}}}margin")
        intent_elem = margin.find(f"{{{HC_NS}}}intent")
        intent_elem.set("value", str(intent_val))
    paraproperties.append(new_pp)

paraproperties.set("itemCnt", str(len(paraproperties)))  # itemCnt 업데이트
```

### 7.2 section0.xml의 hp:p 생성

```python
# 텍스트: 전각 공백 + bullet + 본문
level = 1  # ○
indent = "\u3000\u3000"
marker = "○"
display = f"{indent}{marker} {content}"

# 긴 텍스트면 lineseg 여러 개 생성 (한/글 에디터 스타일)
chars_per_line = 49  # ≈ horzsize(41672) / char_width(850)
num_lines = math.ceil(len(display) / chars_per_line)

for i in range(num_lines):
    flags = "393216" if i == 0 else "1441792"  # ← 필수
    textpos = i * chars_per_line
    vertpos = i * 1600
    # ...
```

### 7.3 BULLET_MARGIN 상수

```python
BULLET_MARGIN = {
    # level: (left, intent_case_HwpUnitChar, intent_default_HWPUNIT_legacy)
    0: (0,      0,     0),        # L0 ● 내어쓰기 없음
    1: (0,  -3072,  -6144),       # L1 ○ (user paraPr 15 값)
    2: (0,  -4572,  -9144),       # L2 ▪ (user paraPr 17 값)
    3: (0,  -6072, -12144),       # L3 - (선형 보간)
}
```

---

## 8. 참고 자료

- [한컴테크 HWPX 포맷 소개](https://tech.hancom.com/hwpxformat/) — HWPX 구조 개요
- [한컴테크 Python HWPX 파싱 (1)](https://tech.hancom.com/python-hwpx-parsing-1/) — refList 구조
- [한컴개발자포럼 linesegarray 토론](https://forum.developer.hancom.com/t/hwpx-linesegarray-lineseg-textpos/1677) — lineseg 공식 답변
- KS X 6101 표준 — OWPML (Open Word-Processor Markup Language)
- 역공학 대상 파일: `v10_user.hwpx` (사용자가 한/글에서 수동 편집한 파일)

---

## 9. 재사용 가능한 체크리스트

새 HWPX 파일에서 테이블 셀 내부에 계층 bullet + 내어쓰기를 구현할 때:

- [ ] header.xml의 paraProperties에서 `max(existing_ids) + 1`부터 순차 ID 할당
- [ ] paraProperties의 `itemCnt` 속성을 실제 개수로 갱신
- [ ] 각 bullet 레벨별 paraPr에 `snapToGrid="1"` 설정
- [ ] paraPr.margin.intent를 음수로 설정 (case/default 각각, 비율 1:2)
- [ ] `heading type="NONE"` (bullet 문자를 텍스트로 삽입하는 경우)
- [ ] 텍스트 내용에 전각 공백(U+3000)으로 계층 들여쓰기 반영
- [ ] lineseg flags: 첫줄 `393216`, 연속줄 `1441792` (절대 `2490368` 사용 금지)
- [ ] 긴 텍스트는 `chars_per_line ≈ cell_width / 850`으로 wrap 계산
- [ ] 각 lineseg의 `horzsize = cellSz.width - ~282` (cell padding 감안)
- [ ] fix_namespaces.py + validate.py로 최종 검증
