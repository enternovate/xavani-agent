<p align="center">
  <img src="assets/xavani-buffalo.jpg" alt="Xavani Agent" width="200"/>
</p>

<h1 align="center">Xavani Agent</h1>

<p align="center">
  <b>The open-source AI agent gateway.</b><br>
  Fully local. Private. Cross-platform. Zero telemetry.<br>
  Built by <a href="https://enternovate.com">Enternovate</a> — Open Source.<br>
  <i>Pronounced: shahr-vaa-nee</i><br>
  <sub>Photo by <a href="https://unsplash.com/@andymcclan?utm_source=xavani-agent&utm_medium=referral">Andy McClanahan</a> on <a href="https://unsplash.com/photos/water-buffalo-on-wheat-field-thC1uwWdMfM?utm_source=xavani-agent&utm_medium=referral">Unsplash</a></sub>
</p>

<p align="center">
  <a href="#quick-start"><img src="https://img.shields.io/badge/Quick%20Start-2%20minutes-4a9eff" alt="Quick Start"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue" alt="MIT"></a>
  <a href="https://github.com/enternovate/xavani-agent"><img src="https://img.shields.io/github/stars/enternovate/xavani-agent?style=social" alt="Stars"></a>
</p>

---

## Welcome to Xavani

Xavani is an **open-source AI agent gateway** that runs entirely on your machine.
Connect to any AI model — OpenAI, Anthropic, Google Gemini, DeepSeek, GLM, Qwen,
Yi, MiniMax, Kimi, Baichuan, Step, Doubao, or local models via Ollama — all
through a single CLI. With a built-in MCP proxy, policy engine, protocol bridge,
memory system, observability stack, and 169+ skills.

Zero telemetry. Zero cloud dependency. Your data stays on your machine.

Built by [Enternovate](https://enternovate.com).

---

## Quick Start

### One-Command Install

```bash
# macOS / Linux
curl -fsSL https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.sh | bash

# Windows (PowerShell)
iwr -Uri https://raw.githubusercontent.com/enternovate/xavani-agent/main/install.ps1 | iex
```

### Via pip

```bash
git clone https://github.com/enternovate/xavani-agent.git
cd xavani-agent
pip install -e .
xavani
```

### Set Your API Key

```bash
# Edit ~/.xavani/.env, add your provider key:
echo "OPENAI_API_KEY=sk-..." >> ~/.xavani/.env
```

Then run `xavani` and start typing.

---

## Supported AI Providers

Xavani works with virtually every major AI provider — global and Chinese.

### Global Providers

| Provider | Env Variable | Models | Sign Up |
|----------|-------------|--------|---------|
| OpenAI | `OPENAI_API_KEY` | GPT-4o, GPT-4.5, o-series | platform.openai.com |
| Anthropic | `ANTHROPIC_API_KEY` | Claude Opus 4.6, Sonnet 4, Haiku | console.anthropic.com |
| Google Gemini | `GOOGLE_API_KEY` | Gemini 2.5 Flash, Gemini 2.5 Pro | aistudio.google.com |
| OpenRouter | `OPENROUTER_API_KEY` | 200+ models across all providers | openrouter.ai/keys |
| xAI Grok | `XAI_API_KEY` | Grok 3, Grok 3 Mini | console.x.ai |
| Groq | `GROQ_API_KEY` | Llama 3, Mixtral, Whisper (fast) | console.groq.com |
| NVIDIA NIM | `NVIDIA_API_KEY` | Llama 3.1 Nemotron, Mistral, +40 models | build.nvidia.com |
| HuggingFace | `HF_TOKEN` | 20+ open-source models | huggingface.co/settings/tokens |
| Ollama (local) | None needed | Llama 4, Qwen, Mistral, DeepSeek | ollama.com |
| LM Studio (local) | None needed | Any local model | lmstudio.ai |

### Chinese AI Providers

| Provider | Env Variable | Models | Sign Up |
|----------|-------------|--------|---------|
| DeepSeek | `DEEPSEEK_API_KEY` | DeepSeek-V3, DeepSeek-R1 | platform.deepseek.com |
| Alibaba Qwen | `QWEN_API_KEY` | Qwen3, QwQ, Qwen2.5 | aliyun.com |
| ZhipuAI GLM | `GLM_API_KEY` | GLM-5, GLM-4-Plus | z.ai / open.bigmodel.cn |
| Moonshot Kimi | `KIMI_API_KEY` | Kimi K2.5, K2 | platform.kimi.ai |
| MiniMax | `MINIMAX_API_KEY` | MiniMax M2.5, T2.5 | minimax.io |
| 01.AI Yi | `YI_API_KEY` | Yi-Lightning, Yi-Large | 01.ai |
| ByteDance Doubao | `DOUBAO_API_KEY` | Doubao-Pro, Doubao-Lite | volcengine.com |
| Baidu ERNIE | `BAIDU_API_KEY` | ERNIE 4.5, ERNIE 3.5 | yiyan.baidu.com |
| Baichuan AI | `BAICHUAN_API_KEY` | Baichuan4, Baichuan3 | baichuan-ai.com |
| StepFun | `STEP_API_KEY` | Step-2, Step-1 | stepfun.com |
| SenseTime | `SENSETIME_API_KEY` | SenseNova 5.5 | sensetime.com |
| OpenCode Go | `OPENCODE_GO_API_KEY` | OpenCode Go models | opencode.ai |
| OpenCode Zen | `OPENCODE_ZEN_API_KEY` | Curated global models | opencode.ai |
| Qwen OAuth | OAuth login | Qwen models | qwen portal |

### Other Providers

| Provider | Env Variable | Notes |
|----------|-------------|-------|
| Arcee AI | `ARCEEAI_API_KEY` | Trinity models — chat.arcee.ai |
| NovitaAI | `NOVITA_API_KEY` | 90+ models — novita.ai |
| Azure Foundry | `AZURE_API_KEY` | Azure OpenAI — portal.azure.com |
| AWS Bedrock | `AWS_ACCESS_KEY_ID` | Bedrock models — aws.amazon.com |
| GitHub Models | `GITHUB_TOKEN` | Models via Copilot — github.com |
| KiloCode | `KILOCODE_API_KEY` | KiloCode gateway |
| Vercel AI Gateway | `AI_GATEWAY_API_KEY` | Vercel AI proxy |

To use a provider, set the env variable in `~/.xavani/.env` and either configure
in `~/.xavani/config.yaml` or use `/model <name>` in the CLI:

```bash
# In ~/.xavani/.env
DEEPSEEK_API_KEY=sk-...
GLM_API_KEY=...
QWEN_API_KEY=...

# In the Xavani CLI
/model deepseek/deepseek-r1
/model glm-5
/model qwen/qwen3
```

---

## Getting the Most Out of Xavani

Xavani is not just a CLI. It's a full-stack AI agent platform with six integrated
systems. Use all of them to unlock its full potential.

### Mode 1: Interactive Agent (Daily Driver)

```bash
xavani
```

169 skills loaded, any provider, persistent memory across sessions. The Context
Enricher analyzes every input to understand intent, load relevant skills, and
confirm understanding before executing.

**Pro tip:** Xavani learns your style over ~10 sessions — your humor, expertise
level, favorite project types, and communication preferences.

### Slash Commands

| Command | Description | Example |
|---------|-------------|---------|
| `/model <name>` | Switch AI model mid-session | `/model gpt-4o` |
| `/reasoning <level>` | Set reasoning effort (low/medium/high) | `/reasoning high` |
| `/fast` | Toggle priority processing | `/fast` |
| `/steer <msg>` | Add context without interrupting | `/steer don't touch prod` |
| `/goal <goal>` | Set a standing goal across turns | `/goal finish this PR` |
| `/subgoal <criterion>` | Add criteria to active goal | `/subgoal add tests` |
| `/personality <name>` | Switch personality | `/personality pirate` |
| `/install <name>` | Install an MCP server | `/install postgres` |
| `/gateway-up` | Start the MCP proxy | `/gateway-up` |
| `/gateway-down` | Stop the gateway | `/gateway-down` |
| `/registry-status` | Show installed servers | `/registry-status` |
| `/policy-add <file>` | Add security policy | `/policy-add strict.yaml` |
| `/audit [--since N]` | View audit log | `/audit --since 24h` |
| `/status` | Show session info | `/status` |
| `/help` | Show all commands | `/help` |

### Connect via Telegram

Xavani has a built-in Telegram bot gateway. You can control Xavani from your
phone — send messages, run commands, receive responses — all through Telegram:

```bash
# 1. Get a bot token from @BotFather on Telegram
# 2. Set it in ~/.xavani/.env:
echo "TELEGRAM_BOT_TOKEN=your_bot_token" >> ~/.xavani/.env
echo "TELEGRAM_ALLOWED_USERS=your_telegram_id" >> ~/.xavani/.env

# 3. Start the gateway (runs bot + MCP proxy)
xavani --gateway
```

Now message your bot on Telegram. Every slash command works — `/model`,
`/reasoning`, `/gateway-up`, `/install`, `/audit`, `/help`. Same Xavani,
now in your pocket.

Also supported: Discord, Slack, WhatsApp, Signal, Matrix, Email, SMS,
and 20+ other messaging platforms. Configure them in `~/.xavani/config.yaml`.

### Mode 2: The MCP Gateway

```bash
xavani --gateway
```

Starts a secure MCP proxy on `localhost:8080` that sits between any AI client
and your tool servers, enforcing policies, rate limits, auth, and audit on
every call.

**How to set up and use the gateway:**

1. **Start the gateway:** `xavani --gateway` (or `/gateway-up` in CLI)
2. **Connect any MCP client** to `http://localhost:8080/mcp`
3. **Secure it with your API key:** The gateway generates a token on first run
4. **Install tool servers:** `/install postgres`, `/install brave-search`
5. **Add policies:** `/policy-add my-rules.yaml`
6. **View audit trail:** `/audit --since 24h`
7. **Stop the gateway:** `/gateway-down`

**What the gateway enforces:**
- Rate limits: 30 calls/min per user (configurable)
- Policies: allow/deny specific tools and resources
- Auth: API key or JWT required for access
- Audit: every request logged with full trace to SQLite

### Mode 3: The Protocol Bridge

Translate between MCP, A2A, and OpenAPI — so any tool works with any protocol.

```bash
# Use an MCP tool from an A2A agent
curl -X POST http://localhost:8080/bridge/mcp-to-a2a \
  -H "Content-Type: application/json" \
  -d '{"mcp_tool": "postgres:query", "params": {"query": "SELECT 1"}}'

# Convert any OpenAPI spec to callable MCP tools
curl -X POST http://localhost:8080/bridge/openapi/convert \
  -H "Content-Type: application/json" \
  -d '{"spec_url": "https://api.example.com/openapi.json"}'
```

### Mode 4: The Memory Layer

Two types of persistent memory, all stored locally:

| Type | What It Stores | Retention |
|------|---------------|-----------|
| Episodic | Full conversations, decisions, outcomes | 90 days (auto-archived) |
| Procedural | Learned patterns, successful approaches | Indefinite (gets smarter) |

Episodic memory is FTS5-indexed for natural language recall:
```
/in the conversation last week about the database migration, what was the
final schema we decided on?
```

Cross-agent context sharing: multiple agents share memory with automatic
conflict resolution.

### Mode 5: The Observability Stack

```bash
open http://localhost:8081    # Live dashboard
/audit --since 7d             # CLI audit viewer
```

- Live dashboard with real-time metrics, latency charts, token usage
- OpenTelemetry-native traces on every tool call, LLM call, and agent step
- CLI audit viewer with filtering by user, tool, or errors

### Mode 6: The Agent Runtime

Package any agent configuration as a portable `.agent.toml` file:

```bash
xavani --runtime create my-reviewer
xavani --runtime export my-reviewer ./my-reviewer.agent.toml
xavani --runtime run ./my-reviewer.agent.toml
```

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

[memory]
type = "episodic"
ttl_days = 30

[policies]
rate_limit = "30/min"
allowed_tools = ["read_file", "search_files", "patch"]
audit = true
```

### Mode 7: The Package Manager

```bash
/install postgres          # Install PostgreSQL MCP server
/install brave-search      # Install web search
/registry-list             # See all available servers
/security-scan postgres    # Scan server for vulnerabilities
```

Every server is security-scanned on install. Policies auto-applied. Audit trail
tracks every tool call.

---

## The Deep Learning Layer

Xavani has a **Context Enricher** that sits between you and the AI:

1. **Receives** your raw message
2. **Analyzes** against your UserProfile (style, knowledge, preferences)
3. **Enriches** with implicit context the AI needs
4. **Matches skills** — detects relevant skills from the 169 available
5. **Reiterates** — confirms understanding before executing
6. **Forwards** the enriched message to the LLM

After ~10 sessions, Xavani adapts to your communication style, humor preferences,
expertise level in different domains, favorite project types, and work schedule.

---

## Power User Workflows

### Code Review Pipeline

```bash
/install filesystem
/install github
xavani --gateway &
xavani --message "Review the last 3 commits for security issues"
```

### Research + Memory

```bash
/ "Research the current state of WebAssembly in 2026"
# Next session — no context needed
/ "Continuing from where I left off on Wasm research"
```

### Dashboard Monitoring

```bash
xavani          # In one terminal
open http://localhost:8081   # In another — live metrics
```

---

## Configuration

Xavani stores everything in `~/.xavani/`:

```
~/.xavani/
  config.yaml          # Main configuration (provider, model, terminal, etc.)
  .env                 # API keys (never uploaded anywhere)
  logs/                # Session logs + traces + metrics
    traces.jsonl       # OpenTelemetry trace spans
    metrics.json       # Performance metrics
    agents/            # Per-agent runtime logs
  skills/              # Loaded skills
  policies/            # Policy rules (YAML)
  installed/           # Installed MCP server configs
  data/                # Memory store (SQLite)
    memory/            # Episodic + procedural memory
    bridge/            # Protocol bridge state
  agent-images/        # Portable agent image registry
```

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
│  │  OpenAI · Anthropic · Gemini · DeepSeek · GLM · Qwen   │  │
│  │  Yi · MiniMax · Kimi · Baichuan · Step · Doubao ·       │  │
│  │  Ernie · SenseTime · Ollama · OpenRouter · xAI · Groq  │  │
│  │  HuggingFace · NVIDIA · Arcee · Azure · AWS · + more   │  │
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

169 built-in skills across 27 categories. All run locally. No cloud dependency.

| Category | Skills | Use Cases |
|----------|--------|-----------|
| Creative | 25 | ASCII art, diagrams, video, music, design |
| ML/AI | 36 | Fine-tuning, RAG, embeddings, training |
| Research | 16 | Web search, deep research, paper writing |
| GitHub | 6 | Code review, PR workflow, repo management |
| MCP | 3 | Build, deploy, manage MCP servers |
| Software Dev | 12 | TDD, debugging, planning, code review |
| Productivity | 16 | Notion, Google Workspace, PDFs, OCR |
| Autonomous Agents | 7 | Deploy coding agents |
| Finance | 8 | Models, analysis, presentations |
| +19 more | 40 | Blockchain, gaming, email, IoT, security |

---

## Privacy

Xavani collects **nothing**. Zero telemetry. Zero analytics. Zero phone-home.
Zero crash reports. Your API keys stay in `~/.xavani/.env` and are never
uploaded. The environment variables `XAVANI_DISABLE_TELEMETRY=1` and
`DO_NOT_TRACK=1` are forced at startup.

All data — logs, traces, metrics, memory, config — stays in `~/.xavani/`
on your machine.

---

## About Enternovate

Enternovate builds open-source AI infrastructure. We believe AI tools should
be private, local, and accessible to everyone — not locked behind vendor clouds
or data-harvesting business models.

Xavani Agent is our flagship open-source project. MIT licensed. Free for any
use, commercial or personal.

---

<p align="center">
  Built by <a href="https://enternovate.com">Enternovate</a> — Open Source.<br>
  Pronounced: <i>shahr-vaa-nee</i><br>
  <b>Buffalo out. ⚡</b>
</p>
