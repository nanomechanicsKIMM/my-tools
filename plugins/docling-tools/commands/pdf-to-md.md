# PDF to Markdown Converter (Docling)

PDF 파일을 Docling으로 변환하고 Obsidian 프론트매터를 자동 삽입한다.

## 인자

$ARGUMENTS 에서 다음을 파싱한다:
- **파일 경로**: 변환할 PDF 파일 (필수, 복수 가능)
- `--table-structure`: 테이블 구조 모델 활성화 (Windows 개발자 모드 필요)
- `-o <path>`: 출력 경로 지정 (단일 파일만 가능)

## 실행 절차

### 1. 인자 파싱

$ARGUMENTS 에서 PDF 파일 경로와 옵션을 분리한다.
- `--table-structure` 가 있으면 해당 옵션 추가
- `-o` 가 있으면 그 다음 값을 출력 경로로 사용
- 나머지를 PDF 파일 경로 목록으로 처리

### 2. 사전 확인

각 PDF 파일에 대해:
- 파일이 존재하는지 확인 (Bash: `test -f "파일경로"`)
- 존재하지 않으면 에러 메시지 출력 후 해당 파일 건너뛰기

convert.py 경로 확인:
- `C:/Users/JHKIM/my-tools/plugins/docling-tools/convert.py`
- 없으면: "convert.py를 찾을 수 없습니다. my-tools를 설치해주세요." 출력 후 중단

### 3. 변환 실행

각 PDF 파일에 대해 Bash로 실행:

```
python "C:/Users/JHKIM/my-tools/plugins/docling-tools/convert.py" "파일경로" [--table-structure] [-o 출력경로]
```

- timeout: 600000 (10분)
- 실패 시 에러 메시지 출력하고 다음 파일로 진행

### 4. 프론트매터 삽입

변환 성공한 각 MD 파일에 대해:

1. Read로 변환된 MD 파일 읽기
2. 파일 최상단에 다음 YAML 프론트매터를 Edit으로 삽입:

```yaml
---
title: "PDF 파일명에서 .pdf 제거한 값"
created: 오늘 날짜 (YYYY-MM-DD)
tags: [pdf, docling]
source: "원본 PDF 파일명 전체"
---
```

- title: 파일명에서 `.pdf` 확장자를 제거한 값
- created: 변환 실행 시점의 날짜
- tags: 기본 `[pdf, docling]`
- source: 원본 PDF 파일의 전체 이름 (경로 제외, 파일명만)

### 5. 결과 보고

변환 결과를 테이블로 출력:

| 파일 | 상태 | 출력 경로 |
|------|------|----------|
| input.pdf | 성공/실패 | output.md |
