# Xavani Agent — Development Guide

Built by [Enternovate](https://enternovate.com).
Derived from Hermes Agent (MIT) — see LICENSE and README for full attribution.

## Quick Start

```bash
cd /path/to/xavani-agent
pip install -e .
xavani
```

## Key Files

```
xavani-agent/
├── xavani.py              # Entry point — Xavani CLI
├── cli.py                 # Xavani CLI core (14,466 lines)
├── run_agent.py           # AIAgent class — conversation loop
├── xavani_cli/
│   ├── skins/
│   │   └── xavani-darkblue.yaml  # Dark blue buffalo theme skin
│   ├── oag_commands.py    # OAG-specific commands: /install, /gateway-up, etc.
│   ├── commands.py        # Slash command registry
│   └── skin_engine.py     # Data-driven skin system
├── gateway/
│   └── run.py             # Gateway server (MCP proxy, messaging platforms)
├── oag_skills/            # 169 built-in skills
│   └── MANIFEST.json      # Skills index
├── install.sh             # macOS/Linux installer
├── install.ps1            # Windows installer
└── assets/
    └── buffalo-logo.txt   # ASCII buffalo logo
```

## Architecture

### Entry Point: xavani.py

```python
# Forces ~/.xavani/ home directory
# Sets XAVANI_HOME to ~/.xavani/ for internal compat
# Disables telemetry (XAVANI_DISABLE_TELEMETRY, DO_NOT_TRACK)
# Loads xavani-darkblue skin
# Registers OAG commands (/install, /gateway-up, etc.)
# Launches XavaniCLI with Xavani branding
```

### Skin System

Skins are YAML files in `xavani_cli/skins/`. No code changes needed to add
a new skin. The `xavani-darkblue` skin uses deep navy/blue/cyan tones with
a cyberpunk aesthetic.

### OAG Commands

Implemented in `xavani_cli/oag_commands.py`. Each command is a `CommandDef`
object registered into the central `COMMAND_REGISTRY`. The `XavaniCLI` class
in `xavani.py` intercepts OAG commands first, then falls through to Xavani.

## Adding a New Skin

Create a YAML file in `xavani_cli/skins/`:
```yaml
name: my-skin
colors:
  banner_title: "#ff6600"
  # ... see xavani-darkblue.yaml for all keys
branding:
  agent_name: "My Agent"
```

Activate with `/skin my-skin` or `set_active_skin("my-skin")`.

## Mandatory Research Guidelines (perpetuity)

Every Xavani session loads an always-on principle pack at
`skills/research-guidelines/`. Eleven thinkers — six modern AI researchers
(Karpathy, LeCun, Hinton, Sutskever, Olah, Hassabis) and five
methodologists (Hamming, Knuth, Popper, Pólya, Tukey) — define how the
agent reasons, builds, and ships. The pack is loaded by
`xavani_cli/research_guidelines.py` and spliced into `DEFAULT_SOUL_MD`
at import time, so every persisted `~/.xavani/SOUL.md` ships with the
condensed reference block.

* **Add a guideline:** drop `<lastname>-guidelines.md` into
  `skills/research-guidelines/` with YAML frontmatter (`name,
  description, domain, mandatory, priority, version, sources`).
* **Verify:** `pytest tests/xavani_cli/test_research_guidelines.py`.
* **Browse the catalogue:** see
  [`skills/research-guidelines/MANIFEST.md`](skills/research-guidelines/MANIFEST.md).

The pack is non-removable by design — `mandatory: true` is the schema
default and the loader filters out everything that opts out. The pack
form is modelled on
[multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills).

## Privacy

Xavani collects NOTHING. No telemetry, no analytics, no phone-home.
All data stays in `~/.xavani/` on the user's machine.
The `XAVANI_DISABLE_TELEMETRY` env var is forced at startup.

## Cross-Platform

- macOS: install.sh, brew tap
- Linux: install.sh, apt/pip
- Windows: install.ps1, pip

Python 3.11+ required. Uses psutil for cross-platform process management
(instead of POSIX-only os.kill).

## License

MIT — free for any use. Built by Enternovate.

## Pre-Generation Invariants (read BEFORE writing any code)

Emit code in the correct shape the FIRST time — these gates cost more to
fix after the fact than to write correctly.

### Lint gate: ruff
- This repo lints with **ruff** (config in `pyproject.toml`, `[tool.ruff]`).
  Run `python3 -m ruff check <files>` on every Python file you touch
  before saying "done", and keep ruff clean on touched files.
- `preview = true` is enabled; the load-bearing lint is `PLW1514`
  (unspecified-encoding) — bare `open()`/`read_text()`/`write_text()` in
  text mode silently corrupts non-ASCII content on Windows. `tests/**`,
  `skills/**`, `optional-skills/**`, and `plugins/**` are per-file-ignored.

### Python version and tests
- The interpreter is **`python3`** (Python 3.11+ required).
- Tests run as `python3 -m pytest <paths> -q` — never the bare `pytest`
  command, and not the full suite by default; run targeted paths.

### No-narration-comments rule (zero tolerance)
- Default to **no comments**. Add a comment only to capture non-obvious
  *why*: a bug workaround, an upstream/platform issue, a non-obvious
  invariant or trade-off chosen after investigation, or a link to the
  PR/issue that explains the decision.
- Never narrate what the code does, restate types, or write "TODO:
  refactor" / "this should be cleaner" notes. When in doubt, prefer better
  naming/types over a comment.

### Never edit generated files
- `oag_skills/MANIFEST.json` — the skills index consumed by
  `xavani_learner/` at runtime; it is tooling-generated (the skills-index
  tooling is `scripts/build_skills_index.py`, which writes
  `website/static/api/skills-index.json`). Regenerate, never hand-edit.
- `uv.lock` — managed by uv; change dependencies via uv and let it
  rewrite the lockfile.
- `xavani_agent.egg-info/`, `dist/`, `build/` — build output; never edit.

### Post-edit checks (run before you say "done")

| Touched | Required check |
|---|---|
| Python | `python3 -m ruff check <files>` + targeted `python3 -m pytest <paths> -q` |
| Docs (AGENTS.md, README, website content) | Website build only when explicitly asked |
| Workflow / CI files (`*.yml`, `*.yaml`) | Validate with `yaml.safe_load` |

## Git Discipline (concurrent sessions)

Multiple sessions may be running in this cwd at the same time, each
modifying different files. Git operations that touch unstaged, staged, or
untracked files outside your own changes will stomp on other sessions'
work.

- Stage **explicit paths only** (`git add <path1> <path2>`); **never**
  `git add -A` or `git add .`.
- Before committing, run `git status` and verify you are only staging
  files YOU changed in THIS session.
- Other sessions may share this cwd — do not touch, revert, or commit
  unstaged/untracked files you did not create.
- Conventional commits only: `feat:` / `fix:` / `perf:` / `test:` /
  `docs:` / `ci:` / `style:`.
