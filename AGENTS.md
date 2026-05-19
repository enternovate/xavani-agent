# Xavani Agent — Development Guide

Built by [Entornovate](https://enternovate.com).
Forked from Hermes Agent by Nous Research.

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
├── cli.py                 # Hermes CLI core (14,466 lines)
├── run_agent.py           # AIAgent class — conversation loop
├── hermes_cli/
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
# Sets HERMES_HOME to ~/.xavani/ for internal compat
# Disables telemetry (HERMES_DISABLE_TELEMETRY, DO_NOT_TRACK)
# Loads xavani-darkblue skin
# Registers OAG commands (/install, /gateway-up, etc.)
# Launches HermesCLI with Xavani branding
```

### Skin System

Skins are YAML files in `hermes_cli/skins/`. No code changes needed to add
a new skin. The `xavani-darkblue` skin uses deep navy/blue/cyan tones with
a cyberpunk aesthetic.

### OAG Commands

Implemented in `hermes_cli/oag_commands.py`. Each command is a `CommandDef`
object registered into the central `COMMAND_REGISTRY`. The `XavaniCLI` class
in `xavani.py` intercepts OAG commands first, then falls through to Hermes.

## Adding a New Skin

Create a YAML file in `hermes_cli/skins/`:
```yaml
name: my-skin
colors:
  banner_title: "#ff6600"
  # ... see xavani-darkblue.yaml for all keys
branding:
  agent_name: "My Agent"
```

Activate with `/skin my-skin` or `set_active_skin("my-skin")`.

## Privacy

Xavani collects NOTHING. No telemetry, no analytics, no phone-home.
All data stays in `~/.xavani/` on the user's machine.
The `HERMES_DISABLE_TELEMETRY` env var is forced at startup.

## Cross-Platform

- macOS: install.sh, brew tap
- Linux: install.sh, apt/pip
- Windows: install.ps1, pip

Python 3.11+ required. Uses psutil for cross-platform process management
(instead of POSIX-only os.kill).

## License

MIT — free for any use. Built by Entornovate.
