#!/usr/bin/env bash
# dlpaper.sh — download a journal/preprint PDF using the user's authenticated
# browser session via dev-browser (defeats bot-UA blocking; carries institutional
# IP + login cookies). Use this when you ALREADY have the direct PDF URL.
# To resolve a DOI/landing page first, use resolve_pdf.js or get_paper.sh.
#
# Usage:
#   ./dlpaper.sh <pdfUrl> [outName.pdf] [options]
# Options:
#   -l, --landing <url>   Article/landing page to open first (session+referrer).
#                         Default: the PDF URL itself.
#   -d, --dest <dir>      Destination directory. Default: $PAPER_DL_DEST or "."
#   -b, --browser <name>  Persistent named dev-browser instance (login reuse).
#   -t, --timeout <sec>   dev-browser script timeout. Default: 120.
#       --login           Visible (headed) window — REQUIRED for bot-protected
#                         publishers (Radware/Cloudflare detect HeadlessChrome).
set -u

TMP_DIR="$HOME/.dev-browser/tmp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JS="$SCRIPT_DIR/download_paper.js"

PDF_URL=""; OUT=""; LANDING=""; DEST="${PAPER_DL_DEST:-.}"
BROWSER=""; HEADLESS="--headless"; TIMEOUT="120"; CONNECT=""

while [ $# -gt 0 ]; do
  case "$1" in
    -l|--landing) LANDING="$2"; shift 2;;
    -d|--dest)    DEST="$2"; shift 2;;
    -b|--browser) BROWSER="$2"; shift 2;;
    -t|--timeout) TIMEOUT="$2"; shift 2;;
    --login)      HEADLESS=""; shift;;
    --connect)    CONNECT=1; shift;;
    -h|--help)    sed -n '2,20p' "$0"; exit 0;;
    -*)           echo "unknown option: $1" >&2; exit 2;;
    *) if [ -z "$PDF_URL" ]; then PDF_URL="$1"; elif [ -z "$OUT" ]; then OUT="$1"; fi; shift;;
  esac
done

[ -z "$PDF_URL" ] && { echo "error: pdfUrl required" >&2; exit 2; }
[ -z "$OUT" ] && OUT="$(echo "$PDF_URL" | sed 's#[/:?&=]#_#g' | tail -c 80).pdf"
case "$OUT" in *.pdf) ;; *) OUT="$OUT.pdf";; esac

mkdir -p "$TMP_DIR" "$DEST"

printf '{"pdfUrl":%s,"landing":%s,"out":%s}\n' \
  "\"$PDF_URL\"" "\"${LANDING:-$PDF_URL}\"" "\"$OUT\"" > "$TMP_DIR/job.json"

CMD=(dev-browser)
if [ -n "$CONNECT" ]; then
  CMD+=(--connect)                       # attach to user's real Chrome (port 9222)
else
  [ -n "$HEADLESS" ] && CMD+=("$HEADLESS")
  [ -n "$BROWSER" ] && CMD+=(--browser "$BROWSER")
fi
[ -n "$TIMEOUT" ] && CMD+=(--timeout "$TIMEOUT")
CMD+=(run "$JS")

echo ">> ${CMD[*]}" >&2
# Exit code is unreliable (QuickJS teardown assertion); judge by stdout JSON.
RESULT="$("${CMD[@]}" 2>/tmp/dlpaper.err)"
LINE="$(echo "$RESULT" | grep -o '{"ok":[^}]*}' | tail -1)"

echo "$LINE"
case "$LINE" in
  *'"ok":true'*) ;;
  *) echo "FAILED. stderr:"; tail -5 /tmp/dlpaper.err >&2; exit 1;;
esac

SRC="$TMP_DIR/$OUT"
if [ ! -s "$SRC" ]; then echo "error: output file missing: $SRC" >&2; exit 1; fi
MAGIC="$(head -c 4 "$SRC")"
if [ "$MAGIC" != "%PDF" ]; then
  echo "error: not a PDF (magic='$MAGIC'). Likely a paywall/login HTML page." >&2
  echo "  -> if bot-protected: add -b papers --login (headed). if paywalled: check Unpaywall." >&2
  exit 1
fi

mv -f "$SRC" "$DEST/$OUT"
echo "OK -> $DEST/$OUT ($(wc -c < "$DEST/$OUT") bytes)"
