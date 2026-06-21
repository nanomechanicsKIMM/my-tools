---
name: fem-sweep
description: FEniCSx/dolfinx 파라미터 스윕을 JSON 정의→백그라운드 병렬 실행→결과 수집→곡선 plot까지 파이프라인으로 처리하는 스킬. 'FEM 스윕', '파라미터 스윕', 'DOE 실행', 'fem sweep', '두께 스윕', '병렬 해석' 등이 언급되면 사용. FEM 파라미터 스윕 전용.
---

# fem-sweep — FEM 파라미터 스윕 파이프라인 (FEniCSx 전용)

독립 파라미터 스윕을 백그라운드 병렬로 돌리고 결과를 곡선으로 종합한다.
**임의의 FEM 문제**의 파라미터/메쉬/물성 스윕에 적용된다.

## 사용 시점
- 한 솔버를 여러 파라미터 값으로 반복 실행해 곡선/표를 얻을 때 *(예: 두께·갭·물성·하중 스윕, DOE)*.
- **FEniCSx/dolfinx 해석 스윕에만 사용한다.** 일반 배치 작업이 아니다.

## 핵심 원칙
- 각 케이스는 **독립** → barrier 불필요, fan-out 병렬.
- **병렬은 케이스 차원에서**(여러 케이스 동시). 한 케이스 내부 MPI 분해도(`mpi_per_case`)와 동시 케이스 수는 **문제 규모로 결정** — 중규모 직접해는 케이스당 serial이 효율적인 경우가 많으나, **강스케일링은 측정 후 결정**(가정 금지).
- 장시간은 `run_in_background`(+슬립 방지 래퍼가 있으면 사용).
- 결과 종합(검증표·정정 판정)은 fan-out 후 단일 synthesis 단계.

## 절차
1. `templates/sweep_config.json`로 스윕 정의(솔버 스크립트, 파라미터 그리드, 출력 키).
2. 그리드 각 점을 케이스로 전개 → `run_in_background`로 동시 실행(동시 케이스 수는 케이스당 메모리로 제한).
3. 각 케이스 결과 JSON 수집.
4. 곡선 plot(관심량 vs 파라미터), 가능하면 해석해/보편곡선 오버레이.
5. `fem-verify`로 곡선의 극한·단조성 교차검증.

## 골격 상태
- `templates/sweep_config.json` — 스윕 정의 스키마(예시 채워짐).
- 러너(`run_sweep.py`)·수집·plot Python은 **다음 실해석에서 점진 추출**(현재 stub 없음). 그때까지는 스키마+절차를 따라 `fem-implementer`가 케이스 스크립트를 작성하고 Bash `run_in_background`로 수동 fan-out.

## 함정
- 동시 케이스 수 × 케이스 메모리 ≤ 가용 RAM 확인.
- 적응증분 하한 `min_dp ≪ 초기 dp`(케이스 첫 step 실패 시 재시도 가능하게).
