# Xavani Agent v0.1.0

**Release Date:** May 19, 2026

> Initial public release of Xavani Agent — a full-featured AI agent platform built by Enternovate. This release ships with multi-platform messaging, native MCP support, a comprehensive skills ecosystem, and extensive security hardening.

---

## Highlights

- **Multi-Platform Messaging Gateway** — Telegram, Discord, Slack, WhatsApp, Signal, Email (IMAP/SMTP), and Home Assistant platforms with unified session management, media attachments, and per-platform tool configuration.

- **MCP (Model Context Protocol) Client** — Native MCP support with stdio and HTTP transports, reconnection, resource/prompt discovery, and sampling (server-initiated LLM requests).

- **Skills Ecosystem** — 70+ bundled and optional skills across 15+ categories with a Skills Hub for discovery, per-platform enable/disable, conditional activation based on tool availability, and prerequisite validation.

- **Centralized Provider Router** — Unified `call_llm()`/`async_call_llm()` API replaces scattered provider logic across vision, summarization, compression, and trajectory saving. All auxiliary consumers route through a single code path with automatic credential resolution.

- **ACP Server** — VS Code, Zed, and JetBrains editor integration via the Agent Communication Protocol standard.

- **CLI Skin/Theme Engine** — Data-driven visual customization: banners, spinners, colors, branding. 7 built-in skins + custom YAML skins.

- **Git Worktree Isolation** — `xavani -w` launches isolated agent sessions in git worktrees for safe parallel work on the same repo.

- **Filesystem Checkpoints & Rollback** — Automatic snapshots before destructive operations with `/rollback` to restore.

- **3,289 Tests** — Comprehensive test suite covering agent, gateway, tools, cron, and CLI.

---

## Core Agent & Architecture

### Provider & Model Support
- Centralized provider router with `resolve_provider_client()` + `call_llm()` API
- Nous Portal as first-class provider in setup
- OpenAI Codex (Responses API) with ChatGPT subscription support
- Codex OAuth vision support + multimodal content adapter
- Validate `/model` against live API instead of hardcoded lists
- Self-hosted Firecrawl support
- Kimi Code API support
- MiniMax model ID update
- OpenRouter provider routing configuration (provider_preferences)
- Nous credential refresh on 401 errors
- z.ai/GLM, Kimi/Moonshot, MiniMax, Azure OpenAI as first-class providers
- Unified `/model` and `/provider` into single view

### Agent Loop & Conversation
- Simple fallback model for provider resilience
- Shared iteration budget across parent + subagent delegation
- Iteration budget pressure via tool result injection
- Configurable subagent provider/model with full credential resolution
- Handle 413 payload-too-large via compression instead of aborting
- Retry with rebuilt payload after compression
- Auto-compress pathologically large gateway sessions
- Tool call repair middleware — auto-lowercase and invalid tool handler
- Reasoning effort configuration and `/reasoning` command
- Detect and block file re-read/search loops after context compression

### Session & Memory
- Session naming with unique titles, auto-lineage, rich listing, and resume by name
- Interactive session browser with search filtering
- Display previous messages when resuming a session
- Honcho AI-native cross-session user modeling
- Proactive async memory flush on session expiry
- Smart context length probing with persistent caching + banner display
- `/resume` command for switching to named sessions in gateway
- Session reset policy for messaging platforms

---

## Messaging Platforms (Gateway)

### Telegram
- Native file attachments: send_document + send_video
- Document file processing for PDF, text, and Office files
- Forum topic session isolation
- Browser screenshot sharing via MEDIA: protocol
- Location support for find-nearby skill
- TTS voice message accumulation fix
- Improved error handling and logging
- Italic regex newline fix + 43 format tests

### Discord
- Channel topic included in session context
- DISCORD_ALLOW_BOTS config for bot message filtering
- Document and video support
- Improved error handling and logging

### Slack
- App_mention 404 fix + document/video support
- Structured logging replacing print statements

### WhatsApp
- Native media sending — images, videos, documents
- Multi-user session isolation
- Cross-platform port cleanup replacing Linux-only fuser
- DM interrupt key mismatch fix

### Signal
- Full Signal messenger gateway via signal-cli-rest-api
- Media URL support in message events

### Email (IMAP/SMTP)
- New email gateway platform

### Home Assistant
- REST tools + WebSocket gateway integration
- Service discovery and enhanced setup
- Toolset mapping fix

### Gateway Core
- Expose subagent tool calls and thinking to users
- Configurable background process watcher notifications
- `edit_message()` for Telegram/Discord/Slack with fallback
- `/compress`, `/usage`, `/update` slash commands
- Eliminated 3x SQLite message duplication in gateway sessions
- Stabilize system prompt across gateway turns for cache hits
- MCP server shutdown on gateway exit
- Pass session_db to AIAgent, fixing session_search error
- Persist transcript changes in /retry, /undo; fix /reset attribute
- UTF-8 encoding fix preventing Windows crashes

---

## CLI & User Experience

### Interactive CLI
- Data-driven skin/theme engine — 7 built-in skins (default, ares, mono, slate, poseidon, sisyphus, charizard) + custom YAML skins
- `/personality` command with custom personality + disable support
- User-defined quick commands that bypass the agent loop
- `/reasoning` command for effort level and display toggle
- `/verbose` slash command to toggle debug at runtime
- `/insights` command — usage analytics, cost estimation & activity patterns
- `/background` command for managing background processes
- `/help` formatting with command categories
- Bell-on-complete — terminal bell when agent finishes
- Up/down arrow history navigation
- Clipboard image paste (Alt+V / Ctrl+V)
- Loading indicators for slow slash commands
- Spinner flickering fix under patch_stdout
- `--quiet/-Q` flag for programmatic single-query mode
- `--fuck-it-ship-it` flag to bypass all approval prompts
- Tools summary flag
- Terminal blinking fix on SSH
- Multi-line paste detection fix

### Setup & Configuration
- Modular setup wizard with section subcommands and tool-first UX
- Container resource configuration prompts
- Backend validation for required binaries
- Config migration system (currently v7)
- API keys properly routed to .env instead of config.yaml
- Atomic write for .env to prevent API key loss on crash
- `xavani tools` — per-platform tool enable/disable with curses UI
- `xavani doctor` for health checks across all configured providers
- `xavani update` with auto-restart for gateway service
- Show update-available notice in CLI banner
- Multiple named custom providers
- Shell config detection improvement for PATH setup
- Consistent XAVANI_HOME and .env path resolution
- Docker backend fix on macOS + subagent auth for Nous Portal

---

## Tool System

### MCP (Model Context Protocol)
- Native MCP client with stdio + HTTP transports
- Sampling support — server-initiated LLM requests
- Resource and prompt discovery
- Automatic reconnection and security hardening
- Banner integration, `/reload-mcp` command
- `xavani tools` UI integration

### Browser
- Local browser backend — zero-cost headless Chromium (no Browserbase needed)
- Console/errors tool, annotated screenshots, auto-recording, dogfood QA skill
- Screenshot sharing via MEDIA: on all messaging platforms

### Terminal & Execution
- `execute_code` sandbox with json_parse, shell_quote, retry helpers
- Docker: custom volume mounts
- Daytona cloud sandbox backend
- SSH backend fix
- Shell noise filtering and login shell execution for environment consistency
- Head+tail truncation for execute_code stdout overflow
- Configurable background process notification modes

### File Operations
- Filesystem checkpoints and `/rollback` command
- Structured tool result hints (next-action guidance) for patch and search_files
- Docker volumes passed to sandbox container config

---

## Skills Ecosystem

### Skills System
- Per-platform skill enable/disable
- Conditional skill activation based on tool availability
- Skill prerequisites — hide skills with unmet dependencies
- Optional skills — shipped but not activated by default
- `xavani skills browse` — paginated hub browsing
- Skills sub-category organization
- Platform-conditional skill loading
- Atomic skill file writes
- Skills sync data loss prevention
- Dynamic skill slash commands for CLI and gateway

### New Skills (selected)
- **ASCII Art** — pyfiglet (571 fonts), cowsay, image-to-ascii
- **ASCII Video** — Full production pipeline
- **DuckDuckGo Search** — Firecrawl fallback; DDGS API expansion
- **Solana Blockchain** — Wallet balances, USD pricing, token names
- **AgentMail** — Agent-owned email inboxes
- **Polymarket** — Prediction market data (read-only)
- **OpenClaw Migration** — Official migration tool
- **Domain Intelligence** — Passive recon: subdomains, SSL, WHOIS, DNS
- **Superpowers** — Software development skills
- **Hermes-Atropos** — RL environment development skill
- Plus: arXiv search, OCR/documents, Excalidraw diagrams, YouTube transcripts, GIF search, Pokémon player, Minecraft modpack server, OpenHue (Philips Hue), Google Workspace, Notion, PowerPoint, Obsidian, find-nearby, and 40+ MLOps skills

---

## Security & Reliability

### Security Hardening
- Path traversal fix in skill_view — prevented reading arbitrary files
- Shell injection prevention in sudo password piping
- Dangerous command detection: multiline bypass fix; tee/process substitution patterns
- Symlink boundary check fix in skills_guard
- Symlink bypass fix in write deny list on macOS
- Multi-word prompt injection bypass prevention
- Cron prompt injection scanner bypass fix
- Enforce 0600/0700 file permissions on sensitive files
- .env file permissions restricted to owner-only
- `--force` flag properly blocked from overriding dangerous verdicts
- FTS5 query sanitization + DB connection leak fix
- Expand secret redaction patterns + config toggle to disable
- In-memory permanent allowlist to prevent data leak
- **CodeQL Security Audit Batch** — 700+ alerts resolved across 52 files:
  - 504 clear-text-logging alerts fixed via centralized `SafeLogFilter` auto-redacting API keys, tokens, and passwords in all entry points
  - 124 path-injection alerts fixed via `validate_path()` guarding all file-system endpoints
  - 33 incomplete-URL-substring-sanitization alerts fixed via `urlparse(hostname)` checks
  - 14 clear-text-storage alerts fixed via redaction before JSON writes, restrictive `.env` permissions (0o600), and `# nosec` justifications for false positives
  - Weak hashing, SSRF, ReDoS, and GitHub Actions injection alerts fixed in auxiliary modules
- `safe_logging.py` — new centralized redaction module with regex patterns for `sk-...`, Bearer tokens, OAuth codes, and long hex/base64 strings
- `validate_path()` — reusable path-traversal guard resolving paths and checking base-directory containment

### Atomic Writes (data loss prevention)
- sessions.json
- Cron jobs
- .env config
- Process checkpoints
- Batch runner
- Skill files

### Reliability
- Guard all print() against OSError for systemd/headless environments
- Reset all retry counters at start of run_conversation
- Return deny on approval callback timeout instead of None
- Fix None message content crashes across codebase
- Fix context overrun crash with local LLM backends
- Prevent `_flush_sentinel` from leaking to external APIs
- Prevent conversation_history mutation in callers
- Fix systemd restart loop
- Close file handles and sockets to prevent fd leaks
- Prevent data loss in clipboard PNG conversion
- Eliminate shell noise from terminal output
- Timezone-aware now() for prompt, cron, and execute_code

### Windows Compatibility
- Guard POSIX-only process functions
- Windows native support via Git Bash + ZIP-based update fallback
- pywinpty for PTY support
- Explicit UTF-8 encoding on all config/data file I/O
- Windows-compatible path handling
- Regex-based search output parsing for drive-letter paths
- Auth store file lock for Windows

---

## Notable Bug Fixes

- Fix DeepSeek V3 tool call parser silently dropping multi-line JSON arguments
- Fix gateway transcript losing 1 message per turn due to offset mismatch
- Fix /retry command silently discarding the agent's final response
- Fix max-iterations retry returning empty string after think-block stripping
- Fix max-iterations retry using hardcoded max_tokens
- Fix Codex status dict key mismatch and visibility filter
- Strip think blocks from final user-facing responses
- Fix think block regex stripping visible content when model discusses tags literally
- Fix Mistral 422 errors from leftover finish_reason in assistant messages
- Fix OPENROUTER_API_KEY resolution order across all code paths
- Fix OPENAI_BASE_URL API key priority
- Fix Anthropic "prompt is too long" 400 error not detected as context length error
- Fix SQLite session transcript accumulating duplicate messages — 3-4x token inflation
- Fix setup wizard skipping API key prompts on first install
- Fix setup wizard showing OpenRouter model list for Nous Portal
- Fix provider selection not persisting when switching via xavani model
- Fix Docker backend failing when docker not in PATH on macOS
- Fix ClawHub Skills Hub adapter for API endpoint changes
- Fix Honcho auto-enable when API key is present
- Fix duplicate 'skills' subparser crash on Python 3.11+
- Fix memory tool entry parsing when content contains section sign
- Fix piped install silently aborting when interactive prompts fail
- Fix false positives in recursive delete detection
- Fix Ruff lint warnings across codebase
- Fix Anthropic native base URL fail-fast
- Fix install.sh creating ~/.xavani before moving Node.js directory
- Fix SystemExit traceback during atexit cleanup on Ctrl+C
- Restore missing MIT license file

---

## Testing

- **3,289 tests** across agent, gateway, tools, cron, and CLI
- Parallelized test suite with pytest-xdist
- Unit tests batch 1: 8 core modules
- Unit tests batch 2: 8 more modules
- Unit tests batch 3: 8 untested modules
- Unit tests batch 4: 5 security/logic-critical modules
- AIAgent (run_agent.py) unit tests
- Trajectory compressor tests
- Clarify tool tests
- Telegram format tests — 43 tests for italic/bold/code rendering
- Vision tools type hints + 42 tests
- Compressor tool-call boundary regression tests
- Test structure reorganization
- Shell noise elimination + fix 36 test failures

---

## RL & Evaluation Environments

- WebResearchEnv — Multi-step web research RL environment
- Modal sandbox concurrency limits to avoid deadlocks
- Hermes-atropos-environments bundled skill
- Local vLLM instance support for evaluation
- YC-Bench long-horizon agent benchmark environment
- OpenThoughts-TBLite evaluation environment and scripts

---

## Documentation

- Full documentation website (Docusaurus) with 37+ pages
- Comprehensive platform setup guides for Telegram, Discord, Slack, WhatsApp, Signal, Email
- AGENTS.md — development guide for AI coding assistants
- CONTRIBUTING.md
- Slash commands reference
- Comprehensive AGENTS.md accuracy audit
- Skin/theme system documentation
- MCP documentation and examples
- Docs accuracy audit — 35+ corrections
- Documentation typo fixes
- CLI config precedence and terminology standardization
- Telegram token regex documentation

---

## License

MIT — free for any use. Built by Enternovate.
