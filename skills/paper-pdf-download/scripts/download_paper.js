// dev-browser sandbox script (QuickJS) — reads job.json from ~/.dev-browser/tmp,
// downloads a PDF using the user's authenticated session and writes it to tmp.
// Success is judged by the wrapper via stdout JSON + file integrity, NOT exit code
// (QuickJS emits a harmless JS_FreeRuntime teardown assertion after large buffers).
//
// Two methods, auto-selected:
//   (A) direct  — fetch the PDF in the page context (same-origin, carries cookies).
//   (B) cdn     — if direct fails (publisher redirects /pdf to a cross-origin CDN,
//                 so CORS blocks the in-page fetch): trigger the browser download to
//                 capture download.url() (final CDN URL), load a doc on the CDN
//                 origin, then same-origin fetch there. (dev-browser blocks the
//                 Playwright download artifact API, so we re-fetch instead of saveAs.)

const job = JSON.parse(await readFile("job.json"));
const page = await browser.getPage("dl");

// Wait for Cloudflare/Radware interstitial ("Just a moment…/잠시만 기다리십시오…") to clear.
async function settle(maxTries) {
  const re = /just a moment|잠시만|verifying|attention required|checking your browser|captcha|enable javascript|please wait/i;
  for (let i = 0; i < (maxTries || 12); i++) {
    const t = await page.title().catch(() => "");
    if (t && !re.test(t)) return t;
    await new Promise(r => setTimeout(r, 2000));
  }
  return await page.title().catch(() => "");
}

async function fetchInPage(url) {
  return await page.evaluate(async (u) => {
    try {
      const res = await fetch(u, { credentials: "include" });
      const ct = res.headers.get("content-type") || "";
      if (!res.ok) return { ok: false, status: res.status, ct };
      const bytes = new Uint8Array(await res.arrayBuffer());
      let bin = "";
      const CH = 0x8000;
      for (let i = 0; i < bytes.length; i += CH) {
        bin += String.fromCharCode.apply(null, bytes.subarray(i, i + CH));
      }
      return { ok: true, status: res.status, ct, b64: btoa(bin), size: bytes.length };
    } catch (e) {
      return { ok: false, err: String(e) };
    }
  }, url);
}

// --- Method A: direct same-origin fetch from the landing page ---
await page.goto(job.landing || job.pdfUrl, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
await settle();
let r = await fetchInPage(job.pdfUrl);
let method = "direct";

// --- Method B: cross-origin CDN fallback ---
if (!r.ok) {
  let finalUrl = null;
  try {
    const dlPromise = page.waitForEvent("download", { timeout: 45000 });
    page.goto(job.pdfUrl).catch(() => {});
    const dl = await dlPromise;
    finalUrl = dl.url();
    try { await dl.cancel(); } catch (e) {}
  } catch (e) { /* no download fired */ }

  if (finalUrl) {
    const m = finalUrl.match(/^https?:\/\/[^\/]+/); // sandbox URL polyfill lacks .origin
    const origin = m ? m[0] : null;
    if (origin) {
      await page.goto(origin + "/robots.txt", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
      await settle(6);
      r = await fetchInPage(finalUrl);
      if (!r.ok) {
        await page.goto(origin + "/", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
        await settle(6);
        r = await fetchInPage(finalUrl);
      }
      method = "cdn:" + origin;
    }
  }
}

if (!r.ok) {
  console.log(JSON.stringify({ ok: false, method, status: r.status, ct: r.ct, error: r.err }));
} else {
  const buf = Buffer.from(r.b64, "base64");
  const magic = String.fromCharCode(buf[0], buf[1], buf[2], buf[3]);
  const path = await writeFile(job.out, buf);
  console.log(JSON.stringify({ ok: true, method, path, ct: r.ct, size: buf.length, isPdf: magic === "%PDF" }));
}
