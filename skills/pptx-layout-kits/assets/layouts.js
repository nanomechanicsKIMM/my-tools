/*
 * layout-kits — reusable PptxGenJS layout library (10 layouts)
 * ------------------------------------------------------------------
 * One content model, 10 interchangeable "layout kits" (palette + chrome).
 * Pick a layout by name; author content against a content-area rect using
 * the bound helpers (card / panel / statCard / chartOpts / table headers).
 * Swap layouts by changing ONE string.
 *
 * Quick start:
 *   const pptxgen = require("pptxgenjs");
 *   const { makeDeck, LAYOUTS } = require("./layouts.js");
 *   const d = makeDeck(pptxgen, "swiss", { total: 3, title: "My Deck" });
 *   d.title({ eyebrow: "REPORT", title: "제목", subtitle: "부제",
 *             stats: [{v:"42%",label:"지표"}], date: "2026-06-28" });
 *   const { slide, area: A, k } = d.content("SECTION", "슬라이드 제목");
 *   d.card(slide, A.x, A.y, A.w/2-0.2, A.h);            // a container
 *   d.statCard(slide, A.x+A.w/2+0.2, A.y, A.w/2-0.2, 1.4, true);
 *   slide.addChart(d.charts.BAR, data, d.chartOpts({ x:..,y:..,w:..,h:.. }));
 *   d.closing({ title: "결론", body: "요약 문장", stats:[...] });
 *   await d.save("out.pptx");
 *
 * Layout names: minimal, topband, sidebar, dark, swiss,
 *               margin, framed, register, datasheet, tabgrid
 * See README.md and contact-sheet.png.
 */
const W = 13.333, H = 7.5,
  KR = process.platform === "win32" ? "맑은 고딕" : "Apple SD Gothic Neo";
const shadow = () => ({ type: "outer", color: "9DB0BD", blur: 7, offset: 3, angle: 90, opacity: 0.22 });

// ============================== 10 LAYOUT KITS ==============================
const LAYOUTS = {
  minimal: { name: "Minimal Navy", layout: "minimal", cardStyle: "shadow",
    bg: "F5F8FA", ink: "1B2A38", muted: "6B7C8C", line: "DCE5EB", cardFill: "FFFFFF", cardBorder: "DCE5EB",
    primary: "0E7C8B", primary2: "16395F", accent: "E0902B", accent2: "57C4D6",
    panelFill: "0E2A47", panelAccent: "57C4D6", panelAccent2: "E0902B", panelInk: "E4ECF2", panelInk2: "AFC2D0",
    tHeadFill: "0E2A47", tHeadInk: "FFFFFF", rowA: "F8FBFC", rowB: "EEF3F6", rowHi: "FBF2E0", tBody: "3A4C5A", thMuted: "8896A3",
    chartColors: ["0E7C8B"], chartArea: "FFFFFF", chartAxis: "6B7C8C", chartGrid: "EDF1F4", chartLabel: "1B2A38",
    statNum: "16395F", good: "2E9E6B", bad: "C0504D", slate: "5B7488", barMuted: "9FB4C2",
    stack: ["16395F", "0E7C8B", "5B7488", "57C4D6", "E0902B"],
    titleBg: "0E2A47", titleSub: "AFC2D0", titleFaint: "7E93A4", titleLine: "2C4A66", cCard: "16395F", cInk: "E4ECF2", cAccent: "57C4D6" },

  topband: { name: "Top-Band Blue", layout: "band", cardStyle: "flat",
    bg: "F7F9FC", ink: "1A2733", muted: "6B7C8C", line: "D8E1EA", cardFill: "FFFFFF", cardBorder: "D8E1EA",
    primary: "1F5FAE", primary2: "13386E", accent: "E0861E", accent2: "9FC3EC",
    panelFill: "EAF1F9", panelAccent: "1F5FAE", panelAccent2: "C0392B", panelInk: "1F3A57", panelInk2: "5A7388",
    tHeadFill: "13386E", tHeadInk: "FFFFFF", rowA: "F6F9FC", rowB: "EAF1F8", rowHi: "FBEFD8", tBody: "33485C", thMuted: "8DA2B5",
    chartColors: ["1F5FAE"], chartArea: "FFFFFF", chartAxis: "6B7C8C", chartGrid: "E8EEF4", chartLabel: "1A2733",
    statNum: "13386E", good: "2E9E6B", bad: "C0392B", slate: "5B7488", barMuted: "A9BED2",
    stack: ["13386E", "1F5FAE", "5B7488", "9FC3EC", "E0861E"],
    titleBg: "13386E", titleSub: "C8D9EC", titleFaint: "7E93A4", titleLine: "2C4A66", cCard: "FFFFFF", cInk: "33485C", cAccent: "1F5FAE" },

  sidebar: { name: "Sidebar Teal", layout: "sidebar", cardStyle: "tint",
    bg: "FAFBFB", ink: "1B2A30", muted: "6E7E84", line: "E0E6E7", cardFill: "F1F6F6", cardBorder: "E0E6E7",
    primary: "0E8C8C", primary2: "0B3A42", accent: "E08A2B", accent2: "4FB3B3", sideMuted: "6E9A9C",
    panelFill: "0B3A42", panelAccent: "4FB3B3", panelAccent2: "E08A2B", panelInk: "E6F0F0", panelInk2: "AFC9C9",
    tHeadFill: "0B3A42", tHeadInk: "FFFFFF", rowA: "F4F8F8", rowB: "E8F1F1", rowHi: "FBEFD8", tBody: "35484C", thMuted: "86A0A0",
    chartColors: ["0E8C8C"], chartArea: "F1F6F6", chartAxis: "6E7E84", chartGrid: "E2EAEA", chartLabel: "1B2A30",
    statNum: "0B3A42", good: "2E9E6B", bad: "C0504D", slate: "5B7488", barMuted: "A6C0C0",
    stack: ["0B3A42", "0E8C8C", "5B7488", "4FB3B3", "E08A2B"],
    titleBg: "0B3A42", titleSub: "AFC9C9", titleFaint: "6E9A9C", titleLine: "1C5159", cCard: "0B3A42", cInk: "E6F0F0", cAccent: "4FB3B3" },

  dark: { name: "Dark Hero", layout: "dark", cardStyle: "darkpanel",
    bg: "0E1A24", ink: "E8EEF2", muted: "8AA0AC", line: "24333E", cardFill: "16242E", cardBorder: "283A45",
    primary: "33C2C9", primary2: "1A2C38", accent: "F2A03D", accent2: "7FD8DC",
    panelFill: "1C3038", panelAccent: "4FE0E0", panelAccent2: "F2A03D", panelInk: "EAF6F6", panelInk2: "9FBEC0",
    tHeadFill: "24414C", tHeadInk: "EAF6F6", rowA: "16242E", rowB: "1B2B35", rowHi: "2E2A1E", tBody: "C7D4DB", thMuted: "37505C",
    chartColors: ["33C2C9"], chartArea: "16242E", chartAxis: "8AA0AC", chartGrid: "24333E", chartLabel: "D6E2E8",
    statNum: "7FD8DC", good: "49C98A", bad: "E2706A", slate: "6E8A98", barMuted: "46606C",
    stack: ["7FD8DC", "33C2C9", "6E8A98", "9FBEC0", "F2A03D"],
    titleBg: "0B141C", titleSub: "9FBEC0", titleFaint: "5E7884", titleLine: "26404C", cCard: "16242E", cInk: "D6E2E8", cAccent: "4FE0E0" },

  swiss: { name: "Swiss Grid", layout: "swiss", cardStyle: "rule", fam: "swiss2",
    bg: "FFFFFF", ink: "111418", muted: "6A7178", line: "D9DCDF", cardFill: "FFFFFF", cardBorder: "FFFFFF",
    primary: "C8102E", primary2: "111418", accent: "C8102E", accent2: "6A7178",
    panelFill: "111418", panelAccent: "FFFFFF", panelAccent2: "F2A35B", panelInk: "EDEEEF", panelInk2: "B9BEC3",
    tHeadFill: "111418", tHeadInk: "FFFFFF", rowA: "FFFFFF", rowB: "F2F3F4", rowHi: "FBE3E6", tBody: "33383D", thMuted: "8A9097",
    chartColors: ["C8102E"], chartArea: "FFFFFF", chartAxis: "6A7178", chartGrid: "E6E8EA", chartLabel: "111418",
    statNum: "111418", good: "2E9E6B", bad: "C8102E", slate: "6A7178", barMuted: "B8BDC2",
    stack: ["111418", "C8102E", "6A7178", "9AA0A6", "E0902B"], mono: KR },

  margin: { name: "Margin Rule", layout: "margin", cardStyle: "rule", fam: "swiss2", mono: KR,
    bg: "FAFAF8", ink: "1A1A1A", muted: "6E6E6A", line: "D8D8D2", cardFill: "FAFAF8", cardBorder: "D8D8D2",
    primary: "B5341F", primary2: "1A1A1A", accent: "B5341F", accent2: "6E6E6A",
    panelFill: "1A1A1A", panelAccent: "FFFFFF", panelAccent2: "F0A35A", panelInk: "EDEDEA", panelInk2: "B8B8B2",
    tHeadFill: "1A1A1A", tHeadInk: "FFFFFF", rowA: "FAFAF8", rowB: "F0F0EA", rowHi: "F6E3DC", tBody: "3A3A36", thMuted: "8A8A84",
    chartColors: ["B5341F"], chartArea: "FAFAF8", chartAxis: "6E6E6A", chartGrid: "E8E8E2", chartLabel: "1A1A1A",
    statNum: "1A1A1A", good: "2E8E5B", bad: "B5341F", slate: "7A7A74", barMuted: "BEBEB6",
    stack: ["1A1A1A", "B5341F", "7A7A74", "B0B0A8", "D08A3A"] },

  framed: { name: "Framed Grid", layout: "framed", cardStyle: "rule", fam: "swiss2", mono: KR,
    bg: "FFFFFF", ink: "111111", muted: "6A6A6A", line: "CFCFCF", cardFill: "FFFFFF", cardBorder: "CFCFCF",
    primary: "333333", primary2: "111111", accent: "D9A521", accent2: "6A6A6A",
    panelFill: "111111", panelAccent: "F0C24A", panelAccent2: "D9A521", panelInk: "EDEDED", panelInk2: "B5B5B5",
    tHeadFill: "111111", tHeadInk: "FFFFFF", rowA: "FFFFFF", rowB: "F3F3F0", rowHi: "FBF0CF", tBody: "333333", thMuted: "8A8A8A",
    chartColors: ["333333"], chartArea: "FFFFFF", chartAxis: "6A6A6A", chartGrid: "E8E8E4", chartLabel: "111111",
    statNum: "111111", good: "2E8E5B", bad: "C0392B", slate: "7A7A7A", barMuted: "BCBCBC",
    stack: ["111111", "D9A521", "7A7A7A", "B5B5B5", "C0392B"] },

  register: { name: "Register Marks", layout: "register", cardStyle: "plain", fam: "swiss2", mono: KR,
    bg: "FFFFFF", ink: "1C2024", muted: "6B7178", line: "D7DBDF", cardFill: "FFFFFF", cardBorder: "D7DBDF",
    primary: "1F4FBF", primary2: "1C2024", accent: "1F4FBF", accent2: "6B7178",
    panelFill: "1C2024", panelAccent: "6FA0FF", panelAccent2: "F0A35A", panelInk: "EAEEF2", panelInk2: "AEB8C2",
    tHeadFill: "1C2024", tHeadInk: "FFFFFF", rowA: "FFFFFF", rowB: "F1F4F8", rowHi: "E3EAFB", tBody: "343A40", thMuted: "8A929A",
    chartColors: ["1F4FBF"], chartArea: "FFFFFF", chartAxis: "6B7178", chartGrid: "E7EAEE", chartLabel: "1C2024",
    statNum: "1C2024", good: "2E8E5B", bad: "C0392B", slate: "6B7178", barMuted: "B6BEC6",
    stack: ["1C2024", "1F4FBF", "6B7178", "AEC3F2", "E0902B"] },

  datasheet: { name: "Datasheet Mono", layout: "datasheet", cardStyle: "rule", fam: "swiss2", mono: "Consolas",
    bg: "F6F6F4", ink: "14181C", muted: "6A7076", line: "CFD3D0", cardFill: "F6F6F4", cardBorder: "CFD3D0",
    primary: "0E7A5F", primary2: "14181C", accent: "0E7A5F", accent2: "6A7076",
    panelFill: "14181C", panelAccent: "4FD0A8", panelAccent2: "E0902B", panelInk: "EAEEEC", panelInk2: "AEB6B2",
    tHeadFill: "14181C", tHeadInk: "FFFFFF", rowA: "F8F8F6", rowB: "EEEEEA", rowHi: "DDEFE8", tBody: "343A38", thMuted: "8A908C",
    chartColors: ["0E7A5F"], chartArea: "F6F6F4", chartAxis: "6A7076", chartGrid: "E4E6E2", chartLabel: "14181C",
    statNum: "14181C", good: "0E7A5F", bad: "C0392B", slate: "6A7076", barMuted: "B8BCB8",
    stack: ["14181C", "0E7A5F", "6A7076", "A8C8BC", "E0902B"] },

  tabgrid: { name: "Tab Grid", layout: "tabgrid", cardStyle: "tab", fam: "swiss2", mono: KR,
    bg: "FFFFFF", ink: "121417", muted: "6A7077", line: "DADDE0", cardFill: "FFFFFF", cardBorder: "DADDE0",
    primary: "FF4438", primary2: "121417", accent: "FF4438", accent2: "6A7077",
    panelFill: "121417", panelAccent: "FF7A70", panelAccent2: "F0A35A", panelInk: "EDEEEF", panelInk2: "B7BBBF",
    tHeadFill: "121417", tHeadInk: "FFFFFF", rowA: "FFFFFF", rowB: "F3F4F5", rowHi: "FFE6E3", tBody: "33373B", thMuted: "8A9097",
    chartColors: ["FF4438"], chartArea: "FFFFFF", chartAxis: "6A7077", chartGrid: "E8EAEC", chartLabel: "121417",
    statNum: "121417", good: "2E8E5B", bad: "FF4438", slate: "6A7077", barMuted: "BABEC2",
    stack: ["121417", "FF4438", "6A7077", "B0B4B8", "F0A35A"] },
};

function asRich(x) { return Array.isArray(x) ? x : (x == null ? null : [{ text: String(x) }]); }

// ============================== deck factory ==============================
function makeDeck(pptxgen, layoutName, opts) {
  opts = opts || {};
  const k = LAYOUTS[layoutName];
  if (!k) throw new Error("unknown layout '" + layoutName + "'. available: " + Object.keys(LAYOUTS).join(", "));
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.author = opts.author || "";
  pres.title = opts.title || "";
  const SH = pres.shapes, CH = pres.charts;
  const TOTAL = opts.total || 10;
  const MONO = k.mono || KR;
  let PNUM = 1; // title = page 1; content() pages start at 2

  function cornerMarks(s, fx, fy, fw, fh, t) {
    const L = (x, y, w, h) => s.addShape(SH.LINE, { x, y, w, h, line: { color: k.accent, width: 1.5 } });
    L(fx, fy, t, 0); L(fx, fy, 0, t); L(fx + fw - t, fy, t, 0); L(fx + fw, fy, 0, t);
    L(fx, fy + fh, t, 0); L(fx, fy + fh - t, 0, t); L(fx + fw - t, fy + fh, t, 0); L(fx + fw, fy + fh - t, 0, t);
  }
  function card(s, x, y, w, h) {
    const st = k.cardStyle;
    if (st === "shadow") s.addShape(SH.RECTANGLE, { x, y, w, h, fill: { color: k.cardFill }, line: { color: k.cardBorder, width: 1 }, shadow: shadow() });
    else if (st === "flat") s.addShape(SH.RECTANGLE, { x, y, w, h, fill: { color: k.cardFill }, line: { color: k.cardBorder, width: 1.25 } });
    else if (st === "tint") s.addShape(SH.RECTANGLE, { x, y, w, h, fill: { color: k.cardFill }, line: { type: "none" } });
    else if (st === "darkpanel") s.addShape(SH.RECTANGLE, { x, y, w, h, fill: { color: k.cardFill }, line: { color: k.cardBorder, width: 1 } });
    else if (st === "rule") { s.addShape(SH.RECTANGLE, { x, y, w, h, fill: { color: k.cardFill }, line: { type: "none" } }); s.addShape(SH.LINE, { x, y, w, h: 0, line: { color: k.ink, width: 2 } }); }
    else if (st === "tab") s.addShape(SH.RECTANGLE, { x, y, w: 0.3, h: 0.1, fill: { color: k.accent }, line: { type: "none" } });
    // "plain": nothing
  }
  function panel(s, x, y, w, h) {
    s.addShape(SH.RECTANGLE, { x, y, w, h, fill: { color: k.panelFill }, line: { type: "none" } });
    s.addShape(SH.RECTANGLE, { x, y, w: 0.1, h, fill: { color: k.panelAccent }, line: { type: "none" } });
  }
  function statCard(s, x, y, w, h, hot) {
    const st = k.cardStyle, acc = hot ? k.accent : k.primary;
    if (st === "rule") { s.addShape(SH.LINE, { x, y, w, h: 0, line: { color: hot ? k.accent : k.ink, width: 2.5 } }); return; }
    if (st === "plain") { s.addShape(SH.LINE, { x, y, w, h: 0, line: { color: hot ? k.accent : k.ink, width: 2 } }); return; }
    if (st === "tab") { s.addShape(SH.RECTANGLE, { x, y, w: 0.3, h: 0.1, fill: { color: acc }, line: { type: "none" } }); return; }
    card(s, x, y, w, h);
    s.addShape(SH.RECTANGLE, { x, y, w, h: 0.07, fill: { color: acc }, line: { type: "none" } });
  }
  function chartOpts(extra) {
    return Object.assign({
      chartArea: { fill: { color: k.chartArea } },
      catAxisLabelColor: k.chartAxis, catAxisLabelFontFace: KR, catAxisLabelFontSize: 11,
      valAxisLabelColor: k.chartAxis, valAxisLabelFontFace: KR, valAxisLabelFontSize: 10,
      valGridLine: { color: k.chartGrid, size: 0.75 }, catGridLine: { style: "none" },
      dataLabelFontFace: KR, dataLabelFontSize: 10, dataLabelColor: k.chartLabel,
      chartColors: k.chartColors, showLegend: false, showTitle: false,
    }, extra || {});
  }
  function th(t) { return { text: t, options: { fill: { color: k.tHeadFill }, color: k.tHeadInk, bold: true, fontSize: 11.5, align: "center", valign: "middle" } }; }

  // ---- header chrome → returns content-area rect ----
  function frame(s, kicker, title) {
    PNUM++;
    s.background = { color: k.bg };
    const pg = String(PNUM).padStart(2, "0");
    if (k.layout === "minimal" || k.layout === "dark") {
      const ix = k.layout === "dark" ? 0.85 : 0.62;
      if (k.layout === "dark") s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: 0.12, h: H, fill: { color: k.primary }, line: { type: "none" } });
      s.addShape(SH.RECTANGLE, { x: ix, y: 0.5, w: 0.16, h: 0.16, fill: { color: k.primary }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: ix + 0.26, y: 0.44, w: 9, h: 0.3, fontFace: KR, fontSize: 11, bold: true, color: k.primary, charSpacing: 2, margin: 0 });
      s.addText(title, { x: ix, y: 0.78, w: W - ix - 1.1, h: 0.72, fontFace: KR, fontSize: 26, bold: true, color: k.ink, margin: 0, valign: "top" });
      s.addText(pg, { x: W - 1.25, y: 0.46, w: 0.7, h: 0.4, fontFace: KR, fontSize: 13, bold: true, color: k.muted, align: "right", margin: 0 });
      s.addText("/ " + TOTAL, { x: W - 1.25, y: 0.74, w: 0.7, h: 0.25, fontFace: KR, fontSize: 9, color: k.muted, align: "right", margin: 0 });
      s.addShape(SH.LINE, { x: ix, y: 7.04, w: W - ix - 0.62, h: 0, line: { color: k.line, width: 1 } });
      if (opts.footer) s.addText(opts.footer, { x: ix, y: 7.08, w: 11, h: 0.3, fontFace: KR, fontSize: 9, color: k.muted, margin: 0 });
      return { x: ix, y: 1.72, w: W - ix - 0.62, h: 5.18 };
    }
    if (k.layout === "band") {
      s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: W, h: 1.18, fill: { color: k.primary2 }, line: { type: "none" } });
      s.addShape(SH.RECTANGLE, { x: 0, y: 1.18, w: W, h: 0.06, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 0.7, y: 0.2, w: 9, h: 0.28, fontFace: KR, fontSize: 11, bold: true, color: k.accent2, charSpacing: 2, margin: 0 });
      s.addText(title, { x: 0.7, y: 0.5, w: 11, h: 0.62, fontFace: KR, fontSize: 22, bold: true, color: "FFFFFF", margin: 0, valign: "middle" });
      s.addText(pg + " / " + TOTAL, { x: W - 1.7, y: 0.2, w: 1.0, h: 0.8, fontFace: KR, fontSize: 14, bold: true, color: "FFFFFF", align: "right", valign: "middle", margin: 0 });
      if (opts.footer) s.addText(opts.footer, { x: 0.7, y: 7.12, w: 11, h: 0.3, fontFace: KR, fontSize: 9, color: k.muted, margin: 0 });
      return { x: 0.7, y: 1.55, w: W - 1.4, h: 5.4 };
    }
    if (k.layout === "sidebar") {
      const sw = 2.7;
      s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: sw, h: H, fill: { color: k.primary2 }, line: { type: "none" } });
      s.addText(opts.brand || "", { x: 0.32, y: 0.4, w: sw - 0.5, h: 0.35, fontFace: KR, fontSize: 15, bold: true, color: "FFFFFF", charSpacing: 3, margin: 0 });
      s.addShape(SH.RECTANGLE, { x: 0.34, y: 0.86, w: 0.5, h: 0.08, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 0.34, y: 2.0, w: sw - 0.6, h: 1.0, fontFace: KR, fontSize: 11, bold: true, color: k.accent2, charSpacing: 2, margin: 0, valign: "top" });
      s.addText(pg, { x: 0.3, y: 5.7, w: sw - 0.6, h: 0.8, fontFace: KR, fontSize: 44, bold: true, color: "FFFFFF", margin: 0 });
      s.addText("/ " + TOTAL, { x: 0.36, y: 6.5, w: sw - 0.6, h: 0.3, fontFace: KR, fontSize: 12, color: k.sideMuted, margin: 0 });
      s.addText(title, { x: sw + 0.32, y: 0.62, w: W - sw - 0.95, h: 0.82, fontFace: KR, fontSize: 23, bold: true, color: k.ink, margin: 0, valign: "middle" });
      return { x: sw + 0.32, y: 1.62, w: W - sw - 0.95, h: 5.25 };
    }
    if (k.layout === "swiss") {
      s.addShape(SH.LINE, { x: 0.62, y: 0.42, w: W - 1.24, h: 0, line: { color: k.ink, width: 3 } });
      s.addShape(SH.RECTANGLE, { x: 0.62, y: 0.62, w: 0.15, h: 0.15, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 0.85, y: 0.57, w: 9, h: 0.28, fontFace: KR, fontSize: 11, bold: true, color: k.ink, charSpacing: 3, margin: 0 });
      s.addText(title, { x: 0.6, y: 0.92, w: W - 2.4, h: 0.7, fontFace: KR, fontSize: 27, bold: true, color: k.ink, margin: 0, valign: "top" });
      s.addText(pg, { x: W - 1.8, y: 0.5, w: 1.18, h: 0.6, fontFace: KR, fontSize: 30, bold: true, color: k.accent, align: "right", margin: 0 });
      s.addText("/ " + TOTAL, { x: W - 1.8, y: 1.12, w: 1.18, h: 0.25, fontFace: KR, fontSize: 10, color: k.muted, align: "right", margin: 0 });
      if (opts.footer) s.addText(opts.footer, { x: 0.62, y: 7.12, w: 11, h: 0.3, fontFace: KR, fontSize: 9, color: k.muted, margin: 0 });
      return { x: 0.62, y: 1.85, w: W - 1.24, h: 5.0 };
    }
    if (k.layout === "margin") {
      const rx = 1.7;
      s.addShape(SH.LINE, { x: rx, y: 0.4, w: 0, h: 6.7, line: { color: k.ink, width: 2.5 } });
      s.addShape(SH.RECTANGLE, { x: 0.5, y: 0.45, w: 0.4, h: 0.12, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 0.45, y: 0.66, w: 1.15, h: 1.3, fontFace: KR, fontSize: 10, bold: true, color: k.muted, charSpacing: 1, valign: "top", margin: 0 });
      s.addText(pg, { x: 0.42, y: 5.7, w: 1.15, h: 0.7, fontFace: MONO, fontSize: 40, bold: true, color: k.ink, margin: 0 });
      s.addText("/ " + TOTAL, { x: 0.46, y: 6.46, w: 1.1, h: 0.3, fontFace: MONO, fontSize: 11, color: k.muted, margin: 0 });
      s.addText(title, { x: rx + 0.3, y: 0.6, w: W - rx - 0.9, h: 0.85, fontFace: KR, fontSize: 24, bold: true, color: k.ink, valign: "middle", margin: 0 });
      if (opts.footer) s.addText(opts.footer, { x: rx + 0.3, y: 7.12, w: 10, h: 0.3, fontFace: KR, fontSize: 9, color: k.muted, margin: 0 });
      return { x: rx + 0.3, y: 1.62, w: W - rx - 0.9, h: 5.25 };
    }
    if (k.layout === "framed") {
      s.addShape(SH.RECTANGLE, { x: 0.5, y: 0.45, w: W - 1.0, h: 6.55, fill: { type: "none" }, line: { color: k.ink, width: 1.5 } });
      s.addShape(SH.RECTANGLE, { x: 0.8, y: 0.72, w: 0.15, h: 0.15, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 1.05, y: 0.68, w: 9, h: 0.28, fontFace: KR, fontSize: 10.5, bold: true, color: k.muted, charSpacing: 2, margin: 0 });
      s.addText(title, { x: 0.8, y: 1.0, w: W - 2.6, h: 0.6, fontFace: KR, fontSize: 23, bold: true, color: k.ink, valign: "top", margin: 0 });
      s.addText(pg + " / " + TOTAL, { x: W - 2.1, y: 0.7, w: 1.4, h: 0.4, fontFace: MONO, fontSize: 14, bold: true, color: k.accent, align: "right", margin: 0 });
      s.addShape(SH.LINE, { x: 0.5, y: 1.7, w: W - 1.0, h: 0, line: { color: k.line, width: 1 } });
      if (opts.footer) s.addText(opts.footer, { x: 0.85, y: 6.74, w: 10, h: 0.25, fontFace: KR, fontSize: 8.5, color: k.muted, margin: 0 });
      return { x: 0.85, y: 1.9, w: W - 1.7, h: 4.78 };
    }
    if (k.layout === "register") {
      cornerMarks(s, 0.55, 0.45, W - 1.1, 6.55, 0.24);
      s.addShape(SH.RECTANGLE, { x: 0.7, y: 0.6, w: 0.15, h: 0.15, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 0.95, y: 0.56, w: 9, h: 0.28, fontFace: KR, fontSize: 10.5, bold: true, color: k.muted, charSpacing: 2, margin: 0 });
      s.addText(title, { x: 0.68, y: 0.9, w: W - 2.4, h: 0.7, fontFace: KR, fontSize: 25, bold: true, color: k.ink, valign: "top", margin: 0 });
      s.addText(pg, { x: W - 1.75, y: 0.58, w: 1.1, h: 0.55, fontFace: MONO, fontSize: 26, bold: true, color: k.accent, align: "right", margin: 0 });
      s.addText("/ " + TOTAL, { x: W - 1.75, y: 1.13, w: 1.1, h: 0.25, fontFace: MONO, fontSize: 10, color: k.muted, align: "right", margin: 0 });
      if (opts.footer) s.addText(opts.footer, { x: 0.75, y: 7.12, w: 10, h: 0.3, fontFace: KR, fontSize: 9, color: k.muted, margin: 0 });
      return { x: 0.78, y: 1.7, w: W - 1.56, h: 5.05 };
    }
    if (k.layout === "datasheet") {
      s.addShape(SH.RECTANGLE, { x: 0.62, y: 0.42, w: W - 1.24, h: 0.46, fill: { type: "none" }, line: { color: k.ink, width: 1 } });
      const fields = opts.meta || [["DOC", "—"], ["REV", "1.0"], ["DATE", opts.date || ""], ["PAGE", pg + "/" + TOTAL]];
      const fwid = (W - 1.24) / fields.length;
      fields.forEach((f, i) => { const x = 0.62 + i * fwid; if (i) s.addShape(SH.LINE, { x, y: 0.42, w: 0, h: 0.46, line: { color: k.line, width: 1 } }); s.addText([{ text: f[0] + "  ", options: { color: k.muted, fontSize: 9 } }, { text: f[1], options: { color: k.ink, bold: true, fontSize: 10 } }], { x: x + 0.16, y: 0.42, w: fwid - 0.2, h: 0.46, fontFace: MONO, valign: "middle", margin: 0 }); });
      s.addText("▸", { x: 0.62, y: 1.06, w: 0.3, h: 0.4, fontFace: KR, fontSize: 16, bold: true, color: k.accent, margin: 0 });
      s.addText(kicker.toUpperCase(), { x: 0.95, y: 1.06, w: 9, h: 0.28, fontFace: KR, fontSize: 10.5, bold: true, color: k.muted, charSpacing: 2, margin: 0 });
      s.addText(title, { x: 0.6, y: 1.36, w: W - 1.3, h: 0.6, fontFace: KR, fontSize: 23, bold: true, color: k.ink, valign: "top", margin: 0 });
      s.addShape(SH.LINE, { x: 0.62, y: 7.04, w: W - 1.24, h: 0, line: { color: k.line, width: 1 } });
      if (opts.footer) s.addText(opts.footer, { x: 0.62, y: 7.08, w: 11, h: 0.3, fontFace: MONO, fontSize: 8.5, color: k.muted, margin: 0 });
      return { x: 0.62, y: 2.06, w: W - 1.24, h: 4.85 };
    }
    if (k.layout === "tabgrid") {
      s.addShape(SH.LINE, { x: 0.62, y: 0.5, w: W - 1.24, h: 0, line: { color: k.line, width: 1 } });
      s.addShape(SH.RECTANGLE, { x: 0.62, y: 0.66, w: 0.34, h: 0.13, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(kicker.toUpperCase(), { x: 1.06, y: 0.62, w: 9, h: 0.28, fontFace: KR, fontSize: 10.5, bold: true, color: k.muted, charSpacing: 2, margin: 0 });
      s.addText(title, { x: 0.6, y: 0.94, w: W - 2.2, h: 0.66, fontFace: KR, fontSize: 25, bold: true, color: k.ink, valign: "top", margin: 0 });
      s.addText(pg, { x: W - 1.7, y: 0.54, w: 1.08, h: 0.6, fontFace: MONO, fontSize: 30, bold: true, color: k.accent, align: "right", margin: 0 });
      s.addText("/ " + TOTAL, { x: W - 1.7, y: 1.15, w: 1.08, h: 0.25, fontFace: MONO, fontSize: 10, color: k.muted, align: "right", margin: 0 });
      if (opts.footer) s.addText(opts.footer, { x: 0.62, y: 7.12, w: 10, h: 0.3, fontFace: KR, fontSize: 9, color: k.muted, margin: 0 });
      return { x: 0.62, y: 1.78, w: W - 1.24, h: 5.05 };
    }
  }

  // ---- numbers row helpers for title/closing ----
  function numbersRowSwiss(s, tx, y, stats) {
    if (!stats || !stats.length) return;
    const aw = W - tx - 0.6, nw = aw / stats.length;
    s.addShape(SH.LINE, { x: tx, y, w: aw, h: 0, line: { color: k.line, width: 1 } });
    stats.forEach((n, i) => { const x = tx + i * nw; if (i) s.addShape(SH.LINE, { x, y: y + 0.22, w: 0, h: 1.05, line: { color: k.line, width: 1 } }); s.addText(n.v, { x: x + 0.08, y: y + 0.3, w: nw - 0.2, h: 0.55, fontFace: KR, fontSize: 26, bold: true, color: i === stats.length - 1 ? k.accent : k.ink, margin: 0 }); s.addText(n.label, { x: x + 0.08, y: y + 0.88, w: nw - 0.2, h: 0.3, fontFace: KR, fontSize: 11, color: k.muted, margin: 0 }); });
  }
  function numberCards(s, y, stats, cardH) {
    if (!stats || !stats.length) return;
    const nw = 2.78, gap = 0.3, total = stats.length * nw + (stats.length - 1) * gap, sx = (W - total) / 2;
    stats.forEach((n, i) => { const x = sx + i * (nw + gap), hot = i === stats.length - 1; statCard(s, x, y, nw, cardH || 1.18, hot); s.addText(n.v, { x, y: y + 0.17, w: nw, h: 0.6, fontFace: KR, fontSize: 26, bold: true, color: hot ? k.accent : k.statNum, align: "center", margin: 0 }); s.addText(n.label, { x, y: y + 0.77, w: nw, h: 0.3, fontFace: KR, fontSize: 11, color: k.muted, align: "center", margin: 0 }); });
  }

  // ---- title slide ----
  function title(o) {
    o = o || {};
    const s = pres.addSlide();
    const eyebrow = o.eyebrow || "", titleTxt = o.title || "", subtitle = o.subtitle || "", date = o.date || "", source = o.source || "";
    if (k.fam === "swiss2") {
      s.background = { color: k.bg };
      if (k.layout === "margin") s.addShape(SH.LINE, { x: 1.7, y: 0.6, w: 0, h: 6.3, line: { color: k.ink, width: 3 } });
      else if (k.layout === "framed") s.addShape(SH.RECTANGLE, { x: 0.5, y: 0.5, w: W - 1.0, h: 6.5, fill: { type: "none" }, line: { color: k.ink, width: 1.5 } });
      else if (k.layout === "register") cornerMarks(s, 0.55, 0.5, W - 1.1, 6.5, 0.3);
      else if (k.layout === "datasheet") { s.addShape(SH.RECTANGLE, { x: 0.62, y: 0.5, w: W - 1.24, h: 0.5, fill: { type: "none" }, line: { color: k.ink, width: 1 } }); s.addText(o.metaLine || (eyebrow), { x: 0.82, y: 0.5, w: 11.5, h: 0.5, fontFace: MONO, fontSize: 10, color: k.ink, valign: "middle", margin: 0 }); }
      else if (k.layout === "tabgrid") s.addShape(SH.RECTANGLE, { x: 0.62, y: 1.6, w: 0.55, h: 0.16, fill: { color: k.accent }, line: { type: "none" } });
      const tx = k.layout === "margin" ? 2.1 : 0.85, ty = k.layout === "datasheet" ? 1.35 : 1.85;
      s.addText(eyebrow, { x: tx, y: ty, w: 9, h: 0.4, fontFace: KR, fontSize: 14, bold: true, color: k.accent, charSpacing: 1, margin: 0 });
      s.addText(titleTxt, { x: tx - 0.03, y: ty + 0.45, w: 11.6, h: 0.95, fontFace: KR, fontSize: 50, bold: true, color: k.ink, margin: 0 });
      if (subtitle) s.addText(subtitle, { x: tx, y: ty + 1.6, w: 11.5, h: 0.6, fontFace: KR, fontSize: 23, bold: true, color: k.accent, margin: 0 });
      if (o.tagline) s.addText(asRich(o.tagline), { x: tx, y: ty + 2.4, w: 11.5, h: 0.5, fontFace: KR, fontSize: 15, color: k.muted, margin: 0 });
      numbersRowSwiss(s, tx, 5.2, o.stats);
      if (date) s.addText(date, { x: tx, y: 6.75, w: 8, h: 0.3, fontFace: KR, fontSize: 11, color: k.muted, margin: 0 });
      return s;
    }
    if (k.layout === "minimal" || k.layout === "dark") {
      s.background = { color: k.titleBg };
      const cx = 10.65, cy = 3.9;
      [2.95, 2.30, 1.68, 1.10, 0.58].forEach((r, i) => s.addShape(SH.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color: i % 2 ? k.accent2 : k.primary, width: i === 0 ? 1.25 : 1.0, transparency: 22 + i * 8 } }));
      s.addShape(SH.OVAL, { x: cx - 0.18, y: cy - 0.18, w: 0.36, h: 0.36, fill: { color: k.accent }, line: { type: "none" } });
      s.addShape(SH.RECTANGLE, { x: 0.85, y: 1.55, w: 0.55, h: 0.1, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(eyebrow, { x: 0.85, y: 1.75, w: 8.2, h: 0.4, fontFace: KR, fontSize: 14, bold: true, color: k.accent2, charSpacing: 1, margin: 0 });
      s.addText(titleTxt, { x: 0.82, y: 2.22, w: 8.6, h: 0.85, fontFace: KR, fontSize: 46, bold: true, color: "FFFFFF", margin: 0 });
      if (subtitle) s.addText(subtitle, { x: 0.85, y: 3.12, w: 8.6, h: 0.6, fontFace: KR, fontSize: 27, bold: true, color: k.accent2, margin: 0 });
      if (o.tagline) s.addText(asRich(o.tagline), { x: 0.85, y: 4.05, w: 9.0, h: 0.5, fontFace: KR, fontSize: 16, color: k.titleSub, margin: 0 });
      if (source) { s.addShape(SH.LINE, { x: 0.85, y: 5.05, w: 7.4, h: 0, line: { color: k.titleLine, width: 1 } }); s.addText(source, { x: 0.85, y: 5.18, w: 8.5, h: 0.8, fontFace: KR, fontSize: 12, color: k.titleSub, lineSpacingMultiple: 1.3, margin: 0 }); }
      if (date) s.addText(date, { x: 0.85, y: 6.75, w: 8, h: 0.3, fontFace: KR, fontSize: 11, color: k.titleFaint, margin: 0 });
      return s;
    }
    if (k.layout === "band") {
      s.background = { color: k.bg };
      s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: W, h: 4.35, fill: { color: k.primary2 }, line: { type: "none" } });
      s.addShape(SH.RECTANGLE, { x: 0, y: 4.35, w: W, h: 0.08, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(eyebrow, { x: 0.9, y: 1.25, w: 11, h: 0.4, fontFace: KR, fontSize: 15, bold: true, color: k.accent2, charSpacing: 1, margin: 0 });
      s.addText(titleTxt, { x: 0.87, y: 1.75, w: 11.5, h: 0.95, fontFace: KR, fontSize: 50, bold: true, color: "FFFFFF", margin: 0 });
      if (subtitle) s.addText(subtitle, { x: 0.9, y: 2.95, w: 11.5, h: 0.5, fontFace: KR, fontSize: 18, bold: true, color: k.accent2, margin: 0 });
      numberCards(s, 4.95, o.stats);
      if (date) s.addText(date, { x: 0, y: 6.7, w: W, h: 0.3, fontFace: KR, fontSize: 11, color: k.muted, align: "center", margin: 0 });
      return s;
    }
    if (k.layout === "sidebar") {
      s.background = { color: k.bg };
      s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: 5.0, h: H, fill: { color: k.primary2 }, line: { type: "none" } });
      s.addText(opts.brand || eyebrow, { x: 0.55, y: 0.55, w: 4, h: 0.4, fontFace: KR, fontSize: 16, bold: true, color: "FFFFFF", charSpacing: 3, margin: 0 });
      s.addShape(SH.RECTANGLE, { x: 0.57, y: 2.0, w: 0.6, h: 0.1, fill: { color: k.accent }, line: { type: "none" } });
      s.addText(eyebrow, { x: 0.57, y: 2.2, w: 4, h: 0.4, fontFace: KR, fontSize: 14, bold: true, color: k.accent2, margin: 0 });
      s.addText(titleTxt, { x: 0.53, y: 2.7, w: 4.2, h: 2.2, fontFace: KR, fontSize: 36, bold: true, color: "FFFFFF", lineSpacingMultiple: 1.0, margin: 0 });
      if (date) s.addText(date, { x: 0.57, y: 6.75, w: 4, h: 0.3, fontFace: KR, fontSize: 10, color: k.sideMuted, margin: 0 });
      const cx = 9.1, cy = 3.75;
      [2.5, 1.85, 1.2, 0.62].forEach((r, i) => s.addShape(SH.OVAL, { x: cx - r, y: cy - r, w: 2 * r, h: 2 * r, fill: { type: "none" }, line: { color: i % 2 ? k.accent2 : k.primary, width: 1.1 } }));
      s.addShape(SH.OVAL, { x: cx - 0.16, y: cy - 0.16, w: 0.32, h: 0.32, fill: { color: k.accent }, line: { type: "none" } });
      if (subtitle) s.addText(subtitle, { x: 5.5, y: 0.9, w: 7, h: 1.0, fontFace: KR, fontSize: 24, bold: true, color: k.ink, lineSpacingMultiple: 1.05, margin: 0 });
      if (o.tagline) s.addText(asRich(o.tagline), { x: 5.5, y: 6.2, w: 7.3, h: 0.5, fontFace: KR, fontSize: 14, color: k.muted, margin: 0 });
      return s;
    }
  }

  // ---- closing slide ----
  function closing(o) {
    o = o || {};
    const s = pres.addSlide();
    const eyebrow = o.eyebrow || "", titleTxt = o.title || "", date = o.date || "", body = o.body ? asRich(o.body) : null, stats = o.stats;
    if (k.fam === "swiss2") {
      s.background = { color: k.bg };
      if (k.layout === "framed") s.addShape(SH.RECTANGLE, { x: 0.5, y: 0.5, w: W - 1.0, h: 6.5, fill: { type: "none" }, line: { color: k.ink, width: 1.5 } });
      else if (k.layout === "register") cornerMarks(s, 0.55, 0.5, W - 1.1, 6.5, 0.3);
      else if (k.layout === "margin") s.addShape(SH.LINE, { x: 1.7, y: 0.6, w: 0, h: 6.3, line: { color: k.ink, width: 3 } });
      const tx = k.layout === "margin" ? 2.1 : 0.85;
      s.addShape(SH.RECTANGLE, { x: tx, y: 0.95, w: 0.5, h: 0.14, fill: { color: k.accent }, line: { type: "none" } });
      if (eyebrow) s.addText(eyebrow, { x: tx, y: 1.18, w: 10, h: 0.35, fontFace: KR, fontSize: 14, bold: true, color: k.accent, charSpacing: 1, margin: 0 });
      s.addText(titleTxt, { x: tx - 0.02, y: 1.55, w: 11, h: 0.8, fontFace: KR, fontSize: 40, bold: true, color: k.ink, margin: 0 });
      if (body) s.addText(body, { x: tx, y: 2.75, w: W - tx - 0.7, h: 2.0, fontFace: KR, fontSize: 15, lineSpacingMultiple: 1.42, valign: "top", margin: 0 });
      numbersRowSwiss(s, tx, 5.15, stats);
      if (date) s.addText(date, { x: tx, y: 6.75, w: 10, h: 0.3, fontFace: KR, fontSize: 10, color: k.muted, margin: 0 });
      return s;
    }
    if (k.layout === "minimal" || k.layout === "dark") {
      s.background = { color: k.titleBg };
      s.addShape(SH.RECTANGLE, { x: 0.85, y: 0.7, w: 0.55, h: 0.1, fill: { color: k.accent }, line: { type: "none" } });
      if (eyebrow) s.addText(eyebrow, { x: 0.85, y: 0.88, w: 10, h: 0.4, fontFace: KR, fontSize: 14, bold: true, color: k.accent2, charSpacing: 1, margin: 0 });
      s.addText(titleTxt, { x: 0.82, y: 1.3, w: 11, h: 0.7, fontFace: KR, fontSize: 34, bold: true, color: "FFFFFF", margin: 0 });
      if (body) { s.addShape(SH.RECTANGLE, { x: 0.85, y: 2.25, w: 11.6, h: 2.75, fill: { color: k.cCard }, line: { color: k.titleLine, width: 1 } }); s.addShape(SH.RECTANGLE, { x: 0.85, y: 2.25, w: 0.11, h: 2.75, fill: { color: k.accent }, line: { type: "none" } }); s.addText(body, { x: 1.25, y: 2.5, w: 10.9, h: 2.3, fontFace: KR, fontSize: 15, lineSpacingMultiple: 1.4, valign: "middle", margin: 0 }); }
      if (stats && stats.length) { const nw = 2.7, gap = 0.27, total = stats.length * nw + (stats.length - 1) * gap, sx = (W - total) / 2; stats.forEach((n, i) => { const x = sx + i * (nw + gap), hot = i === stats.length - 1; s.addShape(SH.RECTANGLE, { x, y: 5.45, w: nw, h: 1.15, fill: { color: k.cCard }, line: { color: k.titleLine, width: 1 } }); s.addShape(SH.RECTANGLE, { x, y: 5.45, w: nw, h: 0.07, fill: { color: hot ? k.accent : k.primary }, line: { type: "none" } }); s.addText(n.v, { x, y: 5.6, w: nw, h: 0.6, fontFace: KR, fontSize: 27, bold: true, color: hot ? k.accent : "FFFFFF", align: "center", margin: 0 }); s.addText(n.label, { x, y: 6.18, w: nw, h: 0.3, fontFace: KR, fontSize: 11, color: k.titleSub, align: "center", margin: 0 }); }); }
      if (date) s.addText(date, { x: 0, y: 7.0, w: W, h: 0.3, fontFace: KR, fontSize: 10, color: k.titleFaint, align: "center", margin: 0 });
      return s;
    }
    if (k.layout === "band") {
      s.background = { color: k.bg };
      s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: W, h: 1.18, fill: { color: k.primary2 }, line: { type: "none" } });
      s.addShape(SH.RECTANGLE, { x: 0, y: 1.18, w: W, h: 0.06, fill: { color: k.accent }, line: { type: "none" } });
      if (eyebrow) s.addText(eyebrow, { x: 0.7, y: 0.2, w: 9, h: 0.28, fontFace: KR, fontSize: 11, bold: true, color: k.accent2, charSpacing: 2, margin: 0 });
      s.addText(titleTxt, { x: 0.7, y: 0.5, w: 11, h: 0.62, fontFace: KR, fontSize: 22, bold: true, color: "FFFFFF", valign: "middle", margin: 0 });
      if (body) { card(s, 0.7, 1.6, W - 1.4, 2.95); s.addShape(SH.RECTANGLE, { x: 0.7, y: 1.6, w: 0.1, h: 2.95, fill: { color: k.accent }, line: { type: "none" } }); s.addText(body, { x: 1.1, y: 1.85, w: W - 2.0, h: 2.45, fontFace: KR, fontSize: 15, lineSpacingMultiple: 1.4, valign: "middle", margin: 0 }); }
      numberCards(s, 4.85, stats, 1.2);
      if (date) s.addText(date, { x: 0, y: 6.6, w: W, h: 0.3, fontFace: KR, fontSize: 10, color: k.muted, align: "center", margin: 0 });
      return s;
    }
    if (k.layout === "sidebar") {
      s.background = { color: k.bg };
      s.addShape(SH.RECTANGLE, { x: 0, y: 0, w: 4.4, h: H, fill: { color: k.primary2 }, line: { type: "none" } });
      s.addShape(SH.RECTANGLE, { x: 0.55, y: 1.2, w: 0.6, h: 0.1, fill: { color: k.accent }, line: { type: "none" } });
      if (eyebrow) s.addText(eyebrow, { x: 0.55, y: 1.4, w: 3.5, h: 0.4, fontFace: KR, fontSize: 14, bold: true, color: k.accent2, margin: 0 });
      s.addText(titleTxt, { x: 0.52, y: 1.85, w: 3.7, h: 1.5, fontFace: KR, fontSize: 34, bold: true, color: "FFFFFF", lineSpacingMultiple: 1.0, margin: 0 });
      if (date) s.addText(date, { x: 0.55, y: 6.75, w: 3.6, h: 0.3, fontFace: KR, fontSize: 10, color: k.sideMuted, margin: 0 });
      if (body) s.addText(body, { x: 4.85, y: 0.85, w: 7.9, h: 3.3, fontFace: KR, fontSize: 15, lineSpacingMultiple: 1.42, valign: "top", margin: 0 });
      if (stats && stats.length) { const aw = 7.9, nw = (aw - 0.6) / stats.length, gap = 0.2; stats.forEach((n, i) => { const x = 4.85 + i * (nw + gap), hot = i === stats.length - 1; statCard(s, x, 4.9, nw, 1.3, hot); s.addText(n.v, { x, y: 5.12, w: nw, h: 0.6, fontFace: KR, fontSize: 22, bold: true, color: hot ? k.accent : k.statNum, align: "center", margin: 0 }); s.addText(n.label, { x, y: 5.75, w: nw, h: 0.3, fontFace: KR, fontSize: 10, color: k.muted, align: "center", margin: 0 }); }); }
      return s;
    }
  }

  return {
    pres, k, KR, MONO, W, H, shapes: SH, charts: CH,
    content: (kicker, title) => { const s = pres.addSlide(); const A = frame(s, kicker, title); return { slide: s, s, area: A, A, k }; },
    title, closing, card, panel, statCard, chartOpts, cornerMarks, th,
    save: (file) => pres.writeFile({ fileName: file }),
  };
}

module.exports = { LAYOUTS, makeDeck, W, H, KR };
