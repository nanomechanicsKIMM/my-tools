---
title: "재사용 레퍼런스 파일 출처 기록"
created: 2026-04-11
tags: [reference, source, patent-draft-review, sync]
---

# 재사용 레퍼런스 파일 출처

> [!note] 목적
> 본 파일은 `patent-draft-review/reference/` 디렉토리 내 **외부 복사 파일**의 원본 출처와 복사 시점 hash를 기록한다. 원본이 갱신되었는지 주기적으로 확인하여 drift를 방지한다 (R-15 완화).

## TRIZ 레퍼런스 (patent-incubation-auto 스킬에서 복사)

| 파일 | 원본 경로 | 복사일 | 원본 SHA-256 (앞 16자) |
|------|-----------|--------|------------------------|
| `triz-40-principles.md` | `C:/Users/JHKIM/.claude/skills/patent-incubation-auto/reference/triz-40-principles.md` | 2026-04-11 | `2f0c24bdbc8cfc7d` |
| `triz-contradiction-matrix.json` | `C:/Users/JHKIM/.claude/skills/patent-incubation-auto/reference/triz-contradiction-matrix.json` | 2026-04-11 | `97e4e8d7b7bc7559` |
| `triz-separation-principles.md` | `C:/Users/JHKIM/.claude/skills/patent-incubation-auto/reference/triz-separation-principles.md` | 2026-04-11 | `69e36c3a1e63035f` |

## 동기화 규칙

1. **원본 갱신 감지**: 주기적으로 원본 파일의 SHA-256 해시를 재계산하여 본 파일의 기록과 비교
2. **Drift 발견 시**: 원본을 복사하여 갱신 후 본 파일의 hash를 업데이트
3. **충돌 해결**: 원본이 변경되었고 본 사본도 수정된 경우, 수동으로 merge 필요 (경고 표시)
4. **Windows 환경**: 심볼릭 링크 지원이 제한적이므로 복사 방식 사용 (향후 Windows 10+ 심볼릭 링크 지원 검증 후 전환 가능)

## 동기화 확인 방법

```bash
python -c "
import hashlib
from pathlib import Path
src_dir = Path('C:/Users/JHKIM/.claude/skills/patent-incubation-auto/reference')
for name in ['triz-40-principles.md', 'triz-contradiction-matrix.json', 'triz-separation-principles.md']:
    h = hashlib.sha256((src_dir/name).read_bytes()).hexdigest()[:16]
    print(f'{name}: {h}')
"
```

출력 해시를 본 파일의 기록과 비교하여 일치 여부 확인.

## 신규 패턴 (patent-draft-review 고유)

아래 파일은 본 스킬에서 새로 작성한 것으로 외부 출처가 없다:

| 파일 | 용도 |
|------|------|
| `korean-patent-typo-patterns.md` | 한국 특허 오탈자·부호·수식 패턴 DB (M2) |
| `korean-claim-form-rules.md` | 한국 특허 청구항 형식 규칙 (M3) |
