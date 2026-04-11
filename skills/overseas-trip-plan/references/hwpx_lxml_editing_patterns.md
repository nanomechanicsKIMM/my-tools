---
title: "HWPX lxml 편집 패턴 레퍼런스"
created: 2026-04-11
tags: [hwpx, lxml, editing-patterns, debugging]
---

# HWPX lxml 편집 패턴 레퍼런스

> 이 세션(2026-04-11) 에서 `overseas-trip-plan` 스킬을 개발하면서 얻은 교훈.
> HWPX 파일을 lxml 로 **구조적으로 편집**할 때 반드시 지켜야 할 규칙 정리.

## 배경

HWPX 는 한컴오피스의 개방형 포맷(ZIP + XML). 단순 텍스트 치환은 `zip_replace.py`로 충분하지만, 행 삽입·삭제·셀 단위 편집처럼 **XML 트리 구조를 바꿔야 할 때** 는 lxml 을 사용한다.

이 과정에서 3번의 로드 실패(v3, v4, v5/v6 겹침)를 거치며 알게 된 5가지 핵심 규칙:

---

## 규칙 1: Phantom Paragraph 방지 ⚠️

### 증상
한글에서 파일을 열면 "빈 문서 1"로 폴백되어 **아예 로드되지 않는다.**

### 원인
HWPX 셀은 여러 `<hp:p>` 를 가질 수 있다. 예를 들어 원본 셀이 다음과 같을 때:

```xml
<hp:subList>
  <hp:p><hp:run><hp:t>미국</hp:t></hp:run><hp:linesegarray>...vertpos="0".../></hp:linesegarray></hp:p>
  <hp:p><hp:run><hp:t>(보스톤, 워싱턴DC)</hp:t></hp:run><hp:linesegarray>...vertpos="1760".../></hp:linesegarray></hp:p>
</hp:subList>
```

순진한 치환 코드가 첫 `<hp:p>` 의 `<hp:t>` 에만 텍스트를 설정하고 나머지 `<hp:p>` 의 `<hp:t>` 는 빈 문자열로 만들면:

```xml
<hp:subList>
  <hp:p><hp:run><hp:t>미국 (로스앤젤레스, 보스턴)</hp:t></hp:run>...vertpos="0".../></hp:p>
  <hp:p><hp:run><hp:t></hp:t></hp:run>...vertpos="1760".../></hp:p>  <!-- ← 유령 -->
</hp:subList>
```

**빈 `<hp:p>` 가 여전히 `<hp:linesegarray>`(vertpos=1760) 를 가진 채 남아**, 한글 layout engine 이 "2번째 줄 위치에 텍스트 없는 문단" 을 해석하지 못해 로드 실패.

### 해결
**여분의 `<hp:p>` 는 반드시 DOM 에서 제거한다.**

```python
def set_cell_text_flow(cell, text):
    sublist = cell.find(hp("subList"))
    ps = sublist.findall(hp("p"))

    # 첫 번째 <hp:p> 에 텍스트 설정
    first_p = ps[0]
    ts = list(first_p.iter(hp("t")))
    ts[0].text = text
    for t in ts[1:]:
        t.text = ""

    strip_linesegarray(first_p)  # 규칙 2

    # ★ 추가 <hp:p> 제거
    for p in ps[1:]:
        sublist.remove(p)
```

---

## 규칙 2: linesegarray 재계산 유도 ⚠️

### 증상
파일은 열리지만 **§3 문단·§4 표 셀의 텍스트가 인접 문단과 겹쳐 보인다** (특히 편집한 곳).

### 원인
`<hp:linesegarray>` 는 원본 텍스트의 위치 메타데이터:
```xml
<hp:linesegarray>
  <hp:lineseg textpos="0" vertpos="6660" horzpos="0" horzsize="48188" .../>
</hp:linesegarray>
```

텍스트를 바꿨는데도 원본 `textpos`/`horzpos`/`horzsize` 가 남으면, 한글은 **새 텍스트를 원본 위치에 그대로 그리려 시도**. 새 텍스트가 길면 wrap 되어 인접 문단과 겹침.

### 해결
편집한 문단의 `<hp:linesegarray>` 를 **완전히 제거**한다. 한글이 로드 시 자동으로 재계산한다 (tor 스킬이 만드는 `<hp:p>` 도 linesegarray 없음).

```python
def strip_linesegarray(p):
    lsa = p.find(hp("linesegarray"))
    if lsa is not None:
        p.remove(lsa)
```

### 주의
- 편집하지 **않은** 문단의 linesegarray 는 건드리지 않는다 (원본 positioning 보존).
- 스킬 `table_utils.py` 의 `set_p_text_flow()` / `set_cell_text_flow()` 는 기본적으로 `strip_linesegarray()` 호출.

---

## 규칙 3: rowCnt + rowAddr 재번호 (행 삽입·삭제 후 필수) ⚠️

### 증상
파일이 열리지 않거나, 표가 이상하게 렌더링된다.

### 원인
HWPX `<hp:tbl>` 은 행 수를 속성으로 저장:
```xml
<hp:tbl rowCnt="10" colCnt="4" ...>
```

그리고 각 셀에 **행 주소** 가 있다:
```xml
<hp:tc>
  <hp:cellAddr colAddr="1" rowAddr="3"/>
  ...
</hp:tc>
```

행을 추가/삭제해도 `rowCnt` 와 `rowAddr` 가 갱신되지 않으면:
- `rowCnt="10"` 이지만 실제 `<hp:tr>` 개수는 11
- deepcopy 한 새 행의 `rowAddr` 가 원본의 값을 그대로 물려받아 중복 발생

한글은 이 불일치를 감지하고 파일 로드 거부.

### 해결
행 편집 직후 반드시 `renumber_table(tbl)` 호출:

```python
def renumber_table(tbl):
    rows = tbl.findall(hp("tr"))
    for row_idx, row in enumerate(rows):
        for cell in row.findall(hp("tc")):
            addr = cell.find(hp("cellAddr"))
            if addr is not None:
                addr.set("rowAddr", str(row_idx))
    tbl.set("rowCnt", str(len(rows)))
```

### colAddr 주의
`colAddr` 는 **병합(rowspan) 구조를 유지**하기 위해 건드리지 않는다. 예: `<hp:cellSpan rowSpan="3">` 인 첫 셀이 colAddr=0 을 차지하면, 다음 행들의 셀은 colAddr 1,2,3 부터 시작.

---

## 규칙 4: cellSpan rowSpan 증감

병합 셀의 `<hp:cellSpan rowSpan="N">` 은 수동 관리:

```python
# 김재현 section 에 새 행 추가 → rowSpan 3 → 4
span = cells_first[0].find(hp("cellSpan"))
old_rs = int(span.get("rowSpan", "1"))
span.set("rowSpan", str(old_rs + 1))
```

### 행 삭제 시
`remove_row_safe()` 로 감소:
```python
remove_row_safe(row, decrement_rowspan_of=kim_first_cell)
```

---

## 규칙 5: XML 선언 형식 (HWP 호환)

### 증상
대부분 작동하지만, 안전성을 위해 원본 양식과 통일.

### lxml 기본
```python
tree.write(path, encoding="utf-8", xml_declaration=True)
# 결과: <?xml version='1.0' encoding='UTF-8'?>  (single-quote)
```

### HWP 가 생성하는 양식 (원본 템플릿)
```xml
<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>
```
double-quote, 공백 포함.

### 해결 (수동 직렬화)
```python
def write_hwpx_xml(tree, path):
    body = etree.tostring(
        tree.getroot(), encoding="utf-8", xml_declaration=False
    ).decode("utf-8")
    decl = '<?xml version="1.0" encoding="UTF-8" standalone="yes" ?>'
    Path(path).write_text(decl + body, encoding="utf-8")
```

---

## 부록: 자동 테스트 시 Hwp 실행 방법

Git bash 에서 `Hwp.exe "파일.hwpx" &` 로 실행하면 **유니코드 경로 인자 전달 실패** 가능. Hwp 가 빈 문서를 연다.

### 해결
PowerShell `Invoke-Item` 사용 (파일 탐색기 더블클릭과 동일):

```bash
powershell.exe -Command "Invoke-Item 'C:\path\to\file.hwpx'"
```

그리고 12초 이상 대기 후 MainWindowTitle 확인:
```bash
powershell.exe -Command "Start-Sleep -Seconds 12; Get-Process Hwp | Select-Object Id, MainWindowTitle"
```

MainWindowTitle 이:
- `국외출장계획서_SID2026_김재현_v6.hwpx [...] - 한글` → **로드 성공**
- `빈 문서 1 - 한글` → **로드 실패**

---

## 규칙 6: 멀티라인 셀 (`set_cell_text_lines`)

### 상황
표 셀에 2~3 줄의 내용을 표시해야 하는 경우 (예: 관심 세션의 발표제목 여러 개,
기관별 방문 상세의 협의 주제 여러 개).

### 문제
단순히 개행 문자 `\n` 을 넣거나 1개 `<hp:p>` 에 긴 텍스트를 넣으면 HWP 가
원하는 위치에서 줄바꿈을 하지 않는다. HWPX 의 "줄" 은 `<hp:p>` 단위이다.

### 해결
`set_cell_text_lines(cell, lines: list[str])` 사용:
1. 첫 `<hp:p>` 를 템플릿으로 `deepcopy`
2. deepcopy 의 `<hp:linesegarray>` 제거 (clean template)
3. 첫 줄은 기존 첫 `<hp:p>` 에 설정 + linesegarray 제거
4. 추가 줄마다 clean_template `deepcopy` → `<hp:t>` 설정 → `subList` 에 append
5. 모든 `<hp:p>` 는 linesegarray 가 없어 HWP 가 로드 시 자동 재계산

```python
set_cell_text_lines(title_cell, [
    "Perovskites: Challenges and Opportunities",
    "High-Efficiency Electroluminescent Perovskites",
    "Lead-Free Perovskite Derivatives for Display",
])
```

### 왜 `clean_template` 이 필요한가
`template_p` 자체는 첫 줄 설정 시 `strip_linesegarray()` 로 linesegarray 가
제거된다. 하지만 `<hp:run>` / `<hp:t>` 구조는 남아있어, 이를 deepcopy 한 뒤
추가 줄의 내용만 바꾸어 재사용하면 동일한 서식이 유지된다.

단, 만약 `template_p` 를 deepcopy 하지 않고 그대로 수정한 상태에서
`addnext()` 하면 얕은 복사 문제로 parent·sibling 체인이 꼬인다. 반드시
**사전에** clean_template 을 복사해두는 것이 안전하다.

---

## 체크리스트

lxml 로 HWPX 를 편집할 때:

- [ ] `set_cell_text_flow()` 로 셀 텍스트 편집 (phantom 방지, 단일 줄)
- [ ] `set_cell_text_lines()` 로 셀 멀티라인 편집 (2~3 줄)
- [ ] `set_p_text_flow()` 로 문단 텍스트 편집 (linesegarray 제거)
- [ ] 빈 문단은 `remove_paragraph()` 로 DOM 에서 완전 삭제
- [ ] 행 삽입·삭제 후 `renumber_table(tbl)` 호출 (rowCnt + rowAddr)
- [ ] 병합 셀 변경 시 `cellSpan rowSpan` 수동 증감
- [ ] 저장 시 `write_hwpx_xml()` 사용 (HWP 호환 선언)
- [ ] 테스트 시 `Invoke-Item` 으로 Hwp 실행

---

## 참고 링크

- `table_utils.py` — 이 규칙들을 구현한 모듈
- `rebuild_sid2026_v6.py` — 실전 사용 예시 (business_trip_plan 작업 디렉터리)
- tor 스킬 `build_tor.py` — linesegarray 없이 `<hp:p>` 생성하는 패턴 레퍼런스
- HWPX 표준: KS X 6101 (OWPML)
