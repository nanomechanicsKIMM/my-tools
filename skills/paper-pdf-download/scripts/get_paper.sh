#!/usr/bin/env bash
# get_paper.sh — one-shot: resolve a DOI/URL to its PDF, then download it.
# Defaults to HEADED + named browser "papers" (required for bot-protected
# publishers; the user must be at the machine for the first login/captcha).
#
# Usage:
#   ./get_paper.sh <DOI-or-URL> [outName.pdf] [options]
# Options:
#   -d <dir>     destination (default: $PAPER_DL_DEST or ".")
#   -b <name>    browser instance (default: papers)
#   -t <sec>     timeout (default: 120)
#   --headless   unattended mode (OA / non-protected only; no window)
#
# Examples:
#   ./get_paper.sh 10.1364/OE.525680
#   ./get_paper.sh 10.3390/cryst15030267 cryst.pdf -d D:/Zettelkasten/References
#   PAPER_DL_DEST=D:/Zettelkasten/References ./get_paper.sh 10.1073/pnas.1005828107
set -u

SDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$HOME/.dev-browser/tmp"
PY="${PAPER_DL_PYTHON:-C:/Users/JHKIM/miniconda3/python}"

INPUT=""; OUT=""; DEST="${PAPER_DL_DEST:-.}"; BROWSER="papers"; TIMEOUT="120"; HEADED="--login"; CONNECT=""
while [ $# -gt 0 ]; do
  case "$1" in
    -d) DEST="$2"; shift 2;;
    -b) BROWSER="$2"; shift 2;;
    -t) TIMEOUT="$2"; shift 2;;
    --headless) HEADED=""; shift;;
    --connect) CONNECT=1; shift;;
    -h|--help) sed -n '2,18p' "$0"; exit 0;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) if [ -z "$INPUT" ]; then INPUT="$1"; elif [ -z "$OUT" ]; then OUT="$1"; fi; shift;;
  esac
done
[ -z "$INPUT" ] && { echo "error: DOI or URL required" >&2; exit 2; }
mkdir -p "$TMP"

# 1) Resolve --------------------------------------------------------------
printf '{"input":%s}\n' "\"$INPUT\"" > "$TMP/resolve.json"
RCMD=(dev-browser)
if [ -n "$CONNECT" ]; then
  RCMD+=(--connect)
else
  [ -z "$HEADED" ] && RCMD+=(--headless)
  [ -n "$BROWSER" ] && RCMD+=(--browser "$BROWSER")
fi
RCMD+=(--timeout 90 run "$SDIR/resolve_pdf.js")
echo ">> resolve: ${RCMD[*]}" >&2
RJSON="$("${RCMD[@]}" 2>/tmp/getpaper.err)"

# Extract fields from the resolver JSON (one python call per field; robust to spaces).
LANDING="$(printf '%s' "$RJSON" | "$PY" -c "import sys,json,re;m=re.search(r'\{.*\}',sys.stdin.read(),re.S);print((json.loads(m.group(0)).get('landing') or '') if m else '')" 2>/dev/null)"
PDFURL="$(printf '%s' "$RJSON" | "$PY" -c "import sys,json,re;m=re.search(r'\{.*\}',sys.stdin.read(),re.S);print((json.loads(m.group(0)).get('pdfUrl') or '') if m else '')" 2>/dev/null)"
TITLE="$(printf '%s' "$RJSON" | "$PY" -c "import sys,json,re;m=re.search(r'\{.*\}',sys.stdin.read(),re.S);print((json.loads(m.group(0)).get('title') or '') if m else '')" 2>/dev/null)"
PAYWALL="$(printf '%s' "$RJSON" | "$PY" -c "import sys,json,re;m=re.search(r'\{.*\}',sys.stdin.read(),re.S);print(json.loads(m.group(0)).get('paywallHint') if m else '')" 2>/dev/null)"

echo "resolved: title='$TITLE'" >&2
echo "          landing=$LANDING" >&2
echo "          pdfUrl=$PDFURL  (paywallHint=$PAYWALL)" >&2

if [ -z "$PDFURL" ]; then
  echo "RESOLVE FAILED — no PDF URL found." >&2
  echo "$RJSON" >&2
  # Unpaywall OA check
  DOI="$(echo "$INPUT" | grep -oE '10\.[0-9]{4,9}/[^ ]+' || true)"
  if [ -n "$DOI" ]; then
    echo "-- Unpaywall ($DOI) --" >&2
    curl -s -k "https://api.unpaywall.org/v2/$DOI?email=${UNPAYWALL_EMAIL:-test@example.com}" 2>/dev/null \
      | "$PY" -c "import sys,json;d=json.load(sys.stdin);print('is_oa=',d.get('is_oa'),'oa_status=',d.get('oa_status'),'pdf=',(d.get('best_oa_location') or {}).get('url_for_pdf'))" 2>/dev/null || true
  fi
  exit 1
fi

[ -z "$OUT" ] && { DOI="$(echo "$INPUT" | grep -oE '10\.[0-9]{4,9}/.+' | sed 's#[/:?&=]#_#g')"; OUT="${DOI:-paper}.pdf"; }

# 2) Download -------------------------------------------------------------
DLARGS=("$PDFURL" "$OUT" -l "${LANDING:-$PDFURL}" -d "$DEST" -t "$TIMEOUT")
if [ -n "$CONNECT" ]; then
  DLARGS+=(--connect)
else
  [ -n "$BROWSER" ] && DLARGS+=(-b "$BROWSER")
  [ -n "$HEADED" ] && DLARGS+=(--login)
fi
bash "$SDIR/dlpaper.sh" "${DLARGS[@]}"
