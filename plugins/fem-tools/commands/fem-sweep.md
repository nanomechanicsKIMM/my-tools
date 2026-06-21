---
description: FEM 파라미터 스윕을 JSON 정의→백그라운드 병렬 실행→수집→곡선 plot (FEniCSx 전용)
---

# /fem-sweep — FEM 파라미터 스윕

FEniCSx/dolfinx 파라미터 스윕을 **fem-sweep** 스킬 파이프라인으로 실행한다.

## 동작
1. `fem-sweep` 스킬을 로드하고 `templates/sweep_config.json`로 스윕을 정의한다.
2. 그리드 각 점을 **독립 케이스**로 전개 → `run_in_background` 병렬 실행. 케이스 내부 MPI 분해도·동시 케이스 수는 문제 규모로 결정(강스케일링 측정).
3. 케이스 JSON 수집 → 곡선 plot(관심량 vs 파라미터, 가능시 해석해 오버레이).
4. `fem-verify`로 극한·단조성 교차검증.

> FEM/FEniCSx 해석 스윕 전용. 케이스 차원 병렬.

입력: `$ARGUMENTS` (sweep_config.json 경로 또는 솔버·파라미터 그리드).
