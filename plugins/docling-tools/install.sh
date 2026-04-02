#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Installing docling-tools dependencies..."
pip install -r "$SCRIPT_DIR/requirements.txt"
echo "docling-tools installed."
