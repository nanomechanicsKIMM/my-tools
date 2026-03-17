#!/usr/bin/env python3
"""
Search Google Patents with a query URL and download the results as CSV using Playwright.
Usage: python google_patents_download.py <search_url> [--output-dir DIR] [--retries N]
Requires: playwright>=1.40.0  (pip install playwright && playwright install chromium)

How it works (2026-03-07):
  Google's XHR download endpoint requires valid Google session cookies.
  Without cookies → 429 Too Many Requests. A fresh Playwright context has no cookies.

  RECOMMENDED: CDP mode (--cdp)
    Connect to the user's already-running Chrome (which has real cookies).
    Chrome must be started with: --remote-debugging-port=9222
    (Create a desktop shortcut with that flag, use it when running the script.)

  FALLBACK: Persistent-context mode (default)
    Uses a dedicated Chrome profile that accumulates cookies over time.
    First runs may get 429; success rate improves after profile has visit history.

Selectors confirmed via DOM inspection 2026-03-07:
  DOWNLOAD_LINK_ANY = "a[href*='download=true']"   (the "Download" dropdown button)
  DOWNLOAD_LINK_CSV = "a[data-proto='DOWNLOAD_CSV']" (the CSV option)
"""
import argparse
import os
import shutil
import sys
import time
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)

PAGE_SETTLE_MS = 8000
DOWNLOAD_LINK_ANY = "a[href*='download=true']"
DOWNLOAD_LINK_CSV = "a[data-proto='DOWNLOAD_CSV']"

_PLAYWRIGHT_PROFILE = Path.home() / ".playwright-chrome-profile"
_CDP_URL = "http://localhost:9222"


# ── Public entry point ────────────────────────────────────────────────────────

def download_csv(
    search_url: str,
    output_dir: str | Path | None = None,
    retries: int = 2,
    timeout_ms: int = 90000,
    use_cdp: bool = False,
    cdp_url: str = _CDP_URL,
    profile_dir: str | Path | None = None,
) -> str:
    """
    Download Google Patents search results as CSV.
    Returns the absolute path of the saved CSV.

    use_cdp=True: connect to the user's running Chrome (recommended).
                  Chrome must be started with --remote-debugging-port=9222.
    use_cdp=False: use a persistent Playwright Chrome profile (may get 429).
    """
    output_dir = Path(output_dir or os.getcwd()).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    last_error: Exception | None = None
    for attempt in range(1, retries + 2):
        try:
            if use_cdp:
                return _download_via_cdp(search_url, output_dir, timeout_ms, cdp_url)
            else:
                profile_path = Path(profile_dir) if profile_dir else _PLAYWRIGHT_PROFILE
                profile_path.mkdir(parents=True, exist_ok=True)
                return _download_via_profile(search_url, output_dir, timeout_ms, profile_path)
        except Exception as e:
            last_error = e
            if attempt <= retries:
                wait_sec = 30 * attempt
                print(f"[attempt {attempt}/{retries+1}] failed: {e}  – retrying in {wait_sec}s …", file=sys.stderr)
                time.sleep(wait_sec)

    raise RuntimeError(
        f"CSV download failed after {retries + 1} attempt(s). Last error: {last_error}\n"
        "\nFallback options:\n"
        "  1) Open the search URL in Chrome, click 'Download' → 'Download (CSV)',\n"
        "     save the file to the output folder, then re-run the pipeline.\n"
        "  2) Use --cdp mode: start Chrome with --remote-debugging-port=9222,\n"
        "     then run this script with --cdp flag."
    ) from last_error


# ── CDP mode: connect to the user's running Chrome ────────────────────────────

def _download_via_cdp(
    search_url: str,
    output_dir: Path,
    timeout_ms: int,
    cdp_url: str,
) -> str:
    """
    Connect to a Chrome instance started with --remote-debugging-port=9222.
    That Chrome has the user's real Google session cookies → no 429.
    Downloads land in Chrome's default Downloads folder; we copy them to output_dir.
    """
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(cdp_url, timeout=10000)
        except Exception as e:
            raise RuntimeError(
                f"Cannot connect to Chrome at {cdp_url}.\n"
                "Start Chrome with the flag --remote-debugging-port=9222:\n"
                '  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" '
                "--remote-debugging-port=9222\n"
                f"Original error: {e}"
            ) from e

        print(f"[info] Connected to Chrome via CDP ({cdp_url})", file=sys.stderr)

        # Open a new tab in the running Chrome
        context = browser.contexts[0] if browser.contexts else browser.new_context()
        page = context.new_page()

        try:
            # 1. Load search results page
            print("[1/3] Loading search page …", file=sys.stderr)
            page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)

            # 2. Wait for Download link
            try:
                page.wait_for_selector(DOWNLOAD_LINK_ANY, timeout=40000)
            except PlaywrightTimeout:
                _save_screenshot(page, output_dir, "gp_no_download_link.png")
                raise RuntimeError("Download link not found within 40s (no results or CAPTCHA?).")

            page.wait_for_timeout(PAGE_SETTLE_MS)

            # 3. Get the CSV href
            href = page.locator(DOWNLOAD_LINK_CSV).get_attribute("href", timeout=10000)
            if not href:
                raise RuntimeError("CSV download link href is empty – UI may have changed.")
            download_url = (
                f"https://patents.google.com{href}" if href.startswith("/") else href
            )
            print("[2/3] Navigating to download URL in Chrome …", file=sys.stderr)

            # 4. Watch the Downloads folder for a new CSV file
            downloads_folder = Path.home() / "Downloads"
            before = set(downloads_folder.glob("*.csv")) if downloads_folder.exists() else set()

            # Navigate to the download URL in the real Chrome context
            # Chrome will download it to the Downloads folder with real cookies.
            page.goto(download_url, wait_until="commit", timeout=timeout_ms)

        except Exception:
            _save_screenshot(page, output_dir, "gp_error.png")
            try:
                page.close()
            except Exception:
                pass
            raise

        # 5. Wait for the new CSV to appear in Downloads
        waited = 0
        poll_ms = 500
        new_csv: Path | None = None
        while waited < timeout_ms:
            if downloads_folder.exists():
                after = set(downloads_folder.glob("*.csv"))
                new_files = after - before
                # Also look for partial downloads that just finished
                completed = {f for f in new_files if not f.suffix == ".crdownload"}
                if completed:
                    new_csv = max(completed, key=lambda f: f.stat().st_mtime)
                    break
            time.sleep(poll_ms / 1000)
            waited += poll_ms

        try:
            page.close()
        except Exception:
            pass

        if new_csv is None:
            raise RuntimeError(
                f"No new CSV appeared in {downloads_folder} within {timeout_ms//1000}s. "
                "Google may have returned 429 – the Chrome session may need more cookies. "
                "Open Chrome, browse patents.google.com for a minute, then retry."
            )

        # 6. Copy to output_dir
        dest = output_dir / new_csv.name
        shutil.copy2(new_csv, dest)
        size = dest.stat().st_size
        print(f"[3/3] Saved: {dest}  ({size:,} bytes)", file=sys.stderr)
        return str(dest)


# ── Persistent-profile mode ───────────────────────────────────────────────────

def _download_via_profile(
    search_url: str,
    output_dir: Path,
    timeout_ms: int,
    profile_path: Path,
) -> str:
    """
    Use a dedicated (non-default) Chrome profile with accumulated cookies.
    Chrome allows CDP on non-default profiles.
    May get 429 on fresh profiles; improves with repeated use.
    """
    with sync_playwright() as p:
        print(f"[info] Chrome profile: {profile_path}", file=sys.stderr)
        try:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                channel="chrome",
                headless=False,
                accept_downloads=True,
                locale="en-US",
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception as e:
            print(f"[warn] Chrome launch failed ({e}), trying bundled Chromium …", file=sys.stderr)
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_path),
                headless=False,
                accept_downloads=True,
                locale="en-US",
            )

        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        try:
            print("[1/3] Loading search page …", file=sys.stderr)
            page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)

            try:
                page.wait_for_selector(DOWNLOAD_LINK_ANY, timeout=40000)
            except PlaywrightTimeout:
                _save_screenshot(page, output_dir, "gp_no_download_link.png")
                raise RuntimeError("Download link not found within 40s.")

            page.wait_for_timeout(PAGE_SETTLE_MS)

            href = page.locator(DOWNLOAD_LINK_CSV).get_attribute("href", timeout=10000)
            if not href:
                raise RuntimeError("CSV download link href is empty – UI may have changed.")
            download_url = (
                f"https://patents.google.com{href}" if href.startswith("/") else href
            )
            print("[2/3] Navigating to download URL …", file=sys.stderr)

            # Navigate directly to the XHR download URL.
            # Use a short timeout so a 429 page fails fast instead of waiting 90s.
            try:
                with page.expect_download(timeout=15000) as dl_info:
                    page.goto(download_url, wait_until="commit", timeout=timeout_ms)
                download = dl_info.value
            except PlaywrightTimeout:
                # Timed out waiting for a download event → probably a 429 or redirect page.
                content = page.content()
                if "429" in content or "That's an error" in content:
                    raise RuntimeError(
                        "429 Too Many Requests – Google requires valid session cookies.\n"
                        "Use --cdp mode: start Chrome with --remote-debugging-port=9222\n"
                        "while logged in to Google, then re-run with --cdp flag."
                    )
                raise RuntimeError(
                    "No download started within 15s. The page may have redirected or shown an error.\n"
                    "Try --cdp mode for reliable downloads with real session cookies."
                )

        except Exception:
            _save_screenshot(page, output_dir, "gp_error.png")
            try:
                context.close()
            except Exception:
                pass
            raise

        if download.failure():
            context.close()
            raise RuntimeError(f"Download failure: {download.failure()}")

        name = download.suggested_filename or "google_patents_results.csv"
        save_path = output_dir / name
        download.save_as(save_path)

        if not save_path.exists():
            context.close()
            raise RuntimeError(f"File not found after save: {save_path}")
        size = save_path.stat().st_size
        if size < 200:
            save_path.unlink(missing_ok=True)
            context.close()
            raise RuntimeError(
                f"Saved file too small ({size} bytes) – likely a 429 error response. "
                "Try --cdp mode or wait and retry."
            )

        context.close()
        print(f"[3/3] Saved: {save_path}  ({size:,} bytes)", file=sys.stderr)
        return str(save_path)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _save_screenshot(page, output_dir: Path, name: str) -> None:
    try:
        path = output_dir / name
        page.screenshot(path=str(path))
        print(f"Screenshot saved: {path}", file=sys.stderr)
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="Download Google Patents search results as CSV via Playwright",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
RECOMMENDED USAGE (CDP mode):
  1) Start Chrome with remote debugging:
       "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" --remote-debugging-port=9222
  2) Run this script with --cdp:
       python google_patents_download.py <URL> --cdp --output-dir <DIR>

  Chrome must remain open while the script runs.
  The script uses your real Google session cookies → no 429 errors.
""",
    )
    parser.add_argument(
        "search_url",
        help="Full Google Patents search URL (with q= and date params)",
    )
    parser.add_argument(
        "--output-dir", "-o",
        default=os.getcwd(),
        help="Directory to save the CSV (default: current directory)",
    )
    parser.add_argument(
        "--retries",
        type=int, default=2,
        help="Number of retry attempts on failure (default: 2)",
    )
    parser.add_argument(
        "--cdp",
        action="store_true",
        help="Connect to running Chrome via CDP (recommended). "
             "Start Chrome with --remote-debugging-port=9222 first.",
    )
    parser.add_argument(
        "--cdp-url",
        default=_CDP_URL,
        help=f"Chrome DevTools Protocol URL (default: {_CDP_URL})",
    )
    parser.add_argument(
        "--profile-dir",
        default=None,
        help=f"Chrome profile directory for persistent-context mode "
             f"(default: {_PLAYWRIGHT_PROFILE})",
    )
    args = parser.parse_args()

    path = download_csv(
        args.search_url,
        output_dir=args.output_dir,
        retries=args.retries,
        use_cdp=args.cdp,
        cdp_url=args.cdp_url,
        profile_dir=args.profile_dir,
    )
    print(path)


if __name__ == "__main__":
    main()
