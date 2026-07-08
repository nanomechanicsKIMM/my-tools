// resolve_dl.js - MERGED resolve + download in ONE dev-browser run (2026-07-08).
// Replaces the old two-step (resolve_pdf.js run + download_paper.js run) which
// navigated the same landing page twice. Reads job.json {input, out} from
// ~/.dev-browser/tmp and prints ONE JSON line:
//   { ok, method, path?, size?, isPdf?, stage?, landing, title, pdfUrl, paywallHint }
//
// PDF URL derivation order: publisher-specific rule -> <meta name="citation_pdf_url">
// (Silverchair platforms, e.g. royalsocietypublishing.org) -> on-page anchor scrape.
// Download ladder: A direct same-origin fetch -> B download-event capture (cross-
// origin CDN 302) -> C navigation capture (navigate the tab to the PDF, read the
// final redirected URL, hop to that origin, fetch same-origin). C covers WAFs that
// only allow navigation-level requests and token CDNs like watermark*.silverchair.com
// (verified 2026-07-08, Benjamin & Ursell 1954).

const job = JSON.parse(await readFile("job.json"));
const input = String(job.input || "").trim();
const target = /^10\.\d{4,9}\//.test(input) ? "https://doi.org/" + input : input;
const page = await browser.getPage("dl");

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

const isHtml = (r) => r.ok && /html|^text\//i.test(r.ct || "");
const originOf = (u) => { const m = String(u || "").match(/^https?:\/\/[^\/]+/); return m ? m[0] : null; };

// ---- 1) resolve: one navigation ----------------------------------------
await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
await settle();

const info = await page.evaluate(() => {
  const loc = location;
  const host = loc.host;
  const path = loc.pathname;
  const html = document.documentElement.outerHTML;
  const txt = ((document.body && document.body.innerText) || "").toLowerCase();

  const anchors = Array.from(document.querySelectorAll("a"))
    .map(a => ({ t: (a.textContent || "").trim().slice(0, 40), href: a.href }))
    .filter(x => x.href && /\.pdf(\?|$)|\/pdf\b|viewmedia|pdfft|stampPDF|getpdf|article_deploy|epdf|article-pdf/i.test(x.href));

  const doiM = path.match(/10\.\d{4,9}\/[^\s/?#]+/);
  let pdfUrl = null;

  if (/opg\.optica\.org/.test(host)) {
    const oe = (loc.href.match(/uri=([a-z]+-\d+-\d+-\d+)/) || html.match(/uri=([a-z]+-\d+-\d+-\d+)/) || [])[1];
    if (oe) pdfUrl = loc.origin + "/viewmedia.cfm?uri=" + oe + "&seq=0";
  } else if (/(^|\.)pnas\.org$/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0] + "?download=true";
  } else if (/(^|\.)mdpi\.com$/.test(host)) {
    pdfUrl = loc.origin + path.replace(/\/$/, "") + "/pdf";
  } else if (/(^|\.)nature\.com$/.test(host)) {
    const id = (path.match(/articles\/([^/?#]+)/) || [])[1];
    if (id) pdfUrl = loc.origin + "/articles/" + id + ".pdf";
  } else if (/(^|\.)arxiv\.org$/.test(host)) {
    const id = (path.match(/(?:abs|pdf)\/(.+?)(?:v\d+)?(?:\.pdf)?$/) || [])[1];
    if (id) pdfUrl = loc.origin + "/pdf/" + id;
  } else if (/onlinelibrary\.wiley\.com/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0];
  } else if (/pubs\.acs\.org/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0];
  } else if (/link\.springer\.com/.test(host) && doiM) {
    pdfUrl = loc.origin + "/content/pdf/" + doiM[0] + ".pdf";
  } else if (/(^|\.)tandfonline\.com/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0];
  }

  // Silverchair & friends publish the real PDF URL in a meta tag (royalsociety,
  // OUP, ASME). Checked BEFORE the anchor scrape - it is authoritative.
  if (!pdfUrl) {
    const meta = document.querySelector("meta[name='citation_pdf_url']");
    if (meta && meta.content) pdfUrl = meta.content;
  }

  if (!pdfUrl && anchors.length) {
    const full = anchors.find(a => !/figure|esm|moesm|suppl/i.test(a.href)) || anchors[0];
    pdfUrl = full.href;
  }

  const paywallHint =
    /buy or subscribe|access through your institution|access via your institution|get access|purchase pdf|purchase access|sign in to read|rent this article/i.test(txt) &&
    !/^.*\bdownload pdf\b/i.test(txt.slice(0, 4000));

  return { landing: loc.href, title: document.title.slice(0, 120), host, pdfUrl,
           candidates: anchors.slice(0, 8), paywallHint };
});

if (!info.pdfUrl) {
  console.log(JSON.stringify({ ok: false, stage: "resolve", ...info }));
} else {
  // ---- 2) download ladder (same run, same session) ----------------------
  let r = await fetchInPage(info.pdfUrl);
  let method = "direct";

  if (!r.ok || isHtml(r)) {
    // B: cross-origin CDN 302 -> capture download.url(), hop, same-origin fetch
    let finalUrl = null;
    try {
      const dlPromise = page.waitForEvent("download", { timeout: 30000 });
      page.goto(info.pdfUrl).catch(() => {});
      const dl = await dlPromise;
      finalUrl = dl.url();
      try { await dl.cancel(); } catch (e) {}
    } catch (e) { /* no download event fired */ }
    if (finalUrl) {
      const origin = originOf(finalUrl);
      if (origin) {
        await page.goto(origin + "/robots.txt", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
        await settle(6);
        r = await fetchInPage(finalUrl);
        method = "cdn:" + origin;
      }
    }
  }

  if (!r.ok || isHtml(r)) {
    // C: navigation capture - navigate the tab itself to the PDF (passes WAF
    // sec-fetch rules and resolves token-CDN redirects), read final URL, fetch
    // from that origin. Real-Chrome PDF viewer keeps page.url() = final URL.
    await page.goto(info.pdfUrl, { waitUntil: "load", timeout: 60000 }).catch(() => {});
    await new Promise(res2 => setTimeout(res2, 4000));
    const finalUrl = page.url();
    const fo = originOf(finalUrl);
    if (fo) {
      if (fo !== originOf(info.landing)) {
        await page.goto(fo + "/robots.txt", { waitUntil: "domcontentloaded", timeout: 30000 }).catch(() => {});
        await settle(6);
      }
      r = await fetchInPage(finalUrl);
      method = "navcap:" + fo;
    }
  }

  if (!r.ok) {
    console.log(JSON.stringify({ ok: false, stage: "download", method, status: r.status,
                                 ct: r.ct, error: r.err, landing: info.landing,
                                 title: info.title, pdfUrl: info.pdfUrl,
                                 paywallHint: info.paywallHint }));
  } else {
    const buf = Buffer.from(r.b64, "base64");
    const magic = String.fromCharCode(buf[0], buf[1], buf[2], buf[3]);
    const path = await writeFile(job.out, buf);
    console.log(JSON.stringify({ ok: true, method, path, ct: r.ct, size: buf.length,
                                 isPdf: magic === "%PDF", landing: info.landing,
                                 title: info.title, pdfUrl: info.pdfUrl,
                                 paywallHint: info.paywallHint }));
  }
}
