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
   - 관심 세션 테이블 rebuild
4. `BinData/image*.jpg` 교체 (필요 시)
5. `write_hwpx_xml` → `pack.py` → `validate.py`
6. `dump_tables.py` 로 결과 검증

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
