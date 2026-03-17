#!/usr/bin/env bash
# my-tools setup: Claude Code skills + Codex skills + plugins
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLUGINS_DIR="$HOME/.claude/plugins"

# ─── 1. Skills → Claude Code ──────────────────────────────────────────────────
install_claude_skills() {
    local claude_skills="$HOME/.claude/skills"
    local skills_src="$REPO_ROOT/skills"
    if [[ ! -d "$skills_src" ]]; then echo "No skills/ folder; skipping."; return; fi
    mkdir -p "$claude_skills"
    for dir in "$skills_src"/*/; do
        [[ -d "$dir" ]] || continue
        local name; name="$(basename "$dir")"
        echo "Deploying Claude skill: $name"
        rm -rf "$claude_skills/$name"
        cp -R "$dir" "$claude_skills/$name"
    done
    echo "Claude Code skills installed."
}

# ─── 2. Skills → Codex ────────────────────────────────────────────────────────
install_codex_skills() {
    local codex_skills="${CODEX_HOME:-$HOME/.codex}/skills"
    local skills_src="$REPO_ROOT/skills"
    if [[ ! -d "$skills_src" ]]; then echo "No skills/ folder; skipping."; return; fi
    mkdir -p "$codex_skills"
    for dir in "$skills_src"/*/; do
        [[ -d "$dir" ]] || continue
        local name; name="$(basename "$dir")"
        echo "Deploying Codex skill: $name"
        rm -rf "$codex_skills/$name"
        cp -R "$dir" "$codex_skills/$name"
    done
    echo "Codex skills installed."
}

# ─── 3. Claude Code Plugins ───────────────────────────────────────────────────
update_plugin_registries() {
    local marketplace="$1" github_repo="$2" plugin_name="$3"
    local version="$4" install_path="$5" sha="$6"
    local plugin_key="${plugin_name}@${marketplace}"
    local now; now="$(date -u '+%Y-%m-%dT%H:%M:%S.000Z')"
    local ip_file="$PLUGINS_DIR/installed_plugins.json"
    local km_file="$PLUGINS_DIR/known_marketplaces.json"
    [[ -f "$ip_file" ]] || echo '{"version":2,"plugins":{}}' > "$ip_file"
    [[ -f "$km_file" ]] || echo '{}' > "$km_file"

    (python3 2>/dev/null || python) - <<EOF
import json

# installed_plugins.json
ip = json.load(open('$ip_file'))
ip['plugins']['$plugin_key'] = [{
    'scope': 'user',
    'installPath': '$install_path',
    'version': '$version',
    'installedAt': '$now',
    'lastUpdated': '$now',
    'gitCommitSha': '$sha'
}]
json.dump(ip, open('$ip_file', 'w'), indent=2, ensure_ascii=False)

# known_marketplaces.json
km = json.load(open('$km_file'))
km['$marketplace'] = {
    'source': {'source': 'github', 'repo': '$github_repo'},
    'installLocation': '$PLUGINS_DIR/marketplaces/$marketplace',
    'lastUpdated': '$now'
}
json.dump(km, open('$km_file', 'w'), indent=2, ensure_ascii=False)
EOF
    echo "  Registry updated."
}

install_bkit() {
    local marketplace="bkit-marketplace"
    local repo="popup-studio-ai/bkit-claude-code"
    local plugin_name="bkit"
    local cache_dir="$PLUGINS_DIR/cache/$marketplace/$plugin_name"
    local temp_dir; temp_dir="$(mktemp -d)"

    echo; echo "Installing bkit plugin..."
    git clone --depth 1 "https://github.com/$repo" "$temp_dir" --quiet

    local sha; sha="$(git -C "$temp_dir" rev-parse HEAD)"
    local version
    local cfg="$temp_dir/bkit.config.json"
    if [[ -f "$cfg" ]]; then
        version="$(python3 -c "import json; print(json.load(open('$cfg'))['version'])" 2>/dev/null || python -c "import json; print(json.load(open('$cfg'))['version'])")"
    else
        version="${sha:0:12}"
    fi

    local install_path="$cache_dir/$version"
    if [[ -d "$install_path" ]]; then
        echo "  bkit $version already installed — skipping."
        rm -rf "$temp_dir"
    else
        mkdir -p "$install_path"
        cp -r "$temp_dir/." "$install_path/"
        rm -rf "$temp_dir"
        echo "  Installed bkit $version -> $install_path"
    fi

    update_plugin_registries "$marketplace" "$repo" "$plugin_name" "$version" "$install_path" "$sha"
}

install_local_plugin() {
    local plugin_name="$1"
    local marketplace="my-tools"
    local repo="nanomechanicsKIMM/my-tools"
    local plugin_src="$REPO_ROOT/plugins/$plugin_name"
    local cache_dir="$PLUGINS_DIR/cache/$marketplace/$plugin_name"
    local mkt_dir="$PLUGINS_DIR/marketplaces/$marketplace/plugins/$plugin_name"

    echo; echo "Installing $plugin_name plugin..."

    if [[ ! -d "$plugin_src" ]]; then
        echo "  plugins/$plugin_name not found; skipping."
        return
    fi

    local version
    version="$(python3 -c "import json; print(json.load(open('$plugin_src/.claude-plugin/plugin.json'))['version'])" 2>/dev/null || python -c "import json; print(json.load(open('$plugin_src/.claude-plugin/plugin.json'))['version'])")"
    local install_path="$cache_dir/$version"

    if [[ -d "$install_path" ]]; then
        echo "  $plugin_name $version already installed — reinstalling."
        rm -rf "$install_path"
    fi
    mkdir -p "$install_path"
    cp -R "$plugin_src/." "$install_path/"
    echo "  Installed $plugin_name $version -> $install_path"

    mkdir -p "$mkt_dir"
    cp -R "$plugin_src/." "$mkt_dir/"
    echo "  Marketplace entry -> $mkt_dir"

    local sha
    sha="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo "bundled")"

    update_plugin_registries "$marketplace" "$repo" "$plugin_name" "$version" "$install_path" "$sha"
}

install_visual_generator() { install_local_plugin "visual-generator"; }
install_hwpx_tools()       { install_local_plugin "hwpx-tools"; }
install_patent_tools()     { install_local_plugin "patent-tools"; }

install_playwright() {
    local marketplace="claude-plugins-official"
    local repo="anthropics/claude-plugins-official"
    local plugin_name="playwright"
    local cache_dir="$PLUGINS_DIR/cache/$marketplace/$plugin_name"

    echo; echo "Installing playwright plugin..."
    local sha; sha="$(git ls-remote "https://github.com/$repo" HEAD | cut -f1)"
    local version="${sha:0:12}"
    local install_path="$cache_dir/$version"

    if [[ -f "$install_path/.mcp.json" ]]; then
        echo "  playwright $version already installed — skipping."
    else
        mkdir -p "$install_path"
        cat > "$install_path/.mcp.json" <<'MCPEOF'
{
  "playwright": {
    "command": "npx",
    "args": ["@playwright/mcp@latest"]
  }
}
MCPEOF
        touch "$install_path/.claude-plugin"
        echo "  Installed playwright $version -> $install_path"
    fi

    update_plugin_registries "$marketplace" "$repo" "$plugin_name" "$version" "$install_path" "$sha"
}

# ─── Main ─────────────────────────────────────────────────────────────────────
echo "=== my-tools setup ==="
install_claude_skills
install_codex_skills
mkdir -p "$PLUGINS_DIR/cache"
install_bkit
install_playwright
install_visual_generator
install_hwpx_tools
install_patent_tools
echo; echo "Done! Restart Claude Code to activate plugins."
