# 대량 테이블 편집 패턴 (v0.3)

이전 연도 템플릿에서 올해 출장계획서를 파생시킬 때, placeholder map 만으로는
해결되지 않는 **구조적 변경**이 자주 발생한다.

- 방문 기관 제거 → §1 내 해당 블록(문단 + 이미지 + 캡션) 통째 삭제
- 출장자 감소 → 스케줄 테이블 삭제·축소, 반출 장비 테이블 컬럼 삭제
- 과제 코드 교체 → 과제 연결 / 예산 테이블의 행 재작성
- 날짜 체계 변경 → 일정·최근 실적 테이블의 날짜 셀 일괄 갱신
- 학회 프로그램 교체 → 관심 세션 테이블 rebuild + Program Overview 이미지 교체

이 문서는 v0.3 에서 `table_utils.py` 에 추가된 helper 로 위 시나리오를
어떻게 구현하는지 정리한다.

---

## 1. 섹션 블록 통째 삭제

구버전 템플릿에서 이번 출장엔 방문하지 않는 **Meta/Apple 방문 블록** 같은
서술 섹션을 한 번에 제거.

```python
from table_utils import delete_range_between

n = delete_range_between(
    root,
    start_needle="Meta Platforms, Inc. 방문",
    end_needle="2. Display Week",
)
print(f"삭제된 paragraph: {n}")
```

- 두 anchor paragraph 가 **같은 parent 의 sibling** 이어야 한다.
- `start_needle` inclusive, `end_needle` exclusive — 새 섹션 헤더를 end 로
  지정하면 이전 섹션 전체(본문 + 이미지 + 캡션 + 빈 paragraph) 가 통째 제거.
- 블록 내부의 `<hp:pic>` 참조 이미지는 DOM 에서 같이 사라지지만, `BinData/`
  의 바이너리 파일은 그대로 남는다 (orphan). 필요 시 수동 정리.

## 2. 다중 run paragraph 텍스트 교체

"라벨(굵게) + 본문(보통) + 트레일링 공백" 처럼 `<hp:run>` 이 여러 개인
문단의 텍스트를 서식 보존하며 갱신.

```python
from table_utils import find_paragraph_by_text, set_multi_run_text

p = find_paragraph_by_text(root, "행사 소개: Display Week")
set_multi_run_text(p, [
    "행사 소개: ",               # <hp:t>[0] — 라벨
    "매년 미국에서 개최되는 ...",  # <hp:t>[1] — 본문
    " ",                          # <hp:t>[2] — 트레일링
])
```

- `set_p_text_flow()` 는 첫 `<hp:t>` 만 채우고 나머지를 비우므로 모든 run 이
  첫 charPrIDRef 스타일로 합쳐져 보인다. 서식을 보존하려면
  `set_multi_run_text` 사용.
- 초과 `<hp:t>` 는 자동 빈 문자열. 부족하면 `texts` 만큼만 설정.

## 3. 테이블 데이터 rows 전면 교체

스케줄/과제 연결/예산 등 **헤더 + 데이터 rows** 구조의 테이블에서 모든
데이터 rows 를 새 값으로 rebuild.

```python
from table_utils import find_table_after, find_paragraph_by_text
from table_utils import rebuild_table_data_rows

heading = find_paragraph_by_text(root, "출장 일정(김재현)")
tbl = find_table_after(heading)

rebuild_table_data_rows(tbl, [
    ["5/4(월)", "인천", "Los Angeles", "-", "출국 및 이동", "-"],
    ["5/5(화)", "-", "-", "LA Convention Center",
        "Display Week Symposium 참석", "-"],
    # ...
])
```

동작:
1. 첫 data row 를 클린 템플릿으로 선택 (colCnt 와 cell 수가 같은 row)
2. 템플릿 cells 의 rowSpan/colSpan 을 1 로 리셋 (병합 해제)
3. 기존 데이터 rows 전부 DOM 삭제
4. 각 row_data 에 대해 deepcopy + `set_cell_text_flow` 로 cell 텍스트 설정
5. `renumber_table(tbl)` 자동 호출

**주의**:
- 기존 템플릿 row 에 병합 셀(rowSpan>1)이 있었다면 리셋되므로 레이아웃이
  달라질 수 있다. 필요 시 `template_row_index=0` 으로 헤더를 템플릿으로 사용.
- cell 텍스트에 줄바꿈(`\n`) 을 포함하려면 `set_cell_text_lines` 을 별도로
  적용 (rebuild 이후 특정 cell 에 추가 작업).

## 4. 테이블 컬럼 삭제

반출 장비 테이블처럼 출장자별 컬럼이 있는 경우, 특정 출장자 컬럼만 제거.

```python
from table_utils import find_table_after, find_paragraph_by_text
from table_utils import find_column_by_header, delete_column

heading = find_paragraph_by_text(root, "반출 예정 전산장비")
tbl = find_table_after(heading)

col = find_column_by_header(tbl, "김현돈")  # None 이면 매치 실패
if col is not None:
    delete_column(tbl, col)
```

동작:
1. 헤더 row 에서 텍스트가 일치하는 cell 의 `colAddr` 탐색
2. 모든 row 에서 해당 `colAddr` cell DOM 제거
3. 나머지 cells 의 `colAddr > col_index` 값을 -1
4. `<hp:tbl colCnt>` -1

**제한**: 삭제 대상 컬럼에 `colSpan>1` 병합 셀이 존재하면 구조가 깨질 수
있다. 일반적으로 `colSpan=1` 인 단순 테이블에서만 사용.

## 5. 특정 name 이 포함된 row 삭제

최근 3년 실적 테이블에서 더 이상 합류하지 않는 출장자의 rows 만 제거.

```python
from table_utils import hp, element_text, remove_row_safe, renumber_table

for r in list(tbl.findall(hp("tr"))):
    cells = r.findall(hp("tc"))
    if not cells:
        continue
    first_cell_text = element_text(cells[0]).strip()
    if first_cell_text == "김현돈":
        remove_row_safe(r)
renumber_table(tbl)
```

## 6. BinData 이미지 교체 (Program Overview 등)

학회 공식 배너를 본문 그림으로 교체.

```python
import shutil
from PIL import Image

# 1) PNG → JPG 변환 (image5 가 JPEG 참조인 경우)
src_png = "/tmp/dw_banner.png"
dst_jpg = "/tmp/dw_banner.jpg"
Image.open(src_png).convert("RGB").save(dst_jpg, "JPEG", quality=90)

# 2) BinData/image5.jpg 덮어쓰기 (파일명 유지 → manifest 재작성 불필요)
shutil.copy(dst_jpg, unpacked_dir / "BinData" / "image5.jpg")
```

주의:
- `content.hpf` 의 `<opf:item id="image5" media-type="image/jpg" .../>` 와
  파일 형식이 일치해야 한다. PNG 를 `.jpg` 로 확장자만 바꾸면 HWP 가 렌더에
  실패할 수 있음 → 반드시 JPEG 로 **변환**.
- 새 이미지의 픽셀 크기는 section0.xml 의 `<hp:orgSz>`, `<hp:curSz>`, 그리고
  `<hp:imgRect>` 좌표와 상이해도 HWP 가 로드 시 자동 스케일링하므로 일반적으로
  문제 없음. 단 비율이 크게 다르면 레이아웃이 깨질 수 있다.

## 7. WebFetch SSL 우회 (curl -k fallback)

일부 학회 사이트(예: `displayweek.org`)는 인증서 중간 체인 문제로 Claude
WebFetch 가 실패한다:

```
self signed certificate in certificate chain
```

대안: bash `curl -k`(insecure) 로 HTML 을 파일로 받고, Python 에서 파싱.

```bash
curl -sSLk --max-time 20 "https://www.displayweek.org/" -o /tmp/dw.html
```

```python
# Python (PYTHONUTF8=1)
import re
with open("/tmp/dw.html", encoding="utf-8") as f:
    html = f.read()
m = re.search(r"<body[^>]*>(.*?)</body>", html, re.S)
body = m.group(1) if m else html
body = re.sub(r"<script.*?</script>", "", body, flags=re.S)
body = re.sub(r"<style.*?</style>", "", body, flags=re.S)
body = re.sub(r"<[^>]+>", " ", body)
body = re.sub(r"\s+", " ", body)
print(body[:5000])
```

- Windows Git Bash 환경에서 `python3` 가 WindowsApps stub 으로 redirect 되어
  실패할 수 있다 → `python` 또는 `python.exe` 사용, 항상 `PYTHONUTF8=1`.
- curl `schannel` 인증서 오류가 나면 `-k` 로 우회. 받아온 원문은 작업 디렉토리
  아래에 보관하여 재현성 확보.

## 8. 진단 도구

편집 대상 테이블을 찾기 전 구조를 파악:

```bash
PYTHONUTF8=1 python scripts/scan_tables.py  unpacked/Contents/section0.xml
# → T00 ~ Tn  전체 리스트 + rowCnt × colCnt + 선행 단락 + 헤더
```

특정 테이블 내용 확인 (편집 전후 diff 용):

```bash
PYTHONUTF8=1 python scripts/dump_tables.py  unpacked/Contents/section0.xml  2 6 8
# → T02, T06, T08 셀 내용 dump
```

## 9. 전체 편집 워크플로우 권장 순서

1. `build_trip_plan.py` 로 공통 필드 치환된 baseline 생성
2. baseline 을 unpack → `scan_tables.py` 로 구조 파악
3. 편집 스크립트 작성:
   - §1 블록 삭제 (`delete_range_between`)
   - §1 본문 paragraph 갱신 (`set_multi_run_text` / `set_p_text_flow`)
   - 스케줄 테이블 rebuild (`rebuild_table_data_rows`)
   - 과제 연결 / 예산 테이블 rebuild (같은 helper, 헤더 + data rows)
   - 반출 장비 테이블 컬럼 삭제 (`delete_column`)
   - 관심 세션 테이블 rebuild (multi-line 셀 = `set_cell_text_lines`)
   - **테이블 뒤 분석 섹션 삽입** (`insert_paragraphs_after`) — v0.4
4. `BinData/image*.jpg` 교체 (필요 시)
5. `write_hwpx_xml` → `pack.py` → `validate.py`
6. `dump_tables.py` 로 결과 검증

---

## 10. 테이블 뒤에 분석·주석 섹션 추가 (v0.4)

기존 테이블의 뒤에 "분석 섹션 / 해설 / 후속 계획" 을 여러 paragraph 로 삽입하는 패턴.

### 10.1. 기본 흐름

```python
from table_utils import (
    find_table_by_anchor, find_containing_paragraph,
    find_paragraph_by_text, insert_paragraphs_after,
)

# 1) 기준이 될 테이블과 그 테이블을 감싸는 <hp:p> 찾기
tbl = find_table_by_anchor(root, ["날짜", "Session", "발표제목", "참석자"])
anchor = find_containing_paragraph(tbl)

# 2) 두 가지 스타일 템플릿 확보 (섹션 헤더 / 본문)
heading_tpl = find_paragraph_by_text(root, "2. Display Week 2026 주요 행사")
body_tpl    = find_paragraph_by_text(root, "행사의 중요성")

# 3) 삽입할 내용 (kind, text) 리스트 구성
content = [
    ("H", "3. 관심 세션 심층 분석"),
    ("B", "본 섹션에서는 관련 기관·발표를 매핑하고 ..."),
    ("H", "3.1. 프로젝트 A 관점"),
    ("B", "■ Samsung Display — Large-area CMP ..."),
    ("B", "■ Meta — Ray-Ban Light Engine ..."),
    ("B", "가. 협력 가능성"),
    ("B", "Samsung Display 는 국내 컨소시엄 구성원으로 ..."),
    # ...수십 개
]

# 4) 일괄 삽입
n = insert_paragraphs_after(
    anchor,
    content,
    templates={"H": heading_tpl, "B": body_tpl},
)
print(f"inserted {n} paragraphs")
```

### 10.2. 주의 사항

- 템플릿 paragraph 는 **섹션 루트 레벨의 <hp:p>** 를 선택 (테이블·셀 내부 <hp:p> 금지)
  → `find_paragraph_by_text(root, ...)` 가 첫 match 를 반환하므로 충분히 특이한 문자열 사용.
- `clone_paragraph_with_text()` 가 내부의 `<hp:tbl>` 과 `<hp:linesegarray>` 를 자동 제거
  → 같은 섹션의 "행사 소개(테이블 없는 본문)" 같은 깨끗한 paragraph 를 템플릿으로 쓰면
  가장 안전.
- **여러 스타일**을 쓰려면 `templates` dict 에 더 많은 kind 추가:
  ```python
  templates = {"H": heading_tpl, "S": sub_tpl, "B": body_tpl, "X": empty_tpl}
  ```
- `items` 의 `kind` 가 `templates` 에 없으면 첫 번째 템플릿으로 자동 fallback → 에러 대신
  문서가 로드 가능한 상태 유지.

### 10.3. 도식화 (기관-발표 매핑) 표현

대량의 "관련 기관 → 발표 → 관계" 매핑을 본문에 표현할 때, 별도 <hp:tbl> 을 생성하는 대신
**bullet-style body paragraph 로 나열**하는 것이 구현·관리 비용이 낮다:

```python
mapping = [
    "■ Samsung Display — Large-area CMP · MicroLED Panel | 관계: 국내 컨소시엄 (협력)",
    "■ Meta (Ajit Ninan) — Ray-Ban Light Engine | 관계: 수요기업/end-user",
    # ...
]
items = [("B", row) for row in mapping]
insert_paragraphs_after(anchor, items, templates={"B": body_tpl})
```

필요 시 나중에 이 bullet 들을 `rebuild_table_data_rows` 기반의 실제 table 로 프로모트할 수도
있지만, 일회용 출장계획서 본문에는 bullet 형태가 충분하다.

---

## v0.3 추가된 helper 요약

| 함수 | 용도 |
|------|------|
| `set_multi_run_text(p, texts)` | 다중 `<hp:run>` paragraph 의 각 `<hp:t>` 를 순서대로 매핑 |
| `find_paragraph_by_text(root, needle)` | 텍스트 포함 `<hp:p>` 탐색 |
| `find_table_after(heading_p)` | 특정 heading 이후 첫 `<hp:tbl>` 반환 |
| `delete_range_between(root, start, end)` | 두 anchor 사이 paragraphs 전부 DOM 삭제 |
| `rebuild_table_data_rows(tbl, rows)` | 헤더 유지, data rows 전면 재작성 |
| `delete_column(tbl, col_index)` | 컬럼 DOM 제거 + colAddr/colCnt 보정 |
| `find_column_by_header(tbl, header_text)` | 헤더 텍스트로 `colAddr` 탐색 |

## v0.4 추가된 helper 요약

| 함수 | 용도 |
|------|------|
| `find_containing_paragraph(elem)` | 임의 element → 조상 `<hp:p>` 추적 (테이블 wrapper 찾기) |
| `clone_paragraph_with_text(template_p, text)` | 템플릿 복제 + 내부 table 제거 + linesegarray 제거 + 텍스트 주입 |
| `insert_paragraphs_after(anchor_p, items, templates)` | (kind, text) 튜플 리스트 → 기준 paragraph 뒤에 일괄 삽입, 스타일 맵 지원 |

---

## 11. 계층적 글머리표 (❍ / - / 본문) 제어 — v0.5

### 11.1. 문제

템플릿의 본문 스타일 paragraph(예: `paraPrIDRef="41"`, `styleIDRef="0"`) 가
`header.xml` 상 `<hh:heading type="BULLET" idRef="2"/>` 를 가지고 있으면,
한컴 한글은 **해당 paraPrIDRef 를 쓰는 모든 문단 앞에 ❍ 글머리표를 자동
렌더**한다. `clone_paragraph_with_text()` 는 `paraPrIDRef` 속성도 그대로
deepcopy 하므로, 단일 본문 템플릿을 여러 문단으로 복제하면 **모든 문단에
❍ 가 붙는 현상**이 발생한다.

### 11.2. 해결: `paraPrIDRef` 를 계층별로 명시 지정

`header.xml` 에 일반적으로 정의된 스타일 3종을 활용:

| paraPrIDRef | `<hh:heading>` | 의미 |
|-------------|----------------|------|
| `"1"` | `type="NONE"` | 글머리표 없음 — 본문·헤더용 |
| `"41"` | `type="BULLET" idRef="2"` (❍) | 최상위 글머리표 |
| `"42"` | `type="BULLET" idRef="1"` (-) | 들여쓰기 + 하위 글머리표 |

**주의**: 실제 ID 는 템플릿마다 다를 수 있다. `header.xml` 에서
`<hh:paraPr id="…" ...>` 의 `<hh:heading type>` 을 확인하고, `<hh:bullets>` 의
`char` 값으로 어떤 기호가 붙는지 확인할 것.

### 11.3. 새 helper 로 계층 구성

```python
from table_utils import (
    find_table_by_anchor, find_containing_paragraph,
    find_paragraph_by_text, insert_styled_paragraphs,
)

tbl = find_table_by_anchor(root, ["날짜", "Session"])
anchor = find_containing_paragraph(tbl)
base = find_paragraph_by_text(root, "행사의 중요성")  # paraPrIDRef="41"

items = [
    # (text, paraPrIDRef)
    ("관심 세션 심층 분석",                     "41"),  # ❍ 최상위
    ("DW 2026 공개 페이지 기반 두 과제 …",      "1"),   # 본문 (no bullet)
    ("KIAT 국제공동과제 (MT8600) — MIT 컨소시엄", "41"), # ❍
    ("관련 기관 및 발표 매핑",                  "42"),  # - 하위
    ("Samsung Display — Large-area CMP …",     "42"),  # -
    ("Meta (Ajit Ninan) — Ray-Ban …",          "42"),  # -
    ("가. 협력 가능성",                         "42"),  # -
    ("Samsung Display 는 MT8600 국내 컨소시엄 …", "1"),  # 본문
    ("나. 위험요인",                            "42"),  # -
    ("Aledia · PlayNitride · VueReal …",        "1"),   # 본문
]
n = insert_styled_paragraphs(anchor, items, base)
```

### 11.4. 섹션 번호 없이 bullet 블록으로 추가

이전 버전에서 "3. 관심 세션 심층 분석" 처럼 **섹션 헤더** (`paraPrIDRef="1"`
+ `charPrIDRef="29"` 큰 글씨) 로 추가했다면, 섹션 번호 체계가 팽창한다.
대신 **기존 섹션(예: 2.) 아래 ❍ 최상위 bullet 으로 편입** 하면 번호 체계를
유지하면서 분석 블록을 넣을 수 있다:

```python
# Before (새 섹션 헤더 추가 — 번호 체계 팽창)
items = [("H", "3. 관심 세션 심층 분석"), ("B", "...")]

# After (기존 섹션 안의 ❍ 최상위 bullet — 번호 유지)
items = [("관심 세션 심층 분석", "41"), ("...", "1")]
```

### 11.5. 주의 — 본문은 반드시 `paraPrIDRef="1"` (또는 `"NONE"` 스타일)

복제한 템플릿의 `paraPrIDRef` 를 명시 교체하지 않으면 기존 bullet 스타일이
상속되어 ❍/- 가 본문 전체에 붙는다. **본문 paragraph 는 반드시**
`para_pr_id_ref="1"` 같은 no-bullet 스타일로 덮어써야 한다. 이 누락이
"동그라미 글머리표가 모든 문단에 삽입" 되는 증상의 유일한 원인이다.

## v0.5 추가된 helper 요약

| 함수 | 용도 |
|------|------|
| `set_paragraph_style(p, para_pr_id_ref, char_pr_id_ref, page_break)` | 기존 `<hp:p>` 의 스타일 속성 명시 덮어쓰기 |
| `clone_paragraph_with_style(template_p, text, para_pr_id_ref, char_pr_id_ref)` | 복제 + 텍스트 + 스타일 덮어쓰기 one-shot |
| `insert_styled_paragraphs(anchor_p, items, base_template)` | `[(text, paraPrID[, charPrID]), ...]` 일괄 삽입 (계층적 글머리표) |

---

## 12. 3-레벨 계층 확장 — header.xml 에 bullet · paraPr 추가 (v0.5)

### 12.1. 상황

기존 템플릿은 일반적으로 **2단계 bullet**(`❍` + `-`) 만 `header.xml` 에 정의한다.
매핑 리스트(예: Samsung Display, Meta …)와 가·나·다·라·마 소제목이 같은
`-` bullet 을 공유하면 계층이 모호해진다. 이때 `header.xml` 에 **level-3 bullet
과 연관 paraPr 2개**를 **순수 추가(additive)** 로 패치하면 3-레벨 계층이 완성된다.

### 12.2. 패치 대상 (header.xml 3 곳)

```xml
<!-- (1) bullets itemCnt 갱신 + 새 bullet id=3 삽입 -->
<hh:bullets itemCnt="3">                              <!-- was 2 -->
  <hh:bullet id="1" char="-"  ...>...</hh:bullet>
  <hh:bullet id="2" char="❍" ...>...</hh:bullet>
  <hh:bullet id="3" char="·"  useImage="0">           <!-- NEW -->
    <hh:paraHead level="0" align="LEFT" useInstWidth="0" autoIndent="1"
                 widthAdjust="0" textOffsetType="PERCENT" textOffset="50"
                 numFormat="DIGIT" charPrIDRef="4294967295" checkable="0"/>
  </hh:bullet>
</hh:bullets>

<!-- (2) paraProperties itemCnt 갱신 -->
<hh:paraProperties itemCnt="60">                      <!-- was 58 -->

<!-- (3) </hh:paraProperties> 직전에 paraPr 2개 추가 -->
<hh:paraPr id="58" ...>                               <!-- level-3 bullet (·) -->
  <hh:align horizontal="JUSTIFY" vertical="BASELINE"/>
  <hh:heading type="BULLET" idRef="3" level="0"/>
  ...
  <hh:margin><hc:left value="7324" unit="HWPUNIT"/></hh:margin>
  <!-- level-2 의 2x 들여쓰기 -->
</hh:paraPr>
<hh:paraPr id="59" ...>                               <!-- level-3 body (no bullet) -->
  <hh:align horizontal="JUSTIFY" vertical="BASELINE"/>
  <hh:heading type="NONE" idRef="0" level="0"/>
  ...
  <hh:margin><hc:left value="5493" unit="HWPUNIT"/></hh:margin>
  <!-- level-2 text 위치로 들여쓰기 -->
</hh:paraPr>
```

**주의**: 기존 bullet/paraPr 는 **건드리지 않는다**(순수 추가). `itemCnt` 2개만
갱신하므로 기존 섹션 렌더링은 변화 없음.

### 12.3. 들여쓰기 단위 (HWPUNIT)

| level | 역할 | 권장 margin.left (default) |
|-------|------|---------------------------|
| 1 (❍) | 최상위 | 0 |
| 2 (-) | 중간 | 3662  (~13 mm) |
| 3 (·) | 최하위 리스트 | 7324  (~26 mm) — level-2 의 2x |
| 3 body | 본문 (no bullet) | 5493  (~19 mm) — level-2 text 위치 |

※ `<hp:case required-namespace="HwpUnitChar">` 블록은 default 의 절반 사용
(예: 3662 → 1831, 5493 → 2747, 7324 → 3662). HWP 구버전 호환.

### 12.4. 4-레벨 구조 사용 예

```python
TOP, SUB, ITEM, BODY, INTRO = "41", "42", "58", "59", "1"

items = [
    ("관심 세션 심층 분석",     TOP),    # ❍
    (INTRO_PARA,              INTRO),  # 본문 (들여쓰기 없음)
    ("KIAT 국제공동과제 …",    TOP),    # ❍
    ("관련 기관 및 발표 매핑",  SUB),    # -
    ("Samsung Display — …",   ITEM),   # ·
    ("Meta — …",             ITEM),   # ·
    ("협력 가능성",            SUB),    # -
    ("Samsung Display 는 …",  BODY),   # body (들여쓰기, no bullet)
    ("위험요인",               SUB),    # -
    ("Aledia · PlayNitride …", BODY),   # body
]
insert_styled_paragraphs(anchor, items, base_tpl)
```

결과 레이아웃:
```
❍ 관심 세션 심층 분석
DW 2026 세션 …                             (INTRO 본문, no indent)

❍ KIAT 국제공동과제 …
    - 관련 기관 및 발표 매핑
        · Samsung Display — …
        · Meta — …
    - 협력 가능성
            Samsung Display 는 …           (BODY, indented)
    - 위험요인
            Aledia · PlayNitride …         (BODY, indented)
```

### 12.5. 패치 스크립트 템플릿

문자열 치환으로 충분 (순수 추가 + itemCnt 갱신):

```python
def patch_header(header_path):
    txt = header_path.read_text(encoding="utf-8")
    if 'hh:bullet id="3"' in txt:
        return  # 이미 적용됨 — idempotent
    txt = txt.replace('<hh:bullets itemCnt="2">',
                      '<hh:bullets itemCnt="3">', 1)
    txt = txt.replace('    </hh:bullets>',
                      NEW_BULLET + '    </hh:bullets>', 1)
    txt = txt.replace('<hh:paraProperties itemCnt="58">',
                      '<hh:paraProperties itemCnt="60">', 1)
    txt = txt.replace('    </hh:paraProperties>',
                      NEW_PARAPR_58 + NEW_PARAPR_59 + '    </hh:paraProperties>', 1)
    header_path.write_text(txt, encoding="utf-8")
```

### 12.6. 함정

- **`itemCnt` 갱신 누락**: 한컴 한글이 실제 개수와 itemCnt 불일치 시 로드 거부.
- **기존 id 충돌**: 추가할 paraPr id 는 **기존 최대값 + 1** 이상이어야 한다.
  `grep 'hh:paraPr id=' header.xml` 로 최대 id 확인 후 선택.
- **스타일 ID 재할당 금지**: 이미 사용 중인 paraPr id 를 수정하면 기존 섹션의
  렌더링이 바뀐다. 반드시 **새 id** 로 추가하고 새 문단만 참조하도록 한다.
- **idempotent 체크**: 같은 템플릿을 여러 번 패치하면 중복 삽입 위험. `if 'id="3"'
  in txt: return` 방어선 필수.

---

## 13. Bullet 리스트 → 3-col 표 변환 패턴

긴 리스트(10+ 항목)를 bullet 으로 나열하면 가독성이 떨어진다. 기존 문서 내 **다른
섹션의 표**를 템플릿으로 재사용해 구조화.

### 13.1. 워크플로우

```python
# 1. 템플릿 표 탐색 (예: 4-col 출장 실적 표)
t05 = find_table_by_anchor(root, ["성명", "출 장 기 간", "출장국가(지역)", "출 장 목 적"])
t05_wrapper = find_containing_paragraph(t05)

# 2. deepcopy → 구조 변환 → 데이터 재작성
def build_mapping_table_wrapper(template_wrapper, data_rows_3col):
    new_wrap = deepcopy(template_wrapper)
    strip_linesegarray(new_wrap)

    tbl = next(new_wrap.iter(hp("tbl")), None)

    # 2a. 불필요 컬럼 삭제 (4 → 3)
    delete_column(tbl, 0)

    # 2b. 남은 컬럼 width 재배치 (예: col1 ↔ col2 swap)
    #     긴 컨텐츠가 들어갈 컬럼을 wide 슬롯으로 옮김
    for row in tbl.findall(hp("tr")):
        cells = row.findall(hp("tc"))
        if len(cells) < 3: continue
        sz1, sz2 = cells[1].find(hp("cellSz")), cells[2].find(hp("cellSz"))
        w1 = sz1.get("width")
        sz1.set("width", sz2.get("width"))
        sz2.set("width", w1)

    # 2c. 표 outer <hp:sz width> 갱신 — 삭제된 컬럼 폭 차감
    first_row_cells = tbl.findall(hp("tr"))[0].findall(hp("tc"))
    new_total = sum(int(c.find(hp("cellSz")).get("width"))
                    for c in first_row_cells[:3])
    tsz = tbl.find(hp("sz"))
    if tsz is not None:
        tsz.set("width", str(new_total))

    # 2d. 헤더 행 텍스트 갱신
    header_cells = tbl.findall(hp("tr"))[0].findall(hp("tc"))
    for i, text in enumerate(["기관", "세션", "관계"]):
        set_cell_text_flow(header_cells[i], text)

    # 2e. 데이터 rows 재작성 (헤더 유지)
    rebuild_table_data_rows(tbl, data_rows_3col)

    return new_wrap

# 3. 분석 paragraph 삽입 후 "관련 기관 및 발표 매핑" 뒤에 표 삽입
heading_p = find_paragraph_by_text(root, "관련 기관 및 발표 매핑")
tbl_wrap = build_mapping_table_wrapper(t05_wrapper, parsed_rows)
heading_p.addnext(tbl_wrap)
```

### 13.2. 함정

- **`<hp:sz width>` 갱신 누락**: `delete_column` 은 `colCnt` 만 갱신, outer
  `<hp:sz width>` 는 유지. 실제 cellSz 합계와 불일치 시 HWP 가 빈 공간 렌더
  또는 테두리 깨짐. **반드시 수동 갱신**.
- **linesegarray 잔존**: deepcopy 한 wrapper `<hp:p>` 의 `<hp:linesegarray>` 를
  `strip_linesegarray` 로 제거해야 HWP 가 재레이아웃.
- **colAddr 재번호**: `delete_column` 이 내부적으로 처리. 별도 `renumber_table`
  불필요 (이미 rebuild_table_data_rows 내에서 호출).
- **템플릿 표 선택 기준**:
  - colCnt 근접 (3→3 이상적, 4→3 1컬럼 삭제)
  - rowspan/colspan 병합 **없는** 행을 템플릿으로 (있으면 `_reset_cell_span`
    이 자동 해제하지만 레이아웃 예측성 감소)
  - cellSz 총 width 가 페이지 폭 대비 적절 (너무 좁거나 넓으면 재조정 필요)
- **중복 heading 매치**: `find_paragraph_by_text` 는 첫 매치만 반환. 같은 문구가
  여러 번 나타나면 (예: KIAT/NC 양쪽의 "관련 기관 및 발표 매핑") 전체 순회로
  모든 matches 수집.

---

## 14. 이미지 삽입 (PNG/JPG) — `image_utils.py` (v0.6)

분석 다이어그램·차트·슬라이드 PNG 를 본문에 삽입해야 할 때 3단계 패턴으로
처리. 기존 이미지 wrapper `<hp:p>` 을 템플릿으로 deepcopy 하면 복잡한
`<hp:pic>` 내부 속성을 모두 자동 처리.

### 14.1. 3단계 삽입 패턴

```python
import shutil
from pathlib import Path
from image_utils import (
    register_image_in_hpf,
    find_pic_wrapper_by_binary_id,
    clone_pic_paragraph,
    HWPUNIT_PER_PX,
)

# (1) BinData/ 에 파일 복사
shutil.copy("risk_slide.png", unpacked / "BinData" / "image9.png")

# (2) content.hpf 에 <opf:item> 등록 (idempotent, 마지막 image 뒤 auto-anchor)
register_image_in_hpf(
    unpacked / "Contents" / "content.hpf",
    img_id="image9", href="BinData/image9.png", media_type="image/png",
)

# (3) section0.xml 에 <hp:pic> wrapper <hp:p> 삽입
template = find_pic_wrapper_by_binary_id(root, "image5")   # 기존 이미지 재사용
new_wrap = clone_pic_paragraph(
    template,
    binary_id="image9",
    orig_px=(1280, 720),            # 원본 PNG 픽셀
    display_w_hwpunit=42520,        # 문서 내 표시 폭 (~15cm)
    pic_id=1900000009, instid=800000009, zorder=20,
)
target_paragraph.addnext(new_wrap)
```

### 14.2. HWPUNIT 변환 (1px @ 96DPI = 75 HWPUNIT)

| 요소 | 값 | 비고 |
|------|----|----|
| `<hp:orgSz width/height>` | `px × 75` | 원본 픽셀 크기 × 75 |
| `<hp:curSz width/height>` | display 목표 | 일반적 `42520 × ?` (≈15cm) |
| `<hc:scaMatrix e1/e5>` | `disp_w / orig_w_hwpunit` | 약 0.44 |
| `<hp:imgRect pt0..3>` | 원본 크기 직사각형 | (0,0)-(W,0)-(W,H)-(0,H) |
| `<hp:imgClip right/bottom>` | 원본 크기 | clip 영역 |
| `<hp:imgDim dimwidth/dimheight>` | 원본 크기 | |
| `<hp:sz width/height>` | display 크기 | 페이지 레이아웃용 |

### 14.3. 함정

- **ID 충돌**: `<hp:pic id>`, `<hp:pic instid>`, `<hp:pic zOrder>` 는 문서 내
  유일해야 한다. 기존 이미지 id 범위 확인 후 충돌 없는 값 선택.
- **shapeComment 누락**: deepcopy 시 원본 파일명이 남음 → `clone_pic_paragraph`
  가 자동 제거.
- **linesegarray 잔존**: wrapper paragraph `<hp:linesegarray>` 는 원본 이미지 크기
  기준으로 layout 계산. 제거 필수 (helper 가 자동 처리).
- **content.hpf itemCnt 불일치**: `register_image_in_hpf` 는 `<opf:manifest>` 는
  itemCnt 가 없어 자동으로 안전. (`<hh:bullets itemCnt>` 같은 헤더와 다름)
- **이미지 파일 경로**: `href` 는 `BinData/imageN.ext` 상대 경로. Windows 절대
  경로 사용 금지.

### 14.4. PIL 기반 슬라이드 생성 (`generate_risk_slide.py`)

NotebookLM 스타일 4행 [위험 요인 ▶ 대응 전략] 슬라이드를 Malgun Gothic 폰트로
렌더. Gemini API 호출 없이 로컬 생성, 재현성 확보.

```python
from generate_risk_slide import render_risk_slide

render_risk_slide(
    out_path="mt8600_risk.png",
    title_line1="위험요인 분석 및 대응 전략:",
    title_line2="시장 위협 대비 KIMM 기술의 포지셔닝 (MT8600)",
    rows=[
        (["Wafer-level mass transfer",
          "선행 상용화 (Aledia, PlayNitride 등)"],
         ["Yield/Throughput 지표 공개 시,",
          "8인치 연속 롤 전사의 우위 수치화 및 재평가."]),
        # ... 최대 4쌍
    ],
)
```

CLI:
```bash
PYTHONUTF8=1 uv run python scripts/generate_risk_slide.py \
    --out risk.png \
    --title "위험요인 분석 및 대응 전략:" \
    --subtitle "시장 위협 대비 기술 포지셔닝" \
    --json rows.json
```

---

## 15. 표 오른쪽 정렬 (wrapper paragraph paraPrIDRef 교체)

`treatAsChar="1"` 인라인 표는 감싸는 `<hp:p>` 의 paragraph 정렬 속성을 따른다.
RIGHT-alignment 를 원하면 wrapper `<hp:p>` 의 `paraPrIDRef` 를 RIGHT 정렬 스타일로
교체.

```python
from table_utils import set_paragraph_style

# RIGHT-aligned paraPr id 탐색 (header.xml 에서 grep):
#   grep 'horizontal="RIGHT"' header.xml
# 예: id=33 이면
set_paragraph_style(tbl_wrapper_p, para_pr_id_ref="33")
```

적절한 RIGHT 스타일이 없으면 header.xml 에 추가 (12절 패턴 참조).

## v0.6 추가된 helper 요약

| 모듈 | 함수 | 용도 |
|------|------|------|
| `image_utils` | `register_image_in_hpf(hpf, id, href, mime)` | content.hpf 에 `<opf:item>` idempotent 추가 |
| `image_utils` | `find_pic_wrapper_by_binary_id(root, id)` | 기존 이미지 wrapper `<hp:p>` 탐색 (템플릿) |
| `image_utils` | `clone_pic_paragraph(tpl, binary_id, orig_px, ...)` | 템플릿 deepcopy + 크기/scale/binary_id 재설정 |
| `generate_risk_slide` | `render_risk_slide(...)` | 4행 위험-대응 슬라이드 PNG (PIL + Malgun Gothic) |
