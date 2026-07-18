#!/usr/bin/env bash
# get_paper.sh — one-shot: resolve a DOI/URL to its PDF and download it.
# v2 (2026-07-08): 3-stage ladder, fastest first
#   0) library dedup (no network)
#   1) HTTP-first fast path (fast_get.py: classification + Unpaywall OA +
#      direct GET for non-protected hosts — no browser, seconds)
#   2) ONE merged browser run (resolve_dl.js: resolve + download ladder
#      direct/cdn/navcap in a single navigation session)
# Old two-step browser path is kept behind --legacy.
#
# Usage:
#   ./get_paper.sh <DOI-or-URL> [outName.pdf] [options]
# Options:
#   -d <dir>     destination = 현재 작업 폴더 (default: $PAPER_DL_DEST or ".")
#   -b <name>    browser instance (default: papers)
#   -t <sec>     timeout (default: 120)
#   --headless   unattended mode (OA / non-protected only; no window)
#   --connect    attach to real Chrome on :9222 (Cloudflare managed challenge)
#   --no-fast    skip the HTTP-first fast path (force browser)
#   --force      try the browser even when classified unsubscribed(none)
#   --legacy     old two-step resolve_pdf.js + dlpaper.sh path
#   --lib <dir>  library for dedup+archive (default: $PAPER_DL_LIBRARY or D:/Zettelkasten/References)
#   --no-library disable library dedup/archive
#
# Examples:
#   ./get_paper.sh 10.1364/OE.525680
#   ./get_paper.sh https://arxiv.org/abs/1706.03762 -d refs --headless
set -u

SDIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$HOME/.dev-browser/tmp"
PY="${PAPER_DL_PYTHON:-}"
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then PY=python3
  elif command -v python >/dev/null 2>&1; then PY=python
  else PY="$HOME/miniconda3/python"; fi
fi

INPUT=""; OUT=""; DEST="${PAPER_DL_DEST:-.}"; BROWSER="papers"; TIMEOUT="120"; HEADED="--login"; CONNECT=""
_LIB_DEFAULT="D:/Zettelkasten/References"
[ -d "$_LIB_DEFAULT" ] || _LIB_DEFAULT="$HOME/Zettelkasten/References"
LIBRARY="${PAPER_DL_LIBRARY:-$_LIB_DEFAULT}"; NOLIB=""; NOFAST=""; FORCE=""; LEGACY=""
while [ $# -gt 0 ]; do
  case "$1" in
    -d) DEST="$2"; shift 2;;
    -b) BROWSER="$2"; shift 2;;
    -t) TIMEOUT="$2"; shift 2;;
    --headless) HEADED=""; shift;;
    --connect) CONNECT=1; shift;;
    --no-fast) NOFAST=1; shift;;
    --force) FORCE=1; shift;;
    --legacy) LEGACY=1; shift;;
    --lib) LIBRARY="$2"; shift 2;;
    --no-library) LIBRARY=""; NOLIB=1; shift;;
    -h|--help) sed -n '2,29p' "$0"; exit 0;;
    -*) echo "unknown option: $1" >&2; exit 2;;
    *) if [ -z "$INPUT" ]; then INPUT="$1"; elif [ -z "$OUT" ]; then OUT="$1"; fi; shift;;
  esac
done
[ -z "$INPUT" ] && { echo "error: DOI or URL required" >&2; exit 2; }
mkdir -p "$TMP"
[ -n "$LIBRARY" ] && [ ! -d "$LIBRARY" ] && LIBRARY=""

jget() { # jget '<json>' key [key...]  -> field or ""
  local js="$1"; shift
  printf '%s' "$js" | "$PY" -c '
import sys,json
try: v=json.load(sys.stdin)
except Exception: print(); sys.exit()
for k in sys.argv[1:]:
    v=v.get(k) if isinstance(v,dict) else None
    if v is None: break
print("" if v is None else v)' "$@" 2>/dev/null
}

archive_to_lib() { # $1 = filename saved in $DEST
  if [ -n "$LIBRARY" ] && [ "$(cd "$DEST" 2>/dev/null && pwd)" != "$(cd "$LIBRARY" && pwd)" ] && [ ! -e "$LIBRARY/$1" ]; then
    cp "$DEST/$1" "$LIBRARY/$1" && echo "LIB -> $LIBRARY/$1"
  fi
}

# 0) Library dedup (before any network/browser work) -----------------------
copy_from_lib() { # $1 = library filename
  echo "SKIP (already in library): $LIBRARY/$1"
  if [ -n "$DEST" ] && [ "$(cd "$DEST" 2>/dev/null && pwd)" != "$(cd "$LIBRARY" && pwd)" ] && [ ! -e "$DEST/$1" ]; then
    mkdir -p "$DEST" && cp "$LIBRARY/$1" "$DEST/$1" && echo "COPY library -> $DEST/$1"
  fi
}
if [ -n "$LIBRARY" ]; then
  if [ -n "$OUT" ] && [ -e "$LIBRARY/$OUT" ]; then copy_from_lib "$OUT"; exit 0; fi
  DOI0="$(echo "$INPUT" | grep -oE '10\.[0-9]{4,9}/[^ ]+' || true)"
  if [ -z "$OUT" ] && [ -n "$DOI0" ]; then
    MATCH="$("$PY" "$SDIR/library_check.py" "$DOI0" "$LIBRARY" 2>/dev/null || true)"
    if [ -n "$MATCH" ]; then echo "(DOI match: $DOI0)"; copy_from_lib "$MATCH"; exit 0; fi
  fi
fi

# 1) HTTP-first fast path (no browser) --------------------------------------
FJSON=""
if [ -z "$NOFAST" ]; then
  echo ">> fast: fast_get.py $INPUT" >&2
  FA=("$INPUT" --dest "$DEST")
  [ -n "$OUT" ] && FA+=(--out "$OUT")
  FJSON="$("$PY" "$SDIR/fast_get.py" "${FA[@]}")"; FCODE=$?
  if [ -z "$FJSON" ]; then FCODE=3; fi
  if [ "$FCODE" = "0" ]; then
    FNAME="$(jget "$FJSON" filename)"
    echo "OK -> $DEST/$FNAME ($(jget "$FJSON" size) bytes, source=fast:$(jget "$FJSON" source | cut -c1-70))"
    archive_to_lib "$FNAME"
    exit 0
  fi
  # canonical name from Crossref: reuse for the browser path + one more dedup shot
  SUGG="$(jget "$FJSON" suggest filename)"
  if [ -z "$OUT" ] && [ -n "$SUGG" ]; then
    OUT="$SUGG"
    if [ -n "$LIBRARY" ] && [ -e "$LIBRARY/$OUT" ]; then copy_from_lib "$OUT"; exit 0; fi
  fi
  if [ "$FCODE" = "4" ] && [ -z "$FORCE" ]; then
    echo "SKIP: 미구독(access=none) + OA 사본 없음 — 브라우저 시도 생략." >&2
    echo "      합법 경로: 기관 SSO 로그인(--connect + 수동), 도서관 ILL, 저자 요청. 강제 시도는 --force." >&2
    exit 1
  fi
  ACC="$(jget "$FJSON" classification access)"; PUB="$(jget "$FJSON" classification publisher)"
  [ -n "$PUB" ] && echo ">> publisher=$PUB access=$ACC — 브라우저 경로 진행" >&2
fi

[ -z "$OUT" ] && { DOI="$(echo "$INPUT" | grep -oE '10\.[0-9]{4,9}/.+' | sed 's#[/:?&=]#_#g')"; OUT="${DOI:-paper}.pdf"; }
case "$OUT" in *.pdf) ;; *) OUT="$OUT.pdf";; esac
mkdir -p "$DEST"

# 2) Browser path ------------------------------------------------------------
if [ -n "$LEGACY" ]; then
  # -- legacy two-step: resolve_pdf.js then dlpaper.sh ----------------------
  printf '{"input":%s}\n' "\"$INPUT\"" > "$TMP/resolve.json"
  RCMD=(dev-browser)
  if [ -n "$CONNECT" ]; then RCMD+=(--connect)
  else
    [ -z "$HEADED" ] && RCMD+=(--headless)
    [ -n "$BROWSER" ] && RCMD+=(--browser "$BROWSER")
  fi
  RCMD+=(--timeout 90 run "$SDIR/resolve_pdf.js")
  echo ">> resolve: ${RCMD[*]}" >&2
  RJSON="$("${RCMD[@]}" 2>/tmp/getpaper.err)"
  LANDING="$(jget "$RJSON" landing)"; PDFURL="$(jget "$RJSON" pdfUrl)"; TITLE="$(jget "$RJSON" title)"
  echo "resolved: title='$TITLE'" >&2
  echo "          pdfUrl=$PDFURL" >&2
  [ -z "$PDFURL" ] && { echo "RESOLVE FAILED — no PDF URL found." >&2; echo "$RJSON" >&2; exit 1; }
  DLARGS=("$PDFURL" "$OUT" -l "${LANDING:-$PDFURL}" -d "$DEST" -t "$TIMEOUT")
  if [ -n "$CONNECT" ]; then DLARGS+=(--connect)
  else
    [ -n "$BROWSER" ] && DLARGS+=(-b "$BROWSER")
    [ -n "$HEADED" ] && DLARGS+=(--login)
  fi
  if [ -n "$NOLIB" ]; then DLARGS+=(--no-library); elif [ -n "$LIBRARY" ]; then DLARGS+=(--lib "$LIBRARY"); fi
  exec bash "$SDIR/dlpaper.sh" "${DLARGS[@]}"
fi

# -- merged single run: resolve_dl.js ----------------------------------------
printf '{"input":%s,"out":%s}\n' "\"$INPUT\"" "\"$OUT\"" > "$TMP/job.json"
CMD=(dev-browser)
if [ -n "$CONNECT" ]; then CMD+=(--connect)
else
  [ -z "$HEADED" ] && CMD+=(--headless)
  [ -n "$BROWSER" ] && CMD+=(--browser "$BROWSER")
fi
CMD+=(--timeout "$TIMEOUT" run "$SDIR/resolve_dl.js")
echo ">> browser: ${CMD[*]}" >&2
RESULT="$("${CMD[@]}" 2>/tmp/getpaper.err)"
LINE="$(printf '%s\n' "$RESULT" | grep -E '^\{.*\}$' | tail -1)"

if [ -z "$LINE" ]; then
  echo "FAILED — no JSON result from resolve_dl.js. stderr:" >&2
  tail -5 /tmp/getpaper.err >&2
  exit 1
fi
OKF="$(jget "$LINE" ok)"; TITLE="$(jget "$LINE" title)"; PDFURL="$(jget "$LINE" pdfUrl)"
METHOD="$(jget "$LINE" method)"; STAGE="$(jget "$LINE" stage)"
echo "resolved: title='$TITLE'" >&2
echo "          pdfUrl=$PDFURL  (method=$METHOD)" >&2

if [ "$OKF" != "True" ] && [ "$OKF" != "true" ]; then
  echo "FAILED at stage=${STAGE:-download}: $LINE" >&2
  if [ -n "$FJSON" ]; then
    echo "-- Unpaywall: is_oa=$(jget "$FJSON" oa is_oa) oa_status=$(jget "$FJSON" oa oa_status)" >&2
  fi
  echo "hint: 봇차단이면 --connect (격리 프로필 Chrome :9222), 진짜 페이월이면 우회 금지 — ILL/저자요청." >&2
  exit 1
fi

# post-process: tmp -> dest, %PDF verify, library archive
SRC="$TMP/$OUT"
if [ ! -s "$SRC" ]; then
  RAWPATH="$(jget "$LINE" path | tr '\\' '/')"
  if [ -n "$RAWPATH" ] && [ -s "$RAWPATH" ]; then SRC="$RAWPATH"
  else echo "error: output file missing: $TMP/$OUT (and no usable path in result)" >&2; exit 1; fi
fi
MAGIC="$(head -c 4 "$SRC")"
if [ "$MAGIC" != "%PDF" ]; then
  echo "error: not a PDF (magic='$MAGIC'). Likely a paywall/login HTML page." >&2
  echo "  -> if bot-protected: --connect. if paywalled: Unpaywall/ILL." >&2
  exit 1
fi
mv -f "$SRC" "$DEST/$OUT"
echo "OK -> $DEST/$OUT ($(wc -c < "$DEST/$OUT") bytes, method=$METHOD)"
[ -z "$NOLIB" ] && archive_to_lib "$OUT"
exit 0
