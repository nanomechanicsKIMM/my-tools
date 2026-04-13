---
name: pdf-to-md
description: opendataloader-pdf로 PDF를 Markdown(MD)으로 변환하는 스킬. 단일 파일·다중 파일·디렉터리 일괄 변환을 지원하고, 표·이미지·읽기 순서를 보존하며 Obsidian 호환 MD를 생성한다. 사용자가 "PDF를 MD로", "PDF를 마크다운으로", "convert pdf to markdown", "pdf to md", "논문 PDF 변환", "Zettelkasten으로 PDF 옮기기", "PDF 텍스트 추출", "opendataloader" 등을 언급하거나 .pdf 경로를 주며 변환·요약·인용 등을 요청하면 반드시 이 스킬을 사용할 것. 학술 논문 PDF, 보고서, 기술문서를 RAG/노트테이킹용 MD로 만들 때 우선 트리거.
---

# PDF → Markdown 변환 스킬 (opendataloader-pdf)

## 무엇을 하는가

`opendataloader-pdf`(벤치마크 1위, 0.907 정확도, 표 0.928)를 사용해 PDF를 구조 보존된 Markdown으로 변환한다. 결정론적 로컬 모드(0.015s/page)가 기본이며, 표·이미지·읽기 순서·헤딩 계층이 모두 보존된다. 산출물은 Obsidian Vault에 바로 붙일 수 있도록 설계되었다.

## 언제 쓰는가

- 학술 논문 PDF를 Obsidian 노트로 옮길 때 (`D:/Zettelkasten/References/`)
- 기술 보고서를 LLM 컨텍스트로 넣기 위해 MD화할 때
- 표가 많은 PDF에서 데이터 추출이 필요할 때
- RAG 파이프라인 전처리

## 전제 조건 (Prerequisites)

Java 11+가 필요하다. 래퍼 스크립트가 다음 순서로 자동 탐색하므로 보통 별도 설정이 필요 없다:

1. `PATH`의 `java`
2. `$JAVA_HOME/bin/java.exe`
3. `<sys.prefix>/Library/bin/java.exe` (현재 Python의 conda env)
4. `C:/Users/JHKIM/miniconda3/Library/bin/java.exe` (이 시스템 기본 — OpenJDK 21 번들됨)

위 4곳 모두에서 못 찾으면 친절한 에러로 종료한다. 그 경우 설치:
- https://adoptium.net/  또는  `winget install EclipseAdoptium.Temurin.21.JDK`

Python 패키지(`opendataloader_pdf`)가 없으면:
```bash
C:/Users/JHKIM/miniconda3/python -m pip install -U opendataloader-pdf
```

## 핵심 워크플로우

### 1단계: 입력 파악

사용자가 제공한 정보로 다음을 결정한다:

| 항목 | 기본값 | 비고 |
|---|---|---|
| `input` | 사용자 제공 | 파일 1개, 여러 개, 또는 디렉터리(재귀 X) |
| `output_dir` | 입력 파일과 같은 폴더 | 사용자가 다른 위치를 지정하면 거기로 |
| `format` | `markdown-with-images` | 도표 포함 논문 기본값. 텍스트만 원하면 `markdown` |
| `image_output` | `external` | Obsidian이 보기 좋은 별도 파일 참조 방식 |
| `markdown_page_separator` | `\n\n---\n<!-- page %page-number% -->\n\n` | 페이지 경계 추적용. 사용자가 원치 않으면 None |

**경로 수집 시 주의**: 사용자가 한 번에 N개의 PDF를 지칭하면 반드시 한 번의 `convert()` 호출에 모두 묶어 전달한다. 매 호출마다 JVM이 새로 뜨기 때문에 N번 호출하면 N배 느리다.

### 2단계: 변환 실행

`scripts/pdf_to_md.py` 래퍼를 사용한다. 직접 Python을 호출하는 것보다 안전:

```bash
C:/Users/JHKIM/miniconda3/python C:/Users/JHKIM/.claude/skills/pdf-to-md/scripts/pdf_to_md.py \
  --input "D:/Zettelkasten/References/paper.pdf" \
  --output "D:/Zettelkasten/References/" \
  --format markdown-with-images
```

다중 입력:
```bash
C:/Users/JHKIM/miniconda3/python C:/Users/JHKIM/.claude/skills/pdf-to-md/scripts/pdf_to_md.py \
  --input "a.pdf" "b.pdf" "folder/" \
  --output "out/"
```

### 3단계: 산출물 검증·후처리

변환 후 출력 MD를 `Read`로 일부 확인한다 (첫 50줄 + 마지막 50줄). 다음을 점검:

- **빈 출력**: 스캔 PDF일 가능성 → OCR 필요 (하이브리드 모드 또는 외부 OCR 권장)
- **깨진 문자**: 한글이 `?`나 공백으로 → `--keep-line-breaks` + `--use-struct-tree` 시도
- **표가 본문에 흘러내림**: `--table-method cluster` 재시도
- **헤더/푸터가 본문에 섞임**: 기본은 제거됨. 포함 원하면 `--include-header-footer`

Obsidian Vault에 넣을 때는 첫 줄에 YAML frontmatter를 사용자가 원하면 추가한다 (`--obsidian` 플래그가 자동 처리).

## 주요 옵션 (자주 쓰는 것만)

| 옵션 | 언제 켜는가 |
|---|---|
| `--format markdown-with-images` | 그림이 중요한 논문/보고서 (기본) |
| `--format markdown` | 텍스트만 필요, 가장 가볍다 |
| `--pages "1-3,5"` | 일부 페이지만 |
| `--password X` | 암호화된 PDF |
| `--use-struct-tree` | Tagged PDF (잘 만들어진 학술지 PDF), 읽기 순서 정확도↑ |
| `--table-method cluster` | 테두리 없는 표가 많을 때 |
| `--keep-line-breaks` | 줄바꿈을 원본 그대로 (시·코드·운문) |
| `--sanitize` | 이메일·전화·신용카드 마스킹 |
| `--obsidian` | YAML frontmatter 자동 삽입 (래퍼 전용 옵션) |

전체 옵션은 `references/options-cheatsheet.md` 참조.

## Obsidian 통합 패턴

사용자 환경: 원문 PDF는 `D:/Zettelkasten/References/`, 노트는 같은 폴더 또는 별도 위치.

권장 출력 구조:
```
D:/Zettelkasten/References/
├── paper.pdf                  # 원본
├── paper.md                   # 변환된 MD
└── paper_images/              # --format markdown-with-images 시
    ├── img-1.png
    └── img-2.png
```

`--obsidian` 플래그를 켜면 다음 frontmatter가 삽입된다:

```yaml
---
source: "paper.pdf"
converted: 2026-04-13
tool: opendataloader-pdf
type: pdf-import
---
```

사용자가 원본 PDF에 대한 위키링크를 원하면 본문 첫 줄에 `[[paper.pdf]]`를 추가한다.

## Troubleshooting

**`java not found`**: Java 미설치. 위 "전제 조건" 참조.

**JVM 시작이 느림 (5–10초)**: 정상. JVM 콜드 스타트. 같은 호출에 파일을 묶어라.

**Encoding 깨짐**: Windows 콘솔 출력 시 발생할 수 있음. 래퍼 스크립트가 UTF-8을 강제한다.

**스캔 PDF가 빈 MD로 나옴**: 로컬 모드는 디지털 PDF만 처리. OCR은 hybrid 모드(별도 서버 필요)나 외부 도구(Tesseract 등) 사용. 이 스킬 범위 밖.

**한 페이지가 통째로 빠짐**: 보안 설정으로 텍스트 추출이 막힌 PDF. `--password`로도 안 풀리면 원본을 다시 받아라.

## 스킬 범위 밖

- OCR (스캔 PDF → 텍스트): hybrid 모드는 별도 서버 구동 필요
- PDF 생성/편집: 이 스킬은 read-only
- Markdown → PDF 역변환
- DOCX/PPTX 등 다른 포맷 변환

## 빠른 검증 (스킬 수정 후 자기 점검용)

```bash
# 샘플 PDF로 확인
C:/Users/JHKIM/miniconda3/python C:/Users/JHKIM/.claude/skills/pdf-to-md/scripts/pdf_to_md.py \
  --input "C:/Users/JHKIM/opendataloader/samples/pdf/lorem.pdf" \
  --output "C:/Users/JHKIM/Claude_work/_pdf_test/" \
  --format markdown
```

성공 시: `C:/Users/JHKIM/Claude_work/_pdf_test/lorem.md` 생성, 본문 첫 줄에 "Lorem ipsum"이 보임.
