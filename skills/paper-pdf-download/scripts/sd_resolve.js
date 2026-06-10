// Custom ScienceDirect PDF link extractor (SPA-aware). Reads resolve.json {input}.
// Polls until the article shell hydrates and a pdfft/pdf anchor appears.
const job = JSON.parse(await readFile("resolve.json"));
const input = String(job.input || "").trim();
const target = /^10\.\d{4,9}\//.test(input) ? "https://doi.org/" + input : input;

const page = await browser.getPage("dl");
await page.goto(target, { waitUntil: "load", timeout: 60000 }).catch(() => {});

const reCf = /just a moment|잠시만|verifying|attention required|checking your browser|captcha|please wait|redirecting/i;
let info = null;
for (let i = 0; i < 25; i++) {
  await new Promise(r => setTimeout(r, 2500));
  try {
    info = await page.evaluate(() => {
      const loc = location;
      const anchors = Array.from(document.querySelectorAll("a"))
        .map(a => ({ t: (a.textContent || "").trim().slice(0, 30), href: a.href }))
        .filter(x => x.href && /pdfft|\/pdf\b|\.pdf(\?|$)/i.test(x.href));
      return { landing: loc.href, title: document.title.slice(0, 120), host: loc.host, anchors };
    });
  } catch (e) { continue; } // navigation in flight (CF redirect) — retry next tick
  const t = (info && info.title) || "";
  if (info && !reCf.test(t) && info.anchors.length) break;
}

let pdfUrl = null;
if (info && info.anchors.length) {
  const full = info.anchors.find(a => /pdfft/i.test(a.href)) ||
               info.anchors.find(a => !/figure|suppl|mmc/i.test(a.href)) || info.anchors[0];
  pdfUrl = full.href;
}
console.log(JSON.stringify({ landing: info && info.landing, title: info && info.title, host: info && info.host, pdfUrl, candidates: (info && info.anchors) || [] }, null, 2));
