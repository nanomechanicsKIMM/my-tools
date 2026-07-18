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
#       --lib <dir>       Library folder for dedup + archival copy.
#                         Default: $PAPER_DL_LIBRARY or D:/Zettelkasten/References
#       --no-library      Disable the library dedup check and archival copy.
set -u

TMP_DIR="$HOME/.dev-browser/tmp"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
JS="$SCRIPT_DIR/download_paper.js"

PDF_URL=""; OUT=""; LANDING=""; DEST="${PAPER_DL_DEST:-.}"
BROWSER=""; HEADLESS="--headless"; TIMEOUT="120"; CONNECT=""
_LIB_DEFAULT="D:/Zettelkasten/References"
[ -d "$_LIB_DEFAULT" ] || _LIB_DEFAULT="$HOME/Zettelkasten/References"
LIBRARY="${PAPER_DL_LIBRARY:-$_LIB_DEFAULT}"

while [ $# -gt 0 ]; do
  case "$1" in
    -l|--landing) LANDING="$2"; shift 2;;
    -d|--dest)    DEST="$2"; shift 2;;
    -b|--browser) BROWSER="$2"; shift 2;;
    -t|--timeout) TIMEOUT="$2"; shift 2;;
    --login)      HEADLESS=""; shift;;
    --connect)    CONNECT=1; shift;;
    --lib)        LIBRARY="$2"; shift 2;;
    --no-library) LIBRARY=""; shift;;
    -h|--help)    sed -n '2,23p' "$0"; exit 0;;
    -*)           echo "unknown option: $1" >&2; exit 2;;
    *) if [ -z "$PDF_URL" ]; then PDF_URL="$1"; elif [ -z "$OUT" ]; then OUT="$1"; fi; shift;;
  esac
done

[ -z "$PDF_URL" ] && { echo "error: pdfUrl required" >&2; exit 2; }
[ -z "$OUT" ] && OUT="$(echo "$PDF_URL" | sed 's#[/:?&=]#_#g' | tail -c 80).pdf"
case "$OUT" in *.pdf) ;; *) OUT="$OUT.pdf";; esac

mkdir -p "$TMP_DIR" "$DEST"

# Library is only used when it actually exists (e.g., D: mounted)
[ -n "$LIBRARY" ] && [ ! -d "$LIBRARY" ] && { echo "note: library not found, skipping dedup: $LIBRARY" >&2; LIBRARY=""; }
DESTABS="$(cd "$DEST" 2>/dev/null && pwd || echo "$DEST")"
LIBABS=""; [ -n "$LIBRARY" ] && LIBABS="$(cd "$LIBRARY" && pwd)"

# 0) Dedup: exact filename already in the library? -> no download.
if [ -n "$LIBRARY" ] && [ -e "$LIBRARY/$OUT" ]; then
  echo "SKIP (already in library): $LIBRARY/$OUT"
  if [ "$DESTABS" != "$LIBABS" ] && [ ! -e "$DEST/$OUT" ]; then
    cp "$LIBRARY/$OUT" "$DEST/$OUT" && echo "COPY library -> $DEST/$OUT"
  fi
  exit 0
fi

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
if [ ! -s "$SRC" ]; then
  # dev-browser writeFile() sanitizes filenames (spaces/parens/non-ASCII -> "_"),
  # so the tmp name can differ from $OUT. Fall back to the "path" field it reported.
  RAWPATH="$(echo "$LINE" | sed -n 's/.*"path":"\([^"]*\)".*/\1/p' | sed 's/\\\\/\//g')"
  if [ -n "$RAWPATH" ] && [ -s "$RAWPATH" ]; then
    SRC="$RAWPATH"
  else
    echo "error: output file missing: $TMP_DIR/$OUT (and no usable path in result)" >&2; exit 1
  fi
fi
MAGIC="$(head -c 4 "$SRC")"
if [ "$MAGIC" != "%PDF" ]; then
  echo "error: not a PDF (magic='$MAGIC'). Likely a paywall/login HTML page." >&2
  echo "  -> if bot-protected: add -b papers --login (headed). if paywalled: check Unpaywall." >&2
  exit 1
fi

mv -f "$SRC" "$DEST/$OUT"
echo "OK -> $DEST/$OUT ($(wc -c < "$DEST/$OUT") bytes)"

# 3) Archival copy: keep the full collection in one library folder.
if [ -n "$LIBRARY" ] && [ "$DESTABS" != "$LIBABS" ] && [ ! -e "$LIBRARY/$OUT" ]; then
  cp "$DEST/$OUT" "$LIBRARY/$OUT" && echo "LIB -> $LIBRARY/$OUT"
fi
