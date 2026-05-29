---
sidebar_position: 2
title: "Skills System"
description: "On-demand knowledge documents — progressive disclosure, agent-managed skills, and the Skills Hub"
---

# Skills System

Skills are on-demand knowledge documents the agent can load when needed. They follow a **progressive disclosure** pattern to minimize token usage and are compatible with the [agentskills.io](https://agentskills.io/specification) open standard.

All skills live in **`~/.xavani/skills/`** — the primary directory and source of truth. On fresh install, bundled skills are copied from the repo. Hub-installed and agent-created skills also go here. The agent can modify or delete any skill.

You can also point Xavani at **external skill directories** — additional folders scanned alongside the local one. See [External Skill Directories](#external-skill-directories) below.

See also:

- [Bundled Skills Catalog](/docs/reference/skills-catalog)
- [Official Optional Skills Catalog](/docs/reference/optional-skills-catalog)

## Using Skills

Every installed skill is automatically available as a slash command:

```bash
# In the CLI or any messaging platform:
/gif-search funny cats
/axolotl help me fine-tune Llama 3 on my dataset
/github-pr-workflow create a PR for the auth refactor
/plan design a rollout for migrating our auth provider

# Just the skill name loads it and lets the agent ask what you need:
/excalidraw
```

The bundled `plan` skill is a good example. Running `/plan [request]` loads the skill's instructions, telling Xavani to inspect context if needed, write a markdown implementation plan instead of executing the task, and save the result under `.xavani/plans/` relative to the active workspace/backend working directory.

You can also interact with skills through natural conversation:

```bash
xavani chat --toolsets skills -q "What skills do you have?"
xavani chat --toolsets skills -q "Show me the axolotl skill"
```

## Progressive Disclosure

Skills use a token-efficient loading pattern:

```
Level 0: skills_list()           → [{name, description, category}, ...]   (~3k tokens)
Level 1: skill_view(name)        → Full content + metadata       (varies)
Level 2: skill_view(name, path)  → Specific reference file       (varies)
```

The agent only loads the full skill content when it actually needs it.

## SKILL.md Format

```markdown
---
name: my-skill
description: Brief description of what this skill does
version: 1.0.0
platforms: [macos, linux]     # Optional — restrict to specific OS platforms
metadata:
  xavani:
    tags: [python, automation]
    category: devops
    fallback_for_toolsets: [web]    # Optional — conditional activation (see below)
    requires_toolsets: [terminal]   # Optional — conditional activation (see below)
    config:                          # Optional — config.yaml settings
      - key: my.setting
        description: "What this controls"
        default: "value"
        prompt: "Prompt for setup"
---

# Skill Title

## When to Use
Trigger conditions for this skill.

## Procedure
1. Step one
2. Step two

## Pitfalls
- Known failure modes and fixes

## Verification
How to confirm it worked.
```

### Platform-Specific Skills

Skills can restrict themselves to specific operating systems using the `platforms` field:

| Value | Matches |
|-------|---------|
| `macos` | macOS (Darwin) |
| `linux` | Linux |
| `windows` | Windows |

```yaml
platforms: [macos]            # macOS only (e.g., iMessage, Apple Reminders, FindMy)
platforms: [macos, linux]     # macOS and Linux
```

When set, the skill is automatically hidden from the system prompt, `skills_list()`, and slash commands on incompatible platforms. If omitted, the skill loads on all platforms.

## Skill output and media delivery

When a skill response (or any agent response) includes a bare absolute path to a media file — for example `/home/user/screenshots/diagram.png` — the gateway auto-detects it, strips it from the visible text, and delivers the file natively to the user's chat (Telegram photo, Discord attachment, etc.) instead of leaving the raw path in the message.

For audio specifically, the `[[audio_as_voice]]` directive promotes audio files to native voice-message bubbles on platforms that support them (Telegram, WhatsApp).

### Forcing document-style delivery: `[[as_document]]`

Sometimes you want the **opposite** of inline preview: you want the file delivered as a downloadable attachment, not a re-compressed image bubble. The classic example is a high-resolution screenshot or chart — Telegram's `sendPhoto` recompresses it to ~200 KB at 1280 px, destroying readability. A 1-2 MB PNG sent via `sendDocument` keeps the original bytes intact.

If a response (or any text inside it — typically the last line) contains the literal directive `[[as_document]]`, every media path extracted from that response is delivered as a document/file attachment rather than an image bubble:

```
Here is your rendered chart:

/home/user/.xavani/cache/chart-q4-2025.png

[[as_document]]
```

The directive is stripped before delivery, so users never see it. Granularity is intentionally all-or-nothing per response: emit `[[as_document]]` once and every image path in the same response is delivered as a document. This mirrors the scope of `[[audio_as_voice]]`.

Use it from a skill when:

- You produce screenshots or charts the user needs as files (for editing in another tool, archiving, sharing intact).
- The default lossy preview would obscure detail (small text, pixel-accurate diagrams, color-sensitive renders).

Platforms without a separate document path (e.g. SMS) fall back to whatever attachment mechanism they have.

### Conditional Activation (Fallback Skills)

Skills can automatically show or hide themselves based on which tools are available in the current session. This is most useful for **fallback skills** — free or local alternatives that should only appear when a premium tool is unavailable.

```yaml
metadata:
  xavani:
    fallback_for_toolsets: [web]      # Show ONLY when these toolsets are unavailable
    requires_toolsets: [terminal]     # Show ONLY when these toolsets are available
    fallback_for_tools: [web_search]  # Show ONLY when these specific tools are unavailable
    requires_tools: [terminal]        # Show ONLY when these specific tools are available
```

| Field | Behavior |
|-------|----------|
| `fallback_for_toolsets` | Skill is **hidden** when the listed toolsets are available. Shown when they're missing. |
| `fallback_for_tools` | Same, but checks individual tools instead of toolsets. |
| `requires_toolsets` | Skill is **hidden** when the listed toolsets are unavailable. Shown when they're present. |
| `requires_tools` | Same, but checks individual tools. |

**Example:** The built-in `duckduckgo-search` skill uses `fallback_for_toolsets: [web]`. When you have `FIRECRAWL_API_KEY` set, the web toolset is available and the agent uses `web_search` — the DuckDuckGo skill stays hidden. If the API key is missing, the web toolset is unavailable and the DuckDuckGo skill automatically appears as a fallback.

Skills without any conditional fields behave exactly as before — they're always shown.

## Secure Setup on Load

Skills can declare required environment variables without disappearing from discovery:

```yaml
required_environment_variables:
  - name: TENOR_API_KEY
    prompt: Tenor API key
    help: Get a key from https://developers.google.com/tenor
    required_for: full functionality
```

When a missing value is encountered, Xavani asks for it securely only when the skill is actually loaded in the local CLI. You can skip setup and keep using the skill. Messaging surfaces never ask for secrets in chat — they tell you to use `xavani setup` or `~/.xavani/.env` locally instead.

Once set, declared env vars are **automatically passed through** to `execute_code` and `terminal` sandboxes — the skill's scripts can use `$TENOR_API_KEY` directly. For non-skill env vars, use the `terminal.env_passthrough` config option. See [Environment Variable Passthrough](/docs/user-guide/security#environment-variable-passthrough) for details.

### Skill Config Settings

Skills can also declare non-secret config settings (paths, preferences) stored in `config.yaml`:

```yaml
metadata:
  xavani:
    config:
      - key: myplugin.path
        description: Path to the plugin data directory
        default: "~/myplugin-data"
        prompt: Plugin data directory path
```

Settings are stored under `skills.config` in your config.yaml. `xavani config migrate` prompts for unconfigured settings, and `xavani config show` displays them. When a skill loads, its resolved config values are injected into the context so the agent knows the configured values automatically.

See [Skill Settings](/docs/user-guide/configuration#skill-settings) and [Creating Skills — Config Settings](/docs/developer-guide/creating-skills#config-settings-configyaml) for details.

## Skill Directory Structure

```text
~/.xavani/skills/                  # Single source of truth
├── mlops/                         # Category directory
│   ├── axolotl/
│   │   ├── SKILL.md               # Main instructions (required)
│   │   ├── references/            # Additional docs
│   │   ├── templates/             # Output formats
│   │   ├── scripts/               # Helper scripts callable from the skill
│   │   └── assets/                # Supplementary files
│   └── vllm/
│       └── SKILL.md
├── devops/
│   └── deploy-k8s/                # Agent-created skill
│       ├── SKILL.md
│       └── references/
├── .hub/                          # Skills Hub state
│   ├── lock.json
│   ├── quarantine/
│   └── audit.log
└── .bundled_manifest              # Tracks seeded bundled skills
```

## External Skill Directories

If you maintain skills outside of Xavani — for example, a shared `~/.agents/skills/` directory used by multiple AI tools — you can tell Xavani to scan those directories too.

Add `external_dirs` under the `skills` section in `~/.xavani/config.yaml`:

```yaml
skills:
  external_dirs:
    - ~/.agents/skills
    - /home/shared/team-skills
    - ${SKILLS_REPO}/skills
```

Paths support `~` expansion and `${VAR}` environment variable substitution.

### How it works

- **Read-only**: External dirs are only scanned for skill discovery. When the agent creates or edits a skill, it always writes to `~/.xavani/skills/`.
- **Local precedence**: If the same skill name exists in both the local dir and an external dir, the local version wins.
- **Full integration**: External skills appear in the system prompt index, `skills_list`, `skill_view`, and as `/skill-name` slash commands — no different from local skills.
- **Non-existent paths are silently skipped**: If a configured directory doesn't exist, Xavani ignores it without errors. Useful for optional shared directories that may not be present on every machine.

### Example

```text
~/.xavani/skills/               # Local (primary, read-write)
├── devops/deploy-k8s/
│   └── SKILL.md
└── mlops/axolotl/
    └── SKILL.md

~/.agents/skills/               # External (read-only, shared)
├── my-custom-workflow/
│   └── SKILL.md
└── team-conventions/
    └── SKILL.md
```

All four skills appear in your skill index. If you create a new skill called `my-custom-workflow` locally, it shadows the external version.

## Skill Bundles

Skill bundles are tiny YAML files that group several skills under a single slash command. When you run `/<bundle-name>`, every skill listed in the bundle loads at once — useful when a particular task always benefits from the same set of skills together.

### Quick example

```bash
# Create a bundle for backend feature work
xavani bundles create backend-dev \
  --skill github-code-review \
  --skill test-driven-development \
  --skill github-pr-workflow \
  -d "Backend feature work — review, test, PR workflow"
```

Then in the CLI or any gateway platform:

```
/backend-dev refactor the auth middleware
```

The agent receives all three skills loaded into one user message, with any text after the slash command attached as a user instruction.

### YAML schema

Bundles live in **`~/.xavani/skill-bundles/<slug>.yaml`** and look like this:

```yaml
name: backend-dev
description: Backend feature work — review, test, PR workflow.
skills:
  - github-code-review
  - test-driven-development
  - github-pr-workflow
instruction: |
  Always start by writing failing tests, then implement.
  Open the PR through the standard workflow with co-author tags.
```

Fields:
- `name` (optional — defaults to the filename stem) — the bundle's display name. Normalized to a hyphen slug for the slash command (`Backend Dev` → `/backend-dev`).
- `description` (optional) — short text shown in `/bundles` and `xavani bundles list`.
- `skills` (required, non-empty list) — skill names or paths relative to your skills directory. Use the same identifier you'd pass to `/<skill-name>`.
- `instruction` (optional) — extra guidance prepended to the loaded skill content. Useful for codifying "how we always use these together."

### Managing bundles

```bash
# List all installed bundles
xavani bundles list

# Inspect one bundle
xavani bundles show backend-dev

# Create a bundle interactively (omit --skill flags to enter them one per line)
xavani bundles create research

# Overwrite an existing bundle
xavani bundles create backend-dev --skill ... --force

# Delete a bundle
xavani bundles delete backend-dev

# Re-scan ~/.xavani/skill-bundles/ and report changes
xavani bundles reload
```

From inside a chat session, `/bundles` lists every installed bundle and its skills.

### Behavior

- **Bundles take precedence over individual skills** when slugs collide. If you name a bundle `research` and you also have a skill called `research`, `/research` invokes the bundle. This is intentional — you opted into the bundle by naming it.
- **Missing skills are skipped, not fatal.** If a bundle lists `skill-foo` and you haven't installed it, the bundle still loads the skills that do resolve, and the agent gets a note listing what was skipped.
- **Bundles work in every surface** — interactive CLI, TUI, dashboard chat, and every gateway platform (Telegram, Discord, Slack, …) — because dispatch is centralized in the same place as individual skill commands.
- **Bundles do not invalidate the prompt cache.** They generate a fresh user message at invocation time, the same way `/<skill-name>` does — no system prompt mutation.

### When bundles beat installing each skill manually

Use a bundle when:
- You always pair the same skills for a recurring task (`/backend-dev`, `/release-prep`, `/incident-response`).
- You want a one-character-shorter mental model than typing several `/skill` invocations in a row.
- You want to ship a team-wide "task profile" by checking the bundle YAML into a shared dotfiles repo and symlinking it into `~/.xavani/skill-bundles/`.

A bundle is just a YAML alias — it doesn't install skills for you. The skills themselves must already be present (in `~/.xavani/skills/` or an external skill directory). Otherwise the bundle invocation just skips the missing ones.

## Agent-Managed Skills (skill_manage tool)

The agent can create, update, and delete its own skills via the `skill_manage` tool. This is the agent's **procedural memory** — when it figures out a non-trivial workflow, it saves the approach as a skill for future reuse.

### When the Agent Creates Skills

- After completing a complex task (5+ tool calls) successfully
- When it hit errors or dead ends and found the working path
- When the user corrected its approach
- When it discovered a non-trivial workflow

### Actions

| Action | Use for | Key params |
|--------|---------|------------|
| `create` | New skill from scratch | `name`, `content` (full SKILL.md), optional `category` |
| `patch` | Targeted fixes (preferred) | `name`, `old_string`, `new_string` |
| `edit` | Major structural rewrites | `name`, `content` (full SKILL.md replacement) |
| `delete` | Remove a skill entirely | `name` |
| `write_file` | Add/update supporting files | `name`, `file_path`, `file_content` |
| `remove_file` | Remove a supporting file | `name`, `file_path` |

:::tip
The `patch` action is preferred for updates — it's more token-efficient than `edit` because only the changed text appears in the tool call.
:::

## Skills Hub

Browse, search, install, and manage skills from online registries, `skills.sh`, direct well-known skill endpoints, and official optional skills.

### Common commands

```bash
xavani skills browse                              # Browse all hub skills (official first)
xavani skills browse --source official            # Browse only official optional skills
xavani skills search kubernetes                   # Search all sources
xavani skills search react --source skills-sh     # Search the skills.sh directory
xavani skills search https://mintlify.com/docs --source well-known
xavani skills inspect openai/skills/k8s           # Preview before installing
xavani skills install openai/skills/k8s           # Install with security scan
xavani skills install official/security/1password
xavani skills install skills-sh/vercel-labs/json-render/json-render-react --force
xavani skills install well-known:https://mintlify.com/docs/.well-known/skills/mintlify
xavani skills install https://sharethis.chat/SKILL.md              # Direct URL (single-file SKILL.md)
xavani skills install https://example.com/SKILL.md --name my-skill # Override name when frontmatter has none
xavani skills list --source hub                   # List hub-installed skills
xavani skills check                               # Check installed hub skills for upstream updates
xavani skills update                              # Reinstall hub skills with upstream changes when needed
xavani skills audit                               # Re-scan all hub skills for security
xavani skills uninstall k8s                       # Remove a hub skill
xavani skills reset google-workspace              # Un-stick a bundled skill from "user-modified" (see below)
xavani skills reset google-workspace --restore    # Also restore the bundled version, deleting your local edits
xavani skills publish skills/my-skill --to github --repo owner/repo
xavani skills snapshot export setup.json          # Export skill config
xavani skills tap add myorg/skills-repo           # Add a custom GitHub source
```

### Supported hub sources

| Source | Example | Notes |
|--------|---------|-------|
| `official` | `official/security/1password` | Optional skills shipped with Xavani. |
| `skills-sh` | `skills-sh/vercel-labs/agent-skills/vercel-react-best-practices` | Searchable via `xavani skills search <query> --source skills-sh`. Xavani resolves alias-style skills when the skills.sh slug differs from the repo folder. |
| `well-known` | `well-known:https://mintlify.com/docs/.well-known/skills/mintlify` | Skills served directly from `/.well-known/skills/index.json` on a website. Search using the site or docs URL. |
| `url` | `https://sharethis.chat/SKILL.md` | Direct HTTP(S) URL to a single-file `SKILL.md`. Name resolution: frontmatter → URL slug → interactive prompt → `--name` flag. |
| `github` | `openai/skills/k8s` | Direct GitHub repo/path installs and custom taps. |
| `clawhub`, `lobehub`, `claude-marketplace` | Source-specific identifiers | Community or marketplace integrations. |

### Integrated hubs and registries

Xavani currently integrates with these skills ecosystems and discovery sources:

#### 1. Official optional skills (`official`)

These are maintained in the Xavani repository itself and install with builtin trust.

- Catalog: [Official Optional Skills Catalog](../../reference/optional-skills-catalog)
- Source in repo: `optional-skills/`
- Example:

```bash
xavani skills browse --source official
xavani skills install official/security/1password
```

#### 2. skills.sh (`skills-sh`)

This is Vercel's public skills directory. Xavani can search it directly, inspect skill detail pages, resolve alias-style slugs, and install from the underlying source repo.

- Directory: [skills.sh](https://skills.sh/)
- CLI/tooling repo: [vercel-labs/skills](https://github.com/vercel-labs/skills)
- Official Vercel skills repo: [vercel-labs/agent-skills](https://github.com/vercel-labs/agent-skills)
- Example:

```bash
xavani skills search react --source skills-sh
xavani skills inspect skills-sh/vercel-labs/json-render/json-render-react
xavani skills install skills-sh/vercel-labs/json-render/json-render-react --force
```

#### 3. Well-known skill endpoints (`well-known`)

This is URL-based discovery from sites that publish `/.well-known/skills/index.json`. It is not a single centralized hub — it is a web discovery convention.

- Example live endpoint: [Mintlify docs skills index](https://mintlify.com/docs/.well-known/skills/index.json)
- Reference server implementation: [vercel-labs/skills-handler](https://github.com/vercel-labs/skills-handler)
- Example:

```bash
xavani skills search https://mintlify.com/docs --source well-known
xavani skills inspect well-known:https://mintlify.com/docs/.well-known/skills/mintlify
xavani skills install well-known:https://mintlify.com/docs/.well-known/skills/mintlify
```

#### 4. Direct GitHub skills (`github`)

Xavani can install directly from GitHub repositories and GitHub-based taps. This is useful when you already know the repo/path or want to add your own custom source repo.

Default taps (browsable without any setup):
- [openai/skills](https://github.com/openai/skills)
- [anthropics/skills](https://github.com/anthropics/skills)
- [huggingface/skills](https://github.com/huggingface/skills)
- [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills)
- [garrytan/gstack](https://github.com/garrytan/gstack)

- Example:

```bash
xavani skills install openai/skills/k8s
xavani skills tap add myorg/skills-repo
```

#### 5. ClawHub (`clawhub`)

A third-party skills marketplace integrated as a community source.

- Site: [clawhub.ai](https://clawhub.ai/)
- Xavani source id: `clawhub`

#### 6. Claude marketplace-style repos (`claude-marketplace`)

Xavani supports marketplace repos that publish Claude-compatible plugin/marketplace manifests.

Known integrated sources include:
- [anthropics/skills](https://github.com/anthropics/skills)
- [aiskillstore/marketplace](https://github.com/aiskillstore/marketplace)

Xavani source id: `claude-marketplace`

#### 7. LobeHub (`lobehub`)

Xavani can search and convert agent entries from LobeHub's public catalog into installable Xavani skills.

- Site: [LobeHub](https://lobehub.com/)
- Public agents index: [chat-agents.lobehub.com](https://chat-agents.lobehub.com/)
- Backing repo: [lobehub/lobe-chat-agents](https://github.com/lobehub/lobe-chat-agents)
- Xavani source id: `lobehub`

#### 8. Direct URL (`url`)

Install a single-file `SKILL.md` directly from any HTTP(S) URL — useful when an author hosts a skill on their own site (no hub listing, no GitHub path to type). Xavani fetches the URL, parses the YAML frontmatter, security-scans it, and installs.

- Xavani source id: `url`
- Identifier: the URL itself (no prefix needed)
- Scope: **single-file `SKILL.md`** only. Multi-file skills with `references/` or `scripts/` need a manifest and should be published via one of the other sources above.

```bash
xavani skills install https://sharethis.chat/SKILL.md
xavani skills install https://example.com/my-skill/SKILL.md --category productivity
```

Name resolution, in order:
1. `name:` field in the SKILL.md YAML frontmatter (recommended — every well-formed skill has one).
2. Parent directory name from the URL path (e.g. `.../my-skill/SKILL.md` → `my-skill`, or `.../my-skill.md` → `my-skill`), when it's a valid identifier (`^[a-z][a-z0-9_-]*$`).
3. Interactive prompt on a terminal with a TTY.
4. On non-interactive surfaces (the `/skills install` slash command inside the TUI, gateway platforms, scripts), a clean error pointing at the `--name` override.

```bash
# Frontmatter has no name and the URL slug is unhelpful — supply one:
xavani skills install https://example.com/SKILL.md --name sharethis-chat

# Or inside a chat session:
/skills install https://example.com/SKILL.md --name sharethis-chat
```

Trust level is always `community` — the same security scan runs as for every other source. The URL is stored as the install identifier, so `xavani skills update` re-fetches from the same URL automatically when you want to refresh.

### Security scanning and `--force`

All hub-installed skills go through a **security scanner** that checks for data exfiltration, prompt injection, destructive commands, supply-chain signals, and other threats.

`xavani skills inspect ...` now also surfaces upstream metadata when available:
- repo URL
- skills.sh detail page URL
- install command
- weekly installs
- upstream security audit statuses
- well-known index/endpoint URLs

Use `--force` when you have reviewed a third-party skill and want to override a non-dangerous policy block:

```bash
xavani skills install skills-sh/anthropics/skills/pdf --force
```

Important behavior:
- `--force` can override policy blocks for caution/warn-style findings.
- `--force` does **not** override a `dangerous` scan verdict.
- Official optional skills (`official/...`) are treated as builtin trust and do not show the third-party warning panel.

### Trust levels

| Level | Source | Policy |
|-------|--------|--------|
| `builtin` | Ships with Xavani | Always trusted |
| `official` | `optional-skills/` in the repo | Builtin trust, no third-party warning |
| `trusted` | Trusted registries/repos such as `openai/skills`, `anthropics/skills`, `huggingface/skills` | More permissive policy than community sources |
| `community` | Everything else (`skills.sh`, well-known endpoints, custom GitHub repos, most marketplaces) | Non-dangerous findings can be overridden with `--force`; `dangerous` verdicts stay blocked |

### Update lifecycle

The hub now tracks enough provenance to re-check upstream copies of installed skills:

```bash
xavani skills check          # Report which installed hub skills changed upstream
xavani skills update         # Reinstall only the skills with updates available
xavani skills update react   # Update one specific installed hub skill
```

This uses the stored source identifier plus the current upstream bundle content hash to detect drift.

:::tip GitHub rate limits
Skills hub operations use the GitHub API, which has a rate limit of 60 requests/hour for unauthenticated users. If you see rate-limit errors during install or search, set `GITHUB_TOKEN` in your `.env` file to increase the limit to 5,000 requests/hour. The error message includes an actionable hint when this happens.
:::

### Publishing a custom skill tap

If you want to share a curated set of skills — for your team, your org, or publicly — you can publish them as a **tap**: a GitHub repository other Xavani users add with `xavani skills tap add <owner/repo>`. No server, no registry sign-up, no release pipeline. Just a directory of `SKILL.md` files.

#### Repo layout

A tap is any GitHub repo (public or private — private needs `GITHUB_TOKEN`) laid out like this:

```
owner/repo
├── skills/                       # default path; configurable per-tap
│   ├── my-workflow/
│   │   ├── SKILL.md              # required
│   │   ├── references/           # optional supporting files
│   │   ├── templates/
│   │   └── scripts/
│   ├── another-skill/
│   │   └── SKILL.md
│   └── third-skill/
│       └── SKILL.md
└── README.md                     # optional but helpful
```

Rules:
- Each skill lives in its own directory under the tap's root path (default `skills/`).
- The directory name becomes the skill's install slug.
- Each skill directory must contain a `SKILL.md` with standard [SKILL.md frontmatter](#skillmd-format) (`name`, `description`, plus optional `metadata.xavani.tags`, `version`, `author`, `platforms`, `metadata.xavani.config`).
- Subdirectories like `references/`, `templates/`, `scripts/`, `assets/` are downloaded alongside `SKILL.md` at install time.
- Skills whose directory name starts with `.` or `_` are ignored.

Xavani discovers skills by listing every subdirectory of the tap path and probing each for `SKILL.md`.

#### Minimal tap example

```
my-org/xavani-skills
└── skills/
    └── deploy-runbook/
        └── SKILL.md
```

`skills/deploy-runbook/SKILL.md`:

```markdown
---
name: deploy-runbook
description: Our deployment runbook — services, rollback, Slack channels
version: 1.0.0
author: My Org Platform Team
metadata:
  xavani:
    tags: [deployment, runbook, internal]
---

# Deploy Runbook

Step 1: ...
```

After pushing that to GitHub, any Xavani user can subscribe and install:

```bash
xavani skills tap add my-org/xavani-skills
xavani skills search deploy
xavani skills install my-org/xavani-skills/deploy-runbook
```

#### Non-default paths

If your skills don't live under `skills/` (common when you're adding a `skills/` subtree to an existing project), edit the tap entry in `~/.xavani/.hub/taps.json`:

```json
{
  "taps": [
    {"repo": "my-org/platform-docs", "path": "internal/skills/"}
  ]
}
```

The `xavani skills tap add` CLI defaults new taps to `path: "skills/"`; edit the file directly if you need a different path. `xavani skills tap list` shows the effective path per tap.

#### Installing individual skills directly (without adding a tap)

Users can also install a single skill from any public GitHub repo without adding the whole repo as a tap:

```bash
xavani skills install owner/repo/skills/my-workflow
```

Useful when you want to share one skill without asking the user to subscribe to your whole registry.

#### Trust levels for taps

New taps are assigned `community` trust by default. Skills installed from them run through the standard security scan and show the third-party warning panel on first install. If your org or a widely-trusted source should get higher trust, add its repo to `TRUSTED_REPOS` in `tools/skills_hub.py` (requires a Xavani core PR).

#### Tap management

```bash
xavani skills tap list                                # show all configured taps
xavani skills tap add myorg/skills-repo               # add (default path: skills/)
xavani skills tap remove myorg/skills-repo            # remove
```

Inside a running session:

```
/skills tap list
/skills tap add myorg/skills-repo
/skills tap remove myorg/skills-repo
```

Taps are stored in `~/.xavani/.hub/taps.json` (created on demand).

## Bundled skill updates (`xavani skills reset`)

Xavani ships with a set of bundled skills in `skills/` inside the repo. On install and on every `xavani update`, a sync pass copies those into `~/.xavani/skills/` and records a manifest at `~/.xavani/skills/.bundled_manifest` mapping each skill name to the content hash at the time it was synced (the **origin hash**).

On each sync, Xavani recomputes the hash of your local copy and compares it to the origin hash:

- **Unchanged** → safe to pull upstream changes, copy the new bundled version in, record the new origin hash.
- **Changed** → treated as **user-modified** and skipped forever, so your edits never get stomped.

The protection is good, but it has one sharp edge. If you edit a bundled skill and then later want to abandon your changes and go back to the bundled version by just copy-pasting from `~/.xavani/xavani-agent/skills/`, the manifest still holds the *old* origin hash from whenever the last successful sync ran. Your fresh copy-paste contents (current bundled hash) won't match that stale origin hash, so sync keeps flagging it as user-modified.

`xavani skills reset` is the escape hatch:

```bash
# Safe: clears the manifest entry for this skill. Your current copy is preserved,
# but the next sync re-baselines against it so future updates work normally.
xavani skills reset google-workspace

# Full restore: also deletes your local copy and re-copies the current bundled
# version. Use this when you want the pristine upstream skill back.
xavani skills reset google-workspace --restore

# Non-interactive (e.g. in scripts or TUI mode) — skip the --restore confirmation.
xavani skills reset google-workspace --restore --yes
```

The same command works in chat as a slash command:

```text
/skills reset google-workspace
/skills reset google-workspace --restore
```

:::note Profiles
Each profile has its own `.bundled_manifest` under its own `XAVANI_HOME`, so `xavani -p coder skills reset <name>` only affects that profile.
:::

### Slash commands (inside chat)

All the same commands work with `/skills`:

```text
/skills browse
/skills search react --source skills-sh
/skills search https://mintlify.com/docs --source well-known
/skills inspect skills-sh/vercel-labs/json-render/json-render-react
/skills install openai/skills/skill-creator --force
/skills check
/skills update
/skills reset google-workspace
/skills list
```

Official optional skills still use identifiers like `official/security/1password` and `official/migration/openclaw-migration`.
