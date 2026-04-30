# bootstrap/

Scripts to provision a clean PC with the OS-level dependencies my-tools relies on.

## Files

| File | Role |
|---|---|
| `install-prereqs.ps1` | Windows: winget-based install of Git, Node LTS, OpenJDK 21, Miniconda3, Obsidian + npm globals + Python pkgs |
| `install-prereqs.sh` | macOS (Homebrew) / Linux (apt + NodeSource) equivalent |
| `clone-marketplaces.ps1` / `.sh` | Clone the 3 external Claude Code marketplaces referenced by `claude-config/settings.json.template` |
| `python-requirements.txt` | Pinned Python deps (`>=` minor versions) used by skills |
| `npm-globals.txt` | Global npm packages (claude-code CLI, qmd, etc.) |

## Order of operations on a fresh PC

```
1. git clone https://github.com/nanomechanicsKIMM/my-tools.git ~/my-tools
2. cd ~/my-tools
3. ./bootstrap/install-prereqs.{ps1,sh}        # OS deps + npm + pip
4. # Open a NEW terminal so PATH/CONDA settings take effect
5. ./bootstrap/clone-marketplaces.{ps1,sh}     # external repos referenced by settings.json
6. ./setup.{ps1,sh}                             # deploy skills + plugins + commands + apply-config
7. # Restart Claude Code
8. # Re-authenticate MCP servers manually (Gmail OAuth, NotebookLM `nlm login`, ...)
```

## Idempotency

All scripts skip work that's already done:
- `winget list --id <pkg>` check before install
- `git pull --ff-only` if directory exists; clone otherwise
- `pip install` is naturally idempotent

Re-running after PATH changes or partial failures is safe.

## What this does NOT install

- **Claude Code itself** — installed via `npm install -g @anthropic-ai/claude-code` (in `npm-globals.txt`)
- **MCP server credentials** — Gmail / NotebookLM / etc. require manual OAuth on each PC
- **Vault** (`LLM_wiki/`) — separate git repository, clone manually
- **GEMINI_API_KEY / other secrets** — set as env vars or in `~/.config/...`

See `docs/NEW-PC-BOOTSTRAP.md` (Phase 6) for the end-to-end checklist.
