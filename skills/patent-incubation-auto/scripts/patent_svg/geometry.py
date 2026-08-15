# -*- coding: utf-8 -*-
"""patent_svg 기하 계층 — 물리 좌표(mm) 계산과 캔버스 변환.

원칙(도면 생성 개선방안 2026-08-08): 물리식 계산은 이 계층에서 좌표로 확정하고,
렌더 엔진(drawsvg)은 그리기만 담당한다. LLM이 캔버스 좌표를 암산하지 않는다.
"""
import math


class Frame:
    """세계 좌표(mm, y 위쪽 양수) -> 캔버스 좌표(px, y 아래쪽 양수) 변환."""

    def __init__(self, scale=10.0, origin_px=(600, 400)):
        self.s = scale
        self.ox, self.oy = origin_px

    def pt(self, x_mm, y_mm):
        return (self.ox + x_mm * self.s, self.oy - y_mm * self.s)

    def d(self, mm):
        return mm * self.s


def polar(r_mm, theta_deg, cx=0.0, cy=0.0):
    """중심 (cx, cy)에서 반경 r, 각도 theta(도, x+축 기준 반시계)의 세계 좌표."""
    t = math.radians(theta_deg)
    return (cx + r_mm * math.cos(t), cy + r_mm * math.sin(t))


def arc_points(r_mm, th0_deg, th1_deg, n=64, cx=0.0, cy=0.0):
    return [polar(r_mm, th0_deg + (th1_deg - th0_deg) * i / (n - 1), cx, cy)
            for i in range(n)]


def beam_polygon(src_xy, aim_xy, src_width_mm, waist_width_mm, frac=1.0):
    """발광원 폭 src_width의 다발이 aim점 방향으로 수렴하는 사다리꼴(세계 좌표).

    frac: 전파 비율(1.0이면 aim점 도달, 그 지점 폭 = waist_width)."""
    sx, sy = src_xy
    ax, ay = aim_xy
    dx, dy = ax - sx, ay - sy
    L = math.hypot(dx, dy)
    ux, uy = -dy / L, dx / L          # 진행 방향의 수직 단위벡터
    ex, ey = sx + dx * frac, sy + dy * frac
    hw0, hw1 = src_width_mm / 2, waist_width_mm / 2
    return [(sx + ux * hw0, sy + uy * hw0), (ex + ux * hw1, ey + uy * hw1),
            (ex - ux * hw1, ey - uy * hw1), (sx - ux * hw0, sy - uy * hw0)]


# ---------- 광학 도메인 (구면 직시형 근안 기하) ----------

def reduced_eye(rot_center=(0.0, 0.0), r_eye_mm=12.0, toward_deg=180.0):
    """축소 모형안 개요 기하. toward_deg = 패널을 향한 방향(각막 쪽).

    반환: dict(outline_center, r, cornea_xy, pupil_gap_deg, retina_arc(th0, th1))"""
    cx, cy = rot_center
    cornea = polar(r_eye_mm, toward_deg, cx, cy)
    return dict(center=(cx, cy), r=r_eye_mm, cornea=cornea,
                pupil_half_deg=22.0, toward_deg=toward_deg,
                retina=(toward_deg + 120.0, toward_deg + 240.0))


def panel_cells(R_mm, span_deg, n_cells, toward_deg=180.0, cx=0.0, cy=0.0):
    """회전중심 기준 반경 R 패널 호 위에 셀 중심 각도를 균등 배치."""
    th = [toward_deg - span_deg / 2 + span_deg * i / (n_cells - 1)
          for i in range(n_cells)]
    return [(polar(R_mm, t, cx, cy), t) for t in th]


def wave_dof_diopter(d_mm, lam_nm=530.0):
    """파동 초점심도 법칙 DoF± ≈ 4λ/d² [디옵터] (원장 정정 2026-08-08)."""
    d = d_mm * 1e-3
    return 4 * lam_nm * 1e-9 / (d * d)
