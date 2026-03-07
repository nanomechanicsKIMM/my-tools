#!/usr/bin/env python3
"""
Search Google Patents with a query URL and download the results as CSV using Playwright.
Usage: python google_patents_download.py <search_url> [--output-dir DIR] [--headless]
Requires: pip install playwright && playwright install chromium
"""
import argparse
import os
import re
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Install Playwright: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


# Selectors for Google Patents (update if UI changes)
SELECTORS = {
    "search_input": "input[type='search'], input[name='q'], input[aria-label*='Search']",
    # Download (CSV) button: text or role
    "download_csv": "button:has-text('Download'), a:has-text('Download'), [aria-label*='Download'], [aria-label*='CSV'], button:has-text('CSV'), a:has-text('CSV')",
}


def download_csv(
    search_url: str,
    output_dir: str | Path | None = None,
    headless: bool = True,
    timeout_ms: int = 60000,
) -> str:
    """
    Open search_url on Google Patents, trigger CSV download, wait for file.
    Returns the path to the downloaded CSV file.
    """
    output_dir = Path(output_dir or os.getcwd())
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            accept_downloads=True,
            locale="en-US",
        )
        page = context.new_page()

        # Navigate directly to the search URL (includes query and date filters)
        page.goto(search_url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_load_state("networkidle", timeout=20000)

        # Wait for results area to be present
        page.wait_for_timeout(3000)
        for selector in [
            "search-result-item", "[data-result]", ".result", "article", "patent-result",
            "main", "[role='main']", "body",
        ]:
            try:
                page.wait_for_selector(selector, timeout=3000)
                break
            except Exception:
                pass

        # Click Download (CSV) and wait for download event with a single timeout
        clicked = False
        download_future = None
        with page.expect_download(timeout=60000) as download_info:
            for selector in [
                "button:has-text('Download (CSV)')",
                "a:has-text('Download (CSV)')",
                "[aria-label*='Download (CSV)']",
                "a:has-text('Download')",
                "button:has-text('Download')",
            ]:
                try:
                    btn = page.locator(selector).first
                    if btn.is_visible(timeout=2000):
                        btn.click()
                        clicked = True
                        break
                except Exception:
                    continue
            if not clicked:
                try:
                    page.get_by_role("button", name=re.compile(r"Download", re.I)).first.click()
                    clicked = True
                except Exception:
                    pass
            if not clicked:
                try:
                    page.get_by_text(re.compile(r"Download\s*\(?CSV\)?", re.I)).first.click()
                    clicked = True
                except Exception:
                    pass

        if not clicked:
            raise RuntimeError(
                "Could not find Download (CSV) button. Run with --no-headless and check the page; "
                "update selectors in scripts/google_patents_download.py or reference.md."
            )

        try:
            download = download_info.value
            name = download.suggested_filename or "google_patents_results.csv"
            download_path = output_dir / name
            download.save_as(download_path)
        except Exception as e:
            # Save screenshot to help debug when run with --no-headless
            try:
                screenshot_path = output_dir / "google_patents_screenshot_on_failure.png"
                page.screenshot(path=str(screenshot_path))
            except Exception:
                pass
            raise RuntimeError(
                f"CSV download did not complete or save failed: {e}. "
                "You can manually open the search URL in a browser, click 'Download (CSV)' above the results, "
                "save the file to the output folder as google_patents_results.csv, then run run_15yr_pipeline.py."
            ) from e

        if not Path(download_path).exists():
            raise RuntimeError("CSV file was not saved to output directory.")

        browser.close()
        return str(download_path)


def main():
    parser = argparse.ArgumentParser(description="Download Google Patents search results as CSV")
    parser.add_argument("search_url", help="Full Google Patents search URL (with q= and date params)")
    parser.add_argument("--output-dir", "-o", default=os.getcwd(), help="Directory to save CSV")
    parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Show browser window")
    args = parser.parse_args()

    path = download_csv(args.search_url, output_dir=args.output_dir, headless=args.headless)
    print(path)


if __name__ == "__main__":
    main()
