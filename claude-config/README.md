# claude-config

Templates for `~/.claude/` user-global configuration. Designed for cross-PC reproducibility.

## Files

| File | Role |
|---|---|
| `settings.json.template` | `~/.claude/settings.json` template with `{{USER_HOME}}` placeholders |
| `CLAUDE.md.template` | Personal global guidelines (Token Efficiency, AI Coding Agent Guidelines, OMC operating principles) — copied verbatim |
| `apply-config.py` | **Main implementation** — placeholder rendering, JSON validation, backup, deploy |
| `apply-config.ps1` | Windows wrapper that calls `apply-config.py` |
| `apply-config.sh` | macOS/Linux/Git Bash wrapper |

> Python 3.7+ required (uses `pathlib`, `argparse`, type hints). The Python implementation handles backslash-heavy Windows paths safely; sed-based variants were too fragile (silent corruption when `\U`, `\T` etc. appeared in paths).

## Placeholders

| Placeholder | Example value | Used for |
|---|---|---|
| `{{USER_HOME}}` | `C:/Users/JHKIM` (Win) or `/Users/foo` (Mac) | JSON paths with forward slashes (`extraKnownMarketplaces.*.source.path`) |
| `{{USER_HOME_BS}}` | `C:\\Users\\JHKIM` | JSON paths with escaped backslashes (Windows-only entries that originally used backslash) |
| `{{USER_HOME_POSIX}}` | `/c/Users/JHKIM` | MSYS/Git Bash style for `permissions.allow` Bash patterns |

## Usage

### Direct Python (recommended, cross-platform)

```bash
python my-tools/claude-config/apply-config.py             # apply
python my-tools/claude-config/apply-config.py --dry-run   # render and validate without writing
```

### Windows (PowerShell wrapper)

```powershell
cd C:\Users\<you>\my-tools
.\claude-config\apply-config.ps1
.\claude-config\apply-config.ps1 --dry-run
```

### macOS / Linux / Git Bash wrapper

```bash
cd ~/my-tools
chmod +x claude-config/apply-config.sh
./claude-config/apply-config.sh
./claude-config/apply-config.sh --dry-run
```

## Backup behavior

Existing files are renamed to `<file>.backup-<YYYYMMDD-HHMMSS>` before being overwritten. The script is idempotent — re-running creates new backups.

## After applying

1. **Restart Claude Code** to pick up new `settings.json`.
2. Re-authenticate any MCP servers (Gmail OAuth, NotebookLM `nlm login`, etc.) — credentials are intentionally not stored in this repo.
3. Verify `extraKnownMarketplaces` paths exist on disk (run `bootstrap/clone-marketplaces.{ps1,sh}` first to ensure honeypot/oh-my-claudecode/Claude-Patent-Creator are cloned).

## Editing

When you change settings on the source PC:

```bash
cp ~/.claude/settings.json my-tools/claude-config/settings.json.template
# Then manually replace concrete paths with placeholders, e.g.:
#   C:/Users/JHKIM/my-tools  →  {{USER_HOME}}/my-tools
```

`apply-config` does the reverse on target PCs.
