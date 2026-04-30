#!/usr/bin/env bash
# apply-config.sh — wrapper around apply-config.py
# Pass --dry-run to validate without writing.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"${PYTHON:-python}" "$DIR/apply-config.py" "$@"
