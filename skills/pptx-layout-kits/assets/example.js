/*
 * example.js — minimal demo of the layout-kits library.
 *   node example.js [layoutName] [outFile]
 *   node example.js                  -> builds all 10 layouts to ./demo-<name>.pptx
 *   node example.js swiss out.pptx   -> builds one layout
 *
 * Requires pptxgenjs resolvable (npm i -g pptxgenjs, or local).
 */
const path = require("path");
let pptxgen;
try { pptxgen = require("pptxgenjs"); }
catch (e) { pptxgen = require("/opt/homebrew/lib/node_modules/pptxgenjs"); }
const { makeDeck, LAYOUTS } = require("./layouts.js");

function buildOne(name, outFile) {
  const d = makeDeck(pptxgen, name, { total: 4, title: "Demo — " + LAYOUTS[name].name, footer: "Demo · layout-kits", brand: "BRAND", date: "2026-06-28" });

  // 1) title
  d.title({
    eyebrow: "QUARTERLY REVIEW · 분기 검토",
    title: "데모 프레젠테이션",
    subtitle: "레이아웃 키트 재사용 예시",
    tagline: [{ text: "핵심 지표 3종  ·  ", options: { color: d.k.muted } }, { text: "전년 대비 +18%", options: { bold: true, color: d.k.accent } }],
    stats: [{ v: "+18%", label: "성장" }, { v: "92%", label: "만족도" }, { v: "1.2M", label: "사용자" }, { v: "0.4s", label: "응답" }],
    source: "출처: 데모 데이터셋",
    metaLine: "DOC: DEMO    REV: 1.0    DATE: 2026-06-28",
    date: "2026-06-28",
  });

  // 2) content slide — stat grid
  {
    const { slide: s, area: A } = d.content("Overview · 개요", "핵심 지표 한눈에 보기");
    const items = [["+18%", "성장률"], ["92%", "만족도"], ["1.2M", "사용자"]];
    const gap = 0.3, cw = (A.w - gap * 2) / 3;
    items.forEach((it, i) => {
      const x = A.x + i * (cw + gap);
      d.statCard(s, x, A.y, cw, 2.0, i === 2);
      s.addText(it[1], { x: x + 0.3, y: A.y + 0.3, w: cw - 0.6, h: 0.35, fontFace: d.KR, fontSize: 13, bold: true, color: d.k.muted, margin: 0 });
      s.addText(it[0], { x: x + 0.3, y: A.y + 0.75, w: cw - 0.6, h: 0.8, fontFace: d.KR, fontSize: 44, bold: true, color: i === 2 ? d.k.accent : d.k.statNum, margin: 0 });
    });
    d.panel(s, A.x, A.y + 2.4, A.w, A.h - 2.4);
    s.addText([{ text: "요약  ", options: { bold: true, color: d.k.panelAccent } }, { text: "모든 지표가 목표를 상회했습니다.", options: { color: d.k.panelInk } }],
      { x: A.x + 0.34, y: A.y + 2.4, w: A.w - 0.6, h: A.h - 2.4, fontFace: d.KR, fontSize: 14, valign: "middle", margin: 0 });
  }

  // 3) content slide — table + chart
  {
    const { slide: s, area: A } = d.content("Detail · 상세", "분기별 추이 및 비교");
    const half = (A.w - 0.34) / 2;
    s.addChart(d.charts.BAR, [{ name: "매출", labels: ["Q1", "Q2", "Q3", "Q4"], values: [4.5, 5.2, 6.1, 7.3] }],
      d.chartOpts({ x: A.x, y: A.y + 0.1, w: half, h: A.h - 0.4, barDir: "col", showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", valAxisMinVal: 0 }));
    const rows = [["Q1", "4.5", "—"], ["Q2", "5.2", "+16%"], ["Q3", "6.1", "+17%"], ["Q4", "7.3", "+20%"]];
    const body = rows.map((r, i) => r.map((c, j) => ({ text: c, options: { fill: { color: i % 2 ? d.k.rowB : d.k.rowA }, color: j === 0 ? d.k.statNum : d.k.tBody, bold: j === 0, fontSize: 12, align: j ? "center" : "left", valign: "middle" } })));
    s.addTable([[d.th("분기"), d.th("매출"), d.th("증감")], ...body], { x: A.x + half + 0.34, y: A.y + 0.1, w: half, colW: [half * 0.34, half * 0.33, half * 0.33], rowH: 0.6, border: { pt: 1, color: d.k.line }, fontFace: d.KR, valign: "middle" });
  }

  // 4) closing
  d.closing({
    eyebrow: "Summary · 요약",
    title: "결론",
    body: [{ text: "분기 전체에서 ", options: { color: d.k.tBody || d.k.cInk } }, { text: "두 자릿수 성장", options: { bold: true, color: d.k.accent } }, { text: "을 유지했습니다. 다음 분기 목표를 상향 조정합니다.", options: { color: d.k.tBody || d.k.cInk } }],
    stats: [{ v: "+18%", label: "성장" }, { v: "92%", label: "만족도" }, { v: "1.2M", label: "사용자" }, { v: "0.4s", label: "응답" }],
    date: "2026-06-28",
  });

  return d.save(outFile);
}

(async () => {
  const arg = process.argv[2];
  if (arg && LAYOUTS[arg]) {
    const out = process.argv[3] || path.join(process.cwd(), "demo-" + arg + ".pptx");
    console.log("WROTE: " + (await buildOne(arg, out)));
  } else {
    for (const name of Object.keys(LAYOUTS)) {
      const out = path.join(process.cwd(), "demo-" + name + ".pptx");
      console.log("WROTE: " + (await buildOne(name, out)));
    }
  }
})().catch((e) => { console.error("ERR", e && e.stack || e); process.exit(1); });
