#!/usr/bin/env bash
# install-prereqs.sh -- Install OS-level prerequisites
# Auto-detects macOS (brew) vs Linux (apt). Idempotent.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== install-prereqs ==="

if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew >/dev/null 2>&1; then
        echo "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    for pkg in git node openjdk@21 miniconda obsidian; do
        if brew list "$pkg" >/dev/null 2>&1; then
            echo "  [skip] $pkg"
        else
            echo "  [install] $pkg"
            brew install "$pkg" || brew install --cask "$pkg" || true
        fi
    done
elif [[ -f /etc/debian_version ]]; then
    sudo apt-get update
    sudo apt-get install -y git curl ca-certificates openjdk-21-jdk
    # Node.js LTS via NodeSource
    if ! command -v node >/dev/null 2>&1; then
        curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
        sudo apt-get install -y nodejs
    fi
    # Miniconda
    if [[ ! -d "$HOME/miniconda3" ]]; then
        curl -fsSL https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -o /tmp/miniconda.sh
        bash /tmp/miniconda.sh -b -p "$HOME/miniconda3"
    fi
else
    echo "Unsupported OS. Install git/node/openjdk-21/miniconda manually."
    exit 1
fi

echo
echo "=== Node.js global packages ==="
npm_globals="$SCRIPT_DIR/npm-globals.txt"
if [[ -f "$npm_globals" ]]; then
    while IFS= read -r pkg; do
        [[ -z "$pkg" || "$pkg" == \#* ]] && continue
        echo "  npm install -g $pkg"
        npm install -g "$pkg" --silent
    done < "$npm_globals"
fi

echo
echo "=== Python packages ==="
PYTHON="${PYTHON:-python3}"
req="$SCRIPT_DIR/python-requirements.txt"
if [[ -f "$req" ]]; then
    "$PYTHON" -m pip install --upgrade pip
    "$PYTHON" -m pip install -r "$req"
else
    echo "  python-requirements.txt not found; skip"
fi

echo
echo "Done. Open a new terminal, then run clone-marketplaces.sh."
