---
title: "Windows 11 + Cursor 한글 인코딩 설정 가이드"
created: 2026-03-07
tags: [Windows, Cursor, 인코딩, UTF-8, 한글]
---

# Windows 11 + Cursor 한글 인코딩 근본 해결

한글 경로·출력이 깨질 때 아래 순서대로 적용하면 근본적으로 줄일 수 있다.

---

## 1. Windows 11 시스템 UTF-8 사용 (가장 중요)

시스템 기본 코드페이지를 UTF-8로 두면 터미널·스크립트·Python이 한글을 안정적으로 쓴다.

1. **설정** → **시간 및 언어** → **언어 및 지역**
2. **관리자 옵션** 또는 **다른 날짜, 시간 및 숫자 형식 설정** 클릭
3. **관리** 탭 → **시스템 로캘 변경**
4. **Beta: 세계 언어 지원을 위해 Unicode UTF-8 사용** 체크
5. **확인** 후 재부팅

또는 PowerShell(관리자):

```powershell
# 현재 코드페이지 확인 (65001 = UTF-8)
chcp
# UTF-8로 설정 (현재 세션)
chcp 65001
```

---

## 2. Cursor 설정 (이미 반영됨)

`%APPDATA%\Cursor\User\settings.json` 에 다음이 있으면 된다.

| 설정 | 값 | 설명 |
|------|-----|------|
| `files.encoding` | `"utf8"` | 파일 저장/열기 기본 UTF-8 |
| `files.autoGuessEncoding` | `true` | 열 때 인코딩 추측 |
| `terminal.integrated.env.windows` | `PYTHONIOENCODING`: `"utf-8"`, `PYTHONUTF8`: `"1"` | 터미널에서 실행되는 Python이 UTF-8 사용 |

Cursor **재시작** 후 터미널에서 Python 실행 시 적용된다.

---

## 3. PowerShell 프로필에서 UTF-8 고정 (선택)

Cursor 통합 터미널이 PowerShell일 때, 매번 출력 인코딩을 UTF-8로 맞추려면:

```powershell
# 프로필 경로 확인
$PROFILE
# 프로필이 없으면 생성
if (!(Test-Path $PROFILE)) { New-Item -Path $PROFILE -ItemType File -Force }
# 아래 한 줄 추가
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

---

## 4. Python 스크립트에서 한글 경로 우회

시스템/터미널 설정만으로도 부족할 때(예: CLI 인자로 한글 경로 전달 시 깨짐):

- **한글 경로를 CLI 인자로 넘기지 말고**, 스크립트 안에서 경로를 결정하거나
- **상대 경로·영문만** 사용하거나
- **경로를 파일에 쓰고** 그 파일만 인자로 전달하는 방식을 쓰면 안정적이다.

이 프로젝트의 `run_aggregate_5000_inprocess.py`, `run_top10k_extract_and_report.py` 처럼 **경로를 스크립트 내부에서 지정**하는 방식이 그 예이다.

---

## 5. 요약

| 단계 | 내용 |
|------|------|
| **1** | Windows 11 **Beta: UTF-8 사용** 켜기 → 재부팅 |
| **2** | Cursor `settings.json` 에 `files.encoding`, `terminal.integrated.env.windows` 설정 후 Cursor 재시작 |
| **3** | (선택) PowerShell `$PROFILE` 에 `OutputEncoding` UTF-8 설정 |
| **4** | 한글 경로는 가능하면 CLI 인자 대신 스크립트 내부 경로로 처리 |

1번(시스템 UTF-8)을 적용하면 대부분의 한글 깨짐이 사라진다.
