// ScienceDirect one-shot: resolve fresh pdfft (for target PII) then trigger the
// cra_js_challenge download in a real (--connect) browser and re-fetch the CDN bytes.
// Reads job.json {article, pii, out}. Writes PDF to ~/.dev-browser/tmp/<out>.
const job = JSON.parse(await readFile("job.json"));
const page = await browser.getPage("dl");
const reCf = /just a moment|잠시만|verifying|attention required|checking your browser|captcha|please wait|redirecting/i;

async function settle(n) {
  for (let i = 0; i < (n || 15); i++) {
    const t = await page.title().catch(() => "");
    if (t && !reCf.test(t)) return t;
    await new Promise(r => setTimeout(r, 2000));
  }
  return await page.title().catch(() => "");
}

// 1) Load the article, clear CF, find the fresh pdfft URL for our PII.
await page.goto(job.article, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
await settle(20);
let pdfUrl = null;
for (let i = 0; i < 15; i++) {
  try {
    pdfUrl = await page.evaluate((pii) => {
      const a = Array.from(document.querySelectorAll("a"))
        .map(x => x.href).find(h => h && h.indexOf(pii + "/pdfft") !== -1);
      return a || null;
    }, job.pii);
  } catch (e) {}
  if (pdfUrl) break;
  await new Promise(r => setTimeout(r, 2000));
}
if (!pdfUrl) { console.log(JSON.stringify({ ok: false, error: "no pdfft url for pii" })); }
else {
  // 2) Navigate to pdfft; the JS challenge solves and triggers a download.
  let finalUrl = null;
  try {
    const dlPromise = page.waitForEvent("download", { timeout: 90000 });
    page.goto(pdfUrl).catch(() => {});
    const dl = await dlPromise;
    finalUrl = dl.url();
    try { await dl.cancel(); } catch (e) {}
  } catch (e) { /* no download fired; maybe inline PDF */ }

  // 3) Fetch the bytes. Prefer the captured CDN url (same-origin re-fetch); else
  //    try whatever the page navigated to.
  async function fetchInPage(u) {
    return await page.evaluate(async (url) => {
      try {
        const res = await fetch(url, { credentials: "include" });
        if (!res.ok) return { ok: false, status: res.status, ct: res.headers.get("content-type") || "" };
        const b = new Uint8Array(await res.arrayBuffer());
        let s = ""; const C = 0x8000;
        for (let i = 0; i < b.length; i += C) s += String.fromCharCode.apply(null, b.subarray(i, i + C));
        return { ok: true, ct: res.headers.get("content-type") || "", b64: btoa(s), size: b.length };
      } catch (e) { return { ok: false, err: String(e) }; }
    }, u);
  }

  let r = { ok: false };
  if (finalUrl) {
    const m = finalUrl.match(/^https?:\/\/[^\/]+/);
    const origin = m ? m[0] : null;
    if (origin) {
      await page.goto(origin + "/", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
      await settle(6);
      r = await fetchInPage(finalUrl);
    }
  }
  if (!r.ok) {
    // last resort: current page URL might be the resolved pdf
    const cur = await page.url().catch(() => null);
    if (cur && /pdfft|\.pdf/i.test(cur)) r = await fetchInPage(cur);
  }

  if (!r.ok) { console.log(JSON.stringify({ ok: false, finalUrl, err: r.err, status: r.status, ct: r.ct })); }
  else {
    const buf = Buffer.from(r.b64, "base64");
    const magic = String.fromCharCode(buf[0], buf[1], buf[2], buf[3]);
    const path = await writeFile(job.out, buf);
    console.log(JSON.stringify({ ok: true, finalUrl, path, ct: r.ct, size: buf.length, isPdf: magic === "%PDF" }));
  }
}
