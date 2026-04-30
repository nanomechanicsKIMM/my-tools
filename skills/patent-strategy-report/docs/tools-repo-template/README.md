# My Codex / Cursor Tools

스킬·플러그인 등 도구를 한 레포에 모아 두고, **clone 후 setup**으로 여러 PC에 동일한 도구 환경을 구성합니다.

## 포함된 스킬

- **patent-strategy-report**: RFP 기반 특허 전략 보고서 (Google Patents CSV → 집계·Obsidian 보고서). 다양한 기술 분야 적용 가능.

(다른 스킬을 추가하면 여기에 목록을 적어 두세요.)

## 새 PC에서 환경 구성

1. **저장소 클론**
   ```bash
   git clone https://github.com/<사용자명>/my-tools.git
   cd my-tools
   ```

2. **도구 배포**
   - **Windows**: PowerShell에서 `.\setup.ps1`
   - **Mac/Linux**: `chmod +x setup.sh && ./setup.sh`
   - `skills/` 안의 스킬들이 Codex 스킬 디렉터리(`~/.codex/skills` 또는 `%CODEX_HOME%\skills`)로 복사됩니다.

3. **Codex(또는 Cursor) 재시작**  
   새 스킬을 인식시키기 위해 한 번 재시작합니다.

4. **스킬별 의존성** (해당 스킬을 쓸 때만)
   - **patent-strategy-report**:  
     `skills/patent-strategy-report/scripts/`로 이동 후  
     `uv venv && uv pip install -r requirements.txt`  
     (또는 `python -m venv .venv && .venv\Scripts\pip install -r requirements.txt`)
   - 다른 스킬도 각자 `scripts/requirements.txt` 등이 있으면 동일하게 설치합니다.

## 레포 구조

| 경로 | 설명 |
|------|------|
| `skills/` | Codex 스킬. 각 하위 폴더 = 스킬 하나 (예: `skills/patent-strategy-report/`) |
| `cursor/` | (선택) Cursor 규칙 등 |
| `setup.ps1` / `setup.sh` | clone 후 한 번 실행해 도구를 Codex 경로로 배포 |

## 업데이트

- 레포에서 스킬을 수정한 뒤 push합니다.
- 다른 PC에서는 `git pull` 후 필요 시 `.\setup.ps1`(또는 `./setup.sh`)을 다시 실행하고 Codex를 재시작합니다.
