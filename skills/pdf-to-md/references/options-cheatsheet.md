# opendataloader-pdf 옵션 치트시트

전체 옵션 schema는 `C:/Users/JHKIM/opendataloader/options.json` 참조.
래퍼(`scripts/pdf_to_md.py`)에 노출되지 않은 고급 옵션이 필요하면 직접 CLI를 호출한다:

```bash
C:/Users/JHKIM/miniconda3/Scripts/opendataloader-pdf.exe \
  -f markdown-with-images -o out/ paper.pdf
```

## 자주 쓰는 옵션

| CLI 플래그 | 기본 | 설명 |
|---|---|---|
| `-o, --output-dir` | 입력 폴더 | 출력 디렉터리 |
| `-f, --format` | json | `json,text,html,pdf,markdown,markdown-with-html,markdown-with-images` (콤마 연결 가능) |
| `-p, --password` | — | 암호화된 PDF |
| `-q, --quiet` | false | 콘솔 로그 억제 |
| `--pages` | 전체 | "1,3,5-7" 형식 |
| `--reading-order` | xycut | `off | xycut` (XY-Cut++ 권장) |
| `--use-struct-tree` | false | Tagged PDF 트리 사용 |
| `--table-method` | default | `default`(테두리) / `cluster`(테두리 없는 표) |
| `--keep-line-breaks` | false | 원본 줄바꿈 유지 |
| `--include-header-footer` | false | 페이지 헤더·푸터 포함 |
| `--detect-strikethrough` | false | 취소선 → `~~text~~` |
| `--sanitize` | false | 개인정보 마스킹 |
| `--markdown-page-separator` | — | 예: `\n\n---\n<!-- page %page-number% -->\n\n` |
| `--image-output` | external | `off | embedded(Base64) | external(파일)` |
| `--image-format` | png | `png | jpeg` |
| `--image-dir` | 자동 | 이미지 별도 디렉터리 |
| `--content-safety-off` | — | `all | hidden-text | off-page | tiny | hidden-ocg` |

## 출력 형식 선택 가이드

| 사용처 | 권장 format |
|---|---|
| Obsidian 노트 + 그림 보존 | `markdown-with-images` |
| 표가 복잡해 HTML로 보존 필요 | `markdown-with-html` |
| LLM 컨텍스트(텍스트만) | `markdown` |
| 좌표 보존 RAG/citation | `markdown,json` |
| 접근성/Tagged PDF 검수 | `pdf` (annotated) |

## Hybrid 모드 (선택 고급)

스캔 PDF·복잡한 표·수식·차트 캡션 자동 생성이 필요하면:

```bash
# 1) 추가 패키지
pip install "opendataloader-pdf[hybrid]"

# 2) 별도 터미널에서 서버 기동
opendataloader-pdf-hybrid --port 5002

# 3) 변환 시 hybrid 옵션 추가
opendataloader-pdf -f markdown --hybrid docling-fast --hybrid-mode auto paper.pdf
```

`auto` 모드는 페이지별로 로컬/AI를 자동 분기. `full`은 모든 페이지를 백엔드에 보냄.

## 페이지 구분자 패턴

페이지 단위 인용/추적이 필요할 때:

```bash
--markdown-page-separator $'\n\n---\n<!-- page %page-number% -->\n\n'
```

(`%page-number%`가 실제 페이지 번호로 치환됨.)
