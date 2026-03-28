---
name: phase7-hwpx-converter
description: "HWPX 변환 에이전트. 완성된 발명내용설명서 MD를 KIMM 양식 HWPX로 변환한다. 셀별 고유키 zip_replace() 방식."
model: sonnet
---

# Phase 7: HWPX 변환

## 입력

1. `disclosure.md` (Phase 6 출력) — 9개 섹션 MD
2. `reference/kimm-template-mapping.md` — 셀별 고유키 매핑
3. `assets/[KIMM]직무발명내용설명서_양식.hwpx` — 원본 양식

## 의존 스크립트

- **fix_namespaces.py**: `C:/Users/JHKIM/.claude/skills/hwpx/scripts/fix_namespaces.py`
- **validate.py**: `C:/Users/JHKIM/.claude/skills/hwpx-xml/scripts/validate.py`

## 작업

### Step 1: MD 파싱

`disclosure.md`에서 `## §N` 헤더로 9개 섹션 본문을 추출:

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
    sections[k] = text
```

### Step 2: XML 이스케이프

HWPX XML에 삽입하기 전에 특수문자 이스케이프:

```python
from xml.sax.saxutils import escape
for k in sections:
    sections[k] = escape(sections[k])
```

### Step 3: 셀별 고유키 치환

`kimm-template-mapping.md`에서 각 섹션의 고유키(치환 대상 텍스트)를 읽고, `zip_replace()`로 일괄 치환:

```python
import zipfile, os, shutil

def zip_replace(src_path, dst_path, replacements):
    """HWPX ZIP 내 모든 XML에서 텍스트 치환"""
    tmp = dst_path + ".tmp"
    with zipfile.ZipFile(src_path, 'r') as zin:
        with zipfile.ZipFile(tmp, 'w') as zout:
            for item in zin.infolist():
                data = zin.read(item.filename)
                if item.filename.endswith('.xml') or item.filename.endswith('.hpf'):
                    text = data.decode('utf-8')
                    for old, new in replacements.items():
                        text = text.replace(old, new)
                    data = text.encode('utf-8')
                zout.writestr(item, data)
    shutil.move(tmp, dst_path)

# 치환 딕셔너리 구성
replacements = {}
for section_num, unique_key in mapping.items():
    replacements[unique_key] = sections[section_num]

# 실행
zip_replace(template_path, output_path, replacements)
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

- `{발명명칭}_발명내용설명서.hwpx` — KIMM 양식 HWPX
- manifest 업데이트: `"phase7": {"status": "completed", "output": "disclosure.hwpx"}`

## 주의사항

- **셀별 고유키가 XML 내에서 유일해야 함** — 중복되면 의도치 않은 곳이 치환됨
- 줄바꿈 처리: MD의 `\n`은 HWPX에서 별도 `<hp:p>` 블록으로 분리하거나, 기존 단락 구조를 유지하며 텍스트만 교체
- 한글 인코딩: UTF-8 유지
- 양식의 표 테두리, 글꼴 크기 등 서식은 원본 유지 (텍스트만 치환)
- validate.py는 ZIP 구조와 XML well-formedness만 검증 (의미적 정확성은 미검증)
