> **CLOSED-EXECUTED 2026-10-24.** Evidence: `docs/CLOSURE-0.3.1.md`.

# Xavani Hermes Parity Plan

## Goal

The plan maps all Hermes parts against Xavani Agent and defines a literal copy procedure plus an edge report.

## Current Context And Assumptions

The work uses 2 repos on this machine.

Hermes totals:

- Hermes reports v0.21.0 with runtime upstream 13e72fb2 and repo HEAD 63279301bc.
- Hermes source lives at /Users/andilemushwana/.hermes/hermes-agent/.
- Hermes root holds 64 files.
- Hermes tree uses 2.2G on disk.
- Hermes tree holds 30268 Python files with venv plus cache.
- Hermes source holds 394 files at agent/.
- Hermes source holds 607 files at hermes_cli/.
- Hermes source holds 167 files at gateway/.
- Hermes source holds 290 files at tools/.
- Hermes source holds 330 files at skills/.
- Hermes source holds 718 files at optional-skills/.
- Hermes source holds 11727 files at plugins/ with node modules.
- Hermes source holds 3807 files at tests/.
- Hermes source holds 437 files at website/docs/.
- Hermes source holds 23 files at docs/.
- Hermes source holds 17 files at locales/.
- Hermes source holds 46 files at evals/.
- Hermes source holds 88 files at scripts/.
- Hermes source holds 2360 files at apps/.
- Hermes source holds 25 files at cron/ with 15 top entries.
- Hermes source holds 7 files at providers/.

Hermes facts:

- Hermes CLI core contains 22426 lines at cli.py.
- Hermes run core contains 10175 lines at run_agent.py.
- Hermes CLI module directory contains 229 top files.
- Hermes tool registry contains 1062 lines at toolsets.py.
- Hermes auth file contains 732 provider matches at hermes_cli/auth.py.
- Hermes skill root contains 13 groups at skills/.
- Hermes optional skill root contains 23 groups at optional-skills/.
- User skill home contains 48 groups at /Users/andilemushwana/.hermes/skills/.
- Hermes plugin root contains 18 plugin dirs plus 3 helper files at plugins/.
- Hermes gateway platform set contains 41 files at gateway/platforms/.
- Hermes test root contains 30 suites at tests/.
- Hermes keeps auth state at /Users/andilemushwana/.hermes/auth.json.
- Hermes keeps config at /Users/andilemushwana/.hermes/config.yaml.
- Hermes changelog uses git log with no CHANGELOG.md file.
- Hermes docs live at https://hermes-agent.nousresearch.com/docs.
- Hermes local docs live at website/docs/ plus docs/.

Xavani facts:

- Xavani reports v0.3.0.
- Xavani source lives at /Users/andilemushwana/xavani-agent/.
- Xavani CLI core contains 16161 lines at cli.py.
- Xavani CLI module directory contains 138 top files.
- Xavani repo skill root contains 27 groups at skills/.
- Xavani skill index reports 189 skills at oag_skills/MANIFEST.json.
- Xavani entry lives at xavani.py with VERSION 0.3.0.
- Xavani home uses /Users/andilemushwana/.xavani/.
- Xavani changelog contains 319 lines at CHANGELOG.md.
- Xavani changelog covers releases 0.1.2 and 0.2.0 and 0.3.0.
- Xavani derives from Hermes under MIT with attribution in LICENSE.
- Xavani AGENTS.md defines ruff gate and pytest rules.

Assumptions:

- The implementer has zero codebase context.
- The implementer runs commands on macOS with python3.
- The implementer shall preserve MIT attribution in LICENSE.
- The implementer must obtain explicit approval before code edits.
- The implementer must keep ~/.hermes/ separate from ~/.xavani/.

## Architecture And Proposed Approach

The implementer inventories all Hermes parts first and maps Xavani gaps second.
The implementer diffs Hermes source against Xavani source file by file.
The implementer copies missing Hermes parts into Xavani and records Xavani advantages in a report.

## What Hermes Is

Hermes is 16 layers.

Layers:

- Root entry layer.
- CLI command layer with 70 commands.
- Agent core layer.
- Model layer with 6 adapters.
- Tool layer.
- Skill layer with 3 sources.
- Plugin layer with 20 plugins.
- MCP layer.
- Gateway layer.
- Job layer.
- Memory layer.
- Surface layer.
- Ops layer.
- Data layer.
- Doc layer.
- Build layer.

Root entry layer with 24 Python files:

- batch_runner.py owns batch runs.
- cli.py owns CLI core with 22426 lines.
- hermes_bootstrap.py owns startup path.
- hermes_constants.py owns shared constants.
- hermes_logging.py owns log setup.
- hermes_startup_watchdog.py owns startup guard.
- hermes_state.py plus 8 state modules own persistence.
- hermes_time.py owns time helpers.
- mcp_serve.py owns MCP server mode.
- mini_swe_runner.py owns mini SWE runs.
- model_tools.py owns model tool schema.
- registration_lifecycle.py owns install lifecycle.
- run_agent.py owns agent loop with 10175 lines.
- setup.py owns package setup.
- toolset_distributions.py owns platform mapping.
- toolsets.py owns tool groups with 1062 lines.
- trajectory_compressor.py owns trajectory compaction.
- utils.py owns shared helpers.

CLI command layer with 70 commands:

- chat and model and moa and fallback.
- worktree and browser and secrets and egress and migrate.
- gateway and proxy and lsp and setup.
- whatsapp and whatsapp-cloud and slack and send.
- login and logout and auth and status.
- pause and resume and cron and sync and webhook and peer and portal.
- kanban and project and hooks and doctor and verify and security and approvals.
- dump and debug and backup and checkpoints and import and import-agent.
- config and skin and console and pairing.
- skills and bundles and plugins and curator and pets.
- journey and learning and memory-graph and memory.
- tools and computer-use and mcp and sessions and insights and monitoring.
- claw and update and uninstall and acp and profile and completion.
- dashboard and serve and desktop and gui and logs and prompt-size.

Agent core layer with 394 files:

- conversation_loop.py owns turn control.
- prompt_builder.py owns system prompt assembly.
- context_engine.py owns context selection.
- conversation_compression.py owns compaction.
- context_compressor.py owns context shrink.
- delegation_context.py owns subagent fan out.
- memory_manager.py owns memory lifecycle.
- memory_provider.py owns external provider link.
- learning_graph.py owns lesson links.
- learning_mutations.py owns lesson edits.
- curator.py owns skill maintenance.
- moa_loop.py owns mixture of agents.
- onboarding.py owns first run flow.
- i18n.py owns locale strings.
- display.py owns terminal render.
- budget_governor.py owns cost guard.
- iteration_budget.py owns step cap.
- error_classifier.py owns error tags.
- retry_utils.py owns retry backoff.

Model layer with 6 adapters:

- anthropic_adapter.py serves Anthropic models.
- azure_identity_adapter.py serves Azure identity.
- bedrock_adapter.py serves Bedrock models.
- codex_responses_adapter.py serves Codex models.
- gemini_native_adapter.py serves Gemini models.
- vertex_adapter.py serves Vertex models.
- models_dev.py owns model catalog data.
- Fallback chains own failure failover.
- Roles own default plus smol plus slow plus plan plus advisor.

Tool layer with 290 files:

- browser_tool.py owns browser control.
- browser_camofox.py owns camofox backend.
- browser_lightpanda.py owns lightpanda backend.
- browser_cdp_tool.py owns CDP control.
- computer_use_tool.py owns cua-driver control.
- code_execution_tool.py owns code runs.
- delegate_tool.py owns subagent spawn.
- clarify_tool.py owns user questions.
- cronjob_tools.py owns job control.
- checkpoint_manager.py owns restore points.
- approval.py owns approval gates.
- toolsets.py owns tool groups.
- toolset_distributions.py owns platform mapping.

Skill layer with 3 sources:

- skills/ owns 13 bundled groups with 330 files.
- Groups serve apple plus autonomous-ai-agents plus creative plus devops plus email plus media plus note-taking plus productivity plus research plus social-media plus software-development plus web plus index-cache.
- optional-skills/ owns 23 installable groups with 718 files.
- Groups serve autonomous-ai-agents plus blockchain plus communication plus creative plus data-science plus devops plus dogfood plus email plus finance plus gaming plus health plus mcp plus migration plus mlops plus payments plus productivity plus research plus security plus smart-home plus software-development plus web-development plus yuanbao.
- User home owns 48 local groups.
- Bundles own aliases for skill sets.
- Curator owns background skill repair.
- Sync owns cross device skill transfer.

Plugin layer with 18 plugin dirs and 11727 files:

- browser and context_engine and cron_providers.
- dashboard_auth and disk-cleanup and google_meet.
- hermes-achievements and image_gen and kanban.
- memory and model-providers and observability.
- platforms and security-guidance and spotify.
- teams_pipeline and video_gen and web.
- plugin_storage.py owns plugin data.
- plugin_utils.py owns plugin helpers.

MCP layer:

- mcp_serve.py owns MCP server mode.
- hermes mcp serve exposes Hermes to other agents.
- hermes mcp add connects a new server.
- hermes mcp list shows configured servers.
- hermes mcp test checks server health.
- hermes mcp catalog shows Nous approved servers.
- hermes mcp install installs 1 catalog server by name.
- optional-mcps/ owns extra MCP definitions.
- mcp-research-data/ owns MCP research files.

Gateway layer with 167 files:

- gateway/run.py owns the gateway server.
- gateway/platforms/ owns 41 files.
- Platforms serve Telegram plus Discord plus Slack plus 17 more.
- Files serve whatsapp plus whatsapp_cloud plus weixin plus qqbot plus signal plus bluebubbles plus webhook plus api_server plus yuanbao plus msgraph_webhook.
- gateway/pairing.py owns DM pairing codes.
- gateway/delivery.py owns message delivery.
- gateway/delivery_ledger.py owns delivery log.
- gateway/channel_directory.py owns channel index.
- gateway/session.py owns gateway sessions.
- gateway/security.py owns gateway guards.
- gateway/slash_access.py owns slash policy.
- gateway/memory_monitor.py owns memory watch.
- gateway/hosted_rooms.py owns hosted rooms.
- Commands serve run plus start plus stop plus restart plus status plus install plus uninstall plus list plus setup plus migrate-legacy plus enroll.

Job layer with 25 cron files:

- cron/jobs.py owns job records.
- cron/scheduler.py owns schedule ticks.
- cron/executions.py owns run history.
- cron/monitor.py owns job health.
- cron/delivery_queue.py owns outbound queue.
- hermes cron owns job create plus list plus run.
- Kanban owns multi profile task board.
- hermes project owns multi folder workspaces.
- hermes worktree owns git worktree reclaim.
- hermes webhook owns dynamic subscriptions.
- acp_adapter/ owns 12 ACP files with server plus session plus tools plus auth.

Memory layer:

- agent/memory_manager.py owns memory lifecycle.
- agent/memory_provider.py owns external provider link.
- agent/learning_graph.py owns lesson links.
- hermes journey owns skill plus memory timeline.
- hermes memory owns provider config.
- hermes sessions owns list plus rename plus export plus prune plus delete.
- hermes insights owns usage analytics.
- hermes monitoring owns health export.
- hermes checkpoints owns prune plus clear.
- hermes backup owns home zip export.
- hermes import owns backup restore.

Surface layer:

- hermes chat owns interactive CLI chat.
- hermes --tui owns terminal UI mode.
- tui_gateway/ owns TUI backend methods.
- ui-tui/ owns TUI frontend files.
- apps/desktop/ owns Electron desktop app with 2360 files.
- hermes dashboard owns web UI dashboard.
- web/ owns web server files.
- hermes serve owns headless backend server.
- hermes console owns safe command console.
- Computer use owns macOS plus Windows plus Linux control.
- Browser owns real profile browsing plus extension router.
- hermes pets owns petdex animated pets.
- hermes skin owns skin list plus switch.
- hermes portal owns Nous Portal setup.
- hermes peer owns bot to bot DMs.
- hermes send owns outbound platform messages.
- hermes proxy owns OpenAI compatible proxy.
- hermes lsp owns language server control.
- hermes acp owns Agent Client Protocol server.

Ops layer:

- hermes config owns show plus edit plus get plus set plus unset plus path plus check plus migrate.
- Secrets own Bitwarden plus 1Password sources.
- Egress owns iron proxy firewall.
- hermes security owns OSV.dev supply audit.
- hermes approvals owns allowlist proposals.
- hermes doctor owns config plus dependency checks.
- hermes verify owns recipe smoke test.
- hermes profile owns isolated instances.
- hermes update owns version upgrade.
- hermes uninstall owns full removal.
- hermes logs owns log inspection.
- hermes prompt-size owns context measurement.
- hermes status owns component status.
- hermes login owns provider login.
- hermes logout owns credential removal.
- hermes pause owns emergency stop.
- hermes resume owns stop lift.

Data layer:

- hermes_state.py plus 8 modules own SQLite persistence.
- Schema uses v30 with trigram FTS index.
- sessions DB owns turns plus tools plus files.
- checkpoints/ owns restore points.
- locales/ owns 17 YAML files for af plus ar plus de plus en plus es plus fr plus ga plus hu plus it plus ja plus ko plus pt plus ru plus tr plus uk plus zh plus zh-hant.
- evals/ owns 46 files for browser_use plus compaction plus core_tool_deferral plus readtool plus session_search_schema plus fanout_resource_bench.

Doc layer:

- website/docs/ owns 437 files.
- Groups own getting-started plus guides plus integrations plus reference plus user-guide.
- Reference owns 14 entries with 1 index file plus 13 doc files for cli-commands plus cli-symbols plus tools-reference plus toolsets-reference plus skills-catalog plus model-catalog plus mcp-config-reference.
- docs/ owns 23 files for ADR plus RFC plus security plus session lifecycle plus kanban spec.
- skills/autonomous-ai-agents/hermes-agent/references/ owns cli-reference plus troubleshooting.

Build layer:

- scripts/ owns 88 files for install plus lint plus audit plus catalog builds.
- install.sh owns macOS plus Linux setup.
- install.ps1 owns Windows setup.
- Dockerfile plus docker-compose.yml own container builds.
- nix/ owns Nix builds.
- native/ owns native helpers.
- pyproject.toml owns Python metadata.
- package.json owns Node metadata.
- cron/scripts/ owns job helper scripts.
- .github/ owns CI workflows.

## Step By Step Tasks

### Task 1: Inventory Root Entry Layer

Goal: Record 25 root Python files.

Do:

- Run ls on Hermes root Python files and record 24 files.
- Record line counts for cli.py plus run_agent.py.
- Compare root list with Xavani root list.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/*.py
wc -l /Users/andilemushwana/.hermes/hermes-agent/cli.py /Users/andilemushwana/.hermes/hermes-agent/run_agent.py
ls /Users/andilemushwana/xavani-agent/*.py | head -n 40
```

Expected output:

- ls shows 25 Python files with cli.py present.
- wc prints 22426 for cli.py and 10175 for run_agent.py.
- Xavani ls shows xavani.py plus cli.py plus run_agent.py.

Verify:

- Run ls /Users/andilemushwana/.hermes/hermes-agent/*.py | wc -l to confirm 25.
- Expected output: 25.

### Task 2: Inventory CLI Catalog

Goal: Record all 70 CLI commands.

Do:

- Run hermes --help to capture the full command list.
- Save output to /tmp/hermes-help.txt.
- Run xavani --help and compare command lists.

Exact commands:

```
hermes --help > /tmp/hermes-help.txt
cat /tmp/hermes-help.txt
hermes --version
```

Expected output:

- Help shows chat as first command.
- Help shows prompt-size as last command.
- hermes --version prints Hermes Agent v0.21.0.

Verify:

- Run wc -l /tmp/hermes-help.txt to confirm content lines above 100.
- Expected output: a count above 100.

### Task 3: Inventory Agent Core

Goal: Record 394 agent files plus 6 adapters.

Do:

- List agent/*adapter*.py and count 6 files.
- Count all agent files with find plus wc.
- Compare with Xavani agent/ directory.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/agent/*adapter*.py
find /Users/andilemushwana/.hermes/hermes-agent/agent -type f | wc -l
ls /Users/andilemushwana/xavani-agent/agent/ | head -n 40
```

Expected output:

- Adapter ls shows 6 files.
- find prints 394.
- Xavani ls shows a similar agent list.

Verify:

- Run find /Users/andilemushwana/.hermes/hermes-agent/agent -type f | wc -l to confirm 394.
- Expected output: 394.

### Task 4: Inventory Tools

Goal: Record 288 tool files plus 1062 line registry.

Do:

- List tools/ head and count full total.
- Read toolsets.py head and note 1062 lines.
- Run hermes tools list to show enabled status.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/tools/ | head -n 40
find /Users/andilemushwana/.hermes/hermes-agent/tools -type f | wc -l
wc -l /Users/andilemushwana/.hermes/hermes-agent/toolsets.py
```

Expected output:

- Head shows browser_tool.py and delegate_tool.py.
- find prints 288.
- wc prints 1062.

Verify:

- Run hermes tools list to confirm exit code 0.
- Expected output: tool table with no error.

### Task 5: Inventory Skills All Sources

Goal: Record 13 plus 23 plus 48 skill groups.

Do:

- Run ls on Hermes skills/ for 13 groups.
- Run ls on optional-skills/ for 23 groups.
- Run ls on user home for 48 groups.
- Run ls on Xavani skills/ for 27 groups.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/skills/
ls /Users/andilemushwana/.hermes/hermes-agent/optional-skills/
ls /Users/andilemushwana/.hermes/skills/ | wc -l
ls /Users/andilemushwana/xavani-agent/skills/ | wc -l
```

Expected output:

- First ls prints 13 names.
- Second ls prints 23 names.
- Third wc prints 48.
- Fourth wc prints 27.

Verify:

- Run python3 index read on oag_skills/MANIFEST.json to confirm 189.
- Expected output: 189.

### Task 6: Inventory Plugins Plus MCP

Goal: Record 20 plugins plus 14 MCP actions.

Do:

- List plugins/ and record 20 names.
- Run hermes mcp --help to list 14 actions.
- Run hermes mcp list to show configured servers.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/plugins/
hermes mcp --help
hermes mcp list
```

Expected output:

- First ls shows kanban and memory and spotify.
- Help shows serve plus add plus list plus catalog plus install.
- List prints 0 or more servers with no error.

Verify:

- Run ls /Users/andilemushwana/.hermes/hermes-agent/plugins/ | wc -l to confirm 20 plus 2 helper files.
- Expected output: a count above 20.

### Task 7: Inventory Gateway

Goal: Record 167 gateway files plus 41 platform files.

Do:

- List gateway/*.py head for core files.
- List gateway/platforms/ for platform files.
- Run hermes gateway --help to list 11 actions.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/gateway/*.py | head -n 30
ls /Users/andilemushwana/.hermes/hermes-agent/gateway/platforms/
hermes gateway --help
```

Expected output:

- Head shows run.py and pairing.py and delivery.py.
- Platforms ls shows whatsapp plus signal plus yuanbao.
- Help shows run plus start plus stop plus status.

Verify:

- Run find gateway -type f | wc -l to confirm 167.
- Expected output: 167.

### Task 8: Inventory Jobs Plus Memory Plus Surfaces

Goal: Record cron plus ACP plus sessions plus UI.

Do:

- List cron/ and count 25 files.
- List acp_adapter/ and count 12 files.
- List tui_gateway/ head for methods.
- List apps/desktop/ head for Electron app.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/cron/
ls /Users/andilemushwana/.hermes/hermes-agent/acp_adapter/
ls /Users/andilemushwana/.hermes/hermes-agent/tui_gateway/ | head -n 30
ls /Users/andilemushwana/.hermes/hermes-agent/apps/desktop/ | head -n 20
```

Expected output:

- cron ls shows jobs.py and scheduler.py.
- acp ls shows server.py and session.py.
- tui ls shows methods files.
- desktop ls shows electron plus src.

Verify:

- Run find cron -type f | wc -l to confirm 25.
- Expected output: 25.

### Task 9: Inventory Data Plus Docs Plus Build

Goal: Record state plus locales plus evals plus docs plus scripts.

Do:

- List hermes_state*.py and count 9 files.
- List locales/ and count 17 YAML files.
- List evals/ and count 46 files.
- List website/docs/reference/ for 13 reference files.

Exact commands:

```
ls /Users/andilemushwana/.hermes/hermes-agent/hermes_state*.py
ls /Users/andilemushwana/.hermes/hermes-agent/locales/
find /Users/andilemushwana/.hermes/hermes-agent/evals -type f | wc -l
ls /Users/andilemushwana/.hermes/hermes-agent/website/docs/reference/
```

Expected output:

- State ls shows 9 files.
- Locales ls shows 17 YAML files.
- Evals find prints 46.
- Reference ls shows 13 files.

Verify:

- Run ls locales/ | wc -l to confirm 17.
- Expected output: 17.

### Task 10: Inventory Ops Commands

Goal: Record config plus security plus maintenance commands.

Do:

- Run hermes config --help to list 8 actions.
- Run hermes doctor to check dependencies.
- Run hermes status to show component health.
- Run hermes tools list to show tool health.

Exact commands:

```
hermes config --help
hermes config show
hermes doctor
hermes status
```

Expected output:

- Help shows show plus get plus set plus check plus migrate.
- Show prints config keys with no error.
- Doctor prints pass marks.
- Status prints component rows.

Verify:

- Run hermes config check to confirm exit code 0.
- Expected output: no missing keys or a short missing list.

### Task 11: Capture Both Changelogs

Goal: Capture Hermes git log plus Xavani CHANGELOG.md.

Do:

- Run git log in Hermes source for 50 commits.
- Save top 5 lines to /tmp/hermes-log.txt.
- Read Xavani CHANGELOG.md lines 1 through 120.

Exact commands:

```
git -C /Users/andilemushwana/.hermes/hermes-agent log --oneline -50
git -C /Users/andilemushwana/.hermes/hermes-agent log --oneline -5 > /tmp/hermes-log.txt
head -n 120 /Users/andilemushwana/xavani-agent/CHANGELOG.md
```

Expected output:

- Log shows 63279301bc as first line.
- File holds 5 lines.
- Head shows 0.3.0 Everyday Carry section.

Verify:

- Run wc -l /tmp/hermes-log.txt to confirm 5.
- Expected output: 5.
- Run wc -l CHANGELOG.md to confirm 319.
- Expected output: 319.

### Task 12: Diff Every Layer

Goal: Produce drift lists for 16 layers.

Do:

- Run diff -rq for hermes_cli versus xavani_cli.
- Run diff -rq for agent versus agent.
- Run diff -rq for gateway versus gateway.
- Run diff -rq for tools versus tools.
- Run diff -rq for skills versus skills.
- Run diff -rq for plugins versus plugins.
- Run diff -rq for cron versus cron.
- Save full output to /tmp/drift.txt.

Exact commands:

```
diff -rq /Users/andilemushwana/.hermes/hermes-agent/hermes_cli /Users/andilemushwana/xavani-agent/xavani_cli | head -n 100
diff --brief /Users/andilemushwana/.hermes/hermes-agent/cli.py /Users/andilemushwana/xavani-agent/cli.py
diff --brief /Users/andilemushwana/.hermes/hermes-agent/gateway/run.py /Users/andilemushwana/xavani-agent/gateway/run.py
diff -rq /Users/andilemushwana/.hermes/hermes-agent/hermes_cli /Users/andilemushwana/xavani-agent/xavani_cli > /tmp/drift.txt; wc -l /tmp/drift.txt
```

Expected output:

- diff prints Only in lines for brand files.
- diff brief reports files differ for cli.py.
- wc prints a count above 50.

Verify:

- Run cat /tmp/drift.txt | head -n 20 to confirm file names.
- Expected output: 20 drift lines.

### Task 13: Copy Hermes Into Xavani Literally

Goal: Bring Xavani to full Hermes parity with exact copies.

Constraints:

- The implementer shall keep MIT attribution in LICENSE.
- The implementer must not overwrite 6 brand paths.
- The implementer must keep home separation.

Do not overwrite these 6 paths:

- /Users/andilemushwana/xavani-agent/xavani.py
- /Users/andilemushwana/xavani-agent/xavani_cli/skins/xavani-darkblue.yaml
- /Users/andilemushwana/xavani-agent/xavani_cli/oag_commands.py
- /Users/andilemushwana/xavani-agent/xavani_cli/research_guidelines.py
- /Users/andilemushwana/xavani-agent/skills/research-guidelines/
- /Users/andilemushwana/xavani-agent/assets/buffalo-logo.txt

Do:

- Copy each missing CLI module with cp -p.
- Copy each missing agent module with cp -p.
- Copy each missing gateway adapter with cp -p.
- Copy each missing tool module with cp -p.
- Copy each missing skill directory with cp -Rp.
- Copy each missing plugin directory with cp -Rp.
- Copy each missing cron file with cp -p.
- Copy each missing locale file with cp -p.
- Copy each missing eval file with cp -p.
- Copy each missing doc file with cp -p.
- Rename HERMES_HOME references to XAVANI_HOME in brand glue only.
- Run ruff check on each copied file.
- Run targeted pytest on each copied area.

Exact commands for 1 file example:

```
cp -p /Users/andilemushwana/.hermes/hermes-agent/hermes_cli/cron.py /Users/andilemushwana/xavani-agent/xavani_cli/cron.py
python3 -m ruff check /Users/andilemushwana/xavani-agent/xavani_cli/cron.py
python3 -m pytest /Users/andilemushwana/xavani-agent/tests/xavani_cli/ -q
```

Expected output:

- cp prints no output on success.
- ruff prints All checks passed.
- pytest prints a pass summary with 0 failures.

Verify:

- Run diff --brief source target to confirm 0 differences except brand glue.
- Expected output: no output means identical files.
- Run grep -rni hermes plus nous on each new file to catch CamelCase leftovers.
- Expected output: no output means zero brand hits.
- Full brand token list: hermes_cli, hermes_constants, HERMES_HOME, HERMES_, hermes-acp, hermes-agent, hermes-gateway, get_default_hermes_root, get_hermes_home, .hermes, HermesCLI, bare hermes in code paths and user strings.

Copy order for all Hermes inches:

- Root files first with 25 files.
- CLI commands second with 70 commands.
- Agent core third with 394 files.
- Model layer fourth with 6 adapters.
- Tool layer fifth with 290 files.
- Skill layer sixth with 13 plus 23 plus 48 groups.
- Plugin layer seventh with 18 plugin dirs.
- MCP layer eighth with serve plus catalog.
- Deliberate skip: hermes_cli/diagnostics_upload.py stays unported because it uploads bundles to Nous-internal S3 and Xavani ships zero phone-home paths.
- Deliberate skip: hermes_cli/gateway_enroll.py stays unported because it enrolls gateways with the Nous relay connector and Xavani ships no relay backend.
- Deferred: hermes_cli/config_migrations.py waits for Xavani config schema convergence (Xavani _config_version 23 versus Hermes migration floor 40, plus missing _persist_migration and fast_safe_load helpers).
- Deferred: hermes_cli/gui_uninstall.py waits for xavani-desktop path mapping (Electron app names plus userdata dirs plus NSIS entries differ per product).
- Deferred: hermes_cli/container_boot.py waits for service_manager track (1137 lines, S6 supervisor) plus gateway lifecycle_ledger gap.
- Deferred: session_recovery track (session_lost_and_found plus session_recovery plus sessions_cmd) waits for xavani_state_common port (1391 lines) plus repair helpers (_db_opens_cleanly, repair_state_db_schema, FTS_STORAGE_VERSION chain) plus agent gaps (skill_commands names, context_compressor _MERGED markers).
- Adapted, not deferred: dashboard_auth registry gains local _xavani_home_key() because hermes_constants.hermes_home_key has no Xavani equivalent.
- Adapted, not deferred: console_engine _sessions_repair guards its repair import (try/except ImportError to ConsoleCommandError) until the repair track lands; _cron_resume rearm path ports rearm_oneshot into cron/jobs adapted to _jobs_file_lock plus _xavani_now with claim checks dropped (no claim subsystem in Xavani); xavani_state gains MAX_SAFE consts plus _configured_transcript_limit plus both resolvers plus SessionExportTooLargeError.
- Deferred: hermes_cli/cli_commands_mixin.py waits for browser_connect helpers (discover_local_cdp_url, find_free_debug_port, is_browser_debug_ready, local_port_in_use) plus journey.register_cli plus agent/turn_context epic.
- Deferred: hermes_cli/cli_billing_mixin.py waits for Nous-billing track (agent/billing_usage, agent/subscription_view, hermes_cli/nous_billing).
- Deferred: hermes_cli/pets.py plus agent/pet/ waits for pet store track (3698 lines across 10 files, store plus generate pipeline).
- Deliberate skip: hermes_cli/portal_cli.py stays unported because it onboards Nous Portal OAuth and Xavani ships no Nous backend.
- Deliberate skip: hermes_cli/telegram_managed_bot.py stays unported because it talks to the Nous-hosted Telegram onboarding service (setup.hermes-agent.nousresearch.com plus HermesSetupBot) and Xavani ships no equivalent backend.
- Gateway layer ninth with 167 files.
- Job layer tenth with 25 cron files plus 12 ACP files.
- Memory layer eleventh with manager plus graph plus sessions.
- Surface layer twelfth with TUI plus desktop plus dashboard.
- Ops layer thirteenth with config plus security.
- Data layer fourteenth with 9 state files plus 17 locales plus 46 evals.
- Doc layer fifteenth with 437 plus 23 files.
- Build layer sixteenth with 88 scripts plus installers.

### Task 14: Record Xavani Edge Over Hermes

Goal: Write an edge report with 10 items and evidence.

Do:

- Test research guidelines loader with pytest.
- Open MANIFEST.md and count 11 thinkers.
- Test todo store at ~/.xavani/todos.json with 1 create plus 1 read.
- Test outstanding ledger at ~/.xavani/outstanding.jsonl.
- Confirm no telemetry with grep for XAVANI_DISABLE_TELEMETRY.
- Confirm skins with ls xavani_cli/skins/.

Exact commands:

```
python3 -m pytest /Users/andilemushwana/xavani-agent/tests/xavani_cli/test_research_guidelines.py -q
ls /Users/andilemushwana/xavani-agent/skills/research-guidelines/
grep -n "XAVANI_DISABLE_TELEMETRY" /Users/andilemushwana/xavani-agent/xavani.py
ls /Users/andilemushwana/xavani-agent/xavani_cli/skins/
```

Expected output:

- pytest prints pass summary.
- ls prints 11 guideline files plus MANIFEST.md.
- grep prints 1 or more matches.
- skins ls prints xavani-darkblue.yaml plus 2 new skins.

Edge list to confirm:

- Mandatory research pack with 11 thinkers.
- Dark blue buffalo skin plus skin engine.
- OAG commands for install plus gateway.
- Approval gate with journal plus /revert.
- Loop engine with /loop plus guards.
- Eval harness with 21 tasks.
- Todo store plus outstanding ledger.
- Document tool for pptx plus xlsx plus docx.
- Zero telemetry with local home.
- oh-my-pi ports with advisor plus hub.

Verify:

- Write results to /tmp/xavani-edge.txt with 10 lines.
- Run wc -l /tmp/xavani-edge.txt to confirm 10.
- Expected output: 10.

## Tests And Validation

The implementer follows TDD for each code copy task.

Cycle:

- Write 1 failing test for the copied module first.
- Run python3 -m pytest path -q to verify 1 failure.
- Copy the Hermes file with cp -p with minimal brand edits.
- Run python3 -m pytest path -q to verify a pass.
- Run python3 -m ruff check files to verify clean lint.
- Commit with explicit paths only.

Exact commands:

```
python3 -m pytest /Users/andilemushwana/xavani-agent/tests/xavani_cli/test_research_guidelines.py -q
python3 -m ruff check /Users/andilemushwana/xavani-agent/xavani_cli/cron.py
git -C /Users/andilemushwana/xavani-agent status --short
git -C /Users/andilemushwana/xavani-agent add /Users/andilemushwana/xavani-agent/xavani_cli/cron.py
git -C /Users/andilemushwana/xavani-agent commit -m "feat: port cron module from Hermes"
```

Expected output:

- pytest prints pass count with 0 failures.
- ruff prints All checks passed.
- git status prints only staged paths from this task.
- git commit prints 1 new commit hash.

Rules:

- The implementer uses python3 -m pytest path -q and never bare pytest.
- The implementer stages explicit paths and never runs git add -A.
- The implementer uses feat plus fix plus test plus docs prefixes.
- The implementer never edits oag_skills/MANIFEST.json by hand.
- The implementer never edits uv.lock by hand.

Validation for all Hermes inches:

- Run hermes doctor after each layer copy to confirm health.
- Run hermes config check after config copies to confirm keys.
- Run hermes tools list after tool copies to confirm tools.
- Run hermes mcp list after MCP copies to confirm servers.
- Run hermes gateway status after gateway copies to confirm status.
- Run pytest for agent plus cli plus gateway plus skills plus state.

## Risks Tradeoffs And Open Questions

Risks:

- Full copy creates merge debt when Hermes ships new commits daily.
- Brand glue breaks when HERMES_HOME paths persist in copied code.
- Skill count drifts when Hermes adds skills without index updates.
- Prompt cache breaks when core edits alter system prompt bytes.
- Auth separation fails when 1 token poller serves 2 homes.
- Windows paths break when POSIX-only calls replace psutil calls.
- Desktop drift grows when Electron app moves faster than Xavani web UI.
- Gateway regressions occur when 30 platform files change at once.
- Plugin load grows when 11727 plugin files copy at once.
- Test time grows when 3807 test files run at once.

Tradeoffs:

- Literal copy gives fast parity but keeps 2 god files above 16000 lines.
- Narrow core keeps cost low but slows new tool additions.
- Local home keeps privacy high but blocks cross device sync.
- Mandatory guidelines raise quality but raise token use per turn.
- Full platform parity raises reach but raises test load for 20 adapters.
- Full desktop parity raises surface match but raises Node build load.

Open questions:

- If Hermes ships v0.22.0 during the copy, do you rebase or freeze at 63279301.
- If skill names collide across 48 plus 27 groups, which name wins.
- If gateway platform count exceeds 20 adapters, do you port all adapters or 5 core adapters first.
- If Xavani edge files conflict with Hermes files, do brand files win in all 6 paths.
- If tests need SYSTEM python3 versus repo .venv, which interpreter runs each suite.
- If desktop source moves faster than CLI source, do you freeze desktop at v0.21.0 or track main.
- If MCP catalog adds new servers weekly, do you auto sync catalog or pin catalog monthly.
- If plugins hold node modules, do you copy source only or full 11727 files.
- If root holds 2.2G with venv, do you copy source only or full tree.
