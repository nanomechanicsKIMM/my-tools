---
title: "Patent Strategy Report Skill – GitHub 배포 및 설치"
created: 2026-03-07
tags: [특허분석, Codex, skill, 설치]
---

# GitHub에 올리고 다른 컴퓨터에 설치하기

이 문서는 **patent-strategy-report** 스킬을 GitHub에 올리고, 다른 PC(또는 Codex가 설치된 환경)에서 사용하는 방법을 안내합니다.

---

## 1. GitHub에 올리기

### 방법 A: 스킬만 별도 저장소로 푸시 (권장)

다른 사람이 **Codex skill-installer**로 한 번에 설치하기 좋습니다. 스킬 폴더 내용을 **저장소 루트**로 둡니다.

1. **새 저장소용 폴더 준비**  
   스킬 폴더를 복사해 저장소 루트로 쓸 디렉터리를 만듭니다.
   ```powershell
   mkdir patent-strategy-report-repo
   cd patent-strategy-report-repo
   ```
   다음 파일·폴더만 복사합니다 (상대 경로: `Patent_Analysis\.codex\skills\patent-strategy-report\` 기준).
   - `SKILL.md`, `README.md`, `reference.md`, `INSTALL.md`, `.gitignore`
   - `templates/` 폴더 전체
   - `scripts/` 폴더 **단, `.venv` 제외** (스크립트 `*.py`와 `requirements.txt`만 복사)
   - `output/` 폴더는 **선택**: 가이드용 `.md`만 넣거나 비우고, `.gitignore`에 따라 `*.csv`, `*.json`은 제외

2. **Git 초기화 및 커밋**
   ```powershell
   git init
   git add .
   git commit -m "Initial: patent-strategy-report skill"
   ```

3. **GitHub에 저장소 생성**  
   GitHub 웹에서 새 저장소 생성 (예: `patent-strategy-report`). **README/ .gitignore 추가하지 말고** 빈 저장소로 만듭니다.

4. **원격 추가 및 푸시**
   ```powershell
   git remote add origin https://github.com/<사용자명>/patent-strategy-report.git
   git branch -M main
   git push -u origin main
   ```

---

### 방법 B: 전체 프로젝트(Patent_Analysis) 저장소에 포함

이미 `Patent_Analysis` 프로젝트를 Git으로 관리한다면, 스킬은 그 안의 한 경로로 올립니다.

1. **프로젝트 루트에서**
   ```powershell
   cd c:\Users\JHKIM\Patent_Analysis
   git init
   ```
   루트에 `.gitignore`가 있다면, 스킬의 `.codex/skills/patent-strategy-report/.gitignore` 규칙(예: `scripts/.venv/`, `output/*.csv`)이 적용되도록 포함해 둡니다.

2. **커밋 및 GitHub 푸시**
   ```powershell
   git add .
   git commit -m "Add patent-strategy-report skill"
   git remote add origin https://github.com/<사용자명>/Patent_Analysis.git
   git branch -M main
   git push -u origin main
   ```
   이 경우 스킬 경로는 **`.codex/skills/patent-strategy-report`** 입니다.

---

## 2. 다른 컴퓨터에 설치하기

다른 PC에서 이 스킬을 쓰는 방법은 두 가지입니다.

### 방법 1: Codex skill-installer 사용 (방법 A 저장소일 때)

**Codex**(및 skill-installer 스킬)가 설치된 환경에서:

- **스킬만 있는 저장소**(방법 A)인 경우, 저장소 **루트가 스킬 폴더**이므로:
  ```bash
  # CODEX_HOME/scripts 또는 skill-installer 스킬 경로에서
  python install-skill-from-github.py --repo <사용자명>/patent-strategy-report --path .
  ```
  또는 URL로:
  ```bash
  python install-skill-from-github.py --url https://github.com/<사용자명>/patent-strategy-report
  ```
  설치 위치: `$CODEX_HOME/skills/patent-strategy-report` (기본값 `~/.codex/skills`).

- **전체 프로젝트**(방법 B)인 경우, 스킬 **하위 경로**를 지정합니다:
  ```bash
  python install-skill-from-github.py --repo <사용자명>/Patent_Analysis --path .codex/skills/patent-strategy-report
  ```

설치 후 **Codex를 한 번 재시작**하면 새 스킬이 인식됩니다.

---

### 방법 2: 수동 clone 후 복사

1. **저장소 클론**
   - 방법 A: `git clone https://github.com/<사용자명>/patent-strategy-report.git`
   - 방법 B: `git clone https://github.com/<사용자명>/Patent_Analysis.git` 후 `Patent_Analysis\.codex\skills\patent-strategy-report` 로 이동

2. **Codex 스킬 디렉터리로 복사**  
   Codex 스킬 기본 경로는 `%USERPROFILE%\.codex\skills`(Windows) 또는 `~/.codex/skills`(Mac/Linux)입니다.  
   환경 변수 `CODEX_HOME`이 있으면 `%CODEX_HOME%\skills`(또는 `$CODEX_HOME/skills`)를 사용합니다.
   ```powershell
   # Windows 예시 (방법 A 클론 폴더가 patent-strategy-report 일 때)
   xcopy /E /I patent-strategy-report %USERPROFILE%\.codex\skills\patent-strategy-report
   ```
   또는 복사할 **내용**만 `%USERPROFILE%\.codex\skills\patent-strategy-report` 에 넣어도 됩니다 (SKILL.md, scripts/, templates/, reference.md 등).

3. **Python 의존성 설치**  
   스크립트를 실행할 PC에서는 다음으로 가상환경과 패키지를 설치합니다.
   ```powershell
   cd %USERPROFILE%\.codex\skills\patent-strategy-report\scripts
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```
   uv 사용 시:
   ```powershell
   cd %USERPROFILE%\.codex\skills\patent-strategy-report\scripts
   uv venv
   uv pip install -r requirements.txt
   ```

4. **동작 확인**  
   RFP 파일과 CSV 경로를 지정해 파이프라인 또는 집계 스크립트를 한 번 실행해 봅니다.
   ```powershell
   python scripts/generate_query.py "경로\RFP.md" --years 10
   ```

---

## 3. 요약

| 단계 | 방법 A (스킬만 저장소) | 방법 B (전체 프로젝트) |
|------|------------------------|------------------------|
| **올리기** | 스킬 내용을 새 repo 루트에 두고 푸시 | Patent_Analysis 안의 `.codex/skills/patent-strategy-report` 로 푸시 |
| **설치(자동)** | `install-skill-from-github.py --repo owner/patent-strategy-report --path .` | `--repo owner/Patent_Analysis --path .codex/skills/patent-strategy-report` |
| **설치(수동)** | `git clone` → `skills/patent-strategy-report` 에 복사 | `git clone` → 해당 경로만 `skills/patent-strategy-report` 로 복사 |
| **의존성** | 두 경우 모두 `scripts/`에서 `pip install -r requirements.txt` 또는 `uv pip install -r requirements.txt` |

다른 컴퓨터에서는 **RFP 마크다운**과 **Google Patents에서 받은 CSV**만 준비하면, 동일한 워크플로로 특허 전략 보고서를 생성할 수 있습니다. 분야는 RFP와 검색어만 바꾸면 됩니다.

---

## 4. 도구 통합 레포지토리로 여러 스킬 한 번에 관리

스킬·플러그인을 **한 GitHub 레포에 모아 두고**, clone 후 setup 한 번으로 여러 PC에 동일한 도구 환경을 구성하는 방법은 [docs/도구_레포지토리_구성_가이드.md](docs/도구_레포지토리_구성_가이드.md)를 참고하세요.  
요약: `my-tools/skills/patent-strategy-report/` 처럼 스킬을 하위 폴더로 넣고, 루트의 `setup.ps1`(또는 `setup.sh`)로 `~/.codex/skills`에 복사하는 방식입니다.
