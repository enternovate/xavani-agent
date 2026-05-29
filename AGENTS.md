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
