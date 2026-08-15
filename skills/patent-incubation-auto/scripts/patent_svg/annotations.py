# -*- coding: utf-8 -*-
"""patent_svg 주석 계층 — 라벨(이름 기반, 도면부호 미사용 정책)과 지시선.

LabelLedger가 배치 bbox를 기록하고 겹침을 회피(세로 넉지)하며,
결과 원장은 validators의 충돌 검사 입력이 된다.
"""
import drawsvg as dw


def _est_width(text, size):
    w = 0.0
    for ch in text:
        w += size * (1.0 if ord(ch) > 0x2E7F else 0.62)
    return w


class LabelLedger:
    def __init__(self, style):
        self.style = style
        self.boxes = []      # (x0, y0, x1, y1, text)
        self.leaders = []    # ((x0,y0),(x1,y1))  캔버스 좌표

    def _bbox(self, px, py, text, size, anchor):
        w, h = _est_width(text, size), size * 1.35
        x0 = px - (w if anchor == "end" else w / 2 if anchor == "middle" else 0)
        return (x0, py - h * 0.8, x0 + w, py + h * 0.35)

    def _collides(self, bb):
        x0, y0, x1, y1 = bb
        for (a0, b0, a1, b1, _) in self.boxes:
            if x0 < a1 and x1 > a0 and y0 < b1 and y1 > b0:
                return True
        return False

    def label(self, frame, world_xy, text, anchor="start", dx=0, dy=0,
              leader_to=None, size=None, max_nudge=10):
        """라벨 배치(캔버스 오프셋 dx, dy px). 겹치면 세로로 넉지.

        leader_to: 지시 대상 세계 좌표 (지시선은 라벨 쪽에서 대상으로)."""
        st = self.style
        size = size or st["font_size"]
        px, py = frame.pt(*world_xy)
        px, py = px + dx, py + dy
        bb = self._bbox(px, py, text, size, anchor)
        step = size * 1.5
        n = 0
        while self._collides(bb) and n < max_nudge:
            py += step if (n % 2 == 0) else -step * (n + 1)
            bb = self._bbox(px, py, text, size, anchor)
            n += 1
        self.boxes.append((*bb, text))
        els = [dw.Text(text, size, px, py, font_family=st["font_family"],
                       fill=st["text_color"], text_anchor=anchor,
                       class_="labeltext")]
        if leader_to is not None:
            tx, ty = frame.pt(*leader_to)
            # 지시선 시작점: 라벨 bbox의 대상 쪽 가장자리 중앙
            sx = bb[0] - 3 if tx < bb[0] else (bb[2] + 3 if tx > bb[2] else (bb[0] + bb[2]) / 2)
            sy = (bb[1] + bb[3]) / 2 if (tx < bb[0] or tx > bb[2]) else (bb[1] - 3 if ty < bb[1] else bb[3] + 3)
            els.append(dw.Line(sx, sy, tx, ty, stroke=st["stroke"],
                               stroke_width=st["stroke_leader"], class_="leader"))
            els.append(dw.Circle(tx, ty, 2.2, fill=st["stroke"], class_="leader-dot"))
            self.leaders.append(((sx, sy), (tx, ty)))
        return els

    def export(self):
        return dict(boxes=self.boxes, leaders=self.leaders)
