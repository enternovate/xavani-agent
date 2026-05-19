<p align="center">
  <img src="assets/xavani-buffalo.png" alt="Xavani Agent" width="200"/>
</p>

<h1 align="center">Xavani Agent</h1>

<p align="center">
  <b>The open-source AI agent gateway.</b><br>
  Fully local. Private. Cross-platform. Zero telemetry.<br>
  Built by <a href="https://enternovate.com">Enternovate</a> — provided as open source.<br>
  <i>Pronounced: shahr-caa-nee</i>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Quick%20Start-2%20minutes-4a9eff" alt="Quick Start"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT"></a>
  <a href="https://github.com/enternovate/xavani-agent"><img src="https://img.shields.io/github/stars/enternovate/xavani-agent?style=social" alt="Stars"></a>
</p>

---

## Welcome to Xavani

Xavani is an **open-source AI agent gateway** that runs entirely on your machine.
It connects you to any AI model through a single CLI, with a built-in MCP proxy,
policy engine, memory system, observability stack, and 169+ skills — all offline,
all private, all yours.

Built by [Enternovate](https://enternovate.com) — a company that believes AI
infrastructure should be open, private, and local by default.

---

## Quick Start

### One-Command Install

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.sh | bash

# Windows (PowerShell)
iwr -Uri https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.ps1 | iex
```

### Or via pip

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

### Set Your API Key

```bash
# Edit ~/.xavani/.env and add your provider key:
echo "OPENAI_API_KEY=sk-..." >> ~/.xavani/.env
echo "ANTHROPIC_API_KEY=sk-ant-..." >> ~/.xavani/.env
echo "GOOGLE_API_KEY=..." >> ~/.xavani/.env
```

Then run `xavani` and start typing.

---

## Getting the Most Out of Xavani

Xavani is not just a CLI chat tool. It's a full-stack AI agent platform with
six integrated systems. Here's how to use each one to its maximum potential.

### Mode 1: Interactive Agent (Daily Driver)

```bash
xavani
```

This is your everyday AI assistant. 169 skills loaded, multi-provider support,
persistent memory across sessions. Everything you type is analyzed by the
Context Enricher (see below) to understand your intent, load relevant skills,
and confirm understanding before executing.

**Pro tip:** Xavani learns your style over time. The more you use it, the
better it understands your preferences. After about 10 sessions, it will
start anticipating what you need.

### Mode 2: The MCP Gateway (Secure Tool Proxy)

```bash
xavani --gateway
```

Starts the Open Agent Gateway Proxy on `localhost:8080`. This sits between
AI clients (Claude Desktop, Cursor, any MCP-compatible app) and your MCP
servers. It enforces security policies, rate limits, authentication, and
audit logging on EVERY tool call.

**Connect Claude Desktop to Xavani:**

```json
{
  "mcpServers": {
    "xavani": {
      "command": "curl",
      "args": ["-X", "POST", "http://localhost:8080/mcp",
               "-H", "Authorization: Bearer $(cat ~/.xavani/gateway.token)",
               "-H", "Content-Type: application/json",
               "-d", "@-"]
    }
  }
}
```

**What you get:**
- Every tool call is logged with full audit trail
- Rate limits prevent runaway agents (default: 30 calls/min per user)
- Policies can deny specific tools or resources
- API key auth keeps unauthorized clients out
- The audit log is queryable via `/audit --since 24h`

### Mode 3: The Protocol Bridge (MCP ↔ A2A ↔ OpenAPI)

The bridge translates between three protocols so you can use tools from
any ecosystem, regardless of what protocol they speak.

**Use MCP tools from A2A agents:**
```bash
curl -X POST http://localhost:8080/bridge/mcp-to-a2a \
  -H "Content-Type: application/json" \
  -d '{"mcp_tool": "postgres:query", "params": {"query": "SELECT 1"}}'
```

**Use any OpenAPI endpoint as an MCP tool:**
```bash
curl -X POST http://localhost:8080/bridge/openapi/convert \
  -H "Content-Type: application/json" \
  -d '{"spec_url": "https://api.example.com/openapi.json"}'
```

### Mode 4: The Memory Layer (Never Forget)

Xavani remembers everything across sessions — not just chat history, but
the actual context of what you were doing, what worked, what didn't, and
what you prefer.

**Two types of memory:**

| Type | What It Stores | How Long |
|------|---------------|----------|
| **Episodic** | Full conversations, decisions, outcomes | 90 days (auto-archived) |
| **Procedural** | Learned patterns, successful approaches | Forever (gets smarter) |

**Episodic memory** captures the full context of every interaction: what you asked,
what the agent did, what the outcome was. You can recall past sessions with
natural language:

```bash
/in the conversation last week about the database migration, what was the
final schema we decided on?
```

Xavani searches its FTS5-indexed episodic memory and returns the relevant context.

**Procedural memory** learns from repeated patterns. If you frequently ask for
code reviews, Xavani gets better at reviewing your code over time. It remembers
which approaches you preferred, which feedback style you respond to, and what
kinds of suggestions you find useful.

**Cross-agent context sharing:**
Multiple agents can share memory. Agent A's learnings are available to Agent B.
Conflict resolution handles overlapping memories automatically.

### Mode 5: The Observability Stack (See Everything)

```bash
# Start the live dashboard
open http://localhost:8081

# Or use the CLI audit viewer
/audit --since 7d
```

The observability stack gives you complete visibility into everything Xavani does:

**Live Dashboard** (localhost:8081):
- Real-time metrics: active sessions, tool calls, latency, error rates
- Token usage tracker per model
- Audit log viewer with filtering
- Trace viewer with status badges

**CLI Audit Viewer:**
```bash
/audit                # Last 20 entries
/audit --since 24h    # Last 24 hours  
/audit --user me      # Filter by user
/audit --errors       # Only failed/denied requests
/audit --export json  # Export for analysis
```

**OpenTelemetry-native tracing:**
Every tool call, LLM call, agent step, memory access, and gateway request
generates a structured trace span. These are stored locally as JSONL for
analysis or exported to any OpenTelemetry-compatible backend.

### Mode 6: The Agent Runtime (Portable Agent Images)

Package any agent configuration into a portable `.agent.toml` file that
can be versioned, shared, and deployed anywhere.

```bash
# Create an agent image
xavani --runtime create my-reviewer

# Export to a portable file
xavani --runtime export my-reviewer ./my-reviewer.agent.toml

# Run from an exported image
xavani --runtime run ./my-reviewer.agent.toml

# List all running agents
xavani --runtime list
```

**Example agent image:**
```toml
[agent]
name = "code-reviewer"
version = "1.0.0"
description = "Automated code review agent"

[model]
provider = "anthropic"
model = "claude-sonnet-4-6"

[skills]
enabled = ["github-code-review", "github-pr-workflow"]

[toolsets]
enabled = ["file", "terminal", "web"]

[memory]
type = "episodic"
ttl_days = 30

[policies]
rate_limit = "30/min"
allowed_tools = ["read_file", "search_files", "patch"]
audit = true

[environment]
LOG_LEVEL = "info"

[system_prompt]
content = "You are a code review agent. Be thorough but constructive."
```

### Mode 7: The Package Manager (Install MCP Servers)

```bash
# Inside interactive mode
/install postgres        # Install PostgreSQL MCP server
/install brave-search    # Install web search
/install filesystem      # Install filesystem access
/registry-list           # See all available servers
/registry-status         # See what's installed
/security-scan postgres  # Scan installed server for vulnerabilities
```

Each server is security-scanned on install. Rate limits and policies are
auto-applied. The audit trail tracks every tool call made through installed
servers.

---

## The Deep Learning Layer

Xavani has a **Context Enricher** that sits between you and the AI. It:

1. **Receives** your raw message
2. **Analyzes** it against your UserProfile (style, knowledge, preferences)
3. **Enriches** it with implicit context the AI needs to give you the best answer
4. **Matches skills** — detects which of the 169 skills are relevant
5. **Reiterates** — confirms understanding before executing
6. **Forwards** the enriched message to the LLM

This means Xavani learns how you communicate. After about 10 sessions, it
adapts to your style — your preferred level of detail, your humor, your
expertise level in different domains, and your favorite things to build.

**What the UserProfile learns:**
- Your communication style: terse, verbose, technical, creative
- Your humor preference: dry, witty, sarcastic, none
- Your favorite project types: trading bots, web apps, CLI tools, etc.
- Your knowledge domains: where you're an expert (skips basics)
- Your pain points: what you don't like doing
- Your working hours: when you're most productive
- Your tone preference: formal, casual, motivational, direct

**What the Skill Orchestrator does:**
- Scans every message for keywords that match skill descriptions
- Loads the top 5 most relevant skills for each interaction
- Suggests skills you haven't tried but would benefit from
- Gets smarter over time based on which skills you actually use

---

## Power User Workflows

### Workflow 1: Code Review Pipeline

```bash
# Install the GitHub skills
/install filesystem
/install github

# Start the MCP gateway (for external tools)
xavani --gateway &

# In another terminal, run Xavani for code review
xavani --message "Review the last 3 commits in this repo for security issues"
```

### Workflow 2: Research + Memory

```bash
# Xavani remembers everything
/ "Research the current state of WebAssembly in 2026"

# Next session — no context needed
/ "Continuing from where I left off on Wasm research"
```

### Workflow 3: Multi-Protocol Tool Integration

```bash
# Start the protocol bridge
xavani --gateway &

# Register A2A agents
curl -X POST http://localhost:8080/bridge/agents/register \
  -H "Content-Type: application/json" \
  -d '{"name": "research-agent", "url": "http://agent-host:9000/a2a"}'

# Now use that agent's skills as MCP tools
```

### Workflow 4: Dashboard Monitoring

```bash
# Start Xavani in one terminal
xavani

# Open the dashboard in another
open http://localhost:8081
# Shows live metrics: sessions, tool calls, latency, error rates, token usage
```

---

## Configuration

Xavani stores all config in `~/.xavani/`:

```
~/.xavani/
  config.yaml          # Main configuration
  .env                 # API keys (never uploaded anywhere)
  logs/                # Session logs + traces + metrics (local only)
    traces.jsonl       # OpenTelemetry-native trace spans
    metrics.json       # Performance metrics
    agents/            # Per-agent runtime logs
  skills/              # Loaded skills
  policies/            # Policy rules (YAML)
  installed/           # Installed MCP server configs
  data/                # Memory store (SQLite)
    memory/            # Episodic + procedural memory databases
    bridge/            # Protocol bridge state
  agent-images/        # Portable agent image registry
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

### Choose Your Provider

```bash
# Default: OpenRouter (works with many models without a dedicated key)
xavani

# Specific provider
export XAVANI_PROVIDER=anthropic
export XAVANI_MODEL=claude-sonnet-4-6
xavani
```

```bash
# Or in ~/.xavani/config.yaml:
provider: anthropic
model: claude-sonnet-4-6
```

---

## Migrating from Hermes Agent

```bash
# Preview what will be migrated
xavani --migrate-from-hermes --dry-run

# Execute migration (strips all API keys/tokens)
xavani --migrate-from-hermes --apply
```

Migrates: config (without secrets), skills, gateway setup, policies.
Excludes: trading skills (proprietary to Enternovate).

## Migrating from OpenClaw Agent

```bash
# Preview
xavani --migrate-from-openclaw --dry-run

# Execute
xavani --migrate-from-openclaw --apply
```

Maps: config, skills, SOUL.md persona, USER.md profile.
Excludes: trading skills, platform-specific configs.

---

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
│  ┌────────────────────────────────────────────────────────┐  │
│  │  CONTEXT ENRICHER (Deep Learning Layer)                  │  │
│  │  1. RECEIVE → 2. ANALYZE → 3. ENRICH → 4. CHECK SKILLS │  │
│  │  5. REITERATE → 6. FORWARD                              │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────┐  ┌───────────────┐  ┌────────────────────┐   │
│  │ REPL / CLI │  │ SKILLS ENGINE │  │ MCP GATEWAY        │   │
│  │ (prompt    │  │ (169 skills)  │  │ (localhost:8080)   │   │
│  │  toolkit)  │  │ SkillOrch.    │  │ PolicyEngine       │   │
│  └────────────┘  └───────────────┘  │ Auth + RateLimit   │   │
│                                      │ Audit Trail + Logs │   │
│  ┌───────────────────────────────────┴────────────────────┐  │
│  │  PROTOCOL BRIDGE                                       │  │
│  │  MCP ↔ A2A ↔ OpenAPI bidirectional translation         │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  MEMORY LAYER                                           │  │
│  │  Episodic (FTS5 SQLite) + Procedural (Pattern Learning) │  │
│  │  Cross-Agent Context Sharing + Auto-Archiving           │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  OBSERVABILITY STACK                                    │  │
│  │  OpenTelemetry Traces · Metrics · Dashboard (:8081)    │  │
│  │  CLI Audit Viewer · Trace Export                        │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  AGENT RUNTIME                                          │  │
│  │  Portable .agent.toml · Lifecycle Manager · Isolation   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  PROVIDER ABSTRACTION LAYER                              │  │
│  │  OpenAI · Claude · Gemini · Ollama · OpenRouter · xAI   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  LOCAL STORAGE                                          │  │
│  │  SQLite · FTS5 · File System · JSONL Traces           │  │
│  │  ~/.xavani/ — never leaves your machine                │  │
│  └────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

---

## Skills

Xavani ships with **169 built-in skills** across 27 categories. All run locally
with zero cloud dependency.

| Category | Skills | Use Cases |
|----------|--------|-----------|
| Autonomous AI Agents | 7 | Deploy Claude Code, Codex, OpenCode agents |
| Creative | 25 | ASCII art, diagrams, video, music, design, animation |
| Finance | 8 | DCF models, comps analysis, PPT decks |
| GitHub | 6 | Code review, PR workflow, issue management, repo ops |
| MCP | 3 | Build, deploy, and manage MCP servers |
| ML/AI | 36 | Fine-tune models, RAG pipelines, embeddings, training |
| Research | 16 | ArXiv, deep research, web search, paper writing |
| Security | 3 | Password management, forensics, OSINT |
| Software Dev | 12 | TDD, debugging, code review, planning, spikes |
| Productivity | 16 | Notion, Airtable, Google Workspace, PDFs, OCR |
| +17 more | 53 | Blockchain, gaming, email, IoT, data science |

> **Note:** Trading-related skills (trading bots, backtesting, forex) are
> proprietary to Enternovate and excluded from the open-source release.

---

## Comparison

| Feature | Xavani | Claude Code | OpenAI Agents | LangChain |
|---------|--------|-------------|---------------|-----------|
| Open Source | ✅ MIT | ❌ | ❌ | ✅ Apache |
| Fully Local | ✅ (zero telemetry) | ✅ | ❌ (cloud API) | ❌ (partial) |
| MCP Gateway | ✅ with policy engine | ❌ | ❌ | ❌ |
| Multi-Provider | ✅ 6+ providers | ❌ Claude only | ❌ OpenAI only | ✅ |
| Built-in Skills | 169+ across 27 categories | Limited | None | 500+ plugins |
| Protocol Bridge | ✅ MCP ↔ A2A ↔ OpenAPI | ❌ | ❌ | ❌ |
| Memory Layer | ✅ Episodic + Procedural | ❌ (chat only) | ❌ | ❌ (RAG only) |
| Observability | ✅ OpenTelemetry-native | ❌ | Partial (proprietary) | Partial (LangSmith) |
| Agent Runtime | ✅ Portable .agent.toml | ❌ | ❌ | ❌ |
| Policy Engine | ✅ Rate limits + RBAC | ❌ | ❌ | ❌ |
| Package Manager | ✅ apm install + registry | ❌ | ❌ | ❌ |
| Cross-Platform | ✅ Mac + Windows + Linux | ✅ | ❌ | ✅ |

---

## Why Xavani?

**Because the AI ecosystem needs an open, private, local-first alternative
to vendor-locked tools.**

- **Not another cloud service** — everything runs on your machine
- **Not a data harvest** — zero telemetry, zero tracking, zero phone-home
- **Not locked to one model** — use any provider or local LLMs
- **Not just a CLI** — it's an MCP gateway, protocol bridge, memory system,
  observability stack, package manager, and agent runtime — all in one
- **Not just a fork** — six integrated systems that no other project has

---

## Privacy

Xavani collects **nothing**. Zero telemetry. Zero analytics. Zero phone-home.
Zero crash reports. Your API keys stay in `~/.xavani/.env` and are never
uploaded anywhere. Your conversation history stays on your machine. The
environment variables `HERMES_DISABLE_TELEMETRY` and `DO_NOT_TRACK` are
forced at startup.

When using the MCP gateway, all traffic stays on localhost unless you
explicitly configure remote access. The protocol bridge communicates only
with endpoints you register. The observability dashboard binds to localhost
by default.

---

## About Enternovate

Enternovate is a private company building open-source AI infrastructure.
We believe AI tools should be private, local, and accessible to everyone —
not locked behind vendor clouds or data-harvesting business models.

Xavani Agent is our flagship open-source project. MIT licensed. Free for any
use, commercial or personal. Built by Enternovate — provided as open source
for the community.

---

<p align="center">
  Built by <a href="https://enternovate.com">Enternovate</a> — Open Source.<br>
  Provided as open source for the community.<br>
  Pronounced: <i>shahr-caa-nee</i><br>
  <b>Buffalo out. ⚡</b>
</p>
