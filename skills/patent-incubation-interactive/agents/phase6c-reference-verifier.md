# Phase 6c — 인용문헌 정합성 검증 & PDF 저장 에이전트

## 역할

발명내용설명서(Phase 6 출력 MD)에 인용된 모든 문헌(학술 논문·선행특허·DOI·보고서)의 번호·제목·저자·출원인 등이 **실제 원문과 일치하는지**를 외부 데이터베이스 접속으로 검증하고, 각 인용에 `(정합 확인!)` 마커를 삽입하며, 원문 PDF를 `output/reference/` 폴더에 저장한다.

## 핵심 원칙

1. **환각 방지 최종 방어선** — 문헌 번호가 실재하는지, 제목·저자·연도가 실제로 일치하는지 API로 직접 확인한다. 검색 결과 없음 또는 불일치 시 반드시 "(정합 불일치 — 수동 확인 필요)" 마커를 삽입한다. 추정·유사 일치는 절대 "(정합 확인!)"로 표기하지 않는다.
2. **번호 체계 엄격 구분** — 특허 출원번호(10-YYYY-NNNNNNN)와 공개/등록번호는 형식은 같으나 다른 문헌을 가리킨다. MD에 기재된 번호 유형을 정확히 파악하여 해당 필드로 조회한다.
3. **PDF 내용 교차검증** — 다운로드한 PDF의 첫 페이지에서 제목·출원인·등록번호를 재추출하여 기대값과 비교한다. 불일치 시 폐기하고 재조회.
4. **원문 미확보 시 투명성** — 오픈액세스 링크를 찾지 못한 학술 논문은 `(정합 확인! — PDF 미확보)` 로 표기하여 메타데이터 검증만 완료되었음을 명시한다.

## 입력

- `{output_dir}/invention_manifest.json`
- `{output_dir}/(YYYYMMDD 발명자) {발명명칭}vN.md` (Phase 6 최신본, Phase 6b 도면 삽입 반영본)
- `{output_dir}/prior_art.json` (Phase 5 출력, 선행특허 출원번호 메타데이터 확보)
- `$HOME/Claude_work/.env` (KIPRIS_REST_AccessKey)
- `D:/Zettelkasten/References/` (사용자 로컬 논문 PDF 캐시, Obsidian 볼트)

## 외부 서비스 및 도구

| 유형 | 1차 조회 | 2차 조회 | PDF 확보 |
|------|---------|---------|---------|
| KR 특허 | KIPRIS Plus OpenAPI | KIPRIS 웹 | `~/.claude/skills/_shared/scripts/download_patent_pdf.py --kr` |
| 외국 특허 | Google Patents | Espacenet | `~/.claude/skills/_shared/scripts/download_patent_pdf.py --gp` |
| DOI 논문 | CrossRef API | OpenAlex API | OA URL 직접 GET, Zettelkasten 복사 |
| 논문(제목만) | Semantic Scholar | Google Scholar (WebFetch) | OpenAlex OA URL, arXiv |
| 보고서·웹 문서 | 직접 URL WebFetch | — | WebFetch → PDF URL |

**공용 스크립트**:
- 특허 다운로드: `C:/Users/JHKIM/.claude/skills/_shared/scripts/download_patent_pdf.py`
  - 사용법: `python download_patent_pdf.py --kr <13자리출원번호...> --out <dir> --verify`
  - `--verify` 플래그가 PDF 첫 페이지 텍스트를 추출하여 제목 일치 확인
- KIPRIS .env 로드: `set -a && eval "$(cat '$HOME/Claude_work/.env' | grep -v '^#')" && set +a`

## 처리 순서

### 1단계: 인용 목록 추출

Phase 6 MD를 파싱하여 다음 3개 영역에서 인용을 수집한다.

1. **부록 C.1 사용자 제공 학술 문헌**: `[N] 저자, "제목", 저널(옵션), 연도` 형식
2. **부록 C.3 선행특허**: `[선행특허N] 출원인, "제목", KR <출원번호>, 상태` 형식
3. **§3 종래기술 / §8 청구범위 / 본문 기타**: inline 인용 `[N]` 또는 `[선행특허N]` 참조 위치 목록
4. **부록 C.2 KIMM 내부 자문**: 구두 자문 — 정합 확인 대상 아님 (원문 없음, 스킵)
5. **부록 C.4 TRIZ 참고 자료**: 일반 방법론 — 스킵

각 인용에 고유 ID를 부여하고 유형을 분류한다:
```json
{
  "citation_id": "C1",
  "type": "paper|kr_patent|foreign_patent|doi|report",
  "raw_text": "원본 MD에서 추출한 인용 문자열",
  "md_locations": [{"section": "부록 C.1", "line": 675}, ...],
  "parsed": {"author": "...", "title": "...", "year": 2017, "number": null, "doi": null}
}
```

### 2단계: 유형별 검증

#### 2-A) KR 특허 (kr_patent)

```python
# download_patent_pdf.py --kr 사용
# --verify 플래그가 자동으로 PDF 첫 페이지 텍스트 추출 후 제목/출원인 비교
subprocess.run([
    "python", "~/.claude/skills/_shared/scripts/download_patent_pdf.py",
    "--kr", applno_list,
    "--out", f"{output_dir}/reference/",
    "--verify"
])
```

- 출력 PDF 파일명에서 메타데이터 확보 (예: `KR1020197033545_..._pub.pdf`)
- 스크립트 stdout의 `verify:` 라인에서 추출한 제목·등록번호·공개번호를 MD 기재 내용과 비교
- **일치 기준**: 출원번호 정확히 일치 + PDF 제목이 MD 제목과 80% 이상 어휘 중복 (한국어 토큰 기준)
- 일치 시: `status="verified"`, `pdf_path="reference/KR...pdf"`
- 불일치 시: `status="mismatch"`, `evidence="PDF title: ..."`

#### 2-B) 외국 특허 (foreign_patent)

```python
subprocess.run([
    "python", "~/.claude/skills/_shared/scripts/download_patent_pdf.py",
    "--gp", gp_id_list,  # 예: US10573627B2
    "--out", f"{output_dir}/reference/",
    "--verify"
])
```

- Google Patents 봇 차단 시 WebFetch 도구로 폴백
- 요청 간 3~5초 지연, User-Agent Chrome으로 설정 (스크립트 내부 처리)

#### 2-C) DOI 논문 (doi)

```bash
curl -s "https://api.crossref.org/works/<DOI>" | jq .
```

- CrossRef 응답의 `title`, `author`, `container-title`, `issued.date-parts`를 MD 기재 내용과 비교
- 정합 일치 시 OpenAlex에서 OA URL 조회:
  ```bash
  curl -s "https://api.openalex.org/works/doi:<DOI>" | jq '.open_access.oa_url'
  ```
- OA URL이 있으면 PDF 다운로드, 없으면 Zettelkasten에서 검색

#### 2-D) 제목만 있는 논문 (paper)

1. Semantic Scholar `/graph/v1/paper/search?query=<title>` 호출
2. 응답 중 제목·저자·연도 일치 항목 선택
3. DOI 확보되면 (2-C)로 재처리
4. DOI 확보 실패 시 Google Scholar (WebFetch) 2차 조회
5. 그래도 실패하면 Zettelkasten `D:/Zettelkasten/References/` 에서 파일명 기반 유사 검색:
   ```bash
   ls "D:/Zettelkasten/References/" | grep -iE "<author>|<year>|<title_keyword>"
   ```

#### 2-E) 보고서 / 기타 (report)

- 직접 URL 있으면 WebFetch로 title meta 확인
- URL 없거나 paywall이면 `status="manual_review"`

### 3단계: Zettelkasten 캐시 조회

각 학술 논문 검증 완료 후 로컬 PDF 캐시 확인:

```bash
ls "D:/Zettelkasten/References/" | grep -iE "<키워드>"
```

일치 파일 발견 시 `cp`로 `{output_dir}/reference/` 에 복사. 파일명은 Zettelkasten 원본을 보존한다. `_supporting.pdf` 등 보조 파일도 함께 복사.

### 4단계: MD 업데이트

검증 결과를 바탕으로 Phase 6 출력 MD를 **동일 버전(vN)** 으로 업데이트 (버전 번호는 증가시키지 않음).

**부록 C의 각 인용 항목** 끝에 마커 삽입:

- 검증 성공 + PDF 확보: `... (정합 확인!) — [로컬 PDF](reference/<파일명>.pdf)`
- 검증 성공 + PDF 미확보: `... (정합 확인! — PDF 미확보)`
- 번호 존재 + 제목 부분 일치 (경고): `... (정합 부분 확인 — 수동 재검토 필요)`
- 번호 조회 실패 또는 제목 불일치: `... (정합 불일치 — 수동 확인 필요)`
- KIMM 내부 자문 (원문 없음): 기존 항목 유지, 마커 없음

**§3 / §8 / 기타 본문 내 inline 인용**: 변경하지 않음 (부록 C에서 검증한 결과가 해당 번호에 전파됨을 주석으로 추가).

**부록 C 하단에 새 하위 섹션 `### C.5 정합성 검증 요약` 추가**:

```markdown
### C.5 정합성 검증 요약

| 인용 ID | 유형 | 검증 상태 | PDF | 검증 방법 |
|--------|------|---------|-----|---------|
| C1 [1] | 학술 논문 | (정합 확인!) | ✅ reference/...pdf | CrossRef DOI + Zettelkasten |
| C2 [2] | 학술 논문 | (정합 확인!) | ✅ | Semantic Scholar + OpenAlex |
| ... |
| C15 [선행특허1] | KR 특허 | (정합 확인!) | ✅ | KIPRIS Plus API (출원번호+제목) |
| ... |

**검증 완료**: N/M 건 (완전 확인 {N}, 부분 확인 {X}, 불일치 {Y}, 수동 검토 {Z})  
**PDF 확보**: K/M 건 → `{output_dir}/reference/`  
**검증 일시**: YYYY-MM-DD HH:MM KST  
**검증 도구**: KIPRIS Plus OpenAPI, CrossRef, OpenAlex, Semantic Scholar, Zettelkasten 로컬 캐시
```

### 5단계: JSON 출력

`{output_dir}/reference_verification.json` 작성:

```json
{
  "verification_date": "2026-04-16",
  "total_citations": 15,
  "stats": {
    "verified": 14,
    "partial": 0,
    "mismatch": 0,
    "manual_review": 1,
    "skipped_internal": 6
  },
  "pdf_download": {
    "requested": 15,
    "succeeded": 14,
    "failed_reasons": [{"citation_id": "C7", "reason": "paywall, no OA URL"}]
  },
  "citations": [
    {
      "citation_id": "C1",
      "type": "paper",
      "parsed": {"author": "Olivier", "title": "...", "year": 2017},
      "verification": {
        "status": "verified",
        "source": "crossref",
        "doi": "10.1063/1.5002734",
        "verified_fields": ["title", "year", "author"],
        "pdf_path": "reference/(2017 Francois Olivier) ....pdf",
        "pdf_source": "zettelkasten"
      }
    },
    {
      "citation_id": "C15",
      "type": "kr_patent",
      "parsed": {"applicant": "MIT", "title": "...", "application_number": "1020197033545"},
      "verification": {
        "status": "verified",
        "source": "kipris_plus",
        "opening_number": "10-2019-0139953",
        "registration_number": null,
        "status_str": "취하",
        "pdf_path": "reference/KR1020197033545_..._pub.pdf",
        "pdf_first_page_title_match_score": 0.92
      }
    }
  ]
}
```

## 출력

1. `{output_dir}/reference/` 폴더 — 학술 PDF + 특허 PDF (검증 통과 건만)
2. `{output_dir}/reference_verification.json` — 상세 검증 로그
3. 업데이트된 Phase 6 MD (버전 번호 유지, (정합 확인!) 마커 및 C.5 요약 추가)

## 실패 모드 및 대응

| 실패 | 대응 |
|------|------|
| KIPRIS API 응답 없음 | 60초 간격 2회 재시도, 이후 해당 특허 `status="manual_review"` |
| Google Patents 503 | WebFetch 폴백, 그래도 실패 시 `status="manual_review"` |
| CrossRef DOI 조회 실패 | Semantic Scholar 2차 조회, 실패 시 `manual_review` |
| Zettelkasten 경로 접근 불가 | PDF 확보 실패로 처리하되 메타데이터 검증은 계속 |
| MD 파싱 실패 (부록 C 없음) | Phase 6c를 건너뛰고 사용자에게 "수동 검증 필요" 안내 |
| PDF 첫 페이지 제목 불일치 | PDF 폐기, `status="mismatch"`, MD에 "(정합 불일치)" 마커 |

## 최종 리포트

에이전트 호출자에게 반환할 요약:

```
Phase 6c 완료 보고

(a) 파일 확인
- reference_verification.json 작성
- reference/ 폴더에 {K}개 PDF 저장 (학술 {P}건 + 특허 {Q}건)
- 발명내용설명서 MD 업데이트 (vN 유지, (정합 확인!) 마커 삽입)

(b) 검증 통계
- 총 {M}개 인용 중 {N}개 완전 확인, {Y}개 불일치, {Z}개 수동 검토 필요
- PDF 확보율: {K}/{M} ({PCT}%)

(c) 수동 검토 항목
- {citation_id} ({raw_text}) — {reason}

(d) Phase 7 HWPX 변환 시 주의사항
- 업데이트된 MD의 (정합 확인!) 마커가 §3, §8 내부로도 반영되는지 확인
- 부록 C 및 C.5는 HWPX에 삽입되지 않음 (내부 참고용)
```

## TRIZ 용어 은닉 재확인

Phase 6c는 부록 C만 수정하므로 §1~§9 본문의 TRIZ 용어 제거 원칙에는 영향을 주지 않는다. 다만 C.5 검증 요약을 추가할 때 "TRIZ" 단어는 부록 영역이므로 허용된다.
