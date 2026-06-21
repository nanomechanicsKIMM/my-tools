---
title: <단계 ID> <해석명>
date: <YYYY-MM-DD>
tags:
  - FEM
  - FEniCSx
  - <residual-stress | contact | strain-transfer | SMA | …>
status: <draft | active | verified>
description: <한 줄 요약 — 무엇을, 어떤 방법으로, 핵심 결과>
---

# <단계 ID> <해석명>

## 1. 문제 정의

> 가정: <측도 GL/Hencky>, <dead/follower 압력>, <frictionless/stick>, <선형/유한변형>. <가정이 틀릴 때의 현상>.

![[<단계>_setup.png]]
*문제 설명: <지오메트리·하중·경계조건>.*

<문제 정의 본문 — 무엇을 풀고 무엇을 검증하는가.>

## 2. FEM 방법

- **정식화**: <Newton+autodiff / mixed TH / 곱분해 eigenstrain / 축대칭 3D Hooke+hoop / quadrature 내부변수>
- **요소·메쉬**: <P2 변위 / P1 압력>, <관심영역 refinement>
- **솔버**: <MUMPS 직접 / Krylov+AMG>, `quadrature_degree=2*degree`, <적응 하중증분: 초기 dp, 성장 ×1.3~1.5, cutback ×0.5, min_dp≪dp>
- 레퍼런스 패턴: <comet-fenicsx / dolfinx-tutorial 해당 예제>

## 3. 결과

![[<단계>_curves.png]]
![[<단계>_deformed.png]]

<핵심 수치 표/문장 — 도달값, 트렌드, 핵심 관찰.>

## 4. 검증 (Verification)

<fem-verify 검증표 삽입 — §1.5 2~3개 채널>

| # | 검증 채널 | 기준 | FEM | 오차 | 판정 |
|---|---|---|---:|---:|:--:|
|   |   |   |   |   |   |

## 5. 핵심 메시지

1. <검증된 결론 1>
2. <robust(geometry지배) vs material지배 구분>

## 6. 한계 (Limitations)

- <적용 범위 밖에서 무효한 가정>
- <미수렴·미달·정정 fail loud>

## Related
- [[<상위 계획/회고 노트>]]
- 상세 코드: `<프로젝트>/<단계>_*.py`
