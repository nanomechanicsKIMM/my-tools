---
name: phase6b-diagram-generator
description: "기술 도면 자동 생성 에이전트. disclosure.md에 Mermaid 인라인 다이어그램 삽입 + HWPX용 PNG 도면 생성."
model: sonnet
---

# Phase 6b: 기술 도면 자동 생성

## 목적

발명내용설명서의 §6(구성)과 §9(추가자료)에 기술된 장치/방법/공정을 시각화한다.

- **disclosure.md** → Mermaid 코드 블록을 인라인 삽입 (Obsidian에서 직접 렌더링)
- **HWPX** → matplotlib로 PNG 파일 생성 (convert_hwpx.py가 §9에 삽입)

### 다이어그램 정책

| 유형 | 도구 | 삽입 위치 |
|------|------|----------|
| 코드화 가능 (흐름도, 구성도, 상태도, 비교표) | **Mermaid** | disclosure.md 인라인 |
| HWPX 삽입용 | **matplotlib PNG** | output/diagrams/*.png |
| 자유 형식 스케치 (사용자 핸드라이팅) | **Excalidraw** | 사용자가 직접 생성 시에만 |

## 입력

1. `disclosure.md` (Phase 6 출력) — §6 구성 내용과 §9 도면 목록
2. `triz_system.json` (Phase 1) — 시스템 구성요소 관계
3. `evaluation.json` (Phase 4) — 상위 IFR 목록
4. `invention_manifest.json` — 발명 기본 정보

## 작업

### Step 1: 도면 목록 결정

`disclosure.md`의 §9(추가자료)에서 도면 목록을 추출한다.
도면 목록이 없으면 §6 내용을 분석하여 필요 도면을 자동 결정한다.

**기본 도면 세트** (특허 유형별):

| 도면 유형 | 방법 특허 | 장비 특허 | 소자 특허 |
|-----------|----------|----------|----------|
| 전체 시스템 구성도 | O | O | - |
| 공정 흐름도 (flowchart) | O | - | - |
| 장치 단면도/구조도 | - | O | - |
| 작동 원리도 (상태 변화) | O | O | - |
| 종래기술 vs 본 발명 비교도 | O | O | O |
| 소자 구조 단면도 | - | - | O |

### Step 2: Mermaid 다이어그램 생성

Obsidian 호환 Mermaid 코드를 생성한다. 도면 유형별 템플릿:

#### 2-1. 전체 시스템 구성도 (block diagram)

```mermaid
graph TD
    subgraph 전사_장치["전사 장치"]
        A[SMA 복합재료 챔버] --> B[진공 펌프]
        A --> C[열처리 모듈]
        A --> D[기판 스테이지]
        A --> E[박막 홀더]
    end
    B -->|압력차 구동| F[점진적 접촉]
    C -->|온도 제어| G[SMA 형상 복원/분리]
```

#### 2-2. 공정 흐름도 (flowchart)

```mermaid
flowchart LR
    S1[기판/박막 배치] --> S2[전처리]
    S2 --> S3[진공 배기]
    S3 --> S4[SMA 변형/접촉]
    S4 --> S5[계면 접합]
    S5 --> S6[가열/분리]
    S6 --> S7[전사 완료]
```

#### 2-3. 작동 원리도 (상태 변화)

```mermaid
stateDiagram-v2
    [*] --> 대기압상태: 챔버 밀봉
    대기압상태 --> 진공배기: 펌프 가동
    진공배기 --> SMA변형: 압력차 증가
    SMA변형 --> 점진적접촉: 중심→가장자리
    점진적접촉 --> 계면접합: 완전 접촉
    계면접합 --> 가열분리: 온도 상승
    가열분리 --> SMA복원: 형상기억 효과
    SMA복원 --> [*]: 전사 완료
```

#### 2-4. 종래기술 vs 본 발명 비교도

```mermaid
graph LR
    subgraph 종래기술["종래기술 (대기 전사)"]
        A1[박막] --> A2[대기 중 접촉]
        A2 --> A3[오염물 포함]
        A3 --> A4[품질 저하]
    end
    subgraph 본발명["본 발명 (진공 전사)"]
        B1[박막] --> B2[진공 중 SMA 접촉]
        B2 --> B3[오염물 배제]
        B3 --> B4[고품질 전사]
    end
```

### Step 3: Python matplotlib 도면 생성 (선택적)

Mermaid로 표현하기 어려운 기술 도면(단면도, 구조 상세도)은 Python matplotlib/PIL로 생성한다.

```python
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
import os

def create_cross_section_diagram(output_dir, filename):
    """장치 단면도 생성"""
    fig, ax = plt.subplots(1, 1, figsize=(10, 8))

    # 챔버 외벽 (SMA)
    chamber = FancyBboxPatch((1, 1), 8, 6,
                              boxstyle="round,pad=0.1",
                              facecolor='lightsteelblue',
                              edgecolor='navy', linewidth=2)
    ax.add_patch(chamber)

    # 기판
    substrate = patches.Rectangle((2, 2), 6, 0.5,
                                   facecolor='gold', edgecolor='black')
    ax.add_patch(substrate)
    ax.text(5, 2.25, '기판', ha='center', va='center', fontsize=10)

    # 박막
    film = patches.Rectangle((2, 3.5), 6, 0.3,
                              facecolor='lightcoral', edgecolor='black')
    ax.add_patch(film)
    ax.text(5, 3.65, '나노박막', ha='center', va='center', fontsize=10)

    # 화살표: 압력차 방향
    ax.annotate('대기압\n(외부)', xy=(0.5, 4), fontsize=9,
                ha='center', va='center')
    ax.annotate('', xy=(1.5, 4), xytext=(0.5, 4),
                arrowprops=dict(arrowstyle='->', color='red', lw=2))

    ax.annotate('진공\n(내부)', xy=(5, 5.5), fontsize=9,
                ha='center', va='center')

    # SMA 벽 레이블
    ax.text(0.8, 7.2, 'SMA 복합재료 챔버 벽', fontsize=11,
            fontweight='bold', color='navy')

    ax.set_xlim(0, 10)
    ax.set_ylim(0, 8)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('발명 장치 단면도', fontsize=14, fontweight='bold')

    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    return filepath

def create_process_flow_diagram(output_dir, filename, steps):
    """공정 흐름 다이어그램 생성"""
    fig, ax = plt.subplots(1, 1, figsize=(14, 4))

    n = len(steps)
    for i, step in enumerate(steps):
        x = i * 2
        box = FancyBboxPatch((x, 0.5), 1.5, 1,
                              boxstyle="round,pad=0.1",
                              facecolor='lightyellow', edgecolor='black')
        ax.add_patch(box)
        ax.text(x + 0.75, 1, step, ha='center', va='center',
                fontsize=8, wrap=True)

        if i < n - 1:
            ax.annotate('', xy=((i+1)*2, 1), xytext=(x+1.5, 1),
                        arrowprops=dict(arrowstyle='->', color='black', lw=1.5))

    ax.set_xlim(-0.5, n * 2)
    ax.set_ylim(0, 2)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('전사 공정 흐름도', fontsize=14, fontweight='bold')

    filepath = os.path.join(output_dir, filename)
    fig.savefig(filepath, dpi=150, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close(fig)
    return filepath
```

### Step 4: disclosure.md에 Mermaid 다이어그램 인라인 삽입

disclosure.md의 §6(구성)과 §9(추가자료)에 Mermaid 코드 블록을 직접 삽입한다.
Obsidian에서 바로 렌더링되므로 별도 파일이 필요 없다.

**§6에 삽입하는 Mermaid** (발명 구성 설명 보조):
- 전체 시스템 구성도 (`graph TD`)
- 공정 흐름도 (`flowchart LR`)
- 작동 원리 상태 변화도 (`stateDiagram-v2`)

**§9에 삽입하는 Mermaid** (추가자료 도면):
- 종래기술 vs 본 발명 비교도 (`graph LR` with subgraph)
- 구성요소 관계도 (`graph TD`)

삽입 형식:
````markdown
[도 1] 전체 시스템 구성도

```mermaid
graph TD
    subgraph 시스템["전사 장치"]
        A[핵심 구성요소 1] --> B[구성요소 2]
        A --> C[구성요소 3]
    end
```

[도 2] 공정 흐름도

```mermaid
flowchart LR
    S1[단계1] --> S2[단계2] --> S3[단계3] --> S4[단계4]
```
````

### Step 5: PNG 도면 생성 (HWPX 삽입용)

Mermaid와 별도로, HWPX에 삽입할 PNG 파일을 matplotlib로 생성한다.
(HWPX는 Mermaid를 렌더링할 수 없으므로 PNG가 필요)

```
{output_dir}/diagrams/
├── fig1_system_overview.png      # 전체 시스템 구성도
├── fig2_process_flow.png         # 공정 흐름도
├── fig3_cross_section.png        # 장치 단면도
├── fig4_operating_principle.png  # 작동 원리도
└── fig5_comparison.png           # 종래기술 vs 본 발명 비교
```

## 출력

1. `{output_dir}/disclosure.md` 업데이트 — §6, §9에 Mermaid 인라인 삽입
2. `{output_dir}/diagrams/*.png` — HWPX 삽입용 PNG 도면
3. manifest 업데이트: `"phase6b": {"status": "completed", "output": "diagrams/", "diagram_count": N}`

## 주의사항

- **Mermaid 우선**: 코드로 표현 가능한 도면은 반드시 Mermaid로 disclosure.md에 인라인 삽입
- **PNG 병행**: HWPX 삽입용으로 matplotlib PNG도 함께 생성
- **Excalidraw 미사용**: 에이전트가 Excalidraw 파일을 생성하지 않는다 (사용자가 핸드라이팅 시에만 직접 생성)
- matplotlib 한글 폰트: `plt.rcParams['font.family'] = 'Malgun Gothic'` (Windows)
- 도면 번호는 [도 1], [도 2] ... 형식으로 통일
- 특허 도면 스타일: 흑백 기본, 강조만 제한적 색상
