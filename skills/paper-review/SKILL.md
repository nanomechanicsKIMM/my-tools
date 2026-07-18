---
name: paper-review
description: "학술 논문 리뷰 스킬. 논문(docx/pdf)을 분석하고 참고문헌 PDF를 자동 다운로드하여 체계적 리뷰를 수행한다. '논문 리뷰', 'paper review', '논문 검토', '논문 피드백', '참고문헌 확인', 'review paper', '서론 리뷰', 'introduction review' 등의 키워드가 나오면 이 스킬을 사용할 것."
---

# Paper Review Skill

학술 논문을 체계적으로 리뷰하는 스킬. 논문 변환 → 참고문헌 수집 → 가이드라인 기반 리뷰의 3단계 파이프라인.

## Workflow

### Phase 1: 문서 변환 (Document Conversion)
입력 문서(docx/pdf)를 markdown으로 누락 없이 완전 변환한다.

**입력**: `.docx` 또는 `.pdf` 파일
**출력**: `{작업폴더}/manuscript.md`

**실행**:
```bash
PYTHONUTF8=1 python3 {skill_dir}/scripts/convert_to_md.py --input <파일경로> --output <출력폴더>
```

**변환 원칙**:
- 본문 텍스트: 단락 구조, 강조(bold/italic) 보존
- 수식: LaTeX 형식으로 변환 (`$...$`, `$$...$$`)
- 표: markdown 표로 변환
- 그림: 캡션과 번호를 `![Figure N: caption]()` 형식으로 보존
- 참고문헌: 원본 번호 체계 유지
- 섹션 구조: heading level 보존

### Phase 2: 참고문헌 수집 (Reference Collection)
본문에서 참고문헌의 DOI를 추출하고 PDF를 자동 다운로드한다.

**입력**: `manuscript.md` (Phase 1 출력)
**출력**:
- `{작업폴더}/refs/ref_NN.pdf` — 다운로드된 PDF들
- `{작업폴더}/refs/download_report.md` — 다운로드 결과 보고서 (실패 건 수동 링크 포함)

**실행**:
```bash
PYTHONUTF8=1 python3 {skill_dir}/scripts/download_refs.py --input <manuscript.md> --output <refs폴더>
```

**다운로드 우선순위** (시행착오를 통해 검증된 순서):
1. Semantic Scholar API — Open Access PDF URL 확인
2. Publisher 직접 접근 — DOI resolve 후 출판사별 PDF URL 패턴 (기관 구독 활용)
3. Google Scholar — [PDF] 링크 탐색
4. 위 3단계 실패 시 → **paper-pdf-download 스킬로 위임** (실제 인증 브라우저로 봇차단·기관구독 저널 수집; 페이월 우회 사이트는 사용하지 않음)

**주요 출판사별 PDF URL 패턴**:
- Nature: `{url}.pdf`
- APS (PhysRevX): `/abstract/` → `/pdf/`
- PNAS: `/doi/pdf/{doi}`
- Science/Science Advances: `/doi/` → `/doi/pdf/`
- Elsevier/ScienceDirect: `/pii/{id}/pdfft`
- IEEE: `/stamp/stamp.jsp?arnumber={id}` → iframe 내 PDF
- AIP/JASA: `/doi/` → `/doi/pdf/`

**실패 처리**:
- 다운로드 실패 시 `download_report.md`에 수동 다운로드 링크 정리
- 사용자에게 수동 다운로드 안내 후 Phase 3로 자동 진행

### Phase 3: 논문 리뷰 (Paper Review)
가이드라인에 따라 체계적으로 리뷰를 수행한다.

**입력**: `manuscript.md` + `refs/*.pdf`
**출력**: `{작업폴더}/review_report.md`

**리뷰 절차 및 모델 배정**:

#### Step 3-1: 참고문헌 그룹 분류 — `haiku`
- manuscript.md의 인용 패턴을 분석하여 참고문헌을 주제/역할별 그룹으로 분류
- 각 그룹에 포함된 DOI 번호와 본문에서의 인용 맥락(어떤 주장의 근거인지)을 정리
- 단순 분류 작업이므로 haiku로 충분

#### Step 3-2: 그룹별 참고문헌 분석 — `sonnet` (병렬)
- 각 그룹당 1개 에이전트를 병렬 실행하여 PDF 내용을 분석
- 에이전트당 PDF 4개 이하 (초과 시 그룹 분할)
- 각 논문에 대해:
  - 핵심 기여 요약 (2-3문장)
  - 본문 인용 서술의 정확성 검증
  - 누락되거나 오특성화된 사항 식별
- PDF 독해 + 사실 대조 작업으로 sonnet이 비용 대비 최적

#### Step 3-3: 종합 리뷰 보고서 작성 — `opus`
- Step 3-2의 모든 분석 결과를 종합
- 가이드라인 5개 항목에 따라 구조화된 리뷰 보고서 작성
- 심각도 분류 (CRITICAL / MAJOR / MINOR) 판정
- 논문 전체의 논리적 공정성, 독창성 주장의 타당성 평가
- 고차원 추론과 종합적 판단이 필요하므로 opus 사용

#### 모델 배정 요약

| Step | 작업 | 모델 | 근거 |
|------|------|------|------|
| 3-1 | 참고문헌 그룹 분류 | **haiku** | 단순 패턴 분류, 토큰 최소화 |
| 3-2 | PDF 읽기 + 인용 검증 | **sonnet** | 기술 문서 독해 + 사실 대조, 병렬 4-5개 |
| 3-3 | 종합 리뷰 보고서 | **opus** | 다관점 종합, 공정성 판단, 심각도 분류 |

**비용 최적화 포인트**:
- Step 3-2가 토큰 소비의 대부분 (PDF 전문 읽기) → sonnet으로 비용 절감
- Step 3-1은 토큰 소비 최소 → haiku로 추가 절감
- Step 3-3만 opus 사용 → 핵심 판단에 집중 투자
- Rate limit 대응: sonnet 에이전트 실패 시 그룹을 2개로 분할하여 재실행

---

## 가이드라인

리뷰 가이드라인은 `references/guideline.md`에 정의되어 있으며, 사용자가 수시로 업데이트할 수 있다. 리뷰 수행 시 항상 최신 가이드라인을 읽어서 적용한다.

---

## 파일 구성

```
paper-review/
├── SKILL.md                          ← 이 파일
├── scripts/
│   ├── convert_to_md.py              ← docx/pdf → markdown 변환
│   └── download_refs.py              ← DOI 추출 + PDF 다운로드
└── references/
    └── guideline.md                  ← 리뷰 가이드라인 (업데이트 가능)
```

## 의존성

- python-docx (docx 읽기)
- PyMuPDF / fitz (pdf 읽기)
- requests (HTTP)
- re (DOI 추출)

## 주의사항

- Windows 환경: 모든 Python 실행 시 `PYTHONUTF8=1` 필수
- SSL 인증서 경고: `urllib3.disable_warnings()` + `verify=False`
- 에이전트 병렬 실행 시 rate limit 주의: 실패 시 그룹 분할 후 재실행
