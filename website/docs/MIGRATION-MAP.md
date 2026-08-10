# Docs IA Migration Map (Task 19)

**Status: review artifact + sidebar skeleton only. NO files were moved in this task.**
All page URLs are unchanged. This map records where every existing page lands in the new
flat IA so the follow-up file-move task can execute mechanically.

**Target model** (from plan): omp flat task-pages (`/docs/quickstart`, `/docs/using`,
`/docs/settings`, …) + pi.dev nav model (Start here / Customization / Reference /
Programmatic usage / Platform setup / Development).

**New sidebar shape** (`website/sidebars.ts`): 7 top-level categories, all collapsed,
max 2 levels deep (previously up to 7 levels, 1,544 lines → now ~110 lines).
The 300+ skill pages under `user-guide/skills/**` collapse to ONE entry:
`reference/skills-catalog` (generated catalog). `reference/optional-skills-catalog`
keeps its URL and remains reachable from the catalog.

---

## 1. New skeleton → mapped pages

| New nav slot | Mapped existing page (id) | Notes |
|---|---|---|
| **Start here / quickstart** | `getting-started/quickstart` | |
| **Start here / installation** | `getting-started/installation` | install.sh covers macOS + Linux |
| **Start here / using** | `user-guide/cli` | CLI Interface page = "using the agent"; no `using` page exists |
| **Start here / providers** | `integrations/providers` | |
| **Start here / security** | `user-guide/security` | |
| **Start here / settings** | `user-guide/configuration` | |
| **Start here / keybindings** | `user-guide/tui` | TUI page documents keybindings/shortcuts |
| **Start here / sessions** | `user-guide/sessions` | |
| **Start here / compaction** | `developer-guide/context-compression-and-caching` | closest existing page |
| **Features / memory** | `user-guide/features/memory` | |
| **Features / plan-mode** | — | **DROPPED** — no page exists (closest: `user-guide/features/goals`) |
| **Features / editing** | — | **DROPPED** — no page exists (closest: `user-guide/checkpoints-and-rollback`, `user-guide/features/code-execution`) |
| **Features / subagents** | `user-guide/features/delegation` | delegation = subagents |
| **Features / skills** | `user-guide/features/skills` | |
| **Features / hooks** | `user-guide/features/hooks` | |
| **Features / custom-tools** | `user-guide/features/tools` | writing your own → `developer-guide/adding-tools` |
| **Features / mcp** | `user-guide/features/mcp` | |
| **Features / cron** | `user-guide/features/cron` | |
| **Features / skins** | `user-guide/features/skins` | |
| **Features / voice** | `user-guide/features/voice-mode` | |
| **Features / computer-use** | `user-guide/features/computer-use` | |
| **Customization / extensions** | `user-guide/features/plugins` | plugins = extensions |
| **Customization / prompt templates** | `user-guide/features/personality` | no templates page; personality = closest (internals: `developer-guide/prompt-assembly`) |
| **Customization / custom models** | `user-guide/configuring-models` | |
| **Customization / custom providers** | `developer-guide/adding-providers` | provider how-tos: `guides/aws-bedrock`, `azure-foundry`, `google-gemini`, `local-ollama-setup`, `minimax-oauth`, `xai-grok-oauth` |
| **Reference / tools** | `reference/tools-reference` | slot is a placeholder for an auto-generated tools category; maps to the built-in tools reference today |
| **Reference / slash-commands** | `reference/slash-commands` | |
| **Reference / cli** | `reference/cli-commands` | |
| **Reference / env-vars** | `reference/environment-variables` | |
| **Reference / toolsets** | `reference/toolsets-reference` | |
| **Reference / faq** | `reference/faq` | |
| **Programmatic / sdk** | `guides/python-library` | Python library = SDK usage |
| **Programmatic / gateway-rpc** | `user-guide/features/api-server` | OpenAI-compatible HTTP API; server internals → `developer-guide/gateway-internals` |
| **Programmatic / json-event-stream** | `developer-guide/programmatic-integration` | covers ACP + TUI gateway JSON-RPC + HTTP API |
| **Platform / macos** | `getting-started/installation` | no dedicated macOS page; installer covers it |
| **Platform / linux** | `getting-started/nix-setup` | Nix & NixOS setup = closest Linux-specific page |
| **Platform / windows** | `user-guide/windows-native` | WSL guide: `user-guide/windows-wsl-quickstart` |
| **Platform / termux** | `getting-started/termux` | |
| **Platform / docker** | `user-guide/docker` | |
| **Platform / tmux** | — | **DROPPED** — no dedicated page (TUI runs inside tmux; see `user-guide/tui`) |
| **Developer / architecture** | `developer-guide/architecture` | |
| **Developer / agent-loop** | `developer-guide/agent-loop` | |
| **Developer / adding-tools** | `developer-guide/adding-tools` | |
| **Developer / adding-providers** | `developer-guide/adding-providers` | |
| **Developer / contributing** | `developer-guide/contributing` | |
| **Skills catalog (single entry)** | `reference/skills-catalog` | replaces all per-skill nesting under Features → Skills → Bundled/Optional → category → skill |

---

## 2. Every current page → new slot

### `docs/getting-started/` (6)
| Current path | New slot |
|---|---|
| `getting-started/quickstart` | Start here / quickstart |
| `getting-started/installation` | Start here / installation (+ Platform / macos) |
| `getting-started/termux` | Platform / termux |
| `getting-started/nix-setup` | Platform / linux |
| `getting-started/updating` | not in skeleton (keep URL) |
| `getting-started/learning-path` | not in skeleton (keep URL) |

### `docs/user-guide/` top level (13)
| Current path | New slot |
|---|---|
| `user-guide/cli` | Start here / using |
| `user-guide/tui` | Start here / keybindings |
| `user-guide/windows-native` | Platform / windows |
| `user-guide/windows-wsl-quickstart` | not in skeleton (keep URL) |
| `user-guide/configuration` | Start here / settings |
| `user-guide/configuring-models` | Customization / custom models |
| `user-guide/sessions` | Start here / sessions |
| `user-guide/profiles` | not in skeleton (keep URL) |
| `user-guide/profile-distributions` | not in skeleton (keep URL) |
| `user-guide/git-worktrees` | not in skeleton (keep URL) |
| `user-guide/docker` | Platform / docker |
| `user-guide/security` | Start here / security |
| `user-guide/checkpoints-and-rollback` | not in skeleton (keep URL) |

### `docs/user-guide/features/` (45)
| Current path | New slot |
|---|---|
| `user-guide/features/memory` | Features / memory |
| `user-guide/features/delegation` | Features / subagents |
| `user-guide/features/skills` | Features / skills |
| `user-guide/features/hooks` | Features / hooks |
| `user-guide/features/tools` | Features / custom-tools |
| `user-guide/features/mcp` | Features / mcp |
| `user-guide/features/cron` | Features / cron |
| `user-guide/features/skins` | Features / skins |
| `user-guide/features/voice-mode` | Features / voice |
| `user-guide/features/computer-use` | Features / computer-use |
| `user-guide/features/plugins` | Customization / extensions |
| `user-guide/features/personality` | Customization / prompt templates |
| `user-guide/features/api-server` | Programmatic / gateway-rpc |
| `user-guide/features/overview`, `v040-capabilities`, `tool-gateway`, `lsp`, `curator`, `memory-providers`, `context-files`, `context-references`, `built-in-plugins`, `kanban`, `kanban-tutorial`, `kanban-worker-lanes`, `codex-app-server-runtime`, `goals`, `code-execution`, `batch-processing`, `web-search`, `x-search`, `browser`, `vision`, `image-generation`, `tts`, `deliverable-mode`, `web-dashboard`, `extending-the-dashboard`, `subscription-proxy`, `spotify`, `acp`, `credential-pools`, `fallback-providers`, `provider-routing`, `honcho` | not in skeleton (keep URL) |

### `docs/user-guide/messaging/` (28 incl. index)
All messaging pages (`bluebubbles`, `dingtalk`, `discord`, `email`, `feishu`,
`google_chat`, `homeassistant`, `line`, `matrix`, `mattermost`, `msgraph-webhook`,
`open-webui`, `qqbot`, `signal`, `simplex`, `slack`, `sms`, `teams-meetings`, `teams`,
`telegram`, `webhooks`, `wecom`, `wecom-callback`, `weixin`, `whatsapp`, `yuanbao`,
`index`) → **not in skeleton (keep URL)**. Follow-up task: re-add as a flat
"Integrations / Messaging" category (they are already flat under `messaging/`).

### `docs/developer-guide/` (26)
| Current path | New slot |
|---|---|
| `developer-guide/architecture` | Developer / architecture |
| `developer-guide/agent-loop` | Developer / agent-loop |
| `developer-guide/adding-tools` | Developer / adding-tools (+ Features / custom-tools pointer) |
| `developer-guide/adding-providers` | Developer / adding-providers (+ Customization / custom providers) |
| `developer-guide/contributing` | Developer / contributing |
| `developer-guide/context-compression-and-caching` | Start here / compaction |
| `developer-guide/programmatic-integration` | Programmatic / json-event-stream |
| `acp-internals`, `adding-platform-adapters`, `browser-supervisor`, `context-engine-plugin`, `creating-skills`, `cron-internals`, `extending-the-cli`, `gateway-internals`, `image-gen-provider-plugin`, `memory-provider-plugin`, `model-provider-plugin`, `plugin-llm-access`, `prompt-assembly`, `provider-runtime`, `session-storage`, `tools-runtime`, `trajectory-format`, `video-gen-provider-plugin`, `web-search-provider-plugin` | not in skeleton (keep URL) |

### `docs/guides/` (28)
`automate-with-cron`, `automation-templates`, `aws-bedrock`, `azure-foundry`,
`build-a-xavani-plugin`, `cron-script-only`, `cron-troubleshooting`,
`daily-briefing-bot`, `delegation-patterns`, `github-pr-review-agent`,
`google-gemini`, `local-llm-on-mac`, `local-ollama-setup`,
`microsoft-graph-app-registration`, `migrate-from-openclaw`, `minimax-oauth`,
`oauth-over-ssh`, `operate-teams-meeting-pipeline`, `pipe-script-output`,
`team-telegram-assistant`, `tips`, `use-mcp-with-xavani`, `use-soul-with-xavani`,
`use-voice-mode-with-xavani`, `webhook-github-pr-review`, `work-with-skills`,
`xai-grok-oauth` → **not in skeleton (keep URL)**. `guides/python-library` →
Programmatic / sdk. Follow-up task: re-add as a flat "Guides" category.

### `docs/reference/` (11)
| Current path | New slot |
|---|---|
| `reference/tools-reference` | Reference / tools |
| `reference/slash-commands` | Reference / slash-commands |
| `reference/cli-commands` | Reference / cli |
| `reference/environment-variables` | Reference / env-vars |
| `reference/toolsets-reference` | Reference / toolsets |
| `reference/faq` | Reference / faq |
| `reference/skills-catalog` | Skills catalog (single top-level entry) |
| `reference/optional-skills-catalog`, `reference/mcp-config-reference`, `reference/model-catalog`, `reference/profile-commands` | not in skeleton (keep URL) |

### `docs/integrations/` (2)
| Current path | New slot |
|---|---|
| `integrations/providers` | Start here / providers |
| `integrations/index` | not in skeleton (keep URL) |

### Misc
- `docs/index.md` (docs landing) and `docs/user-stories.mdx` (`user-stories` is the
  first item in the sidebar, unchanged).

---

## 3. Explicitly dropped slots (spec slots with no page and no good mapping)

- **Features / plan-mode** → no page (closest: `user-guide/features/goals`)
- **Features / editing** → no page (closest: `user-guide/checkpoints-and-rollback`)
- **Platform / tmux** → no page (TUI runs in tmux; see `user-guide/tui`)

## 4. Build status

- `npm run build` result: **PASSED** (see task report).
- No unresolved sidebar links: every id in `sidebars.ts` resolves to an existing page.

## 5. Follow-up work (not this task)

1. Physically move files + fix frontmatter ids + add redirects (multi-hour job).
2. Re-add guides/messaging/extra feature+reference pages as additional flat
   top-level categories once files settle.
3. Generate the auto-generated **tools** category behind Reference / tools.
