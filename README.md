<p align="center">
  <img src="assets/xavani-buffalo.png" alt="Xavani Agent" width="200"/>
</p>

<h1 align="center">Xavani Agent</h1>

<p align="center">
  <b>The open-source AI agent gateway.</b><br>
  Fully local. Private. Cross-platform. Built by <a href="https://enternovate.com">Enternovate</a>.<br>
  <i>Pronounced: shahr-caa-nee</i>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Quick%20Start-2%20minutes-4a9eff" alt="Quick Start"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT"></a>
  <a href="https://github.com/enternovate/xavani-agent"><img src="https://img.shields.io/github/stars/enternovate/xavani-agent?style=social" alt="Stars"></a>
</p>

---

## What is Xavani?

Xavani is an **open-source AI agent gateway** that runs entirely on your machine. It connects you to any AI model (OpenAI, Claude, Gemini, Ollama, OpenRouter) through a single CLI, with a built-in MCP gateway, 169+ skills, and zero telemetry.

Built by [Enternovate](https://enternovate.com) and provided as open source. Your data stays on your device. Always.

**Pronunciation:** Xavani is pronounced **shahr-caa-nee**. The "X" takes on a soft "sh" sound, like the beginning of the word "shah."

## Features

| Feature | Description |
|---------|-------------|
| **Multi-Provider** | OpenAI, Anthropic Claude, Google Gemini, Ollama (local), OpenRouter, xAI Grok, and more |
| **169+ Built-in Skills** | Code review, GitHub, web research, MCP servers, data analysis, creative tools |
| **MCP Gateway** | Run `xavani --gateway` to expose an MCP proxy on `localhost:8080` |
| **Skills Registry** | 169 skills across 27 categories — install with `/install` |
| **/gateway Commands** | `/gateway-up` to start, `/gateway-down` to stop, `/audit` to view logs |
| **Policy Engine** | Set rate limits, allow/deny rules, audit logging |
| **Local-Only** | No telemetry. No cloud dependency. No data leaves your machine. |
| **Cross-Platform** | macOS, Windows, Linux |
| **Dark Blue Theme** | Beautiful cyberpunk-themed TUI with buffalo logo |

## Quick Start

### One-Command Install

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.sh | bash

# Windows (PowerShell)
iwr -Uri https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.ps1 | iex
```

### Or Install via pip

```bash
git clone https://github.com/enternovate/xavani-agent.git
cd xavani-agent
pip install -e .
xavani
```

### Or via Homebrew

```bash
brew tap enternovate/xavani
brew install xavani-agent
xavani
```

## Usage

```bash
# Interactive mode (recommended)
xavani

# Single query mode
xavani --message "Write a Python script to analyze this CSV"

# Start MCP gateway (for connecting Claude Desktop, Cursor, etc.)
xavani --gateway

# Install an MCP server
xavani --install postgres

# List available tools
xavani --list-tools

# Migrate from Hermes Agent
xavani --migrate-from-hermes --dry-run    # Preview
xavani --migrate-from-hermes --apply      # Execute

# Migrate from OpenClaw Agent
xavani --migrate-from-openclaw --dry-run   # Preview
xavani --migrate-from-openclaw --apply     # Execute
```

### Slash Commands (in interactive mode)

| Command | Description |
|---------|-------------|
| `/install <name>` | Install an MCP server from registry |
| `/gateway-up` | Start the MCP proxy gateway |
| `/gateway-down` | Stop the gateway |
| `/registry-status` | Show installed servers & status |
| `/policy-add <file>` | Add a policy rule |
| `/audit [--since 24h]` | View audit log |
| `/help` | Show all commands |
| `/exit` | Quit |

## Configuration

Xavani stores all config in `~/.xavani/`:

```
~/.xavani/
  config.yaml          # Main configuration
  .env                 # API keys (never uploaded anywhere)
  logs/                # Session logs (local only)
  skills/              # Loaded skills
  policies/            # Policy rules
  installed/           # Installed MCP server configs
  data/                # Local data store
```

### API Keys

Set your provider API keys in `~/.xavani/.env`:

```bash
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
OPENROUTER_API_KEY=...
GROK_API_KEY=...
```

Or use the `/setup` command in interactive mode.

### Choose Your Provider

```bash
# Default: OpenRouter (works with many models without a dedicated key)
xavani --message "Hello"

# Or pick a specific provider
export XAVANI_PROVIDER=anthropic
export XAVANI_MODEL=claude-sonnet-4-6
xavani
```

## Migrating from Hermes Agent

If you're currently using Hermes Agent (by Nous Research), you can migrate your configuration and skills to Xavani:

1. **Install Xavani** (as shown above)

2. **Preview the migration:**
   ```bash
   xavani --migrate-from-hermes --dry-run
   ```

3. **Run the migration:**
   ```bash
   xavani --migrate-from-hermes --apply
   ```

**What gets migrated:**
- `~/.hermes/config.yaml` → `~/.xavani/config.yaml` (all API keys/tokens/secrets are stripped)
- `~/.hermes/.env.example` → `~/.xavani/.env.example` (without real keys)
- Installed skills from `~/.hermes/skills/` → `~/.xavani/skills/`
- Gateway config from `~/.hermes/gateway.yaml` if present
- Policy files from `~/.hermes/policies/`

**What is NOT migrated:**
- Files containing API keys, tokens, or secrets (`.env`, `credentials.json`, etc.)
- Trading skills (these are proprietary to Enternovate and excluded from the open-source release)

You can also run the migration script directly:
```bash
python scripts/migrate_from_hermes.py --dry-run   # Preview
python scripts/migrate_from_hermes.py --apply      # Execute
```

## Migrating from OpenClaw Agent

If you're migrating from OpenClaw Agent, Xavani provides a compatible migration path:

1. **Install Xavani** (as shown above)

2. **Preview the migration:**
   ```bash
   xavani --migrate-from-openclaw --dry-run
   ```

3. **Run the migration:**
   ```bash
   xavani --migrate-from-openclaw --apply
   ```

**Concept Mapping:**

| OpenClaw | Xavani Equivalent |
|----------|-------------------|
| `~/.openclaw/config.yaml` | `~/.xavani/config.yaml` |
| `~/.openclaw/.env` | `~/.xavani/.env` |
| `~/.openclaw/skills/` | `~/.xavani/skills/` |
| `~/.openclaw/SOUL.md` | Persona section in `config.yaml` |
| `~/.openclaw/USER.md` | User profile in `config.yaml` |
| `~/.openclaw/logs/` | `~/.xavani/logs/` |
| ClawHub skills registry | Skills Registry (`/install`) |
| OpenClaw Connect gateway | MCP Gateway (`localhost:8080`) |

**What gets migrated:**
- Compatible config settings (provider, model, temperature, etc.)
- Installed skills
- SOUL.md persona → stored in config.yaml
- USER.md user profile → stored in config.yaml

**What is NOT migrated:**
- Files containing API keys/tokens/secrets
- Trading skills (proprietary to Enternovate, excluded)
- Platform-specific configs that don't have Xavani equivalents

## Architecture

```
                         ┌──────────────┐
                         │   YOU        │
                         │  (CLI / TUI) │
                         └──────┬───────┘
                                │
┌───────────────────────────────┴───────────────────────────────┐
│                    XAVANI AGENT                               │
│                                                               │
│  ┌────────────┐  ┌───────────────┐  ┌────────────────────┐   │
│  │ REPL / CLI │  │ SKILLS ENGINE │  │ MCP GATEWAY        │   │
│  │ (prompt    │  │ (169 skills)  │  │ (localhost:8080)   │   │
│  │  toolkit)  │  └───────────────┘  └────────────────────┘   │
│  └────────────┘                                              │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  PROVIDER ABSTRACTION LAYER                              │  │
│  │  OpenAI  ·  Claude  ·  Gemini  ·  Ollama  ·  OpenRouter │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LOCAL STORAGE (SQLite + FTS5 + File System)           │  │
│  │  ~/.xavani/ — never leaves your machine                │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

## Skills

Xavani ships with **169 built-in skills** across 27 categories. All skills run locally with no cloud dependency.

> **Note:** Trading-related skills (e.g., deriv-trading, backtesting, forex) are **proprietary to Enternovate** and are excluded from the open-source release. If you need these, please contact Enternovate for a commercial license.

| Category | Skills | What You Can Do |
|----------|--------|-----------------|
| Autonomous AI Agents | 7 | Deploy Claude Code, Codex, OpenCode agents |
| Creative | 25 | ASCII art, diagrams, video, music, design |
| Finance | 8 | DCF models, comps analysis, PPT decks |
| GitHub | 6 | Code review, PR workflow, issue management |
| MCP | 3 | Build & manage MCP servers |
| ML/AI | 36 | Fine-tune models, RAG pipelines, embeddings |
| Research | 16 | ArXiv, web search, deep research |
| Security | 3 | Password management, forensics, OSINT |
| Software Dev | 12 | TDD, debugging, code review, planning |
| +18 more | 53 | Productivity, data science, gaming, email, IoT |

All skills run locally. No cloud dependency. Your data stays yours.

## Comparison: Xavani vs Others

| Feature | Xavani | Claude Code | OpenAI Agents | LangChain |
|---------|--------|-------------|---------------|-----------|
| Open Source | ✅ MIT | ❌ | ❌ | ✅ |
| Local-Only | ✅ | ✅ | ❌ | ❌ |
| MCP Gateway | ✅ | ❌ | ❌ | ❌ |
| Multi-Provider | ✅ 6+ | ❌ (Claude only) | ❌ (OpenAI only) | ✅ |
| Built-in Skills | 169+ | Limited | None | 500+ plugins |
| Cross-Platform | ✅ | ✅ | ❌ | ✅ |
| Private | ✅ (no telemetry) | Partial | ❌ | Partial |
| Policy Engine | ✅ | ❌ | ❌ | ❌ |

## Why Xavani?

Because the AI agent ecosystem needs an **open, private, local-first** alternative to vendor-locked tools. Xavani is:

- **Not another cloud service** — everything runs on your machine
- **Not a data harvest** — zero telemetry, zero tracking
- **Not locked to one model** — use any provider, or run local LLMs
- **Not just a CLI** — it's also an MCP gateway, a skills platform, and a developer tool

## Privacy

Xavani collects **nothing**. No telemetry, no analytics, no phone-home, no crash reports. Your API keys stay in `~/.xavani/.env` and are never uploaded anywhere. Your conversation history stays in `~/.xavani/logs/` on your machine.

When using the MCP gateway, all traffic stays on localhost unless you configure remote access.

## License

MIT — free for any use, commercial or personal.

---

<p align="center">
  Built by <a href="https://enternovate.com">Enternovate</a> — Open Source.<br>
  Provided as open source for the community.<br>
  Pronounced: <i>shahr-caa-nee</i><br>
  <b>Buffalo out. ⚡</b>
</p>
