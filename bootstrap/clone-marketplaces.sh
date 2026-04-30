#!/usr/bin/env bash
# clone-marketplaces.sh -- Clone external Claude Code marketplaces.
# Idempotent: pulls if directory exists; clones otherwise.
set -euo pipefail

declare -a repos=(
    "https://github.com/orientpine/honeypot|honeypot"
    "https://github.com/yeachan-heo/oh-my-claudecode|oh-my-claudecode"
    "https://github.com/RobThePCGuy/Claude-Patent-Creator|Claude-Patent-Creator"
    "https://github.com/chrisryugj/korean-law-mcp.git|korean-law-mcp"
)

USER_HOME="${USERPROFILE:-$HOME}"

echo "=== clone-marketplaces ==="
for r in "${repos[@]}"; do
    url="${r%%|*}"
    dir="${r##*|}"
    target="$USER_HOME/$dir"
    if [[ -d "$target/.git" ]]; then
        echo "  [pull] $dir"
        git -C "$target" pull --ff-only
    else
        echo "  [clone] $url -> $target"
        git clone "$url" "$target"
    fi
done

echo
echo "Done. claude-config/settings.json.template references:"
for r in "${repos[@]}"; do
    echo "  $USER_HOME/${r##*|}"
done
