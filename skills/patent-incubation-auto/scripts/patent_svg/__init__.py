# -*- coding: utf-8 -*-
"""patent_svg — 특허 도면 SVG 생성 래퍼 (계산-렌더 분리, drawsvg 기반).

도입: (20260808) patent-incubation-auto SVG 도면 생성 개선방안 (my-tools 루트).
사용 순서: FigureSpec(dict/JSON) -> geometry로 세계 좌표 계산 -> primitives/annotations로
Drawing 구성 -> exporters.save() -> validators.validate() 0건 확인 후 완료 보고.
"""
from . import geometry, primitives, annotations, styles, validators, exporters  # noqa: F401
