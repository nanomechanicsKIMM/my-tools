# Phase 6c — 인용문헌 정합성 검증 & PDF 저장 에이전트

## 역할

발명내용설명서(Phase 6 출력 MD)에 인용된 모든 문헌(학술 논문·선행특허·DOI·보고서)의 번호·제목·저자·출원인 등이 **실제 원문과 일치하는지**를 외부 데이터베이스 접속으로 검증하고, **참고문헌 리스트를 검증된 실제 문헌의 순수 서지만 남도록 정리(미검증 제거 + 본문 inline 인용 gap 없이 재번호)** 하며, 검증 이력은 `reference_verification.json`에 기록하고 원문 PDF를 `output/reference/` 폴더에 저장한다. **리스트에는 마커·편집문구를 넣지 않는다.**

## 핵심 원칙

1. **환각 방지 최종 방어선** — 문헌 번호가 실재하는지, 제목·저자·연도가 실제로 일치하는지 API로 직접 확인한다. 검색 결과 없음 또는 불일치 문헌은 **리스트에서 제거**하고 본문 inline 인용을 재번호한다. 추정·유사 일치를 검증된 것으로 리스트에 남기지 않는다. 제거·정정 이력은 reference_verification.json에만 기록한다.
2. **번호 체계 엄격 구분** — 특허 출원번호(10-YYYY-NNNNNNN)와 공개/등록번호는 형식은 같으나 다른 문헌을 가리킨다. MD에 기재된 번호 유형을 정확히 파악하여 해당 필드로 조회한다.
3. **PDF 내용 교차검증** — 다운로드한 PDF의 첫 페이지에서 제목·출원인·등록번호를 재추출하여 기대값과 비교한다. 불일치 시 폐기하고 재조회.
4. **원문 미확보 시** — 메타데이터(번호·제목·저자·연도)가 검증되면 리스트에 남긴다. PDF 확보 여부는 reference_verification.json의 pdf_path 필드로만 구분하고, 리스트에는 표기하지 않는다.

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

> [!important] 인용 위치 비의존 (2026-07 신설)
> 참고문헌은 부록 C가 아니라 **§9** 또는 다른 섹션에 있을 수 있다. 특정 섹션에만
> 의존하지 말고, MD 전체에서 `- [N] ...` 형식의 참고문헌 리스트 항목을 모두 수집한다.
> (실제 사고: 참고문헌이 §9에 있었는데 부록 C만 찾다가 Phase 6c가 통째로 스킵됨.)

Phase 6 MD를 파싱하여 아래 영역에서 인용을 수집한다. **없는 섹션은 건너뛰되, `- [N]`
리스트가 있는 곳은 위치와 무관하게 모두 대상에 포함한다.**

1. **참고문헌 리스트** (`§9 참고문헌` 또는 `부록 C.1/C.3`): `[N] 저자, "제목", 저널/출원번호, 연도` 형식 — 학술·특허 모두
2. **§3 종래기술 / §8 청구범위 / 본문 기타**: inline 인용 `[N]` 참조 위치 목록
3. **KIMM 내부 자문**: 구두 자문 — 정합 확인 대상 아님 (원문 없음, 스킵)
4. **TRIZ 참고 자료**: 일반 방법론 — 스킵

각 참고문헌의 `citation_id` 는 MD의 `[N]` 번호와 **정확히 일치**시킨다(verify_citations.py 대조 기준).

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

### 4단계: MD 참고문헌 정리 (클린 리스트)

검증 결과를 바탕으로 Phase 6 출력 MD를 **동일 버전(vN)** 으로 업데이트한다(버전 번호 미증가). 마커·편집문구는 절대 삽입하지 않는다.

1. **검증된 문헌만 리스트에 남긴다.** 정정이 필요한 서지는 정정된 값으로 교체(정정 표기 없이).
2. **미검증·실재 불명·중복 문헌은 리스트에서 삭제**한다.
3. 삭제로 생긴 번호 공백을 없애기 위해 참고문헌을 `[1]~[N]`로 **재번호**하고, 그에 맞춰 §3·§4·§5·§6·§7·§8·표·부록의 **본문 inline `[N]` 인용을 일괄 갱신**한다(참고문헌 리스트 줄은 재작성으로 대체).
4. 리스트 형식: `- [N] 저자, "제목", 저널 권(호), 페이지 (연도). DOI/KIPRIS` — 순수 서지만.
5. KIMM 내부 자문(구두)은 리스트에 넣지 않는다.

검증/정정/제거 이력, PDF 확보 여부(pdf_path), 재번호 맵(renumber_map)은 모두 `reference_verification.json`에만 기록한다. MD에는 검증 요약 섹션을 만들지 않는다.

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

### 6단계: 강제 게이트 실행 (필수)

MD와 reference_verification.json 작성 완료 후, 반드시 게이트를 실행하여 마커-레코드
정합을 기계적으로 확인한다:

```bash
PYTHONUTF8=1 python {SKILL_ROOT}/scripts/verify_citations.py \
  --md "{output_dir}/{발명명칭}vN.md" \
  --verification "{output_dir}/reference_verification.json"
```

- exit 0: 통과 → Phase 7 진행
- exit 1: 편집문구 잔존/미검증 문헌 존재/removed 재등장 → 리스트 정리(제거·재번호) 후 재실행
- exit 2: 검증 파일 부재/참고문헌 미검출 → Phase 6c 미완료 상태이므로 처음부터 재실행

**검증되지 않은 문헌은 리스트에 남기지 않고 제거한다(마커로 표기하지 않음). 리스트에 편집문구가
남거나 미검증 문헌이 있으면 이 게이트가 exit 1로 잡아낸다.**

## 출력

1. `{output_dir}/reference/` 폴더 — 학술 PDF + 특허 PDF (검증 통과 건만)
2. `{output_dir}/reference_verification.json` — 검증 audit(status verified/corrected/removed, renumber_map)
3. 정리된 Phase 6 MD (버전 번호 유지): 참고문헌=검증 순수 서지, 마커 없음, 미검증 제거 후 재번호
4. verify_citations.py exit 0 확인 (게이트 통과 증빙)

## 실패 모드 및 대응

| 실패 | 대응 |
|------|------|
| KIPRIS API 응답 없음 | 60초 간격 2회 재시도, 이후 해당 특허 `status="manual_review"` |
| Google Patents 503 | WebFetch 폴백, 그래도 실패 시 `status="manual_review"` |
| CrossRef DOI 조회 실패 | Semantic Scholar 2차 조회, 실패 시 `manual_review` |
| Zettelkasten 경로 접근 불가 | PDF 확보 실패로 처리하되 메타데이터 검증은 계속 |
| MD 파싱 실패 (참고문헌 리스트 없음) | Phase 6c를 건너뛰고 사용자에게 "수동 검증 필요" 안내 |
| PDF 첫 페이지 제목 불일치 | PDF 폐기, `status="mismatch"`(removed 처리), 해당 문헌 리스트에서 제거 + 본문 재번호 |

## 최종 리포트

에이전트 호출자에게 반환할 요약:

```
Phase 6c 완료 보고

(a) 파일 확인
- reference_verification.json 작성 (검증 audit + renumber_map)
- reference/ 폴더에 {K}개 PDF 저장 (학술 {P}건 + 특허 {Q}건)
- 발명내용설명서 MD 참고문헌 정리 (vN 유지, 검증 순수 서지만, 미검증 제거 후 재번호)

(b) 검증 통계
- 총 {M}개 인용 중 {N}개 검증(verified/corrected), {R}개 제거(removed)
- 최종 리스트 {F}건, PDF 확보율: {K}/{F}

(c) 제거된 문헌
- {citation_id} ({raw_text}) — {reason}

(d) Phase 7 HWPX 변환 시 주의사항
- verify_citations.py exit 0 확인(리스트 클린 + 검증 매칭)
- 본문 inline [N] 재번호가 §3~§8·표·부록에 일관 적용됐는지 확인
```

## TRIZ 용어 은닉 재확인

Phase 6c는 참고문헌 리스트 정리와 inline 인용 번호 갱신만 수행하므로 §1~§9 본문의 TRIZ 용어 제거 원칙에 영향을 주지 않는다(서지·번호 외 본문 문구는 변경하지 않음).
