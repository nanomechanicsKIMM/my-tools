# fem-tools 의존성 (Dependencies)

이 플러그인의 에이전트·스킬은 **FEniCSx/dolfinx 런타임을 직접 호출**한다. 플러그인 자체는 마크다운(에이전트·스킬·템플릿)이라 설치가 필요 없지만, **생성된 해석 코드를 실행하려면 아래 스택이 갖춰져 있어야 한다**. dolfinx는 일반 `pip install`로 풀스택이 깔리지 않는 것이 가장 흔한 함정이다.

## 1. 핵심 런타임 (필수)

| 구성요소 | 역할 | 비고 |
|---|---|---|
| **dolfinx** (≥0.8, 권장 0.9.x) | FEM 계산 백엔드 | C++/Python. 버전마다 API가 바뀜 — 코드와 설치 버전을 일치시킬 것 |
| **ufl** | 변분 약형식·자동미분 | dolfinx와 버전 짝 |
| **basix** | 요소·기저함수 | dolfinx와 버전 짝 |
| **ffcx** | UFL→C 커널 컴파일 (`quadrature_degree` 추정 주체) | 컴파일 캐시 디렉터리 쓰기권한 필요 |
| **PETSc + petsc4py** | 선형/비선형 솔버 | **MUMPS 포함 빌드여야** 직접해(LU) 사용 가능 |
| **MPI + mpi4py** | 병렬/통신 (단일코어도 통신자 사용) | MPICH 또는 OpenMPI. `mpirun` PATH 필요 |
| **numpy** | 배열 | — |

> **버전 일치가 핵심**: dolfinx·ufl·basix·ffcx·petsc4py는 서로 ABI/API로 묶여 있다. 섞이면 import 에러나 조용한 오작동. 하나의 환경(conda env 등)으로 통일.

## 2. 메쉬·후처리 (대부분의 문제에서 사실상 필수)

| 구성요소 | 역할 | 비고 |
|---|---|---|
| **gmsh** (+ python API) | CAD/비정형 메쉬 생성, `gmshio.model_to_mesh` | OpenCASCADE 포함 빌드 권장 |
| **h5py / adios2** | XDMF·VTX 결과 출력 | XDMF는 h5py, VTX(권장)는 adios2 |
| **pyvista** (+ VTK) | 3D 변형형상 시각화 | headless 환경은 `pyvista.start_xvfb()` 또는 OSMesa |
| **matplotlib** | 검증 곡선·문제설명 그림 (`shared/fem_figures.py`) | 비ASCII 라벨은 폰트 설정 필요(§5) |
| **scipy** | 보조 수치(보간·특수함수 등) | 선택 |

## 3. 설치 (권장: conda-forge — pip 풀스택 설치는 비권장)

```bash
# conda/mamba (가장 견고)
mamba create -n fenicsx -c conda-forge \
  fenics-dolfinx mpich pyvista gmsh python-gmsh h5py adios2 matplotlib scipy
mamba activate fenicsx
```
- 대안: 공식 **Docker 이미지**(`dolfinx/dolfinx`) 또는 **spack**. Windows는 WSL2 또는 Docker 권장(네이티브 빌드 비권장).
- `pip install fenics-dolfinx`는 시스템 PETSc/MPI/CMake 등 빌드 의존성을 직접 갖춰야 해 실패하기 쉬움 — 가급적 conda-forge.

## 4. 인터프리터 탐지 (에이전트·스크립트 공통)

해석 코드는 **dolfinx가 설치된 python**으로 실행해야 한다(시스템 python 아님). 우선순위:
1. 환경변수 `FENICSX_PYTHON`이 있으면 그것을 사용.
2. 활성 conda env(`$CONDA_PREFIX/bin/python`)에서 `import dolfinx` 성공하면 사용.
3. 후보 경로 시도 *(예: `/opt/homebrew/Caskroom/miniforge/base/envs/fenicsx/bin/python`은 한 예시일 뿐, 환경마다 다름)*.

설치 확인:
```bash
PYBIN=<dolfinx python>
$PYBIN -c "import dolfinx, ufl, basix, ffcx; print('dolfinx', dolfinx.__version__)"
$PYBIN -c "from petsc4py import PETSc; print('petsc', PETSc.Sys.getVersion())"
$PYBIN -c "from mpi4py import MPI; print('mpi ranks ok')"
$PYBIN -c "from petsc4py import PETSc; print('MUMPS' , 'mumps' in PETSc.Options().getAll() or True)"  # MUMPS는 LU solve 시 실패 여부로 최종 확인
command -v mpirun || echo "WARN: mpirun not on PATH"
```

## 5. 플랫폼·실행 주의

- **BLAS/LAPACK**: 가능하면 최적화 백엔드(예: Accelerate/MKL/OpenBLAS) — `numpy.show_config()`로 확인.
- **GPU**: dolfinx 0.9는 GPU 미지원 → CPU(MPI)로 실행.
- **arm64/페이지크기 등 플랫폼차**: x86 가정 라이브러리 mmap 이슈 주의.
- **장시간 해석 슬립 방지**: macOS `caffeinate -i <cmd>`, Linux `systemd-inhibit`/`caffeine` 등 — 환경에 맞게.
- **비ASCII(한글 등) 그림 라벨**: matplotlib `font.family`를 설치된 폰트로 설정(`shared/fem_figures.py`는 macOS `AppleGothic` 예시 — 다른 OS에선 교체 필요), `axes.unicode_minus=False`.
- **FFCX 캐시**: `XDG_CACHE_HOME`/홈 디렉터리 쓰기권한 필요(컨테이너·CI에서 읽기전용 FS 주의).

## 6. 레퍼런스 (정식화 패턴 — 설치 아님)
- `comet-fenicsx` (고체·연속체역학 정식화), `dolfinx-tutorial` (API 관용구). 새 정식화 전 해당 예제 확인.
