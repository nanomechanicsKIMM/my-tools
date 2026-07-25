# layout-kits — reusable PptxGenJS layout library

10 interchangeable **layout kits** (palette + page chrome) for consultant-grade
16:9 decks. Write your content **once** against a content-area rectangle and the
bound helpers; switch the whole look by changing **one string** (the layout name).

Korean-ready (default font: `Apple SD Gothic Neo` on macOS, `맑은 고딕` on
Windows). Designed for technical/report
decks (tables, native charts, figures). Built and validated with `pptxgenjs` 4.x.

![contact sheet](contact-sheet.png)

## The 10 layouts

| name | family | signature motif | palette |
|------|--------|-----------------|---------|
| `minimal`   | modern  | top kicker+title, shadow cards | navy / teal / amber |
| `topband`   | modern  | full-width color band header, flat boxes | corporate blue |
| `sidebar`   | modern  | left full-height sidebar, tint blocks | deep teal |
| `dark`      | modern  | full dark mode, luminous panels | slate / cyan / amber |
| `swiss`     | swiss   | masthead rule + hairline grid (no boxes) | black / red |
| `margin`    | swiss   | left vertical rule + marginalia | off-white / brick red |
| `framed`    | swiss   | outer content frame box | white / mustard |
| `register`  | swiss   | corner register (trim) marks | white / cobalt |
| `datasheet` | swiss   | top DOC/REV/DATE/PAGE metastrip + mono | light / engineering green |
| `tabgrid`   | swiss   | per-card color tab markers | white / vermilion |

The 5 `swiss`-family layouts share the International Typographic DNA
(modular grid, hairline rules, no shadows, one sharp accent, big numerals).

## Install / requirements

`pptxgenjs` must be resolvable. The module tries `require("pptxgenjs")`; the
example also falls back to the global install. LibreOffice + poppler only needed
for rendering/QA (not for generation).

## API

```js
const pptxgen = require("pptxgenjs");
const { makeDeck, LAYOUTS } = require("./layouts.js");

const d = makeDeck(pptxgen, "swiss", {
  total: 6,                       // page count shown in "NN / total"
  title: "deck title (metadata)",
  author: "...", footer: "footer text (optional)",
  brand: "KIMM",                  // sidebar brand label
});
```

`makeDeck(pptxgen, layoutName, opts)` returns a **deck** object:

| member | description |
|--------|-------------|
| `d.title(o)` | add the title slide (page 1). `o`: `{eyebrow, title, subtitle, tagline, stats, source, date, metaLine}` |
| `d.content(kicker, title)` | add a content slide; returns `{ slide, area, k }`. `area` = `{x,y,w,h}` usable rect |
| `d.closing(o)` | add the closing slide. `o`: `{eyebrow, title, body, stats, date}` |
| `d.card(s,x,y,w,h)` | container in the kit's style (shadow/flat/tint/dark/rule/tab/plain) |
| `d.panel(s,x,y,w,h)` | emphasis panel (dark/colored block + accent bar) |
| `d.statCard(s,x,y,w,h,hot)` | stat container; `hot=true` uses the accent color |
| `d.chartOpts(extra)` | chart options pre-themed to the kit; merge your `{x,y,w,h,...}` |
| `d.th(text)` | a themed table header cell object |
| `d.cornerMarks(s,x,y,w,h,t)` | draw register marks |
| `d.k` | the kit color tokens (see below) |
| `d.shapes`, `d.charts` | `pres.shapes` / `pres.charts` |
| `d.KR`, `d.W`, `d.H` | font name, slide width 13.333, height 7.5 |
| `d.save(file)` | `pres.writeFile`; returns a Promise |

`stats` is `[{ v, label }]` (last item is auto-accented). `tagline`/`body`
accept a string **or** a pptxgenjs rich-text array.

### Kit color tokens (`d.k.*`)

`bg, ink, muted, line, cardFill, cardBorder, primary, primary2, accent, accent2,
panelFill, panelAccent, panelAccent2, panelInk, panelInk2, tHeadFill, tHeadInk,
rowA, rowB, rowHi, tBody, thMuted, chartColors, statNum, good, bad, slate,
barMuted, stack[5]`. Use these for every color so content adapts to light/dark
kits automatically — **never hardcode hex in content**.

## Coordinate model

All content positions are **relative to `area`** (`d.content().area`). Columns:

```js
const { slide: s, area: A } = d.content("KICKER", "Title");
const gap = 0.34, colW = (A.w - gap) / 2;
d.card(s, A.x, A.y, colW, A.h);                 // left column
d.card(s, A.x + colW + gap, A.y, colW, A.h);    // right column
```

Because layouts return different `area` rects (sidebar shifts x, band shifts y,
framed insets), the same fractional code reflows correctly across all 10.

## Minimal example

```js
const d = makeDeck(require("pptxgenjs"), "datasheet", { total: 3 });
d.title({ eyebrow: "REPORT", title: "제목", subtitle: "부제",
          stats: [{v:"42%",label:"지표"}], date: "2026-06-28" });
const { slide: s, area: A } = d.content("SECTION", "내용 슬라이드");
d.statCard(s, A.x, A.y, A.w/3 - 0.2, 1.6, true);
s.addText("42%", { x: A.x+0.3, y: A.y+0.5, w: 2, h: 0.8, fontFace: d.KR, fontSize: 40, bold: true, color: d.k.accent });
d.closing({ title: "결론", body: "요약 한 줄.", stats: [{v:"42%",label:"지표"}] });
await d.save("out.pptx");
```

Run the bundled demo (builds one or all 10):

```bash
node example.js swiss out.pptx     # one layout
node example.js                    # all 10 -> demo-<name>.pptx
```

## QA (render to images)

```bash
soffice --headless --convert-to pdf out.pptx
pdftoppm -jpeg -r 150 out.pdf slide      # slide-01.jpg ...
```

Dark/light handling, table fills, and chart theming are all driven by `d.k`, so a
visual pass per new content layout is still recommended (overflow, contrast).

## Notes

- Page numbering: `title()` = page 1 (no number shown); each `content()` auto-
  increments (02, 03, …); `closing()` shows no number. Set `opts.total` to match.
- `datasheet` uses `Consolas` for ASCII metadata/numerals (`opts.meta` overrides
  the DOC/REV/DATE/PAGE fields); Korean text always uses the default KR font.
- Animated GIFs embed via `slide.addImage({ path: "x.gif", ... })` and play in
  PowerPoint slideshow (static viewers show frame 1).
- Provenance: distilled from an internal KIMM technical-report deck project.
