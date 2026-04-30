# CSV 수동 다운로드 방법 (자동 스크립트 실패 시)

자동 다운로드 스크립트가 Google Patents UI 변경 등으로 실패한 경우, 아래 순서로 **수동**으로 CSV를 받은 뒤 파이프라인을 이어가면 됩니다.

## 1. 검색 URL 열기

아래 URL을 브라우저 주소창에 붙여넣어 엽니다.

```
https://patents.google.com/?q=%28Display+OR+Transformable+OR+Deformation+OR+sensing+OR+User+OR+interface+OR+User+OR+Experience+OR+display+OR+panel+OR+screen+OR+OLED+OR+LED+OR+flexible+OR+stretchable+OR+foldable+OR+rollable+OR+backplane+OR+TFT+OR+pixel%29&after=priority:20110101&before=priority:20251231
```

(동일 URL이 `search_url_15yr.txt` 에도 있습니다.)

## 2. 결과 페이지에서 CSV 다운로드

- 검색 결과가 나온 **위쪽**에 **"Download (CSV)"** 버튼이 있습니다.
- 클릭하면 최대 1,000건이 CSV로 내려받아집니다 (생성에 몇 초 걸릴 수 있음).

## 3. 파일 저장 위치

- 다운로드된 CSV 파일 이름을 **`google_patents_results.csv`** 로 변경합니다.
- 다음 폴더에 넣습니다:
  - **`Patent_Analysis\.codex\skills\patent-strategy-report\output\`**
- 즉, 최종 경로는:
  - `...\output\google_patents_results.csv`

## 4. 다음 단계

CSV를 위 경로에 두었다면, **2번 파이프라인 실행**으로 진행합니다.

```bash
cd .codex\skills\patent-strategy-report\scripts
uv run python run_15yr_pipeline.py "..\output\google_patents_results.csv"
```

---

*자동 스크립트는 Playwright로 "Download (CSV)" 클릭 후 다운로드 이벤트를 기다리는데, Google Patents가 다른 방식으로 CSV를 제공하면 이벤트가 발생하지 않아 실패할 수 있습니다. 수동 다운로드 후 같은 CSV를 사용하면 이후 단계는 동일하게 진행됩니다.*
