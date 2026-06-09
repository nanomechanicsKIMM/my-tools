// dev-browser sandbox script — reads resolve.json {input} from ~/.dev-browser/tmp,
// navigates to the DOI/article, and prints JSON:
//   { landing, title, host, pdfUrl, candidates[], paywallHint }
// pdfUrl is the best-guess full-article PDF URL (publisher-specific derivation +
// on-page link scrape). All URL parsing happens IN the page (real URL/location API);
// the sandbox URL polyfill lacks .origin/.pathname.

const job = JSON.parse(await readFile("resolve.json"));
const input = String(job.input || "").trim();
const target = /^10\.\d{4,9}\//.test(input) ? "https://doi.org/" + input : input;

const page = await browser.getPage("dl");
await page.goto(target, { waitUntil: "domcontentloaded", timeout: 60000 }).catch(() => {});
// wait for Cloudflare/Radware interstitial to clear before reading the page
{
  const re = /just a moment|잠시만|verifying|attention required|checking your browser|captcha|enable javascript|please wait/i;
  for (let i = 0; i < 12; i++) {
    const t = await page.title().catch(() => "");
    if (t && !re.test(t)) break;
    await new Promise(r => setTimeout(r, 2000));
  }
}

const info = await page.evaluate(() => {
  const loc = location;
  const host = loc.host;
  const path = loc.pathname;
  const html = document.documentElement.outerHTML;
  const txt = ((document.body && document.body.innerText) || "").toLowerCase();

  const anchors = Array.from(document.querySelectorAll("a"))
    .map(a => ({ t: (a.textContent || "").trim().slice(0, 40), href: a.href }))
    .filter(x => x.href && /\.pdf(\?|$)|\/pdf\b|viewmedia|pdfft|stampPDF|getpdf|article_deploy|epdf/i.test(x.href));

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
  } else if (/onlinelibrary\.wiley\.com/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0];
  } else if (/pubs\.acs\.org/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0];
  } else if (/link\.springer\.com/.test(host) && doiM) {
    pdfUrl = loc.origin + "/content/pdf/" + doiM[0] + ".pdf";
  } else if (/(^|\.)tandfonline\.com/.test(host) && doiM) {
    pdfUrl = loc.origin + "/doi/pdf/" + doiM[0];
  }

  if (!pdfUrl && anchors.length) {
    // prefer a full-article candidate over figure/epub
    const full = anchors.find(a => !/figure|esm|moesm|suppl/i.test(a.href)) || anchors[0];
    pdfUrl = full.href;
  }

  const paywallHint =
    /buy or subscribe|access through your institution|access via your institution|get access|purchase pdf|purchase access|sign in to read|rent this article/i.test(txt) &&
    !/^.*\bdownload pdf\b/i.test(txt.slice(0, 4000));

  return { landing: loc.href, title: document.title.slice(0, 120), host, pdfUrl, candidates: anchors.slice(0, 8), paywallHint };
});

console.log(JSON.stringify(info, null, 2));
