# -*- coding: utf-8 -*-
"""fig1 -> native PPT slide (reference module for pptx_figkit)."""
import pptx_figkit as K

INK = "1A1A1A"; NAVY = "1F3A5F"; ORANGE = "E69F00"; GRAY = "7F7F7F"
R_, G_, B_ = "FF0000", "00FF00", "0000FF"; WHITE = "FFFFFF"; BLACK = "000000"
FS_TITLE = 10.5; FS_HEADING = 9.0; FS_BANNER = 7.5; FS_VERDICT = 7.5
FS_CHIP = 7.5; FS_LAYER = 7.3; FS_BULLET = 7.0; FS_LAYER_SM = 6.9; FS_NOTE = 6.9
IND = "   "


def add_slide(prs, img_dir=None):
    s = K.Slide(prs, 183, 98)
    s.banner(0.012, 0.988, 0.928, 0.992,
             "XR 근안 디스플레이 요구사항(§2):   리프레시율 ≥ 90 Hz   ·   "
             "60 PPD 분해능 (10^{3}~10^{4} PPI)   ·   양안 시야 ~220°   ·   "
             "패널 휘도 ≥ 10^{5} cd/m^{2} (AR)", FS_BANNER, NAVY)
    AX = [s.axes(0.012 + i * 0.247, 0.012 + i * 0.247 + 0.235, 0.02, 0.90,
                 xlim=(0, 10), ylim=(0, 10)) for i in range(4)]

    def title(ax, letter, name):
        ax.text(0.2, 9.75, letter, FS_TITLE, INK, ha="left", va="center", bold=True, w_local=2.0)
        ax.text(5.0, 9.75, name, FS_HEADING, NAVY, ha="center", va="center", bold=True, w_local=9.2)

    def bullets(ax, lines):
        ax.text(0.6, 9.05, lines, FS_BULLET, INK, ha="left", va="top",
                w_local=9.2, h_local=4.4, line_spacing=1.5)

    def layer(ax, y, h, label, fc, sm=False):
        ax.rect(1.3, y, 7.4, h, fc, ec=INK, lw=0.5, label=label,
                label_fs=(FS_LAYER_SM if sm else FS_LAYER), label_color=INK)

    def colorfilter(ax, y):
        w3 = (8.7 - 1.3) / 3.0
        for k, c in enumerate((R_, G_, B_)):
            ax.rect(1.3 + k * w3, y, w3, 0.7, c, ec=INK, lw=0.5)
        ax.text(5.0, y + 0.35, "컬러필터", FS_LAYER_SM, INK, ha="center", va="center", w_local=4.0)

    def emit(ax, base, color, xs=(2.6, 5.0, 7.4)):
        for x in xs:
            ax.arrow(x, base + 0.06, x, base + 0.75, color, lw=0.8)

    def verdict(ax, text, fc):
        n = len([c for c in text if c != " "]); w = max(3.8, n * 0.72 + 1.8)
        ax.rect(5.0 - w / 2, 0.42 - 0.475, w, 0.95, fc, ec=None, rounded=True, round_adj=0.5,
                label=text, label_fs=FS_VERDICT, label_color=WHITE, label_bold=True)

    # (a) LCD
    ax = AX[0]; title(ax, "a", "LCD")
    bullets(ax, ["• 백라이트 빛을 여닫는 광밸브", "• 응답속도 ~5 ms (액정)", "• 휘도 ~3×10^{3} cd/m^{2}"])
    y = 1.3
    layer(ax, y, 1.0, "백라이트", "FFF3CC"); y += 1.08
    layer(ax, y, 0.7, "편광판", "E3E3E3", sm=True); y += 0.78
    layer(ax, y, 1.0, "TFT + 액정", "DCEBF7"); y += 1.08
    colorfilter(ax, y); y += 0.78
    layer(ax, y, 0.7, "편광판", "E3E3E3", sm=True)
    emit(ax, y + 0.7, GRAY); verdict(ax, "근안용: 부적합", GRAY)

    # (b) OLEDoS
    ax = AX[1]; title(ax, "b", "OLED (OLEDoS)")
    bullets(ax, ["• 유기물 자발광, 응답 ~110 µs", "• 현 XR 헤드셋의 주류",
                 "• 휘도 한계 10^{3}~10^{4} cd/m^{2},", IND + "고휘도 구동 시 번인"])
    y = 1.3
    layer(ax, y, 1.0, "Si CMOS 백플레인", "D7E3F0"); y += 1.08
    layer(ax, y, 1.0, "백색 OLED층 (유기물)", "FFE3B3"); y += 1.08
    colorfilter(ax, y); y += 0.78
    layer(ax, y, 0.7, "박막 봉지층", "E3E3E3", sm=True)
    emit(ax, y + 0.7, ORANGE); verdict(ax, "현 주류 (VR)", "4E79A7")

    # (c) Micro-LED
    ax = AX[2]; title(ax, "c", "Micro-LED")
    bullets(ax, ["• 무기물 자발광, 응답 ~ns", "• 10^{5}~10^{7} cd/m^{2}, 긴 수명",
                 "• 난제: 대량 전사와 집적", IND + "(§3~§4)"])
    y = 1.3
    layer(ax, y, 1.0, "Si CMOS·LTPS 백플레인", "D7E3F0"); y += 1.08
    chip_y = y + 0.25
    for x, c, lab, tc in ((1.9, R_, "R", WHITE), (4.35, G_, "G", BLACK), (6.8, B_, "B", WHITE)):
        ax.oval(x + 0.35, y + 0.10, 0.10, "9A9A9A")
        ax.oval(x + 0.95, y + 0.10, 0.10, "9A9A9A")
        ax.rect(x, chip_y, 1.3, 0.95, c, ec=INK, lw=0.5, label=lab, label_fs=FS_CHIP,
                label_color=tc, label_bold=True)
    ax.text(5.0, chip_y + 2.15, "전사된 GaN/AlGaInP 칩", FS_NOTE, INK, ha="center",
            va="center", italic=True, w_local=8.5)
    emit(ax, chip_y + 0.95, ORANGE, xs=(2.55, 5.0, 7.45)); verdict(ax, "AR 최유력 후보", "2E86AB")

    # (d) QD-EL
    ax = AX[3]; title(ax, "d", "QD-EL")
    bullets(ax, ["• 전계발광 양자점(QD)", "• 좁은 발광 선폭, 인쇄 공정",
                 "• 초기 단계: 휘도 ~10^{2} cd/m^{2},", IND + "수명 (18인치 잉크젯 시연)"])
    y = 1.3
    layer(ax, y, 1.0, "TFT 백플레인", "D7E3F0"); y += 1.08
    layer(ax, y, 0.7, "전극", "E3E3E3", sm=True); y += 0.78
    layer(ax, y, 1.0, "QD 발광층 (인쇄)", "FBE9E5")
    for k in range(9):
        ax.oval(1.85 + k * 0.78, y + 0.30, 0.13, (R_, G_, B_)[k % 3])
    y += 1.08
    layer(ax, y, 0.7, "투명 전극", "E3E3E3", sm=True)
    emit(ax, y + 0.7, ORANGE); verdict(ax, "신흥 기술", ORANGE)
    return s


if __name__ == "__main__":
    import os
    prs = K.new_deck()
    add_slide(prs)
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "figures_v2", "_kit_test_fig1.pptx")
    prs.save(out); print("saved:", out, "| shapes:", len(prs.slides[0].shapes))
