# Environment Variables Reference

This file is AUTO-GENERATED. Do not edit by hand.
Regenerate with: `python3 scripts/generate_env_docs.py`

Scanned: 753 environment variables.

## `AGENT_BROWSER_ENGINE`

**Used at:**
- `tools/browser_tool.py:680`

## `AGENT_BROWSER_EXECUTABLE_PATH`

**Purpose:** 1. AGENT_BROWSER_EXECUTABLE_PATH — explicit user-configured browser

**Used at:**
- `tools/browser_tool.py:3555`

## `AI_GATEWAY_API_KEY`

**Used at:**
- `xavani_cli/main.py:2615`
- `xavani_cli/models.py:3149`

## `AI_GATEWAY_BASE_URL`

**Used at:**
- `xavani_cli/models.py:3152`

## `ALL_PROXY`

**Used at:**
- `gateway/platforms/qqbot/adapter.py:471`
- `tests/agent/test_proxy_and_url_validation.py:43`

## `ALPHA_VANTAGE_KEY`

**Purpose:** Optionally enrich with Alpha Vantage

**Used at:**
- `oag_skills/finance/stocks/scripts/stocks_client.py:252`
- `oag_skills/finance/stocks/scripts/stocks_client.py:386`
- `optional-skills/finance/stocks/scripts/stocks_client.py:252`
- `optional-skills/finance/stocks/scripts/stocks_client.py:386`

## `ANTHROPIC_API_KEY`

**Purpose:** This remains as a compatibility fallback for pre-migration Xavani configs.

**Used at:**
- `agent/anthropic_adapter.py:1136`
- `mini_swe_runner.py:222`
- `oag_skills/red-teaming/godmode/scripts/auto_jailbreak.py:349`
- `skills/red-teaming/godmode/scripts/auto_jailbreak.py:349`
- `tests/tools/test_code_execution_modes.py:405`
- `tests/tools/test_code_execution_modes.py:423`
- `tests/xavani_cli/test_env_loader.py:56`
- `tests/xavani_cli/test_non_ascii_credential.py:136`
- ... and 2 more

## `ANTHROPIC_TOKEN`

**Purpose:** 1. Xavani-managed OAuth/setup token env var

**Used at:**
- `agent/anthropic_adapter.py:1114`
- `xavani_cli/config.py:3668`
- `xavani_cli/web_server.py:1505`

## `API_BASE_URL`

**Defaults:** https://api.example.com

**Used at:**
- `oag_skills/mcp/fastmcp/templates/api_wrapper.py:16`
- `optional-skills/mcp/fastmcp/templates/api_wrapper.py:16`

## `API_SERVER_CORS_ORIGINS`

**Used at:**
- `gateway/config.py:1527`
- `gateway/platforms/api_server.py:658`

## `API_SERVER_ENABLED`

**Purpose:** API Server

**Used at:**
- `gateway/config.py:1525`

## `API_SERVER_HOST`

**Used at:**
- `gateway/config.py:1529`
- `gateway/platforms/api_server.py:651`

## `API_SERVER_KEY`

**Used at:**
- `gateway/config.py:1526`
- `gateway/platforms/api_server.py:656`

## `API_SERVER_MODEL_NAME`

**Used at:**
- `gateway/config.py:1547`
- `gateway/platforms/api_server.py:661`

## `API_SERVER_PORT`

**Used at:**
- `gateway/config.py:1528`
- `gateway/platforms/api_server.py:654`

## `API_TIMEOUT_SECONDS`

**Defaults:** 20

**Used at:**
- `oag_skills/mcp/fastmcp/templates/api_wrapper.py:18`
- `optional-skills/mcp/fastmcp/templates/api_wrapper.py:18`

## `API_TOKEN`

**Used at:**
- `oag_skills/mcp/fastmcp/templates/api_wrapper.py:17`
- `optional-skills/mcp/fastmcp/templates/api_wrapper.py:17`

## `APPDATA`

**Used at:**
- `xavani_cli/gateway_windows.py:175`

## `APPTAINER_CACHEDIR`

**Used at:**
- `tools/environments/singularity.py:102`

## `AUXILIARY_VIDEO_MODEL`

**Used at:**
- `tools/vision_tools.py:1419`

## `AUXILIARY_VISION_API_KEY`

**Used at:**
- `tests/agent/test_auxiliary_config_bridge.py:126`

## `AUXILIARY_VISION_BASE_URL`

**Used at:**
- `tests/agent/test_auxiliary_config_bridge.py:125`

## `AUXILIARY_VISION_MODEL`

**Used at:**
- `tests/agent/test_auxiliary_config_bridge.py:100`
- `tests/agent/test_auxiliary_config_bridge.py:127`
- `tests/agent/test_auxiliary_config_bridge.py:137`
- `tests/agent/test_auxiliary_config_bridge.py:164`
- `tests/agent/test_auxiliary_config_bridge.py:177`
- `tests/agent/test_auxiliary_config_bridge.py:189`
- `tools/browser_tool.py:237`
- `tools/vision_tools.py:1056`
- ... and 1 more

## `AUXILIARY_VISION_PROVIDER`

**Purpose:** auto provider should not be set

**Used at:**
- `tests/agent/test_auxiliary_config_bridge.py:89`
- `tests/agent/test_auxiliary_config_bridge.py:102`
- `tests/agent/test_auxiliary_config_bridge.py:136`
- `tests/agent/test_auxiliary_config_bridge.py:143`
- `tests/agent/test_auxiliary_config_bridge.py:153`
- `tests/agent/test_auxiliary_config_bridge.py:163`
- `tests/agent/test_auxiliary_config_bridge.py:176`
- `tests/agent/test_auxiliary_config_bridge.py:188`
- ... and 1 more

## `AUXILIARY_WEB_EXTRACT_MODEL`

**Used at:**
- `tests/agent/test_auxiliary_config_bridge.py:112`
- `tests/agent/test_auxiliary_config_bridge.py:166`
- `tests/agent/test_auxiliary_config_bridge.py:179`
- `tools/browser_tool.py:242`
- `tools/web_tools.py:302`

## `AUXILIARY_WEB_EXTRACT_PROVIDER`

**Purpose:** auto should not be set

**Used at:**
- `tests/agent/test_auxiliary_config_bridge.py:91`
- `tests/agent/test_auxiliary_config_bridge.py:111`
- `tests/agent/test_auxiliary_config_bridge.py:165`
- `tests/agent/test_auxiliary_config_bridge.py:178`
- `tests/agent/test_auxiliary_config_bridge.py:195`

## `AWS_ACCESS_KEY_ID`

**Used at:**
- `xavani_cli/model_switch.py:1094`

## `AWS_BEARER_TOKEN_BEDROCK`

**Purpose:** Prompt for API key

**Used at:**
- `xavani_cli/main.py:4927`
- `xavani_cli/model_switch.py:1091`

## `AWS_EC2_METADATA_DISABLED`

**Purpose:** never the legitimate source for `xavani doctor`.

**Used at:**
- `xavani_cli/doctor.py:1752`
- `xavani_cli/doctor.py:1753`
- `xavani_cli/doctor.py:1766`

## `AWS_SECRET_ACCESS_KEY`

**Used at:**
- `xavani_cli/model_switch.py:1095`

## `AZURE_ANTHROPIC_KEY`

**Used at:**
- `xavani_cli/runtime_provider.py:1084`
- `xavani_cli/runtime_provider.py:1362`

## `AZURE_CLIENT_ID`

**Used at:**
- `agent/azure_identity_adapter.py:383`

## `AZURE_CLIENT_SECRET`

**Used at:**
- `agent/azure_identity_adapter.py:384`

## `AZURE_FEDERATED_TOKEN_FILE`

**Used at:**
- `agent/azure_identity_adapter.py:381`

## `AZURE_FOUNDRY_API_KEY`

**Used at:**
- `xavani_cli/auth.py:5703`
- `xavani_cli/auth.py:5705`
- `xavani_cli/main.py:3644`
- `xavani_cli/runtime_provider.py:885`
- `xavani_cli/runtime_provider.py:889`

## `AZURE_FOUNDRY_BASE_URL`

**Used at:**
- `xavani_cli/runtime_provider.py:800`

## `AZURE_TENANT_ID`

**Purpose:** standard ``AZURE_*`` env vars; surface them below.

**Used at:**
- `agent/azure_identity_adapter.py:376`
- `agent/azure_identity_adapter.py:385`

## `BLUEBUBBLES_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1768`
- `xavani_cli/setup.py:2535`

## `BLUEBUBBLES_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1773`

## `BLUEBUBBLES_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1774`

## `BLUEBUBBLES_PASSWORD`

**Used at:**
- `gateway/config.py:1755`
- `gateway/platforms/bluebubbles.py:161`

## `BLUEBUBBLES_SEND_READ_RECEIPTS`

**Defaults:** true

**Used at:**
- `gateway/config.py:1766`

## `BLUEBUBBLES_SERVER_URL`

**Purpose:** BlueBubbles (iMessage)

**Used at:**
- `gateway/config.py:1754`
- `gateway/platforms/bluebubbles.py:159`
- `xavani_cli/setup.py:2359`
- `xavani_cli/setup.py:2535`

## `BLUEBUBBLES_WEBHOOK_HOST`

**Defaults:** 127.0.0.1

**Used at:**
- `gateway/config.py:1763`
- `gateway/platforms/bluebubbles.py:164`

## `BLUEBUBBLES_WEBHOOK_PATH`

**Defaults:** /bluebubbles-webhook

**Used at:**
- `gateway/config.py:1765`
- `gateway/platforms/bluebubbles.py:172`

## `BLUEBUBBLES_WEBHOOK_PORT`

**Defaults:** 8645

**Used at:**
- `gateway/config.py:1764`
- `gateway/platforms/bluebubbles.py:168`

## `BROWSERBASE_ADVANCED_STEALTH`

**Used at:**
- `plugins/browser/browserbase/provider.py:109`

## `BROWSERBASE_API_KEY`

**Used at:**
- `plugins/browser/browserbase/provider.py:78`
- `xavani_cli/nous_subscription.py:296`
- `xavani_cli/nous_subscription.py:544`
- `xavani_cli/nous_subscription.py:584`
- `xavani_cli/setup.py:2846`

## `BROWSERBASE_KEEP_ALIVE`

**Used at:**
- `plugins/browser/browserbase/provider.py:112`

## `BROWSERBASE_PROJECT_ID`

**Used at:**
- `plugins/browser/browserbase/provider.py:79`
- `xavani_cli/nous_subscription.py:296`
- `xavani_cli/nous_subscription.py:584`

## `BROWSERBASE_PROXIES`

**Purpose:** Optional env-var knobs

**Used at:**
- `plugins/browser/browserbase/provider.py:107`

## `BROWSERBASE_SESSION_TIMEOUT`

**Used at:**
- `plugins/browser/browserbase/provider.py:114`

## `BROWSER_CDP_URL`

**Purpose:** Env preserved; nothing reaped.

**Used at:**
- `cli.py:8604`
- `cli.py:8704`
- `tests/test_tui_gateway_server.py:3903`
- `tests/test_tui_gateway_server.py:3907`
- `tests/test_tui_gateway_server.py:3922`
- `tests/test_tui_gateway_server.py:3931`
- `tests/test_tui_gateway_server.py:3955`
- `tests/test_tui_gateway_server.py:4018`
- ... and 20 more

## `BROWSER_INACTIVITY_TIMEOUT`

**Purpose:** especially when subagents are doing multi-step browser tasks.

**Used at:**
- `tools/browser_tool.py:1193`

## `BROWSER_USE_API_KEY`

**Purpose:** managed Nous gateway via ``tool_gateway.browser: gateway``.

**Used at:**
- `plugins/browser/browser_use/provider.py:146`
- `xavani_cli/nous_subscription.py:297`
- `xavani_cli/nous_subscription.py:543`
- `xavani_cli/nous_subscription.py:583`

## `CAMOFOX_SESSION_KEY`

**Used at:**
- `tools/browser_camofox.py:144`

## `CAMOFOX_URL`

**Used at:**
- `tools/browser_camofox.py:62`
- `xavani_cli/nous_subscription.py:295`

## `CAMOFOX_USER_ID`

**Used at:**
- `tools/browser_camofox.py:139`

## `CANVAS_API_TOKEN`

**Used at:**
- `oag_skills/productivity/canvas/scripts/canvas_api.py:24`
- `optional-skills/productivity/canvas/scripts/canvas_api.py:24`

## `CANVAS_BASE_URL`

**Used at:**
- `oag_skills/productivity/canvas/scripts/canvas_api.py:25`
- `optional-skills/productivity/canvas/scripts/canvas_api.py:25`

## `CI`

**Used at:**
- `tests/tools/test_local_shell_init.py:191`

## `CLAUDE_CODE_OAUTH_TOKEN`

**Purpose:** 2. CLAUDE_CODE_OAUTH_TOKEN (used by Claude Code for setup-tokens)

**Used at:**
- `agent/anthropic_adapter.py:1122`
- `xavani_cli/web_server.py:1505`

## `CODEX_HOME`

**Used at:**
- `xavani_cli/auth.py:3275`
- `xavani_cli/codex_models.py:184`

## `COLORFGBG`

**Purpose:** 4. COLORFGBG (xterm/Konsole/urxvt)

**Used at:**
- `cli.py:1439`

## `COMFY_CLOUD_API_KEY`

**Used at:**
- `oag_skills/creative/comfyui/tests/conftest.py:58`
- `oag_skills/creative/comfyui/tests/conftest.py:63`
- `skills/creative/comfyui/tests/conftest.py:58`
- `skills/creative/comfyui/tests/conftest.py:63`

## `COPILOT_CLI_PATH`

**Used at:**
- `agent/copilot_acp_client.py:63`
- `xavani_cli/auth.py:5574`
- `xavani_cli/auth.py:5771`

## `COPILOT_GH_HOST`

**Used at:**
- `xavani_cli/copilot_auth.py:137`

## `COURTLISTENER_TOKEN`

**Used at:**
- `oag_skills/research/osint-investigation/scripts/fetch_courtlistener.py:135`
- `optional-skills/research/osint-investigation/scripts/fetch_courtlistener.py:135`

## `CUSTOM_API_KEY`

**Used at:**
- `xavani_cli/models.py:2264`

## `CUSTOM_BASE_URL`

**Used at:**
- `xavani_cli/runtime_provider.py:653`

## `DAYTONA_API_KEY`

**Purpose:** Skip entire module if no API key

**Used at:**
- `tests/integration/test_daytona_terminal.py:21`
- `tools/terminal_tool.py:2257`
- `xavani_cli/config.py:5123`
- `xavani_cli/doctor.py:1140`
- `xavani_cli/setup.py:1650`

## `DBUS_SESSION_BUS_ADDRESS`

**Used at:**
- `tests/xavani_cli/test_gateway_service.py:1421`
- `tests/xavani_cli/test_gateway_service.py:1430`
- `xavani_cli/gateway.py:1417`

## `DEEPSEEK_API_KEY`

**Purpose:** Cleared, but sibling entries untouched.

**Used at:**
- `tests/run_agent/test_deepseek_v4_thinking_live.py:26`
- `tests/xavani_cli/test_prompt_api_key.py:52`
- `tests/xavani_cli/test_prompt_api_key.py:94`
- `tests/xavani_cli/test_prompt_api_key.py:107`
- `tests/xavani_cli/test_prompt_api_key.py:119`

## `DELEGATION_CHILD_TIMEOUT_SECONDS`

**Used at:**
- `tools/delegate_tool.py:395`

## `DELEGATION_MAX_CONCURRENT_CHILDREN`

**Used at:**
- `tools/delegate_tool.py:368`

## `DINGTALK_ALLOWED_CHATS`

**Used at:**
- `gateway/config.py:1150`
- `gateway/config.py:1153`
- `gateway/platforms/dingtalk.py:410`
- `tests/gateway/test_allowed_channels_widening.py:235`

## `DINGTALK_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1155`
- `gateway/config.py:1158`
- `gateway/platforms/dingtalk.py:461`

## `DINGTALK_CLIENT_ID`

**Purpose:** DingTalk

**Used at:**
- `gateway/config.py:452`
- `gateway/config.py:1624`
- `gateway/platforms/dingtalk.py:150`
- `xavani_cli/gateway.py:3994`
- `xavani_cli/gateway.py:4036`

## `DINGTALK_CLIENT_SECRET`

**Used at:**
- `gateway/config.py:453`
- `gateway/config.py:1625`
- `gateway/platforms/dingtalk.py:150`

## `DINGTALK_FREE_RESPONSE_CHATS`

**Used at:**
- `gateway/config.py:1144`
- `gateway/config.py:1147`
- `gateway/platforms/dingtalk.py:396`

## `DINGTALK_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1634`

## `DINGTALK_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1639`

## `DINGTALK_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1640`

## `DINGTALK_MENTION_PATTERNS`

**Used at:**
- `gateway/config.py:1141`
- `gateway/config.py:1142`
- `gateway/platforms/dingtalk.py:419`

## `DINGTALK_REGISTRATION_SOURCE`

**Used at:**
- `xavani_cli/dingtalk_auth.py:41`

## `DINGTALK_REQUIRE_MENTION`

**Defaults:** false

**Used at:**
- `gateway/config.py:1139`
- `gateway/config.py:1140`
- `gateway/platforms/dingtalk.py:391`

## `DINGTALK_WEBHOOK_URL`

**Used at:**
- `tools/send_message_tool.py:1746`

## `DISCORD_ALLOWED_CHANNELS`

**Purpose:** Check allowed channels - if set, only respond in these channels

**Used at:**
- `gateway/config.py:958`
- `gateway/config.py:961`
- `gateway/platforms/discord.py:2342`
- `gateway/platforms/discord.py:4473`

## `DISCORD_ALLOWED_ROLES`

**Purpose:** Users with ANY of these roles can interact with the bot.

**Used at:**
- `gateway/platforms/discord.py:654`
- `gateway/run.py:6257`

## `DISCORD_ALLOWED_USERS`

**Purpose:** Parse allowed user entries (may contain usernames or IDs)

**Used at:**
- `gateway/platforms/discord.py:645`
- `gateway/platforms/discord.py:2857`
- `scripts/discord-voice-doctor.py:203`
- `xavani_cli/setup.py:2054`

## `DISCORD_ALLOW_ANY_ATTACHMENT`

**Defaults:** false

**Used at:**
- `gateway/platforms/discord.py:3589`

## `DISCORD_ALLOW_BOTS`

**Purpose:** Determine which bot messages to include in context

**Defaults:** none

**Used at:**
- `gateway/platforms/discord.py:759`
- `gateway/platforms/discord.py:3708`
- `tests/gateway/test_discord_bot_filter.py:107`

## `DISCORD_AUTO_THREAD`

**Defaults:** true

**Used at:**
- `gateway/config.py:946`
- `gateway/config.py:947`
- `gateway/platforms/discord.py:4526`
- `tests/gateway/test_discord_slash_commands.py:783`

## `DISCORD_BOT_TOKEN`

**Purpose:** Discord

**Used at:**
- `gateway/config.py:1328`
- `gateway/session.py:228`
- `scripts/discord-voice-doctor.py:195`
- `tests/xavani_cli/test_non_ascii_credential.py:74`
- `tools/discord_tool.py:64`
- `xavani_cli/config.py:5188`
- `xavani_cli/setup.py:2050`
- `xavani_cli/setup.py:2529`
- ... and 1 more

## `DISCORD_COMMAND_SYNC_POLICY`

**Defaults:** safe

**Used at:**
- `gateway/platforms/discord.py:1148`

## `DISCORD_FREE_RESPONSE_CHANNELS`

**Used at:**
- `gateway/config.py:942`
- `gateway/config.py:945`
- `gateway/platforms/discord.py:3622`

## `DISCORD_HIDE_SLASH_COMMANDS`

**Purpose:** everyone in the guild.

**Defaults:** false

**Used at:**
- `gateway/platforms/discord.py:3183`
- `tests/gateway/test_discord_slash_auth.py:382`

## `DISCORD_HISTORY_BACKFILL`

**Purpose:** and prepends them to the user message for context.

**Defaults:** true

**Used at:**
- `gateway/config.py:971`
- `gateway/config.py:972`
- `gateway/platforms/discord.py:3662`
- `tests/gateway/test_config.py:437`

## `DISCORD_HISTORY_BACKFILL_LIMIT`

**Defaults:** 50

**Used at:**
- `gateway/config.py:974`
- `gateway/config.py:975`
- `gateway/platforms/discord.py:3678`
- `tests/gateway/test_config.py:438`

## `DISCORD_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1335`

## `DISCORD_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1340`

## `DISCORD_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1341`

## `DISCORD_IGNORED_CHANNELS`

**Purpose:** entry on the thread or its parent rejects the interaction.

**Used at:**
- `gateway/config.py:952`
- `gateway/config.py:955`
- `gateway/platforms/discord.py:2359`
- `gateway/platforms/discord.py:4481`
- `tests/gateway/test_discord_channel_controls.py:309`
- `tests/gateway/test_discord_channel_controls.py:348`

## `DISCORD_MAX_ATTACHMENT_BYTES`

**Used at:**
- `gateway/platforms/discord.py:3600`

## `DISCORD_NO_THREAD_CHANNELS`

**Used at:**
- `gateway/config.py:964`
- `gateway/config.py:967`
- `gateway/platforms/discord.py:4523`
- `tests/gateway/test_discord_channel_controls.py:328`

## `DISCORD_REACTIONS`

**Defaults:** true

**Used at:**
- `gateway/config.py:948`
- `gateway/config.py:949`
- `gateway/platforms/discord.py:1357`

## `DISCORD_REPLY_TO_MODE`

**Purpose:** Reply threading mode for Discord (off/first/all)

**Used at:**
- `gateway/config.py:997`
- `gateway/config.py:999`
- `gateway/config.py:1345`
- `tests/gateway/test_discord_reply_mode.py:422`
- `tests/gateway/test_discord_reply_mode.py:431`
- `tests/gateway/test_discord_reply_mode.py:443`
- `tests/gateway/test_discord_reply_mode.py:453`
- `tests/gateway/test_discord_reply_mode.py:466`

## `DISCORD_REQUIRE_MENTION`

**Defaults:** true

**Used at:**
- `gateway/config.py:937`
- `gateway/config.py:938`
- `gateway/platforms/discord.py:3574`

## `DISCORD_THREAD_REQUIRE_MENTION`

**Purpose:** Env value preserved, not clobbered by yaml.

**Defaults:** false

**Used at:**
- `gateway/config.py:939`
- `gateway/config.py:940`
- `gateway/platforms/discord.py:3653`
- `tests/gateway/test_config.py:329`
- `tests/gateway/test_config.py:348`

## `DISPLAY`

**Purpose:** Linux/other posix: need DISPLAY or WAYLAND_DISPLAY

**Used at:**
- `tools/mcp_oauth.py:159`
- `xavani_cli/web_server.py:4785`

## `DO_NOT_TRACK`

**Used at:**
- `oag_cli.py:56`
- `oag_cli.py:141`
- `xavani.py:51`

## `E2E_MATRIX_HS`

**Used at:**
- `tests/e2e/matrix_xsign_bootstrap/test_bootstrap.py:53`

## `EDITOR`

**Purpose:** a working program on Windows (it defaults to /usr/bin/nano).

**Used at:**
- `tests/tools/test_windows_native_support.py:106`
- `tests/tools/test_windows_native_support.py:121`
- `tests/tools/test_windows_native_support.py:137`
- `xavani_cli/config.py:5231`
- `xavani_cli/stdio.py:131`
- `xavani_cli/stdio.py:132`

## `ELEVENLABS_API_KEY`

**Used at:**
- `scripts/discord-voice-doctor.py:227`
- `tools/tts_tool.py:820`
- `tools/tts_tool.py:1927`
- `tools/tts_tool.py:2064`
- `tools/tts_tool.py:2250`
- `xavani_cli/nous_subscription.py:294`
- `xavani_cli/nous_subscription.py:537`
- `xavani_cli/nous_subscription.py:580`
- ... and 3 more

## `EMAIL_ADDRESS`

**Purpose:** Email

**Used at:**
- `gateway/config.py:1486`
- `gateway/platforms/email.py:113`
- `gateway/platforms/email.py:260`
- `tools/send_message_tool.py:1497`

## `EMAIL_ALLOWED_USERS`

**Purpose:** sending a reply even though the handler returned None.

**Used at:**
- `gateway/platforms/email.py:458`

## `EMAIL_HOME_ADDRESS`

**Used at:**
- `gateway/config.py:1499`

## `EMAIL_HOME_ADDRESS_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1504`

## `EMAIL_HOME_ADDRESS_THREAD_ID`

**Used at:**
- `gateway/config.py:1505`

## `EMAIL_IMAP_HOST`

**Used at:**
- `gateway/config.py:1488`
- `gateway/platforms/email.py:115`
- `gateway/platforms/email.py:262`
- `xavani_cli/gateway.py:3800`

## `EMAIL_IMAP_PORT`

**Defaults:** 993

**Used at:**
- `gateway/platforms/email.py:263`

## `EMAIL_PASSWORD`

**Used at:**
- `gateway/config.py:1487`
- `gateway/platforms/email.py:114`
- `gateway/platforms/email.py:261`
- `tools/send_message_tool.py:1498`
- `xavani_cli/gateway.py:3799`

## `EMAIL_POLL_INTERVAL`

**Defaults:** 15

**Used at:**
- `gateway/platforms/email.py:266`

## `EMAIL_SMTP_HOST`

**Used at:**
- `gateway/config.py:1489`
- `gateway/platforms/email.py:116`
- `gateway/platforms/email.py:264`
- `tools/send_message_tool.py:1499`
- `xavani_cli/gateway.py:3801`

## `EMAIL_SMTP_PORT`

**Defaults:** 587

**Used at:**
- `gateway/platforms/email.py:265`
- `tools/send_message_tool.py:1501`

## `EVM_RPC_URL`

**Used at:**
- `oag_skills/blockchain/evm/scripts/evm_client.py:394`
- `optional-skills/blockchain/evm/scripts/evm_client.py:394`

## `EVOLVER_MODEL`

**Used at:**
- `oag_skills/research/darwinian-evolver/scripts/parrot_openrouter.py:39`
- `oag_skills/research/darwinian-evolver/templates/custom_problem_template.py:47`
- `optional-skills/research/darwinian-evolver/scripts/parrot_openrouter.py:39`
- `optional-skills/research/darwinian-evolver/templates/custom_problem_template.py:47`

## `EXA_API_KEY`

**Used at:**
- `xavani_cli/nous_subscription.py:287`
- `xavani_cli/nous_subscription.py:575`

## `FAL_IMAGE_MODEL`

**Used at:**
- `tools/image_generation_tool.py:556`

## `FAL_KEY`

**Used at:**
- `plugins/video_gen/fal/__init__.py:331`
- `plugins/video_gen/fal/__init__.py:402`
- `tools/tool_backend_helpers.py:138`
- `tools/tool_backend_helpers.py:145`

## `FAL_VIDEO_MODEL`

**Used at:**
- `plugins/video_gen/fal/__init__.py:220`

## `FEISHU_ALLOWED_USERS`

**Used at:**
- `gateway/platforms/feishu.py:1532`

## `FEISHU_ALLOW_ALL_USERS`

**Used at:**
- `tests/gateway/test_setup_feishu.py:272`

## `FEISHU_ALLOW_BOTS`

**Purpose:** feishu.allow_bots is bridged to this env var at config load.

**Defaults:** none

**Used at:**
- `gateway/config.py:1201`
- `gateway/config.py:1202`
- `gateway/platforms/feishu.py:1512`
- `tests/gateway/test_config.py:494`
- `tests/gateway/test_config.py:510`

## `FEISHU_APP_ID`

**Purpose:** Feishu / Lark

**Used at:**
- `gateway/config.py:1644`
- `gateway/platforms/feishu.py:1521`
- `xavani_cli/gateway.py:4361`

## `FEISHU_APP_SECRET`

**Used at:**
- `gateway/config.py:1645`
- `gateway/platforms/feishu.py:1522`
- `xavani_cli/gateway.py:4362`

## `FEISHU_BOT_NAME`

**Used at:**
- `gateway/platforms/feishu.py:1537`

## `FEISHU_BOT_OPEN_ID`

**Used at:**
- `gateway/platforms/feishu.py:1535`

## `FEISHU_BOT_USER_ID`

**Used at:**
- `gateway/platforms/feishu.py:1536`

## `FEISHU_CONNECTION_MODE`

**Defaults:** websocket

**Used at:**
- `gateway/config.py:1654`
- `gateway/platforms/feishu.py:1525`

## `FEISHU_DOMAIN`

**Defaults:** feishu

**Used at:**
- `gateway/config.py:1653`
- `gateway/platforms/feishu.py:1523`

## `FEISHU_ENCRYPT_KEY`

**Used at:**
- `gateway/config.py:1656`
- `gateway/platforms/feishu.py:1527`

## `FEISHU_GROUP_POLICY`

**Defaults:** allowlist

**Used at:**
- `gateway/platforms/feishu.py:1529`

## `FEISHU_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1662`

## `FEISHU_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1667`

## `FEISHU_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1668`

## `FEISHU_REACTIONS`

**Defaults:** true

**Used at:**
- `gateway/platforms/feishu.py:2814`

## `FEISHU_REQUIRE_MENTION`

**Defaults:** true

**Used at:**
- `gateway/platforms/feishu.py:1578`

## `FEISHU_VERIFICATION_TOKEN`

**Used at:**
- `gateway/config.py:1659`
- `gateway/platforms/feishu.py:1528`

## `FEISHU_WEBHOOK_HOST`

**Used at:**
- `gateway/platforms/feishu.py:1560`

## `FEISHU_WEBHOOK_PATH`

**Used at:**
- `gateway/platforms/feishu.py:1566`

## `FEISHU_WEBHOOK_PORT`

**Used at:**
- `gateway/platforms/feishu.py:1563`

## `FIRECRAWL_API_KEY`

**Used at:**
- `plugins/browser/firecrawl/provider.py:68`
- `plugins/browser/firecrawl/provider.py:78`
- `tools/web_tools.py:1382`
- `xavani_cli/nous_subscription.py:288`
- `xavani_cli/nous_subscription.py:529`
- `xavani_cli/nous_subscription.py:571`
- `xavani_cli/setup.py:2848`

## `FIRECRAWL_API_URL`

**Used at:**
- `plugins/browser/firecrawl/provider.py:75`
- `tools/web_tools.py:1383`
- `tools/web_tools.py:1403`
- `xavani_cli/nous_subscription.py:288`
- `xavani_cli/nous_subscription.py:530`
- `xavani_cli/nous_subscription.py:572`

## `FIRECRAWL_BROWSER_TTL`

**Used at:**
- `plugins/browser/firecrawl/provider.py:90`

## `GATEWAY_ALLOWED_USERS`

**Used at:**
- `gateway/run.py:6273`
- `gateway/run.py:6418`

## `GATEWAY_ALLOW_ALL_USERS`

**Purpose:** allow everyone (fixes #24457).

**Used at:**
- `gateway/platforms/telegram.py:542`
- `gateway/run.py:3740`
- `gateway/run.py:6277`
- `tests/gateway/test_allowlist_startup_check.py:23`

## `GATEWAY_HEALTH_TIMEOUT`

**Defaults:** 3

**Used at:**
- `xavani_cli/web_server.py:491`
- `xavani_cli/web_server.py:495`

## `GATEWAY_HEALTH_URL`

**Used at:**
- `xavani_cli/web_server.py:489`

## `GATEWAY_PROXY_KEY`

**Used at:**
- `gateway/run.py:15215`

## `GATEWAY_PROXY_URL`

**Used at:**
- `gateway/run.py:15164`

## `GEMINI_API_KEY`

**Used at:**
- `tools/tts_tool.py:1207`
- `tools/tts_tool.py:1946`
- `xavani_cli/setup.py:500`
- `xavani_cli/setup.py:1349`

## `GEMINI_BASE_URL`

**Used at:**
- `tools/tts_tool.py:1218`

## `GH_TOKEN`

**Used at:**
- `oag_skills/devops/watchers/scripts/watch_github.py:122`
- `optional-skills/devops/watchers/scripts/watch_github.py:122`
- `xavani_cli/doctor.py:1843`

## `GITHUB_TOKEN`

**Purpose:** Skills Hub

**Used at:**
- `oag_skills/devops/watchers/scripts/watch_github.py:122`
- `optional-skills/devops/watchers/scripts/watch_github.py:122`
- `tests/tools/test_code_execution_modes.py:424`
- `tools/tirith_security.py:274`
- `xavani_cli/doctor.py:1843`
- `xavani_cli/setup.py:548`

## `GLM_BASE_URL`

**Purpose:** The garbage value should NOT have been saved

**Used at:**
- `tests/xavani_cli/test_model_provider_persistence.py:352`
- `tests/xavani_cli/test_model_provider_persistence.py:376`
- `tests/xavani_cli/test_model_provider_persistence.py:398`

## `GOOGLE_API_KEY`

**Used at:**
- `tests/xavani_cli/test_non_ascii_credential.py:102`
- `tools/tts_tool.py:1207`
- `tools/tts_tool.py:1946`
- `xavani_cli/setup.py:500`
- `xavani_cli/setup.py:1349`

## `GOOGLE_APPLICATION_CREDENTIALS`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:573`
- `plugins/platforms/google_chat/adapter.py:3021`
- `plugins/platforms/google_chat/adapter.py:3180`

## `GOOGLE_CHAT_ALLOWED_USERS`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:3103`

## `GOOGLE_CHAT_BOOTSTRAP_SPACES`

**Purpose:** Env-configured allowed spaces (comma-separated). Optional.

**Used at:**
- `plugins/platforms/google_chat/adapter.py:737`

## `GOOGLE_CHAT_DEBUG_RAW`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:1175`

## `GOOGLE_CHAT_HOME_CHANNEL`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:3025`
- `plugins/platforms/google_chat/adapter.py:3116`

## `GOOGLE_CHAT_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `plugins/platforms/google_chat/adapter.py:3029`

## `GOOGLE_CHAT_MAX_BYTES`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:553`

## `GOOGLE_CHAT_MAX_MESSAGES`

**Purpose:** FlowControl knobs (env-configurable).

**Defaults:** 1

**Used at:**
- `plugins/platforms/google_chat/adapter.py:552`

## `GOOGLE_CHAT_PROJECT_ID`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:2976`
- `plugins/platforms/google_chat/adapter.py:3006`
- `plugins/platforms/google_chat/adapter.py:3076`

## `GOOGLE_CHAT_SERVICE_ACCOUNT_JSON`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:3020`
- `plugins/platforms/google_chat/adapter.py:3094`
- `plugins/platforms/google_chat/adapter.py:3179`

## `GOOGLE_CHAT_SUBSCRIPTION`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:2981`
- `plugins/platforms/google_chat/adapter.py:3011`

## `GOOGLE_CHAT_SUBSCRIPTION_NAME`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:2980`
- `plugins/platforms/google_chat/adapter.py:3010`
- `plugins/platforms/google_chat/adapter.py:3052`
- `plugins/platforms/google_chat/adapter.py:3085`

## `GOOGLE_CLOUD_PROJECT`

**Used at:**
- `plugins/platforms/google_chat/adapter.py:2977`
- `plugins/platforms/google_chat/adapter.py:3007`

## `GROQ_API_KEY`

**Used at:**
- `scripts/discord-voice-doctor.py:226`
- `tools/transcription_tools.py:249`
- `tools/transcription_tools.py:298`
- `tools/transcription_tools.py:571`

## `GROQ_BASE_URL`

**Defaults:** https://api.groq.com/openai/v1

**Used at:**
- `tools/transcription_tools.py:101`

## `HASS_TOKEN`

**Purpose:** Home Assistant

**Used at:**
- `gateway/config.py:1475`
- `gateway/platforms/homeassistant.py:55`
- `gateway/platforms/homeassistant.py:86`
- `tools/homeassistant_tool.py:44`
- `tools/homeassistant_tool.py:355`
- `tools/send_message_tool.py:1717`
- `xavani_cli/setup.py:535`
- `xavani_cli/tools_config.py:1134`
- ... and 1 more

## `HASS_URL`

**Defaults:** http://homeassistant.local:8123

**Used at:**
- `gateway/config.py:1481`
- `gateway/platforms/homeassistant.py:87`
- `tools/homeassistant_tool.py:43`
- `tools/send_message_tool.py:1716`

## `HINDSIGHT_API_KEY`

**Used at:**
- `plugins/memory/hindsight/__init__.py:334`
- `plugins/memory/hindsight/__init__.py:616`
- `plugins/memory/hindsight/__init__.py:703`
- `plugins/memory/hindsight/__init__.py:1145`

## `HINDSIGHT_API_LLM_BASE_URL`

**Used at:**
- `plugins/memory/hindsight/__init__.py:425`

## `HINDSIGHT_API_URL`

**Used at:**
- `plugins/memory/hindsight/__init__.py:618`
- `plugins/memory/hindsight/__init__.py:1147`

## `HINDSIGHT_BANK_ID`

**Used at:**
- `plugins/memory/hindsight/__init__.py:343`

## `HINDSIGHT_BUDGET`

**Used at:**
- `plugins/memory/hindsight/__init__.py:344`

## `HINDSIGHT_IDLE_TIMEOUT`

**Used at:**
- `plugins/memory/hindsight/__init__.py:336`
- `plugins/memory/hindsight/__init__.py:442`
- `plugins/memory/hindsight/__init__.py:917`
- `plugins/memory/hindsight/__init__.py:1130`

## `HINDSIGHT_LLM_API_KEY`

**Used at:**
- `plugins/memory/hindsight/__init__.py:420`
- `plugins/memory/hindsight/__init__.py:909`

## `HINDSIGHT_MODE`

**Used at:**
- `plugins/memory/hindsight/__init__.py:333`

## `HINDSIGHT_RETAIN_ASSISTANT_PREFIX`

**Used at:**
- `plugins/memory/hindsight/__init__.py:340`
- `plugins/memory/hindsight/__init__.py:1190`

## `HINDSIGHT_RETAIN_SOURCE`

**Used at:**
- `plugins/memory/hindsight/__init__.py:338`
- `plugins/memory/hindsight/__init__.py:1184`

## `HINDSIGHT_RETAIN_TAGS`

**Used at:**
- `plugins/memory/hindsight/__init__.py:337`
- `plugins/memory/hindsight/__init__.py:1178`

## `HINDSIGHT_RETAIN_USER_PREFIX`

**Used at:**
- `plugins/memory/hindsight/__init__.py:339`
- `plugins/memory/hindsight/__init__.py:1187`

## `HINDSIGHT_TIMEOUT`

**Used at:**
- `plugins/memory/hindsight/__init__.py:335`
- `plugins/memory/hindsight/__init__.py:1126`

## `HOME`

**Purpose:** which is the exact scenario where RHEL root loses /usr/local/bin.

**Used at:**
- `agent/copilot_acp_client.py:87`
- `tests/stress/test_atypical_scenarios.py:55`
- `tests/stress/test_atypical_scenarios.py:543`
- `tests/stress/test_atypical_scenarios.py:569`
- `tests/stress/test_atypical_scenarios.py:596`
- `tests/stress/test_atypical_scenarios.py:605`
- `tests/stress/test_atypical_scenarios.py:697`
- `tests/stress/test_benchmarks.py:63`
- ... and 16 more

## `HONCHO_API_KEY`

**Purpose:** No default host block and no root-level API key = Honcho not configured

**Used at:**
- `plugins/memory/honcho/cli.py:39`
- `plugins/memory/honcho/cli.py:179`
- `plugins/memory/honcho/cli.py:221`
- `plugins/memory/honcho/cli.py:292`
- `plugins/memory/honcho/cli.py:766`
- `plugins/memory/honcho/client.py:342`
- `plugins/memory/honcho/client.py:398`
- `tests/test_honcho_client_config.py:75`

## `HONCHO_BASE_URL`

**Used at:**
- `plugins/memory/honcho/cli.py:294`
- `plugins/memory/honcho/client.py:343`
- `plugins/memory/honcho/client.py:409`

## `HONCHO_ENVIRONMENT`

**Used at:**
- `plugins/memory/honcho/client.py:349`

## `HONCHO_TIMEOUT`

**Used at:**
- `plugins/memory/honcho/client.py:344`
- `plugins/memory/honcho/client.py:415`

## `HTTPS_PROXY`

**Used at:**
- `gateway/platforms/qqbot/adapter.py:469`

## `IDENTITY_ENDPOINT`

**Used at:**
- `agent/azure_identity_adapter.py:387`

## `INVOCATION_ID`

**Purpose:** exits when the gateway dies, taking the detached helper with it).

**Used at:**
- `gateway/run.py:9782`
- `gateway/shutdown_forensics.py:141`
- `gateway/shutdown_forensics.py:343`

## `IRC_ALLOWED_USERS`

**Used at:**
- `plugins/platforms/irc/adapter.py:638`

## `IRC_CHANNEL`

**Used at:**
- `plugins/platforms/irc/adapter.py:122`
- `plugins/platforms/irc/adapter.py:530`
- `plugins/platforms/irc/adapter.py:541`
- `plugins/platforms/irc/adapter.py:604`
- `plugins/platforms/irc/adapter.py:656`
- `plugins/platforms/irc/adapter.py:674`
- `plugins/platforms/irc/adapter.py:755`
- `tests/xavani_cli/test_setup_irc.py:28`

## `IRC_HOME_CHANNEL`

**Purpose:** with ``deliver=irc`` have a sensible target without extra config.

**Used at:**
- `plugins/platforms/irc/adapter.py:702`

## `IRC_HOME_CHANNEL_NAME`

**Used at:**
- `plugins/platforms/irc/adapter.py:706`

## `IRC_NICKNAME`

**Defaults:** xavani-bot

**Used at:**
- `plugins/platforms/irc/adapter.py:121`
- `plugins/platforms/irc/adapter.py:595`
- `plugins/platforms/irc/adapter.py:687`
- `plugins/platforms/irc/adapter.py:765`

## `IRC_NICKSERV_PASSWORD`

**Used at:**
- `plugins/platforms/irc/adapter.py:129`
- `plugins/platforms/irc/adapter.py:697`
- `plugins/platforms/irc/adapter.py:698`
- `plugins/platforms/irc/adapter.py:773`

## `IRC_PORT`

**Used at:**
- `plugins/platforms/irc/adapter.py:120`
- `plugins/platforms/irc/adapter.py:583`
- `plugins/platforms/irc/adapter.py:589`
- `plugins/platforms/irc/adapter.py:681`
- `plugins/platforms/irc/adapter.py:759`

## `IRC_SERVER`

**Purpose:** Connection settings (env vars override config.yaml)

**Used at:**
- `plugins/platforms/irc/adapter.py:119`
- `plugins/platforms/irc/adapter.py:529`
- `plugins/platforms/irc/adapter.py:540`
- `plugins/platforms/irc/adapter.py:563`
- `plugins/platforms/irc/adapter.py:655`
- `plugins/platforms/irc/adapter.py:673`
- `plugins/platforms/irc/adapter.py:754`
- `tests/xavani_cli/test_setup_irc.py:28`

## `IRC_SERVER_PASSWORD`

**Purpose:** existing config.yaml users; env-reads at construct time still win.

**Used at:**
- `plugins/platforms/irc/adapter.py:128`
- `plugins/platforms/irc/adapter.py:695`
- `plugins/platforms/irc/adapter.py:696`
- `plugins/platforms/irc/adapter.py:772`

## `IRC_USE_TLS`

**Used at:**
- `plugins/platforms/irc/adapter.py:124`
- `plugins/platforms/irc/adapter.py:125`
- `plugins/platforms/irc/adapter.py:690`
- `plugins/platforms/irc/adapter.py:766`

## `JOURNAL_STREAM`

**Used at:**
- `gateway/shutdown_forensics.py:144`

## `LINEAR_API_KEY`

**Used at:**
- `oag_skills/productivity/linear/scripts/linear_api.py:65`
- `plugins/teams_pipeline/pipeline.py:219`
- `skills/productivity/linear/scripts/linear_api.py:65`

## `LINE_ALLOWED_GROUPS`

**Used at:**
- `plugins/platforms/line/adapter.py:681`

## `LINE_ALLOWED_ROOMS`

**Used at:**
- `plugins/platforms/line/adapter.py:684`

## `LINE_ALLOWED_USERS`

**Used at:**
- `plugins/platforms/line/adapter.py:678`

## `LINE_BUTTON_LABEL`

**Used at:**
- `plugins/platforms/line/adapter.py:702`

## `LINE_CHANNEL_ACCESS_TOKEN`

**Used at:**
- `plugins/platforms/line/adapter.py:647`
- `plugins/platforms/line/adapter.py:1477`
- `plugins/platforms/line/adapter.py:1491`
- `plugins/platforms/line/adapter.py:1511`
- `plugins/platforms/line/adapter.py:1551`

## `LINE_CHANNEL_SECRET`

**Used at:**
- `plugins/platforms/line/adapter.py:651`
- `plugins/platforms/line/adapter.py:1479`
- `plugins/platforms/line/adapter.py:1494`
- `plugins/platforms/line/adapter.py:1511`

## `LINE_DELIVERED_TEXT`

**Used at:**
- `plugins/platforms/line/adapter.py:706`

## `LINE_HOME_CHANNEL`

**Used at:**
- `plugins/platforms/line/adapter.py:1523`

## `LINE_HOST`

**Purpose:** Webhook server

**Defaults:** 0.0.0.0

**Used at:**
- `plugins/platforms/line/adapter.py:656`
- `plugins/platforms/line/adapter.py:1519`

## `LINE_INTERRUPTED_TEXT`

**Used at:**
- `plugins/platforms/line/adapter.py:710`

## `LINE_PENDING_TEXT`

**Used at:**
- `plugins/platforms/line/adapter.py:698`

## `LINE_PORT`

**Used at:**
- `plugins/platforms/line/adapter.py:659`
- `plugins/platforms/line/adapter.py:1514`

## `LINE_PUBLIC_URL`

**Used at:**
- `plugins/platforms/line/adapter.py:668`
- `plugins/platforms/line/adapter.py:1521`

## `LINE_SLOW_RESPONSE_THRESHOLD`

**Used at:**
- `plugins/platforms/line/adapter.py:690`

## `LM_API_KEY`

**Purpose:** Gate: don't probe 127.0.0.1 on every keystroke for users who don't use LM Studio.

**Used at:**
- `tests/xavani_cli/test_prompt_api_key.py:145`
- `tests/xavani_cli/test_prompt_api_key.py:161`
- `xavani_cli/commands.py:1112`
- `xavani_cli/commands.py:1127`
- `xavani_cli/model_switch.py:1144`
- `xavani_cli/model_switch.py:1156`
- `xavani_cli/status.py:355`

## `LM_BASE_URL`

**Purpose:** Gate: don't probe 127.0.0.1 on every keystroke for users who don't use LM Studio.

**Used at:**
- `xavani_cli/commands.py:1112`
- `xavani_cli/commands.py:1128`
- `xavani_cli/model_switch.py:1144`
- `xavani_cli/model_switch.py:1150`
- `xavani_cli/status.py:353`

## `LOCALAPPDATA`

**Purpose:** MinGit:      %LOCALAPPDATA%\xavani\git\usr\bin\bash.exe (legacy/32-bit fallback)

**Used at:**
- `tools/browser_tool.py:3524`
- `tools/environments/local.py:251`
- `xavani_cli/browser_connect.py:76`
- `xavani_cli/plugins_cmd.py:51`
- `xavani_cli/stdio.py:225`

## `LOGNAME`

**Used at:**
- `xavani_cli/auth.py:3023`
- `xavani_cli/gateway.py:1802`
- `xavani_cli/gateway.py:1832`
- `xavani_cli/gateway.py:1898`
- `xavani_cli/gateway_windows.py:277`

## `MATRIX_ACCESS_TOKEN`

**Purpose:** Matrix

**Used at:**
- `gateway/config.py:1443`
- `gateway/platforms/matrix.py:241`
- `gateway/platforms/matrix.py:340`
- `tools/send_message_tool.py:1617`
- `xavani_cli/setup.py:2229`

## `MATRIX_ALLOWED_ROOMS`

**Used at:**
- `gateway/config.py:1189`
- `gateway/config.py:1192`
- `gateway/platforms/matrix.py:407`
- `tests/gateway/test_allowed_channels_widening.py:372`

## `MATRIX_ALLOWED_USERS`

**Used at:**
- `gateway/platforms/matrix.py:463`

## `MATRIX_AUTO_THREAD`

**Defaults:** true

**Used at:**
- `gateway/config.py:1193`
- `gateway/config.py:1194`
- `gateway/platforms/matrix.py:416`
- `tests/gateway/test_matrix_mention.py:767`
- `tests/gateway/test_matrix_mention.py:777`

## `MATRIX_DEVICE_ID`

**Used at:**
- `gateway/config.py:1462`

## `MATRIX_DM_MENTION_THREADS`

**Used at:**
- `gateway/config.py:1195`
- `gateway/config.py:1196`
- `tests/gateway/test_matrix_mention.py:802`

## `MATRIX_ENCRYPTION`

**Purpose:** rather than silently degrading to plaintext-only at connect time.

**Used at:**
- `gateway/config.py:1460`
- `gateway/platforms/matrix.py:282`
- `gateway/platforms/matrix.py:349`
- `xavani_cli/gateway.py:3811`

## `MATRIX_FREE_RESPONSE_ROOMS`

**Used at:**
- `gateway/config.py:1183`
- `gateway/config.py:1186`
- `gateway/platforms/matrix.py:395`
- `tests/gateway/test_matrix_mention.py:763`
- `tests/gateway/test_matrix_mention.py:774`

## `MATRIX_HOMESERVER`

**Used at:**
- `gateway/config.py:1444`
- `gateway/platforms/matrix.py:243`
- `gateway/platforms/matrix.py:338`
- `tools/send_message_tool.py:1616`
- `xavani_cli/gateway.py:3808`

## `MATRIX_HOME_ROOM`

**Used at:**
- `gateway/config.py:1465`

## `MATRIX_HOME_ROOM_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1470`

## `MATRIX_HOME_ROOM_THREAD_ID`

**Used at:**
- `gateway/config.py:1471`

## `MATRIX_PASSWORD`

**Used at:**
- `gateway/config.py:1445`
- `gateway/config.py:1457`
- `gateway/platforms/matrix.py:242`
- `xavani_cli/gateway.py:3809`
- `xavani_cli/setup.py:2229`
- `xavani_cli/setup.py:2261`

## `MATRIX_RECOVERY_KEY`

**Purpose:** to share Megolm sessions with the rotated device.

**Used at:**
- `gateway/platforms/matrix.py:811`
- `tests/e2e/matrix_xsign_bootstrap/test_bootstrap.py:208`
- `tests/e2e/matrix_xsign_bootstrap/test_bootstrap.py:322`

## `MATRIX_REQUIRE_MENTION`

**Used at:**
- `gateway/config.py:1180`
- `gateway/config.py:1181`
- `tests/gateway/test_matrix_mention.py:772`
- `tests/gateway/test_matrix_mention.py:812`
- `tests/gateway/test_matrix_mention.py:817`

## `MATRIX_USER_ID`

**Used at:**
- `gateway/config.py:1454`

## `MATTERMOST_ALLOWED_CHANNELS`

**Used at:**
- `gateway/config.py:1172`
- `gateway/config.py:1175`
- `gateway/platforms/mattermost.py:749`
- `tests/gateway/test_allowed_channels_widening.py:311`

## `MATTERMOST_FREE_RESPONSE_CHANNELS`

**Used at:**
- `gateway/config.py:1166`
- `gateway/config.py:1169`
- `gateway/platforms/mattermost.py:767`

## `MATTERMOST_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1433`

## `MATTERMOST_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1438`

## `MATTERMOST_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1439`

## `MATTERMOST_REPLY_MODE`

**Defaults:** off

**Used at:**
- `gateway/platforms/mattermost.py:105`

## `MATTERMOST_REQUIRE_MENTION`

**Used at:**
- `gateway/config.py:1163`
- `gateway/config.py:1164`

## `MATTERMOST_TOKEN`

**Purpose:** Mattermost

**Used at:**
- `gateway/config.py:1423`
- `gateway/platforms/mattermost.py:64`
- `gateway/platforms/mattermost.py:90`
- `tools/send_message_tool.py:1589`
- `xavani_cli/setup.py:2315`

## `MATTERMOST_URL`

**Used at:**
- `gateway/config.py:1425`
- `gateway/platforms/mattermost.py:65`
- `gateway/platforms/mattermost.py:88`
- `tools/send_message_tool.py:1588`

## `MEM0_AGENT_ID`

**Used at:**
- `plugins/memory/mem0/__init__.py:61`

## `MEM0_API_KEY`

**Used at:**
- `plugins/memory/mem0/__init__.py:59`

## `MEM0_USER_ID`

**Used at:**
- `plugins/memory/mem0/__init__.py:60`

## `MESSAGING_CWD`

**Used at:**
- `gateway/run.py:797`
- `xavani_cli/config.py:3562`

## `MIGRATION_JSON_OUTPUT`

**Purpose:** Also dump JSON for programmatic use

**Used at:**
- `oag_skills/migration/openclaw-migration/scripts/openclaw_to_xavani.py:3144`
- `optional-skills/migration/openclaw-migration/scripts/openclaw_to_xavani.py:3144`

## `MINIMAX_API_KEY`

**Used at:**
- `tools/tts_tool.py:992`
- `tools/tts_tool.py:1937`
- `tools/tts_tool.py:2256`
- `xavani_cli/setup.py:496`
- `xavani_cli/setup.py:1325`

## `MINIMAX_GROUP_ID`

**Used at:**
- `tools/tts_tool.py:1013`

## `MINIMAX_PORTAL_BASE_URL`

**Used at:**
- `xavani_cli/web_server.py:2082`

## `MISTRAL_API_KEY`

**Used at:**
- `scripts/discord-voice-doctor.py:260`
- `scripts/discord-voice-doctor.py:264`
- `tools/transcription_tools.py:684`
- `tools/tts_tool.py:1112`
- `tools/tts_tool.py:1950`
- `xavani_cli/nous_subscription.py:364`
- `xavani_cli/setup.py:498`
- `xavani_cli/setup.py:1337`

## `MOCK_LSP_SCRIPT`

**Used at:**
- `tests/agent/lsp/_mock_lsp_server.py:63`

## `MODAL_TOKEN_ID`

**Purpose:** Check for Modal authentication

**Used at:**
- `tests/integration/test_modal_terminal.py:74`
- `tools/tool_backend_helpers.py:66`
- `xavani_cli/config.py:5119`
- `xavani_cli/setup.py:1540`
- `xavani_cli/setup.py:1551`
- `xavani_cli/setup.py:1595`

## `MODAL_TOKEN_SECRET`

**Used at:**
- `tools/tool_backend_helpers.py:66`
- `xavani_cli/setup.py:1551`

## `MSGRAPH_WEBHOOK_ACCEPTED_RESOURCES`

**Used at:**
- `gateway/config.py:1575`

## `MSGRAPH_WEBHOOK_CLIENT_STATE`

**Used at:**
- `gateway/config.py:1574`

## `MSGRAPH_WEBHOOK_ENABLED`

**Purpose:** Microsoft Graph webhook platform

**Used at:**
- `gateway/config.py:1568`

## `MSGRAPH_WEBHOOK_PORT`

**Used at:**
- `gateway/config.py:1573`

## `MSGRAPH_WEBHOOK_STORE_PATH`

**Used at:**
- `plugins/teams_pipeline/store.py:35`

## `MSI_ENDPOINT`

**Used at:**
- `agent/azure_identity_adapter.py:387`

## `MY_CUSTOM_UNRELATED_VAR`

**Used at:**
- `tests/xavani_cli/test_web_server.py:73`
- `tests/xavani_cli/test_web_server.py:75`

## `MY_UNICODE_VAR`

**Purpose:** Not a credential suffix — should be left alone

**Used at:**
- `tests/xavani_cli/test_non_ascii_credential.py:82`

## `NOTIFY_SOCKET`

**Used at:**
- `gateway/systemd_notify.py:23`
- `gateway/systemd_notify.py:44`

## `NOTION_API_KEY`

**Used at:**
- `plugins/teams_pipeline/pipeline.py:123`

## `NOUS_INFERENCE_BASE_URL`

**Used at:**
- `agent/auxiliary_client.py:1268`
- `xavani_cli/auth.py:4927`
- `xavani_cli/auth.py:7105`

## `NOUS_PORTAL_BASE_URL`

**Used at:**
- `xavani_cli/auth.py:4580`
- `xavani_cli/auth.py:4922`
- `xavani_cli/auth.py:7100`
- `xavani_cli/web_server.py:1986`

## `NOVITA_API_KEY`

**Used at:**
- `xavani_cli/models.py:1570`

## `NOVITA_BASE_URL`

**Used at:**
- `xavani_cli/models.py:1574`

## `NO_COLOR`

**Used at:**
- `xavani_cli/colors.py:17`
- `xavani_cli/security_advisories.py:272`

## `NO_PROXY`

**Used at:**
- `gateway/platforms/base.py:448`

## `OAG_GATEWAY`

**Used at:**
- `xavani.py:448`

## `OAG_HOME`

**Used at:**
- `oag_cli.py:25`
- `oag_cli.py:137`
- `xavani_cli/oag_commands.py:189`

## `OAUTHLIB_RELAX_TOKEN_SCOPE`

**Purpose:** Accept partial scopes — user may deselect some permissions in the consent screen

**Used at:**
- `oag_skills/productivity/google-workspace/scripts/setup.py:367`
- `plugins/platforms/google_chat/oauth.py:539`
- `skills/productivity/google-workspace/scripts/setup.py:367`

## `OLLAMA_API_KEY`

**Used at:**
- `agent/chat_completion_helpers.py:759`
- `tests/xavani_cli/test_ollama_cloud_auth.py:285`
- `tests/xavani_cli/test_ollama_cloud_auth.py:626`
- `tests/xavani_cli/test_ollama_cloud_auth.py:645`
- `tests/xavani_cli/test_ollama_cloud_auth.py:659`
- `xavani_cli/models.py:3281`
- `xavani_cli/runtime_provider.py:700`

## `OLLAMA_BASE_URL`

**Used at:**
- `xavani_cli/models.py:3283`

## `OPENAI_API_KEY`

**Used at:**
- `agent/auxiliary_client.py:1725`
- `agent/auxiliary_client.py:3285`
- `cli.py:2772`
- `cli.py:2774`
- `mini_swe_runner.py:223`
- `oag_skills/red-teaming/godmode/scripts/auto_jailbreak.py:351`
- `plugins/google_meet/meet_bot.py:463`
- `plugins/image_gen/openai/__init__.py:145`
- ... and 20 more

## `OPENAI_BASE_URL`

**Purpose:** Detect custom endpoint

**Used at:**
- `agent/auxiliary_client.py:1724`
- `agent/auxiliary_client.py:2916`
- `tests/xavani_cli/test_clear_stale_base_url.py:38`
- `tests/xavani_cli/test_clear_stale_base_url.py:50`
- `tests/xavani_cli/test_clear_stale_base_url.py:77`
- `tests/xavani_cli/test_env_loader.py:24`
- `tests/xavani_cli/test_env_loader.py:37`
- `tests/xavani_cli/test_env_loader.py:73`
- ... and 10 more

## `OPENAI_IMAGE_MODEL`

**Used at:**
- `plugins/image_gen/openai/__init__.py:106`
- `plugins/image_gen/openai-codex/__init__.py:114`

## `OPENCORPORATES_API_TOKEN`

**Used at:**
- `oag_skills/research/osint-investigation/scripts/fetch_opencorporates.py:182`
- `optional-skills/research/osint-investigation/scripts/fetch_opencorporates.py:182`

## `OPENROUTER_API_KEY`

**Purpose:** Default to OpenRouter

**Used at:**
- `agent/auxiliary_client.py:1522`
- `agent/auxiliary_client.py:1539`
- `agent/auxiliary_client.py:3966`
- `cli.py:2772`
- `cli.py:2774`
- `mini_swe_runner.py:236`
- `oag_skills/red-teaming/godmode/scripts/auto_jailbreak.py:347`
- `oag_skills/red-teaming/godmode/scripts/auto_jailbreak.py:353`
- ... and 33 more

## `OPENROUTER_BASE_URL`

**Used at:**
- `cli.py:2766`
- `xavani_cli/runtime_provider.py:652`
- `xavani_cli/runtime_provider.py:1141`

## `OPENVIKING_ACCOUNT`

**Used at:**
- `plugins/memory/openviking/__init__.py:104`
- `plugins/memory/openviking/__init__.py:462`

## `OPENVIKING_AGENT`

**Used at:**
- `plugins/memory/openviking/__init__.py:106`
- `plugins/memory/openviking/__init__.py:464`

## `OPENVIKING_API_KEY`

**Used at:**
- `plugins/memory/openviking/__init__.py:461`

## `OPENVIKING_ENDPOINT`

**Used at:**
- `plugins/memory/openviking/__init__.py:422`
- `plugins/memory/openviking/__init__.py:460`

## `OPENVIKING_USER`

**Used at:**
- `plugins/memory/openviking/__init__.py:105`
- `plugins/memory/openviking/__init__.py:463`

## `OSV_ENDPOINT`

**Defaults:** https://api.osv.dev/v1/query

**Used at:**
- `tools/osv_check.py:31`

## `OTHER_VAR`

**Used at:**
- `tests/xavani_cli/test_prompt_api_key.py:120`

## `PARALLEL_API_KEY`

**Used at:**
- `tests/integration/test_web_tools.py:584`
- `xavani_cli/nous_subscription.py:289`
- `xavani_cli/nous_subscription.py:527`
- `xavani_cli/nous_subscription.py:573`

## `PATH`

**Purpose:** Check if the link dir is on PATH

**Used at:**
- `tests/stress/test_subprocess_e2e.py:43`
- `tests/stress/test_subprocess_e2e.py:76`
- `xavani_cli/doctor.py:1051`
- `xavani_cli/gateway.py:2037`
- `xavani_cli/gateway.py:2815`
- `xavani_cli/kanban_db.py:5043`
- `xavani_cli/main.py:1023`
- `xavani_cli/main.py:1036`
- ... and 3 more

## `PATHEXT`

**Used at:**
- `xavani_cli/kanban_db.py:5030`

## `PLAYWRIGHT_BROWSERS_PATH`

**Used at:**
- `tools/browser_tool.py:3516`

## `PREFIX`

**Purpose:** Determine the expected command link directory (mirrors install.sh logic)

**Used at:**
- `agent/skill_utils.py:106`
- `xavani_cli/doctor.py:997`
- `xavani_cli/uninstall.py:153`
- `xavani_constants.py:295`

## `PULSE_SERVER`

**Purpose:** recording/playback works fine. Don't block if PULSE_SERVER is set.

**Used at:**
- `tools/voice_mode.py:124`
- `tools/voice_mode.py:142`
- `tools/voice_mode.py:151`

## `PYTEST_CURRENT_TEST`

**Purpose:** production (no PYTEST_CURRENT_TEST) this is a single dict lookup.

**Used at:**
- `xavani_cli/auth.py:818`
- `xavani_cli/auth.py:883`
- `xavani_cli/auth.py:4011`

## `PYTHONHASHSEED`

**Used at:**
- `tests/conftest.py:1266`

## `PYTHONIOENCODING`

**Used at:**
- `tests/test_xavani_bootstrap.py:64`
- `tests/test_xavani_bootstrap.py:144`
- `tests/tools/test_windows_native_support.py:102`
- `tests/tools/test_windows_native_support.py:150`
- `xavani_bootstrap.py:29`

## `PYTHONPATH`

**Purpose:** branch's modules instead of the installed package.

**Used at:**
- `tests/agent/lsp/test_client_e2e.py:28`
- `xavani_cli/codex_runtime_plugin_migration.py:598`
- `xavani_cli/gateway_windows.py:395`

## `PYTHONUTF8`

**Purpose:** Module-level apply_windows_utf8_bootstrap() ran during import.

**Used at:**
- `tests/test_xavani_bootstrap.py:63`
- `tests/test_xavani_bootstrap.py:133`
- `tests/tools/test_windows_native_support.py:103`
- `xavani_bootstrap.py:27`

## `ProgramFiles`

**Used at:**
- `tools/environments/local.py:266`
- `xavani_cli/browser_connect.py:74`
- `xavani_cli/plugins_cmd.py:49`

## `QQBOT_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1795`
- `xavani_cli/setup.py:2538`

## `QQBOT_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1811`

## `QQBOT_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1813`

## `QQ_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1789`

## `QQ_APP_ID`

**Purpose:** QQ (Official Bot API v2)

**Used at:**
- `gateway/config.py:1778`
- `gateway/platforms/qqbot/adapter.py:214`
- `tools/send_message_tool.py:1934`
- `xavani_cli/gateway.py:4533`
- `xavani_cli/setup.py:2537`
- `xavani_cli/tools_config.py:1023`

## `QQ_CLIENT_SECRET`

**Used at:**
- `gateway/config.py:1779`
- `gateway/platforms/qqbot/adapter.py:216`
- `tools/send_message_tool.py:1936`
- `xavani_cli/gateway.py:4534`

## `QQ_GROUP_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1792`

## `QQ_HOME_CHANNEL`

**Purpose:** Back-compat: accept the pre-rename name and log a one-time warning.

**Used at:**
- `gateway/config.py:1799`
- `xavani_cli/setup.py:2538`
- `xavani_cli/status.py:441`

## `QQ_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1814`

## `QQ_PORTAL_HOST`

**Purpose:** or test environments.  Default: q.qq.com (production).

**Defaults:** q.qq.com

**Used at:**
- `gateway/platforms/qqbot/constants.py:23`

## `QQ_STT_API_KEY`

**Purpose:** 2. QQ-specific env vars (set by `xavani setup gateway` / `xavani gateway`)

**Used at:**
- `gateway/platforms/qqbot/adapter.py:2074`

## `QQ_STT_MODEL`

**Defaults:** glm-asr

**Used at:**
- `gateway/platforms/qqbot/adapter.py:2080`

## `REQUESTS_CA_BUNDLE`

**Used at:**
- `xavani_cli/auth.py:3780`

## `RETAINDB_API_KEY`

**Used at:**
- `plugins/memory/retaindb/__init__.py:487`
- `plugins/memory/retaindb/__init__.py:499`

## `RETAINDB_BASE_URL`

**Used at:**
- `plugins/memory/retaindb/__init__.py:500`

## `RETAINDB_PROJECT`

**Purpose:** If unset, the API auto-creates and uses the "default" project — no config required.

**Used at:**
- `plugins/memory/retaindb/__init__.py:504`

## `SEARXNG_URL`

**Used at:**
- `tools/web_tools.py:1397`
- `xavani_cli/nous_subscription.py:291`

## `SEC_USER_AGENT`

**Used at:**
- `oag_skills/research/osint-investigation/scripts/fetch_sec_edgar.py:44`
- `optional-skills/research/osint-investigation/scripts/fetch_sec_edgar.py:44`

## `SENATE_LDA_TOKEN`

**Used at:**
- `oag_skills/research/osint-investigation/scripts/fetch_senate_ld.py:132`
- `optional-skills/research/osint-investigation/scripts/fetch_senate_ld.py:132`

## `SESSION_IDLE_MINUTES`

**Purpose:** Session settings

**Used at:**
- `gateway/config.py:1863`

## `SESSION_RESET_HOUR`

**Used at:**
- `gateway/config.py:1870`

## `SHELL`

**Used at:**
- `tools/environments/local.py:234`

## `SIGNAL_ACCOUNT`

**Used at:**
- `gateway/config.py:1403`
- `gateway/platforms/signal.py:176`
- `xavani_cli/gateway.py:3792`
- `xavani_cli/gateway.py:4643`

## `SIGNAL_ALLOWED_USERS`

**Purpose:** recorded at adapter level (run.py still enforces auth separately).

**Defaults:** *

**Used at:**
- `gateway/platforms/signal.py:218`
- `xavani_cli/gateway.py:4718`

## `SIGNAL_GROUP_ALLOWED_USERS`

**Purpose:** Parse allowlists — group policy is derived from presence of group allowlist

**Used at:**
- `gateway/platforms/signal.py:201`
- `xavani_cli/gateway.py:4733`
- `xavani_cli/gateway.py:4746`

## `SIGNAL_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1413`

## `SIGNAL_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1418`

## `SIGNAL_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1419`

## `SIGNAL_HTTP_URL`

**Purpose:** Signal

**Used at:**
- `gateway/config.py:1402`
- `gateway/platforms/signal.py:176`
- `xavani_cli/gateway.py:4642`

## `SIGNAL_IGNORE_STORIES`

**Defaults:** true

**Used at:**
- `gateway/config.py:1411`

## `SIGNAL_REACTIONS`

**Defaults:** true

**Used at:**
- `gateway/platforms/signal.py:1498`

## `SIGNAL_REQUIRE_MENTION`

**Defaults:** false

**Used at:**
- `gateway/config.py:1133`
- `gateway/config.py:1134`
- `gateway/platforms/signal.py:210`

## `SIMPLEX_HOME_CHANNEL`

**Used at:**
- `plugins/platforms/simplex/adapter.py:609`

## `SIMPLEX_HOME_CHANNEL_NAME`

**Used at:**
- `plugins/platforms/simplex/adapter.py:613`

## `SIMPLEX_WS_URL`

**Defaults:** ws://127.0.0.1:5225

**Used at:**
- `plugins/platforms/simplex/adapter.py:570`
- `plugins/platforms/simplex/adapter.py:582`
- `plugins/platforms/simplex/adapter.py:589`
- `plugins/platforms/simplex/adapter.py:605`
- `plugins/platforms/simplex/adapter.py:646`

## `SLACK_ALLOWED_CHANNELS`

**Purpose:** env var must not be overwritten by config.yaml

**Used at:**
- `gateway/config.py:929`
- `gateway/config.py:932`
- `gateway/platforms/slack.py:3031`
- `tests/gateway/test_slack_mention.py:671`
- `tests/gateway/test_slack_mention.py:693`

## `SLACK_ALLOWED_USERS`

**Purpose:** Authorization — reuse the exec-approval allowlist.

**Used at:**
- `gateway/platforms/slack.py:2408`
- `gateway/platforms/slack.py:2508`

## `SLACK_ALLOW_BOTS`

**Defaults:** none

**Used at:**
- `gateway/config.py:918`
- `gateway/config.py:919`
- `gateway/platforms/slack.py:1790`

## `SLACK_APP_TOKEN`

**Used at:**
- `gateway/platforms/slack.py:524`

## `SLACK_BOT_TOKEN`

**Purpose:** Slack

**Used at:**
- `gateway/config.py:1374`
- `xavani_cli/setup.py:2118`
- `xavani_cli/setup.py:2533`
- `xavani_cli/tools_config.py:1019`

## `SLACK_FREE_RESPONSE_CHANNELS`

**Used at:**
- `gateway/config.py:921`
- `gateway/config.py:924`
- `gateway/platforms/slack.py:3008`
- `tests/gateway/test_slack_mention.py:384`

## `SLACK_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1392`
- `xavani_cli/setup.py:2533`

## `SLACK_HOME_CHANNEL_NAME`

**Used at:**
- `gateway/config.py:1397`

## `SLACK_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1398`

## `SLACK_REACTIONS`

**Defaults:** true

**Used at:**
- `gateway/config.py:925`
- `gateway/config.py:926`
- `gateway/platforms/slack.py:1333`

## `SLACK_REQUIRE_MENTION`

**Defaults:** true

**Used at:**
- `gateway/config.py:914`
- `gateway/config.py:915`
- `gateway/platforms/slack.py:2990`
- `tests/gateway/test_slack_mention.py:383`

## `SLACK_STRICT_MENTION`

**Defaults:** false

**Used at:**
- `gateway/config.py:916`
- `gateway/config.py:917`
- `gateway/platforms/slack.py:3002`
- `tests/gateway/test_slack_mention.py:520`

## `SMS_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1515`

## `SMS_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1520`

## `SMS_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1521`

## `SMS_INSECURE_NO_SIGNATURE`

**Used at:**
- `gateway/platforms/sms.py:108`

## `SMS_WEBHOOK_HOST`

**Used at:**
- `gateway/platforms/sms.py:83`

## `SMS_WEBHOOK_PORT`

**Used at:**
- `gateway/platforms/sms.py:81`

## `SMS_WEBHOOK_URL`

**Used at:**
- `gateway/platforms/sms.py:84`

## `SOME_TOKEN`

**Used at:**
- `tests/xavani_cli/test_send_cmd.py:369`

## `SPOTIFY_CLIENT_ID`

**Used at:**
- `xavani_cli/auth.py:2140`

## `SPOTIFY_REDIRECT_URI`

**Used at:**
- `xavani_cli/auth.py:2163`

## `SQLITE_MAX_ROWS`

**Defaults:** 200

**Used at:**
- `oag_skills/mcp/fastmcp/templates/database_server.py:18`
- `optional-skills/mcp/fastmcp/templates/database_server.py:18`

## `SQLITE_PATH`

**Defaults:** ./app.db

**Used at:**
- `oag_skills/mcp/fastmcp/templates/database_server.py:17`
- `optional-skills/mcp/fastmcp/templates/database_server.py:17`

## `SSH_CLIENT`

**Purpose:** Explicit SSH session → no local display

**Used at:**
- `tools/mcp_oauth.py:148`
- `tools/mcp_oauth.py:418`
- `xavani_cli/auth.py:2920`

## `SSH_TTY`

**Purpose:** Explicit SSH session → no local display

**Used at:**
- `tools/mcp_oauth.py:148`
- `tools/mcp_oauth.py:418`
- `xavani_cli/auth.py:2920`

## `SSL_CERT_FILE`

**Used at:**
- `gateway/run.py:494`
- `gateway/run.py:500`
- `gateway/run.py:517`
- `tests/gateway/test_ssl_certs.py:30`
- `tests/gateway/test_ssl_certs.py:34`
- `tests/gateway/test_ssl_certs.py:43`
- `tests/gateway/test_ssl_certs.py:56`
- `tests/gateway/test_ssl_certs.py:71`
- ... and 2 more

## `STT_GROQ_MODEL`

**Defaults:** whisper-large-v3-turbo

**Used at:**
- `tools/transcription_tools.py:95`

## `STT_MISTRAL_MODEL`

**Defaults:** voxtral-mini-latest

**Used at:**
- `tools/transcription_tools.py:96`

## `STT_OPENAI_BASE_URL`

**Defaults:** https://api.openai.com/v1

**Used at:**
- `tools/transcription_tools.py:102`

## `STT_OPENAI_MODEL`

**Defaults:** whisper-1

**Used at:**
- `tools/transcription_tools.py:94`

## `SUDO_PASSWORD`

**Used at:**
- `tools/terminal_tool.py:869`
- `xavani_cli/setup.py:1466`
- `xavani_cli/status.py:405`

## `SUDO_USER`

**Used at:**
- `xavani_cli/gateway.py:1802`
- `xavani_cli/gateway.py:1832`

## `SUPERMEMORY_API_KEY`

**Used at:**
- `plugins/memory/supermemory/__init__.py:464`
- `plugins/memory/supermemory/__init__.py:495`

## `SUPERMEMORY_CONTAINER_TAG`

**Purpose:** Supports {identity} template for profile-scoped containers.

**Used at:**
- `plugins/memory/supermemory/__init__.py:499`

## `TAVILY_API_KEY`

**Used at:**
- `xavani_cli/nous_subscription.py:290`
- `xavani_cli/nous_subscription.py:528`
- `xavani_cli/nous_subscription.py:574`

## `TEAMS_ALLOWED_USERS`

**Purpose:** Teams user who could message the bot could approve dangerous commands.

**Used at:**
- `plugins/platforms/teams/adapter.py:852`
- `plugins/platforms/teams/adapter.py:1148`

## `TEAMS_ALLOW_ALL_USERS`

**Used at:**
- `plugins/platforms/teams/adapter.py:853`

## `TEAMS_CHANNEL_ID`

**Used at:**
- `plugins/platforms/teams/adapter.py:212`

## `TEAMS_CHAT_ID`

**Used at:**
- `plugins/platforms/teams/adapter.py:213`

## `TEAMS_CLIENT_ID`

**Used at:**
- `plugins/platforms/teams/adapter.py:410`
- `plugins/platforms/teams/adapter.py:432`
- `plugins/platforms/teams/adapter.py:537`
- `plugins/platforms/teams/adapter.py:639`
- `plugins/platforms/teams/adapter.py:1108`

## `TEAMS_CLIENT_SECRET`

**Used at:**
- `plugins/platforms/teams/adapter.py:411`
- `plugins/platforms/teams/adapter.py:433`
- `plugins/platforms/teams/adapter.py:538`
- `plugins/platforms/teams/adapter.py:640`
- `plugins/platforms/teams/adapter.py:1131`

## `TEAMS_DELIVERY_MODE`

**Used at:**
- `plugins/platforms/teams/adapter.py:208`

## `TEAMS_GRAPH_ACCESS_TOKEN`

**Used at:**
- `plugins/platforms/teams/adapter.py:210`

## `TEAMS_HOME_CHANNEL`

**Used at:**
- `plugins/platforms/teams/adapter.py:451`

## `TEAMS_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `plugins/platforms/teams/adapter.py:455`

## `TEAMS_INCOMING_WEBHOOK_URL`

**Used at:**
- `plugins/platforms/teams/adapter.py:209`

## `TEAMS_PORT`

**Used at:**
- `plugins/platforms/teams/adapter.py:442`
- `plugins/platforms/teams/adapter.py:643`

## `TEAMS_SERVICE_URL`

**Used at:**
- `plugins/platforms/teams/adapter.py:448`
- `plugins/platforms/teams/adapter.py:544`

## `TEAMS_TEAM_ID`

**Used at:**
- `plugins/platforms/teams/adapter.py:211`

## `TEAMS_TENANT_ID`

**Used at:**
- `plugins/platforms/teams/adapter.py:412`
- `plugins/platforms/teams/adapter.py:434`
- `plugins/platforms/teams/adapter.py:539`
- `plugins/platforms/teams/adapter.py:641`
- `plugins/platforms/teams/adapter.py:1137`

## `TELEGRAM_ALLOWED_CHATS`

**Used at:**
- `gateway/config.py:1043`
- `gateway/config.py:1046`
- `gateway/platforms/telegram.py:4226`
- `tests/gateway/test_allowed_channels_widening.py:142`
- `tests/gateway/test_allowed_channels_widening.py:160`

## `TELEGRAM_ALLOWED_TOPICS`

**Used at:**
- `gateway/config.py:1048`
- `gateway/config.py:1051`
- `gateway/platforms/telegram.py:4241`

## `TELEGRAM_ALLOWED_USERS`

**Purpose:** Check missing allowlist on existing config

**Used at:**
- `gateway/config.py:1072`
- `gateway/config.py:1075`
- `gateway/platforms/telegram.py:536`
- `xavani_cli/setup.py:1984`

## `TELEGRAM_BOT_TOKEN`

**Purpose:** Telegram

**Used at:**
- `gateway/config.py:1296`
- `tests/xavani_cli/test_env_loader.py:55`
- `xavani_cli/config.py:5187`
- `xavani_cli/setup.py:1979`
- `xavani_cli/setup.py:2525`
- `xavani_cli/tools_config.py:1015`

## `TELEGRAM_CRON_THREAD_ID`

**Used at:**
- `cron/scheduler.py:318`

## `TELEGRAM_EXCLUSIVE_BOT_MENTIONS`

**Defaults:** true

**Used at:**
- `gateway/config.py:1032`
- `gateway/config.py:1033`
- `gateway/platforms/telegram.py:4206`

## `TELEGRAM_FALLBACK_IPS`

**Used at:**
- `gateway/config.py:1310`

## `TELEGRAM_FREE_RESPONSE_CHATS`

**Used at:**
- `gateway/config.py:1037`
- `gateway/config.py:1040`
- `gateway/platforms/telegram.py:4211`

## `TELEGRAM_GROUP_ALLOWED_CHATS`

**Used at:**
- `gateway/config.py:1082`
- `gateway/config.py:1085`

## `TELEGRAM_GROUP_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1077`
- `gateway/config.py:1080`

## `TELEGRAM_GUEST_MODE`

**Defaults:** false

**Used at:**
- `gateway/config.py:1034`
- `gateway/config.py:1035`
- `gateway/platforms/telegram.py:4197`

## `TELEGRAM_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1318`
- `tests/xavani_cli/test_send_cmd.py:370`
- `tests/xavani_cli/test_send_cmd.py:390`

## `TELEGRAM_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1323`

## `TELEGRAM_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1324`

## `TELEGRAM_IGNORED_THREADS`

**Used at:**
- `gateway/config.py:1053`
- `gateway/config.py:1056`
- `gateway/platforms/telegram.py:4249`

## `TELEGRAM_MENTION_PATTERNS`

**Used at:**
- `gateway/config.py:1030`
- `gateway/config.py:1031`
- `gateway/platforms/telegram.py:4271`

## `TELEGRAM_PROXY`

**Used at:**
- `gateway/config.py:1059`
- `gateway/config.py:1060`
- `tests/gateway/test_config.py:610`
- `tests/gateway/test_config.py:628`

## `TELEGRAM_REACTIONS`

**Defaults:** false

**Used at:**
- `gateway/config.py:1057`
- `gateway/config.py:1058`
- `gateway/platforms/telegram.py:5401`
- `tests/gateway/test_telegram_reactions.py:302`
- `tests/gateway/test_telegram_reactions.py:321`

## `TELEGRAM_REPLY_TO_MODE`

**Purpose:** Reply threading mode for Telegram (off/first/all)

**Used at:**
- `gateway/config.py:1068`
- `gateway/config.py:1070`
- `gateway/config.py:1304`
- `tests/gateway/test_telegram_reply_mode.py:266`
- `tests/gateway/test_telegram_reply_mode.py:275`
- `tests/gateway/test_telegram_reply_mode.py:287`
- `tests/gateway/test_telegram_reply_mode.py:297`
- `tests/gateway/test_telegram_reply_mode.py:310`

## `TELEGRAM_REQUIRE_MENTION`

**Defaults:** false

**Used at:**
- `gateway/config.py:1028`
- `gateway/config.py:1029`
- `gateway/platforms/telegram.py:4188`

## `TELEGRAM_WEBHOOK_PORT`

**Purpose:** See GHSA-3vpc-7q5r-276h.

**Defaults:** 8443

**Used at:**
- `gateway/platforms/telegram.py:1496`

## `TELEGRAM_WEBHOOK_SECRET`

**Used at:**
- `gateway/platforms/telegram.py:1497`

## `TELEGRAM_WEBHOOK_URL`

**Purpose:** Decide between webhook and polling mode

**Used at:**
- `gateway/platforms/telegram.py:1482`

## `TENOR_API_KEY`

**Used at:**
- `tests/xavani_cli/test_config.py:256`

## `TERM`

**Used at:**
- `xavani_cli/colors.py:19`
- `xavani_cli/main.py:7879`

## `TERMINAL_CONTAINER_DISK`

**Defaults:** 51200

**Used at:**
- `xavani_cli/doctor.py:1176`

## `TERMINAL_CONTAINER_PERSISTENT`

**Purpose:** Enable persistence for this test

**Defaults:** true

**Used at:**
- `tests/integration/test_daytona_terminal.py:101`
- `tests/integration/test_daytona_terminal.py:113`
- `tools/terminal_tool.py:1099`
- `xavani_cli/doctor.py:1217`
- `xavani_cli/status.py:389`

## `TERMINAL_CWD`

**Purpose:** other dev files — inflating token usage by ~10k for no benefit.

**Used at:**
- `agent/agent_init.py:1435`
- `agent/prompt_builder.py:699`
- `agent/system_prompt.py:238`
- `agent/tool_executor.py:127`
- `agent/tool_executor.py:595`
- `cli.py:2017`
- `cli.py:4710`
- `cli.py:5047`
- ... and 29 more

## `TERMINAL_DAYTONA_IMAGE`

**Defaults:** nikolaik/python-nodejs:python3.11-nodejs20

**Used at:**
- `tools/terminal_tool.py:1074`
- `tools/terminal_tool.py:2310`
- `xavani_cli/status.py:385`

## `TERMINAL_DOCKER_IMAGE`

**Defaults:** python:3.11-slim

**Used at:**
- `tools/terminal_tool.py:1070`
- `tools/terminal_tool.py:2307`
- `xavani_cli/status.py:382`

## `TERMINAL_DOCKER_MOUNT_CWD_TO_WORKSPACE`

**Defaults:** false

**Used at:**
- `tools/terminal_tool.py:1025`

## `TERMINAL_DOCKER_RUN_AS_HOST_USER`

**Defaults:** false

**Used at:**
- `tools/terminal_tool.py:1102`

## `TERMINAL_DOCKER_VOLUMES`

**Used at:**
- `gateway/run.py:1675`

## `TERMINAL_ENV`

**Purpose:** For Modal: skip local check (Modal pulls server-side).

**Defaults:** local

**Used at:**
- `agent/prompt_builder.py:793`
- `batch_runner.py:277`
- `cli.py:5824`
- `gateway/run.py:1667`
- `tests/tools/test_code_execution.py:26`
- `tests/tools/test_code_execution_modes.py:29`
- `tools/credential_files.py:400`
- `tools/skills_tool.py:386`
- ... and 5 more

## `TERMINAL_LIFETIME_SECONDS`

**Defaults:** 300

**Used at:**
- `tools/terminal_tool.py:2315`

## `TERMINAL_LOCAL_PERSISTENT`

**Defaults:** false

**Used at:**
- `tools/terminal_tool.py:1093`

## `TERMINAL_MODAL_IMAGE`

**Used at:**
- `tools/terminal_tool.py:1073`
- `tools/terminal_tool.py:2309`

## `TERMINAL_MODAL_MODE`

**Defaults:** auto

**Used at:**
- `tools/terminal_tool.py:1069`

## `TERMINAL_PERSISTENT_SHELL`

**Defaults:** true

**Used at:**
- `tools/terminal_tool.py:1091`

## `TERMINAL_SANDBOX_DIR`

**Used at:**
- `tools/environments/base.py:96`
- `tools/terminal_tool.py:2313`

## `TERMINAL_SCRATCH_DIR`

**Used at:**
- `tools/environments/singularity.py:81`

## `TERMINAL_SINGULARITY_IMAGE`

**Used at:**
- `tools/terminal_tool.py:1072`
- `tools/terminal_tool.py:2308`

## `TERMINAL_SSH_HOST`

**Purpose:** SSH-specific config

**Defaults:** not set

**Used at:**
- `cli.py:5862`
- `tests/tools/test_file_sync_perf.py:34`
- `tests/tools/test_ssh_environment.py:17`
- `tools/terminal_tool.py:1082`
- `xavani_cli/config.py:5129`
- `xavani_cli/doctor.py:1104`
- `xavani_cli/setup.py:1710`
- `xavani_cli/status.py:377`

## `TERMINAL_SSH_KEY`

**Purpose:** SSH key

**Used at:**
- `tests/tools/test_ssh_environment.py:20`
- `tools/terminal_tool.py:1085`
- `xavani_cli/doctor.py:1108`
- `xavani_cli/setup.py:1728`

## `TERMINAL_SSH_PORT`

**Purpose:** SSH port

**Defaults:** 22

**Used at:**
- `cli.py:5864`
- `tests/tools/test_ssh_environment.py:19`
- `xavani_cli/doctor.py:1107`
- `xavani_cli/setup.py:1722`

## `TERMINAL_SSH_USER`

**Purpose:** SSH user

**Defaults:** not set

**Used at:**
- `cli.py:5863`
- `tests/tools/test_file_sync_perf.py:35`
- `tests/tools/test_ssh_environment.py:18`
- `tools/terminal_tool.py:1083`
- `xavani_cli/config.py:5130`
- `xavani_cli/doctor.py:1106`
- `xavani_cli/setup.py:1716`
- `xavani_cli/status.py:378`

## `TERMINAL_TIMEOUT`

**Defaults:** 180, 60

**Used at:**
- `cli.py:5826`
- `tests/xavani_cli/test_kanban_core_functionality.py:2790`
- `tools/process_registry.py:1018`
- `tools/terminal_tool.py:2314`
- `xavani_cli/kanban_db.py:5453`
- `xavani_cli/kanban_db.py:5455`

## `TERMINAL_VERCEL_RUNTIME`

**Defaults:** node24

**Used at:**
- `tests/cli/test_cli_init.py:482`
- `tests/xavani_cli/test_setup.py:525`
- `tools/terminal_tool.py:1075`
- `xavani_cli/doctor.py:1163`
- `xavani_cli/status.py:388`

## `TERMINAL_X`

**Used at:**
- `tests/tools/test_terminal_config_env_sync.py:123`

## `TERMUX_VERSION`

**Used at:**
- `agent/skill_utils.py:106`
- `xavani_cli/doctor.py:998`
- `xavani_cli/uninstall.py:154`
- `xavani_constants.py:296`

## `TERM_PROGRAM`

**Purpose:** 6. TERM_PROGRAM allow-list (currently empty)

**Used at:**
- `cli.py:1460`

## `TEST_RELOAD_VAR`

**Used at:**
- `tests/xavani_cli/test_web_server.py:40`
- `tests/xavani_cli/test_web_server.py:48`
- `tests/xavani_cli/test_web_server.py:53`

## `TIRITH_BIN`

**Used at:**
- `tools/tirith_security.py:101`

## `TOOL_GATEWAY_DOMAIN`

**Used at:**
- `tools/managed_tool_gateway.py:134`

## `TOOL_GATEWAY_SCHEME`

**Used at:**
- `tools/managed_tool_gateway.py:116`

## `TOOL_GATEWAY_USER_TOKEN`

**Used at:**
- `tools/managed_tool_gateway.py:86`

## `TWILIO_ACCOUNT_SID`

**Purpose:** SMS (Twilio)

**Used at:**
- `gateway/config.py:433`
- `gateway/config.py:1509`
- `gateway/platforms/sms.py:62`
- `tools/send_message_tool.py:1538`

## `TWILIO_AUTH_TOKEN`

**Used at:**
- `gateway/config.py:1514`
- `gateway/platforms/sms.py:62`

## `TWILIO_PHONE_NUMBER`

**Used at:**
- `gateway/platforms/sms.py:79`
- `tools/send_message_tool.py:1539`

## `TZ`

**Used at:**
- `tests/test_timezone.py:180`
- `tests/test_timezone.py:202`

## `USDA_API_KEY`

**Used at:**
- `oag_skills/health/fitness-nutrition/scripts/nutrition_search.py:26`
- `optional-skills/health/fitness-nutrition/scripts/nutrition_search.py:26`

## `USER`

**Defaults:** user, xavani, your-user

**Used at:**
- `plugins/memory/honcho/cli.py:428`
- `tools/environments/singularity.py:92`
- `xavani_cli/auth.py:3023`
- `xavani_cli/gateway.py:1802`
- `xavani_cli/gateway.py:1832`
- `xavani_cli/gateway.py:1898`
- `xavani_cli/gateway_windows.py:277`
- `xavani_cli/kanban_decompose.py:176`
- ... and 3 more

## `USERDOMAIN`

**Used at:**
- `xavani_cli/gateway_windows.py:282`

## `USERNAME`

**Used at:**
- `xavani_cli/gateway_windows.py:277`

## `USERPROFILE`

**Used at:**
- `xavani_cli/gateway_windows.py:178`

## `VERCEL_OIDC_TOKEN`

**Used at:**
- `tools/terminal_tool.py:168`
- `xavani_cli/config.py:5127`

## `VERCEL_PROJECT_ID`

**Used at:**
- `tests/xavani_cli/test_setup.py:528`
- `tests/xavani_cli/test_setup.py:574`
- `tools/terminal_tool.py:170`
- `xavani_cli/config.py:5127`
- `xavani_cli/setup.py:747`

## `VERCEL_TEAM_ID`

**Used at:**
- `tests/xavani_cli/test_setup.py:529`
- `tests/xavani_cli/test_setup.py:575`
- `tools/terminal_tool.py:171`
- `xavani_cli/config.py:5127`
- `xavani_cli/setup.py:751`

## `VERCEL_TOKEN`

**Used at:**
- `tests/xavani_cli/test_setup.py:527`
- `tests/xavani_cli/test_setup.py:573`
- `tools/terminal_tool.py:169`
- `xavani_cli/config.py:5127`
- `xavani_cli/setup.py:744`

## `VIRTUAL_ENV`

**Purpose:** environment IS a venv.  (#8620)

**Used at:**
- `agent/lsp/servers.py:272`
- `tests/tools/test_code_execution_modes.py:335`
- `xavani_cli/gateway.py:1983`

## `VISUAL`

**Purpose:** Find editor

**Used at:**
- `tests/tools/test_windows_native_support.py:138`
- `xavani_cli/config.py:5231`
- `xavani_cli/stdio.py:131`

## `VOICE_TOOLS_OPENAI_KEY`

**Used at:**
- `tools/tool_backend_helpers.py:110`
- `xavani_cli/setup.py:493`
- `xavani_cli/setup.py:1210`
- `xavani_cli/setup.py:1251`

## `WATCHDOG_USEC`

**Used at:**
- `gateway/systemd_notify.py:48`

## `WATCHER_STATE_DIR`

**Used at:**
- `oag_skills/devops/watchers/scripts/_watermark.py:36`
- `optional-skills/devops/watchers/scripts/_watermark.py:36`

## `WAYLAND_DISPLAY`

**Purpose:** Linux/other posix: need DISPLAY or WAYLAND_DISPLAY

**Used at:**
- `tools/mcp_oauth.py:159`
- `xavani_cli/clipboard.py:62`
- `xavani_cli/clipboard.py:318`
- `xavani_cli/web_server.py:4786`

## `WEBHOOK_ENABLED`

**Purpose:** Webhook platform

**Used at:**
- `gateway/config.py:1552`
- `xavani_cli/setup.py:2430`

## `WEBHOOK_PORT`

**Used at:**
- `gateway/config.py:1553`

## `WEBHOOK_SECRET`

**Used at:**
- `gateway/config.py:1554`

## `WEB_TOOLS_DEBUG`

**Used at:**
- `tests/integration/test_web_tools.py:608`

## `WECOM_BOT_ID`

**Purpose:** WeCom (Enterprise WeChat)

**Used at:**
- `gateway/config.py:1672`
- `gateway/platforms/wecom.py:164`
- `xavani_cli/gateway.py:4045`

## `WECOM_CALLBACK_AGENT_ID`

**Used at:**
- `gateway/config.py:1704`

## `WECOM_CALLBACK_CORP_ID`

**Purpose:** WeCom callback mode (self-built apps)

**Used at:**
- `gateway/config.py:1695`

## `WECOM_CALLBACK_CORP_SECRET`

**Used at:**
- `gateway/config.py:1696`

## `WECOM_CALLBACK_ENCODING_AES_KEY`

**Used at:**
- `gateway/config.py:1706`

## `WECOM_CALLBACK_HOST`

**Defaults:** 0.0.0.0

**Used at:**
- `gateway/config.py:1707`

## `WECOM_CALLBACK_PORT`

**Defaults:** 8645

**Used at:**
- `gateway/config.py:1708`

## `WECOM_CALLBACK_TOKEN`

**Used at:**
- `gateway/config.py:1705`

## `WECOM_DM_POLICY`

**Defaults:** open

**Used at:**
- `gateway/platforms/wecom.py:172`

## `WECOM_GROUP_POLICY`

**Defaults:** open

**Used at:**
- `gateway/platforms/wecom.py:175`

## `WECOM_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1685`

## `WECOM_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1690`

## `WECOM_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1691`

## `WECOM_SECRET`

**Used at:**
- `gateway/config.py:1673`
- `gateway/platforms/wecom.py:165`
- `xavani_cli/gateway.py:4046`

## `WECOM_WEBSOCKET_URL`

**Used at:**
- `gateway/config.py:1682`
- `gateway/platforms/wecom.py:169`

## `WEIXIN_ACCOUNT_ID`

**Used at:**
- `gateway/config.py:1713`
- `tools/send_message_tool.py:237`
- `xavani_cli/gateway.py:4233`

## `WEIXIN_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1735`

## `WEIXIN_BASE_URL`

**Used at:**
- `gateway/config.py:1723`
- `tools/send_message_tool.py:245`

## `WEIXIN_CDN_BASE_URL`

**Used at:**
- `gateway/config.py:1726`
- `tools/send_message_tool.py:246`
- `xavani_cli/gateway.py:4282`

## `WEIXIN_DM_POLICY`

**Used at:**
- `gateway/config.py:1729`

## `WEIXIN_GROUP_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1738`

## `WEIXIN_GROUP_POLICY`

**Used at:**
- `gateway/config.py:1732`

## `WEIXIN_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1744`
- `tools/send_message_tool.py:269`

## `WEIXIN_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1749`

## `WEIXIN_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1750`

## `WEIXIN_SPLIT_MULTILINE_MESSAGES`

**Used at:**
- `gateway/config.py:1741`

## `WEIXIN_TOKEN`

**Purpose:** Weixin (personal WeChat via iLink Bot API)

**Used at:**
- `gateway/config.py:1712`
- `tools/send_message_tool.py:236`
- `xavani_cli/gateway.py:3818`
- `xavani_cli/gateway.py:4234`

## `WHATSAPP_ALLOWED_USERS`

**Purpose:** ── Step 3: Allowed users ────────────────────────────────────────────

**Used at:**
- `gateway/config.py:1118`
- `gateway/config.py:1121`
- `xavani_cli/main.py:1612`

## `WHATSAPP_DM_POLICY`

**Defaults:** open

**Used at:**
- `gateway/config.py:1115`
- `gateway/config.py:1116`
- `gateway/platforms/whatsapp.py:272`

## `WHATSAPP_ENABLED`

**Purpose:** WhatsApp (typically uses different auth mechanism)

**Used at:**
- `gateway/config.py:1352`
- `gateway/config.py:1353`
- `xavani_cli/main.py:1608`
- `xavani_cli/main.py:1703`
- `xavani_cli/tools_config.py:1021`

## `WHATSAPP_FREE_RESPONSE_CHATS`

**Used at:**
- `gateway/config.py:1111`
- `gateway/config.py:1114`
- `gateway/platforms/whatsapp.py:320`

## `WHATSAPP_GROUP_ALLOWED_USERS`

**Used at:**
- `gateway/config.py:1125`
- `gateway/config.py:1128`

## `WHATSAPP_GROUP_POLICY`

**Defaults:** open

**Used at:**
- `gateway/config.py:1122`
- `gateway/config.py:1123`
- `gateway/platforms/whatsapp.py:274`

## `WHATSAPP_HOME_CHANNEL`

**Used at:**
- `gateway/config.py:1364`

## `WHATSAPP_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1369`

## `WHATSAPP_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1370`

## `WHATSAPP_MENTION_PATTERNS`

**Used at:**
- `gateway/config.py:1108`
- `gateway/config.py:1109`
- `gateway/platforms/whatsapp.py:375`

## `WHATSAPP_MODE`

**Purpose:** messages are preserved for troubleshooting.

**Defaults:** self-chat

**Used at:**
- `gateway/platforms/whatsapp.py:292`
- `gateway/platforms/whatsapp.py:617`
- `xavani_cli/main.py:1549`

## `WHATSAPP_NPM_INSTALL_TIMEOUT`

**Purpose:** to accommodate slower systems like Unraid NAS

**Used at:**
- `gateway/platforms/whatsapp.py:567`

## `WHATSAPP_REPLY_PREFIX`

**Used at:**
- `gateway/platforms/whatsapp.py:297`

## `WHATSAPP_REQUIRE_MENTION`

**Defaults:** false

**Used at:**
- `gateway/config.py:1106`
- `gateway/config.py:1107`
- `gateway/platforms/whatsapp.py:315`

## `WSL_DISTRO_NAME`

**Used at:**
- `cli.py:2231`

## `WSS_PROXY`

**Used at:**
- `gateway/platforms/qqbot/adapter.py:467`

## `WT_SESSION`

**Used at:**
- `cli.py:2229`

## `XAI_API_KEY`

**Used at:**
- `plugins/video_gen/xai/__init__.py:97`
- `tests/tools/test_transcription_dotenv_fallback.py:242`
- `tools/xai_http.py:79`
- `xavani_cli/setup.py:1268`
- `xavani_cli/tools_config.py:128`
- `xavani_cli/tools_config.py:132`
- `xavani_cli/tools_config.py:954`

## `XAI_BASE_URL`

**Used at:**
- `agent/auxiliary_client.py:1333`
- `plugins/video_gen/xai/__init__.py:100`
- `tools/tts_tool.py:929`
- `tools/xai_http.py:80`
- `xavani_cli/auth.py:3727`
- `xavani_cli/auth.py:6559`

## `XAI_IMAGE_MODEL`

**Used at:**
- `plugins/image_gen/xai/__init__.py:104`

## `XAI_STT_BASE_URL`

**Defaults:** https://api.x.ai/v1

**Used at:**
- `tools/transcription_tools.py:103`
- `tools/transcription_tools.py:739`

## `XAVANI_ACCEPT_HOOKS`

**Used at:**
- `agent/shell_hooks.py:774`
- `xavani_cli/oneshot.py:176`

## `XAVANI_AGENT_NOTIFY_INTERVAL`

**Used at:**
- `gateway/run.py:719`

## `XAVANI_AGENT_TIMEOUT`

**Used at:**
- `gateway/run.py:715`

## `XAVANI_AGENT_TIMEOUT_WARNING`

**Used at:**
- `gateway/run.py:717`
- `tests/gateway/test_gateway_inactivity_timeout.py:248`
- `tests/gateway/test_gateway_inactivity_timeout.py:254`

## `XAVANI_ALLOW_PRIVATE_URLS`

**Purpose:** 1. Env var override (highest priority)

**Used at:**
- `tools/url_safety.py:118`

## `XAVANI_ALLOW_ROOT_GATEWAY`

**Used at:**
- `xavani_cli/gateway.py:3127`

## `XAVANI_API_CALL_STALE_TIMEOUT`

**Used at:**
- `run_agent.py:913`

## `XAVANI_API_KEY`

**Used at:**
- `tui_gateway/server.py:6294`

## `XAVANI_API_TIMEOUT`

**Used at:**
- `agent/chat_completion_helpers.py:1293`
- `run_agent.py:893`
- `tests/agent/test_local_stream_timeout.py:37`
- `tests/agent/test_local_stream_timeout.py:46`
- `tests/agent/test_local_stream_timeout.py:62`
- `tests/agent/test_local_stream_timeout.py:72`

## `XAVANI_APPROVAL_REASON_LOG`

**Used at:**
- `xavani_approval_reasoning.py:42`

## `XAVANI_AUDIT_LOG`

**Used at:**
- `xavani_operator/audit.py:40`

## `XAVANI_AUTO_CONTINUE_FRESHNESS`

**Used at:**
- `gateway/run.py:330`
- `gateway/run.py:723`

## `XAVANI_BACKGROUND_NOTIFICATIONS`

**Used at:**
- `gateway/run.py:2777`

## `XAVANI_BASE_URL`

**Used at:**
- `tui_gateway/server.py:6296`

## `XAVANI_BIN`

**Used at:**
- `xavani_cli/kanban_db.py:5096`

## `XAVANI_BUNDLED_PLUGINS`

**Used at:**
- `xavani_cli/plugins.py:66`

## `XAVANI_BUNDLED_SKILLS`

**Used at:**
- `xavani_constants.py:190`

## `XAVANI_BUNDLES_DIR`

**Used at:**
- `agent/skill_bundles.py:81`

## `XAVANI_CA_BUNDLE`

**Used at:**
- `xavani_cli/auth.py:3778`
- `xavani_cli/auth.py:7224`

## `XAVANI_CHECKPOINT_TIMEOUT`

**Purpose:** Git subprocess timeout (seconds).

**Defaults:** 30

**Used at:**
- `tools/checkpoint_manager.py:151`

## `XAVANI_CODEX_BASE_URL`

**Used at:**
- `xavani_cli/auth.py:3334`
- `xavani_cli/auth.py:6181`
- `xavani_cli/auth.py:6707`
- `xavani_cli/web_server.py:2404`

## `XAVANI_CODEX_REFRESH_TIMEOUT_SECONDS`

**Defaults:** 20

**Used at:**
- `xavani_cli/auth.py:3313`

## `XAVANI_COMPUTER_USE`

**Purpose:** Check for environment variable gate

**Used at:**
- `tools/computer_use_tool.py:38`

## `XAVANI_COMPUTER_USE_BACKEND`

**Used at:**
- `tools/computer_use/tool.py:142`

## `XAVANI_CONTAINER`

**Purpose:** Explicit opt-out

**Used at:**
- `xavani_cli/config.py:456`

## `XAVANI_COPILOT_ACP_ARGS`

**Used at:**
- `agent/copilot_acp_client.py:69`
- `xavani_cli/auth.py:5577`
- `xavani_cli/auth.py:5774`

## `XAVANI_COPILOT_ACP_COMMAND`

**Used at:**
- `agent/copilot_acp_client.py:62`
- `xavani_cli/auth.py:5573`
- `xavani_cli/auth.py:5770`

## `XAVANI_CRON_AUTO_DELIVER_CHAT_ID`

**Used at:**
- `tests/cron/test_scheduler.py:1285`
- `tests/cron/test_scheduler.py:1313`
- `tests/cron/test_scheduler.py:1349`
- `tests/cron/test_scheduler.py:1387`
- `tools/send_message_tool.py:435`

## `XAVANI_CRON_AUTO_DELIVER_PLATFORM`

**Used at:**
- `tests/cron/test_scheduler.py:1284`
- `tests/cron/test_scheduler.py:1312`
- `tests/cron/test_scheduler.py:1348`
- `tests/cron/test_scheduler.py:1386`
- `tools/send_message_tool.py:434`

## `XAVANI_CRON_AUTO_DELIVER_THREAD_ID`

**Used at:**
- `tests/cron/test_scheduler.py:1286`
- `tests/cron/test_scheduler.py:1314`
- `tests/cron/test_scheduler.py:1350`
- `tests/cron/test_scheduler.py:1388`
- `tools/send_message_tool.py:438`

## `XAVANI_CRON_MAX_PARALLEL`

**Used at:**
- `cron/scheduler.py:1844`

## `XAVANI_CRON_SCRIPT_TIMEOUT`

**Used at:**
- `cron/scheduler.py:786`

## `XAVANI_CRON_SESSION`

**Purpose:** scheduler process — every job this process runs is a cron job.

**Used at:**
- `cron/scheduler.py:1338`

## `XAVANI_CRON_TIMEOUT`

**Purpose:** _touch_activity() on every tool call, API call, and stream delta).

**Used at:**
- `cron/scheduler.py:1602`
- `tests/cron/test_cron_inactivity_timeout.py:188`
- `tests/cron/test_cron_inactivity_timeout.py:198`
- `tests/cron/test_cron_inactivity_timeout.py:206`
- `tests/cron/test_cron_inactivity_timeout.py:215`
- `tests/cron/test_cron_profile.py:284`
- `tests/cron/test_cron_profile.py:306`

## `XAVANI_CUA_DRIVER_CMD`

**Used at:**
- `tools/computer_use/cua_backend.py:59`

## `XAVANI_CUA_DRIVER_VERSION`

**Purpose:** ---------------------------------------------------------------------------

**Used at:**
- `tools/computer_use/cua_backend.py:57`

## `XAVANI_DASHBOARD_TUI`

**Used at:**
- `xavani_cli/main.py:10036`

## `XAVANI_DEBUG_INTERRUPT`

**Purpose:** to avoid flooding production gateway logs.

**Used at:**
- `tools/environments/base.py:41`
- `tools/interrupt.py:36`

## `XAVANI_DEV`

**Used at:**
- `xavani_cli/config.py:367`

## `XAVANI_DISABLE_FILE_STATE_GUARD`

**Purpose:** Re-read each call so tests can toggle via monkeypatch.setenv.

**Used at:**
- `tests/tools/test_file_state_registry.py:201`
- `tools/file_state.py:275`

## `XAVANI_DISABLE_LAZY_INSTALLS`

**Used at:**
- `tools/lazy_deps.py:237`

## `XAVANI_DISABLE_TELEMETRY`

**Purpose:** Setup OAG telemetry opt-out before any import that might read it

**Used at:**
- `oag_cli.py:55`
- `oag_cli.py:140`
- `xavani.py:50`

## `XAVANI_DISABLE_WINDOWS_UTF8`

**Used at:**
- `xavani_cli/stdio.py:112`

## `XAVANI_DISCORD_TEXT_BATCH_DELAY_SECONDS`

**Purpose:** Text batching: merge rapid successive messages (Telegram-style)

**Defaults:** 0.6

**Used at:**
- `gateway/platforms/discord.py:573`

## `XAVANI_DISCORD_TEXT_BATCH_SPLIT_DELAY_SECONDS`

**Defaults:** 2.0

**Used at:**
- `gateway/platforms/discord.py:574`

## `XAVANI_DOCKER_BINARY`

**Purpose:** 1. Explicit override via env var (e.g. for Podman on immutable distros)

**Used at:**
- `tools/environments/docker.py:126`

## `XAVANI_ENABLE_PROJECT_PLUGINS`

**Used at:**
- `xavani_cli/web_server.py:4278`

## `XAVANI_EPHEMERAL_SYSTEM_PROMPT`

**Used at:**
- `cli.py:2820`
- `gateway/run.py:2579`

## `XAVANI_EPISODIC_MEMORY`

**Used at:**
- `agent/agent_init.py:1000`

## `XAVANI_EXEC_ASK`

**Purpose:** Enable interactive exec approval for dangerous commands on messaging platforms

**Used at:**
- `gateway/run.py:788`
- `tests/gateway/test_approve_deny_commands.py:397`
- `tests/gateway/test_approve_deny_commands.py:444`
- `tests/gateway/test_approve_deny_commands.py:485`
- `tests/gateway/test_approve_deny_commands.py:527`
- `tests/gateway/test_approve_deny_commands.py:581`
- `tests/gateway/test_approve_deny_commands.py:641`
- `tests/test_tui_gateway_server.py:1507`
- ... and 1 more

## `XAVANI_FEISHU_DEDUP_CACHE_SIZE`

**Used at:**
- `gateway/platforms/feishu.py:1540`

## `XAVANI_FEISHU_MEDIA_BATCH_DELAY_SECONDS`

**Used at:**
- `gateway/platforms/feishu.py:1557`

## `XAVANI_FEISHU_TEXT_BATCH_DELAY_SECONDS`

**Used at:**
- `gateway/platforms/feishu.py:1543`

## `XAVANI_FEISHU_TEXT_BATCH_MAX_CHARS`

**Used at:**
- `gateway/platforms/feishu.py:1554`

## `XAVANI_FEISHU_TEXT_BATCH_MAX_MESSAGES`

**Used at:**
- `gateway/platforms/feishu.py:1550`

## `XAVANI_FEISHU_TEXT_BATCH_SPLIT_DELAY_SECONDS`

**Defaults:** 2.0

**Used at:**
- `gateway/platforms/feishu.py:1546`

## `XAVANI_FILE_MUTATION_VERIFIER`

**Used at:**
- `run_agent.py:1810`

## `XAVANI_FULL_TRACEBACK`

**Used at:**
- `cli.py:132`

## `XAVANI_GATEWAY_ADAPTER_DISCONNECT_TIMEOUT`

**Used at:**
- `gateway/run.py:1868`

## `XAVANI_GATEWAY_BUSY_ACK_ENABLED`

**Purpose:** never actually delivered.

**Used at:**
- `gateway/run.py:731`
- `gateway/run.py:2948`

## `XAVANI_GATEWAY_BUSY_INPUT_MODE`

**Used at:**
- `gateway/run.py:729`
- `gateway/run.py:2724`

## `XAVANI_GATEWAY_DETACHED`

**Used at:**
- `xavani_cli/gateway.py:1252`

## `XAVANI_GATEWAY_EXIT_DIAG`

**Used at:**
- `xavani_cli/gateway.py:3243`

## `XAVANI_GATEWAY_LOCK_DIR`

**Used at:**
- `gateway/status.py:69`

## `XAVANI_GATEWAY_PLATFORM_CONNECT_TIMEOUT`

**Used at:**
- `gateway/run.py:1883`

## `XAVANI_GATEWAY_RUNNING`

**Used at:**
- `xavani_cli/notifications.py:29`

## `XAVANI_GATEWAY_SESSION`

**Used at:**
- `tests/gateway/test_approve_deny_commands.py:396`
- `tests/gateway/test_approve_deny_commands.py:443`
- `tests/gateway/test_approve_deny_commands.py:484`
- `tests/gateway/test_approve_deny_commands.py:526`
- `tests/gateway/test_approve_deny_commands.py:580`
- `tests/test_tui_gateway_server.py:1506`
- `tests/tools/test_approval_heartbeat.py:52`
- `tools/tirith_security.py:47`
- ... and 1 more

## `XAVANI_GIT_BASH_PATH`

**Used at:**
- `tools/environments/local.py:238`

## `XAVANI_GWS_BIN`

**Used at:**
- `oag_skills/productivity/google-workspace/scripts/google_api.py:88`
- `skills/productivity/google-workspace/scripts/google_api.py:88`

## `XAVANI_HOME`

**Purpose:** ---------------------------------------------------------------------------

**Used at:**
- `agent/lsp/install.py:124`
- `gateway/oag_proxy.py:51`
- `gateway/protocol_bridge.py:45`
- `gateway/shutdown_forensics.py:175`
- `mcp_serve.py:72`
- `mcp_serve.py:109`
- `mcp_serve.py:372`
- `oag_cli.py:136`
- ... and 109 more

## `XAVANI_HOME_MODE`

**Used at:**
- `xavani_cli/config.py:437`

## `XAVANI_HONCHO_HOST`

**Used at:**
- `plugins/memory/honcho/client.py:52`

## `XAVANI_HUMAN_DELAY_MAX_MS`

**Defaults:** 2500

**Used at:**
- `gateway/platforms/base.py:3081`

## `XAVANI_HUMAN_DELAY_MIN_MS`

**Defaults:** 800

**Used at:**
- `gateway/platforms/base.py:3077`

## `XAVANI_HUMAN_DELAY_MODE`

**Defaults:** off

**Used at:**
- `gateway/platforms/base.py:3069`

## `XAVANI_IGNORE_RULES`

**Purpose:** AGENTS.md/SOUL.md/.cursorrules and persistent memory are not loaded.

**Used at:**
- `cli.py:2816`
- `tests/xavani_cli/test_ignore_user_config_flags.py:136`
- `tests/xavani_cli/test_ignore_user_config_flags.py:145`
- `tests/xavani_cli/test_ignore_user_config_flags.py:153`
- `tests/xavani_cli/test_ignore_user_config_flags.py:168`
- `tests/xavani_cli/test_ignore_user_config_flags.py:181`
- `tui_gateway/server.py:1936`
- `tui_gateway/server.py:1937`
- ... and 1 more

## `XAVANI_IGNORE_USER_CONFIG`

**Purpose:** config as a fallback so defaults stay sensible).

**Used at:**
- `cli.py:330`
- `tests/xavani_cli/test_ignore_user_config_flags.py:166`
- `tests/xavani_cli/test_ignore_user_config_flags.py:180`
- `tests/xavani_cli/test_ignore_user_config_flags.py:193`
- `xavani_cli/main.py:1457`

## `XAVANI_INFERENCE_MODEL`

**Purpose:** stderr redirect so the message actually reaches the terminal.

**Used at:**
- `tests/test_tui_gateway_server.py:1847`
- `tui_gateway/server.py:787`
- `tui_gateway/server.py:807`
- `tui_gateway/server.py:1149`
- `xavani_cli/oneshot.py:159`
- `xavani_cli/oneshot.py:248`

## `XAVANI_INFERENCE_PROVIDER`

**Purpose:** provider override so chat uses the endpoint the user last saved.

**Used at:**
- `cli.py:2755`
- `gateway/run.py:870`
- `tests/test_tui_gateway_server.py:1743`
- `tests/test_tui_gateway_server.py:1798`
- `tests/xavani_cli/test_env_loader.py:93`
- `tui_gateway/server.py:822`
- `tui_gateway/server.py:1161`
- `xavani_cli/main.py:1851`
- ... and 2 more

## `XAVANI_INTERACTIVE`

**Purpose:** and the non-interactive auto-approve path must not fire.

**Used at:**
- `acp_adapter/server.py:1455`
- `acp_adapter/server.py:1456`
- `acp_adapter/server.py:1480`
- `cli.py:14409`
- `oag_cli.py:368`
- `tests/test_tui_gateway_server.py:1508`
- `tests/tools/test_command_guards.py:92`
- `tests/tools/test_command_guards.py:120`
- ... and 12 more

## `XAVANI_KANBAN_BOARD`

**Purpose:** relies on the env var.

**Used at:**
- `gateway/run.py:5316`
- `gateway/run.py:5318`
- `gateway/run.py:5364`
- `plugins/kanban/dashboard/plugin_api.py:1390`
- `plugins/kanban/dashboard/plugin_api.py:1392`
- `plugins/kanban/dashboard/plugin_api.py:1405`
- `plugins/kanban/dashboard/plugin_api.py:2002`
- `plugins/kanban/dashboard/plugin_api.py:2004`
- ... and 12 more

## `XAVANI_KANBAN_CLAIM_LOCK`

**Purpose:** never went through the dispatcher path.

**Used at:**
- `tools/kanban_tools.py:589`

## `XAVANI_KANBAN_CLAIM_TTL_SECONDS`

**Used at:**
- `xavani_cli/kanban_db.py:135`

## `XAVANI_KANBAN_DB`

**Used at:**
- `xavani_cli/kanban_db.py:343`

## `XAVANI_KANBAN_DISPATCH_IN_GATEWAY`

**Used at:**
- `gateway/run.py:5041`

## `XAVANI_KANBAN_HOME`

**Used at:**
- `xavani_cli/kanban_db.py:204`

## `XAVANI_KANBAN_RUN_ID`

**Used at:**
- `tools/kanban_tools.py:118`
- `xavani_cli/kanban.py:1820`

## `XAVANI_KANBAN_SPECIFY_MAX_TOKENS`

**Defaults:** 6000

**Used at:**
- `xavani_cli/kanban_specify.py:49`

## `XAVANI_KANBAN_STOP_NUDGE`

**Used at:**
- `agent/kanban_stop.py:31`

## `XAVANI_KANBAN_TASK`

**Purpose:** itself — we must do it on its behalf.

**Used at:**
- `agent/conversation_loop.py:3546`
- `agent/conversation_loop.py:3953`
- `agent/kanban_stop.py:34`
- `agent/kanban_stop.py:88`
- `model_tools.py:308`
- `model_tools.py:345`
- `tests/xavani_cli/test_kanban_notify.py:517`
- `tests/xavani_cli/test_kanban_notify.py:599`
- ... and 11 more

## `XAVANI_KANBAN_WORKSPACE`

**Used at:**
- `tests/stress/_fake_worker.py:23`

## `XAVANI_KANBAN_WORKSPACES_ROOT`

**Used at:**
- `xavani_cli/kanban_db.py:365`

## `XAVANI_LANGUAGE`

**Used at:**
- `agent/i18n.py:208`

## `XAVANI_LIVE_TESTS`

**Used at:**
- `tests/run_agent/test_deepseek_v4_thinking_live.py:25`
- `tests/run_agent/test_sequential_chats_live.py:50`

## `XAVANI_LOCAL_STT_LANGUAGE`

**Used at:**
- `tools/transcription_tools.py:745`

## `XAVANI_MANAGED`

**Used at:**
- `xavani_cli/config.py:217`
- `xavani_cli/config.py:322`

## `XAVANI_MATRIX_TEXT_BATCH_DELAY_SECONDS`

**Defaults:** 0.6

**Used at:**
- `gateway/platforms/matrix.py:448`

## `XAVANI_MATRIX_TEXT_BATCH_SPLIT_DELAY_SECONDS`

**Defaults:** 2.0

**Used at:**
- `gateway/platforms/matrix.py:451`

## `XAVANI_MAX_ITERATIONS`

**Purpose:** Read from env var or use default (same as CLI)

**Defaults:** 90

**Used at:**
- `cli.py:2782`
- `cli.py:2784`
- `gateway/platforms/api_server.py:896`
- `gateway/run.py:594`
- `gateway/run.py:713`
- `gateway/run.py:3619`
- `gateway/run.py:11457`
- `gateway/run.py:16164`
- ... and 2 more

## `XAVANI_MEET_AUTH_STATE`

**Used at:**
- `plugins/google_meet/meet_bot.py:455`

## `XAVANI_MEET_DURATION`

**Used at:**
- `plugins/google_meet/meet_bot.py:457`

## `XAVANI_MEET_GUEST_NAME`

**Used at:**
- `plugins/google_meet/meet_bot.py:456`

## `XAVANI_MEET_HEADED`

**Used at:**
- `plugins/google_meet/meet_bot.py:454`

## `XAVANI_MEET_LOBBY_TIMEOUT`

**Used at:**
- `plugins/google_meet/meet_bot.py:623`

## `XAVANI_MEET_MODE`

**Purpose:** v2: optional realtime mode. Enabled when XAVANI_MEET_MODE=realtime.

**Used at:**
- `plugins/google_meet/meet_bot.py:459`

## `XAVANI_MEET_OUT_DIR`

**Used at:**
- `plugins/google_meet/meet_bot.py:453`

## `XAVANI_MEET_REALTIME_INSTRUCTIONS`

**Used at:**
- `plugins/google_meet/meet_bot.py:462`

## `XAVANI_MEET_REALTIME_KEY`

**Used at:**
- `plugins/google_meet/meet_bot.py:463`

## `XAVANI_MEET_REALTIME_MODEL`

**Used at:**
- `plugins/google_meet/meet_bot.py:460`

## `XAVANI_MEET_REALTIME_VOICE`

**Used at:**
- `plugins/google_meet/meet_bot.py:461`

## `XAVANI_MEET_URL`

**Used at:**
- `plugins/google_meet/meet_bot.py:452`

## `XAVANI_MODEL`

**Used at:**
- `cron/scheduler.py:1422`
- `tests/test_tui_gateway_server.py:1846`
- `tui_gateway/server.py:786`
- `tui_gateway/server.py:806`
- `tui_gateway/server.py:1148`

## `XAVANI_NODE`

**Used at:**
- `xavani_cli/main.py:1053`

## `XAVANI_NOUS_MIN_KEY_TTL_SECONDS`

**Defaults:** 1800

**Used at:**
- `agent/auxiliary_client.py:1287`
- `agent/auxiliary_client.py:2685`
- `run_agent.py:2673`
- `xavani_cli/runtime_provider.py:982`
- `xavani_cli/runtime_provider.py:1176`
- `xavani_cli/runtime_provider.py:1198`

## `XAVANI_NOUS_TIMEOUT_SECONDS`

**Defaults:** 15

**Used at:**
- `agent/auxiliary_client.py:1288`
- `agent/auxiliary_client.py:2686`
- `run_agent.py:2674`
- `xavani_cli/runtime_provider.py:983`
- `xavani_cli/runtime_provider.py:1199`

## `XAVANI_OAUTH_TRACE`

**Used at:**
- `xavani_cli/auth.py:793`

## `XAVANI_OPENROUTER_CACHE`

**Purpose:** Determine cache enabled: env var overrides config.

**Used at:**
- `agent/auxiliary_client.py:357`

## `XAVANI_OPENROUTER_CACHE_TTL`

**Purpose:** Determine TTL: env var overrides config.

**Used at:**
- `agent/auxiliary_client.py:369`

## `XAVANI_OPTIONAL_SKILLS`

**Used at:**
- `xavani_constants.py:170`

## `XAVANI_OSINT_CACHE`

**Used at:**
- `oag_skills/research/osint-investigation/scripts/fetch_icij_offshore.py:53`
- `optional-skills/research/osint-investigation/scripts/fetch_icij_offshore.py:53`

## `XAVANI_OSINT_UA`

**Used at:**
- `oag_skills/research/osint-investigation/scripts/_http.py:45`
- `optional-skills/research/osint-investigation/scripts/_http.py:45`

## `XAVANI_PERF_LOG`

**Used at:**
- `scripts/profile-tui.py:56`

## `XAVANI_PERF_NODE`

**Purpose:** Stored on args as `extra_flags` list.

**Used at:**
- `scripts/profile-tui.py:438`

## `XAVANI_PLATFORM`

**Used at:**
- `agent/prompt_builder.py:1053`
- `agent/skill_commands.py:55`
- `agent/skill_commands.py:59`
- `agent/skill_utils.py:191`
- `tests/agent/test_skill_commands.py:171`
- `tests/agent/test_skill_commands.py:233`
- `tests/agent/test_skill_commands.py:288`
- `tools/skills_tool.py:550`

## `XAVANI_PLUGINS_DEBUG`

**Purpose:** mid-process can call ``_install_plugin_debug_handler(force=True)``.

**Used at:**
- `xavani_cli/plugins.py:98`
- `xavani_cli/plugins.py:112`

## `XAVANI_PORTAL_BASE_URL`

**Used at:**
- `xavani_cli/auth.py:4579`
- `xavani_cli/auth.py:4921`
- `xavani_cli/auth.py:7099`
- `xavani_cli/web_server.py:1985`

## `XAVANI_PREFILL_MESSAGES_FILE`

**Used at:**
- `cron/scheduler.py:1458`
- `gateway/run.py:2542`

## `XAVANI_PROFILE`

**Purpose:** comments are the deliberate handoff channel between tasks.

**Used at:**
- `tools/kanban_tools.py:632`
- `tools/kanban_tools.py:715`
- `xavani_cli/kanban_decompose.py:175`
- `xavani_cli/kanban_specify.py:143`

## `XAVANI_PROFILE_TEST_ONLY`

**Used at:**
- `tests/cron/test_cron_profile.py:283`

## `XAVANI_PROFILE_TEST_SHARED`

**Used at:**
- `tests/cron/test_cron_profile.py:282`
- `tests/cron/test_cron_profile.py:304`

## `XAVANI_PROMETHEUS_PORT`

**Purpose:** Env var takes precedence

**Used at:**
- `xavani_observability/prometheus.py:107`

## `XAVANI_PYTHON_SRC_ROOT`

**Purpose:** subprocess; inserting it first ensures the installed packages win.

**Used at:**
- `tests/tui_gateway/test_entry_sys_path.py:29`
- `tests/tui_gateway/test_entry_sys_path.py:65`
- `tests/tui_gateway/test_entry_sys_path.py:83`
- `tests/tui_gateway/test_entry_sys_path.py:99`
- `tui_gateway/entry.py:11`

## `XAVANI_QUIET`

**Purpose:** Suppress startup messages for clean CLI experience

**Used at:**
- `cli.py:57`
- `gateway/run.py:785`
- `xavani_cli/main.py:1098`

## `XAVANI_QWEN_BASE_URL`

**Used at:**
- `xavani_cli/auth.py:2007`

## `XAVANI_REDACT_SECRETS`

**Purpose:** downgrade — see `_log_redaction_status()` in gateway/run.py and cli.py.

**Defaults:** true

**Used at:**
- `agent/redact.py:76`
- `cli.py:651`
- `cli.py:11994`
- `gateway/run.py:741`
- `gateway/run.py:3633`
- `tests/xavani_cli/test_debug.py:352`
- `tests/xavani_cli/test_redact_config_bridge.py:56`
- `tests/xavani_cli/test_redact_config_bridge.py:142`
- ... and 2 more

## `XAVANI_RESTART_DRAIN_TIMEOUT`

**Used at:**
- `gateway/run.py:721`
- `gateway/run.py:2744`
- `xavani_cli/gateway.py:2444`

## `XAVANI_REVISION`

**Used at:**
- `xavani_cli/banner.py:242`

## `XAVANI_RPC_DIR`

**Used at:**
- `tests/tools/test_code_execution.py:128`
- `tools/code_execution_tool.py:385`

## `XAVANI_RUNAWAY_MAX_REPEATS`

**Used at:**
- `agent/conversation_loop.py:307`

## `XAVANI_SESSION_CHAT_ID`

**Used at:**
- `tests/cron/test_cron_script.py:547`
- `tests/cron/test_scheduler.py:2278`
- `tests/gateway/test_session_env.py:62`
- `tests/gateway/test_session_env.py:106`
- `tests/gateway/test_session_env.py:154`
- `tests/gateway/test_session_env.py:291`
- `tools/cronjob_tools.py:155`
- `tools/yuanbao_tools.py:240`
- ... and 1 more

## `XAVANI_SESSION_CHAT_NAME`

**Used at:**
- `tests/cron/test_cron_script.py:548`
- `tests/gateway/test_session_env.py:63`
- `tests/gateway/test_session_env.py:107`
- `tests/gateway/test_session_env.py:155`
- `tools/cronjob_tools.py:166`

## `XAVANI_SESSION_EXPIRE_DAYS`

**Used at:**
- `xavani_state.py:3236`

## `XAVANI_SESSION_ID`

**Purpose:** never leaks one session's id into the next session's tools.

**Used at:**
- `acp_adapter/server.py:1462`
- `acp_adapter/server.py:1463`
- `acp_adapter/server.py:1485`
- `agent/agent_init.py:917`
- `agent/conversation_compression.py:380`
- `tests/acp/test_server.py:1117`
- `tests/acp/test_server.py:1136`
- `tests/acp/test_server.py:1155`
- ... and 6 more

## `XAVANI_SESSION_KEY`

**Purpose:** (concurrency-safe). Keep os.environ as fallback for CLI/cron.

**Defaults:** default

**Used at:**
- `gateway/run.py:16161`
- `tests/gateway/test_approve_deny_commands.py:398`
- `tests/gateway/test_approve_deny_commands.py:445`
- `tests/gateway/test_approve_deny_commands.py:486`
- `tests/gateway/test_approve_deny_commands.py:528`
- `tests/gateway/test_approve_deny_commands.py:582`
- `tests/gateway/test_approve_deny_commands.py:642`
- `tests/gateway/test_session_env.py:175`
- ... and 15 more

## `XAVANI_SESSION_PLATFORM`

**Purpose:** Verify env vars were cleaned up by the finally block

**Used at:**
- `agent/prompt_builder.py:1054`
- `agent/skill_commands.py:56`
- `agent/skill_utils.py:192`
- `gateway/session_context.py:36`
- `gateway/session_context.py:40`
- `tests/agent/test_skill_commands.py:234`
- `tests/cron/test_cron_script.py:546`
- `tests/cron/test_scheduler.py:2277`
- ... and 23 more

## `XAVANI_SESSION_SOURCE`

**Used at:**
- `agent/background_review.py:320`
- `agent/conversation_compression.py:391`
- `cli.py:6050`
- `cli.py:6450`
- `run_agent.py:527`
- `xavani_cli/main.py:1467`

## `XAVANI_SESSION_THREAD_ID`

**Used at:**
- `gateway/session_context.py:17`
- `tests/gateway/test_session_env.py:66`
- `tests/gateway/test_session_env.py:70`
- `tests/gateway/test_session_env.py:110`
- `tests/gateway/test_session_env.py:156`
- `tools/cronjob_tools.py:157`

## `XAVANI_SESSION_USER_ID`

**Used at:**
- `tests/gateway/test_session_env.py:64`
- `tests/gateway/test_session_env.py:100`
- `tests/gateway/test_session_env.py:108`
- `tests/gateway/test_session_env.py:292`
- `tools/send_message_tool.py:331`

## `XAVANI_SESSION_USER_NAME`

**Used at:**
- `tests/gateway/test_session_env.py:65`
- `tests/gateway/test_session_env.py:109`

## `XAVANI_SHARED_AUTH_DIR`

**Used at:**
- `xavani_cli/auth.py:3996`

## `XAVANI_SIGTERM_GRACE`

**Defaults:** 1.5

**Used at:**
- `cli.py:14079`
- `cli.py:14544`

## `XAVANI_SKILL_AUDIT`

**Used at:**
- `xavani_skill_audit.py:46`

## `XAVANI_SKIP_CHMOD`

**Purpose:** Explicit opt-out

**Used at:**
- `xavani_cli/config.py:456`

## `XAVANI_SKIP_HOME_CHECK`

**Used at:**
- `xavani_home_check.py:246`

## `XAVANI_SKIP_NODE_BOOTSTRAP`

**Used at:**
- `xavani_cli/main.py:997`

## `XAVANI_SKIP_STATE_INTEGRITY`

**Used at:**
- `xavani_state_integrity.py:156`

## `XAVANI_SPINNER_PAUSE`

**Used at:**
- `agent/display.py:723`
- `tools/approval.py:939`
- `tools/terminal_tool.py:470`

## `XAVANI_SPOTIFY_ACCOUNTS_BASE_URL`

**Used at:**
- `xavani_cli/auth.py:2193`

## `XAVANI_SPOTIFY_API_BASE_URL`

**Used at:**
- `xavani_cli/auth.py:2178`

## `XAVANI_SPOTIFY_CLIENT_ID`

**Used at:**
- `xavani_cli/auth.py:2139`

## `XAVANI_SPOTIFY_REDIRECT_URI`

**Used at:**
- `xavani_cli/auth.py:2162`

## `XAVANI_STREAM_READ_TIMEOUT`

**Used at:**
- `agent/chat_completion_helpers.py:1300`
- `tests/agent/test_local_stream_timeout.py:38`
- `tests/agent/test_local_stream_timeout.py:47`
- `tests/agent/test_local_stream_timeout.py:63`
- `tests/agent/test_local_stream_timeout.py:73`

## `XAVANI_STREAM_RETRIES`

**Used at:**
- `agent/chat_completion_helpers.py:1654`
- `tests/run_agent/test_streaming.py:1146`
- `tests/run_agent/test_streaming.py:1147`
- `tests/run_agent/test_streaming.py:1154`
- `tests/run_agent/test_streaming.py:1204`
- `tests/run_agent/test_streaming.py:1205`
- `tests/run_agent/test_streaming.py:1212`
- `tests/run_agent/test_streaming.py:1292`
- ... and 8 more

## `XAVANI_STREAM_STALE_TIMEOUT`

**Used at:**
- `agent/chat_completion_helpers.py:1915`

## `XAVANI_TELEGRAM_DISABLE_FALLBACK_IPS`

**Used at:**
- `gateway/platforms/telegram.py:1397`

## `XAVANI_TELEGRAM_FOLLOWUP_GRACE_SECONDS`

**Defaults:** 3.0

**Used at:**
- `gateway/run.py:7032`

## `XAVANI_TELEGRAM_MEDIA_BATCH_DELAY_SECONDS`

**Purpose:** as a single MessageEvent instead of self-interrupting multiple turns.

**Defaults:** 0.8

**Used at:**
- `gateway/platforms/telegram.py:409`

## `XAVANI_TELEGRAM_NOTIFICATIONS`

**Purpose:** push notifications.  Supports ENV override for quick testing.

**Used at:**
- `gateway/run.py:5954`

## `XAVANI_TENANT`

**Used at:**
- `tools/kanban_tools.py:665`

## `XAVANI_TERMINAL_SECURITY_MODE`

**Used at:**
- `agent/transports/codex_app_server_session.py:189`

## `XAVANI_TIMEZONE`

**Purpose:** have caused a false "not due" with the old replace(tzinfo=...) approach.

**Used at:**
- `gateway/run.py:735`
- `tests/test_timezone.py:50`
- `tests/test_timezone.py:59`
- `tests/test_timezone.py:65`
- `tests/test_timezone.py:74`
- `tests/test_timezone.py:89`
- `tests/test_timezone.py:99`
- `tests/test_timezone.py:104`
- ... and 17 more

## `XAVANI_TOKEN_BUDGET`

**Used at:**
- `agent/agent_init.py:1458`

## `XAVANI_TOOL_PROGRESS`

**Used at:**
- `xavani_cli/config.py:3632`

## `XAVANI_TOOL_PROGRESS_MODE`

**Used at:**
- `gateway/run.py:15532`
- `xavani_cli/config.py:3633`

## `XAVANI_TUI`

**Used at:**
- `xavani_cli/main.py:1363`

## `XAVANI_TUI_BACKGROUND`

**Purpose:** 3. Explicit bg hex

**Used at:**
- `cli.py:1432`

## `XAVANI_TUI_CHECKPOINTS`

**Used at:**
- `tui_gateway/server.py:1934`

## `XAVANI_TUI_DIR`

**Purpose:** Footgun: --dev against a prebuilt bundle that has no source/node_modules.

**Used at:**
- `scripts/profile-tui.py:53`
- `xavani_cli/main.py:1070`

## `XAVANI_TUI_GATEWAY_NO_FLUSH`

**Purpose:** existing flush-after-write behaviour is unchanged.

**Used at:**
- `tui_gateway/transport.py:67`

## `XAVANI_TUI_GATEWAY_SHUTDOWN_GRACE_S`

**Used at:**
- `tui_gateway/entry.py:59`

## `XAVANI_TUI_MAX_TURNS`

**Used at:**
- `tui_gateway/server.py:1805`

## `XAVANI_TUI_PASS_SESSION_ID`

**Used at:**
- `tui_gateway/server.py:1935`

## `XAVANI_TUI_PROVIDER`

**Purpose:** _resolve_startup_runtime() on /new.

**Used at:**
- `tests/test_tui_gateway_server.py:1797`
- `tests/test_tui_gateway_server.py:1845`
- `tui_gateway/server.py:801`
- `tui_gateway/server.py:1162`

## `XAVANI_TUI_RPC_POOL_WORKERS`

**Used at:**
- `tui_gateway/server.py:170`

## `XAVANI_TUI_SIDECAR_URL`

**Used at:**
- `tui_gateway/entry.py:35`

## `XAVANI_TUI_SKILLS`

**Used at:**
- `tui_gateway/server.py:1815`

## `XAVANI_TUI_SLASH_TIMEOUT_S`

**Used at:**
- `tui_gateway/server.py:139`

## `XAVANI_TUI_THEME`

**Purpose:** 2. Theme hint

**Used at:**
- `cli.py:1423`

## `XAVANI_TUI_TOOLSETS`

**Used at:**
- `tui_gateway/server.py:914`

## `XAVANI_TUI_TOOL_PROGRESS`

**Used at:**
- `tui_gateway/server.py:899`

## `XAVANI_USER_EMAIL`

**Used at:**
- `tools/email_planner.py:440`

## `XAVANI_VISION_DOWNLOAD_TIMEOUT`

**Used at:**
- `tools/vision_tools.py:64`

## `XAVANI_VOICE`

**Purpose:** persisted stale toggle.

**Used at:**
- `tui_gateway/server.py:5675`
- `tui_gateway/server.py:5756`

## `XAVANI_VOICE_DEBUG`

**Used at:**
- `xavani_cli/voice.py:248`

## `XAVANI_VOICE_TTS`

**Purpose:** Runtime-only flag (CLI parity) — see voice.toggle on/off above.

**Used at:**
- `tui_gateway/server.py:5680`
- `tui_gateway/server.py:5784`

## `XAVANI_WECOM_TEXT_BATCH_DELAY_SECONDS`

**Purpose:** WeCom clients split long messages around 4000 chars.

**Defaults:** 0.6

**Used at:**
- `gateway/platforms/wecom.py:190`

## `XAVANI_WECOM_TEXT_BATCH_SPLIT_DELAY_SECONDS`

**Defaults:** 2.0

**Used at:**
- `gateway/platforms/wecom.py:191`

## `XAVANI_WRITE_SAFE_ROOT`

**Used at:**
- `agent/file_safety.py:70`

## `XAVANI_XAI_BASE_URL`

**Used at:**
- `agent/auxiliary_client.py:1332`
- `xavani_cli/auth.py:3726`
- `xavani_cli/auth.py:6558`

## `XAVANI_XAI_REFRESH_TIMEOUT_SECONDS`

**Defaults:** 20

**Used at:**
- `xavani_cli/auth.py:3667`

## `XAVANI_YOLO_MODE`

**Purpose:** we just verify the mechanism exists

**Used at:**
- `cli.py:3465`
- `cli.py:3520`
- `cli.py:9231`
- `cli.py:9239`
- `tests/gateway/test_yolo_command.py:60`
- `tests/gateway/test_yolo_command.py:66`
- `tests/test_tui_gateway_server.py:1328`
- `tests/tools/test_yolo_mode.py:118`
- ... and 11 more

## `XDG_RUNTIME_DIR`

**Used at:**
- `tests/xavani_cli/test_gateway_service.py:1407`
- `tests/xavani_cli/test_gateway_service.py:1429`
- `xavani_cli/gateway.py:1378`
- `xavani_cli/gateway.py:1384`
- `xavani_cli/gateway.py:1411`
- `xavani_cli/gateway.py:1414`

## `XDG_STATE_HOME`

**Used at:**
- `gateway/status.py:72`

## `YUANBAO_API_DOMAIN`

**Used at:**
- `gateway/config.py:1835`

## `YUANBAO_APP_ID`

**Purpose:** Yuanbao — YUANBAO_APP_ID preferred

**Used at:**
- `gateway/config.py:1820`

## `YUANBAO_APP_KEY`

**Purpose:** Yuanbao — YUANBAO_APP_ID preferred

**Used at:**
- `gateway/config.py:1820`

## `YUANBAO_APP_SECRET`

**Used at:**
- `gateway/config.py:1821`

## `YUANBAO_BOT_ID`

**Used at:**
- `gateway/config.py:1829`

## `YUANBAO_DM_ALLOW_FROM`

**Used at:**
- `gateway/config.py:1852`
- `gateway/platforms/yuanbao.py:4588`

## `YUANBAO_DM_POLICY`

**Defaults:** open

**Used at:**
- `gateway/config.py:1849`
- `gateway/platforms/yuanbao.py:4583`

## `YUANBAO_GROUP_ALLOW_FROM`

**Used at:**
- `gateway/config.py:1858`
- `gateway/platforms/yuanbao.py:4599`

## `YUANBAO_GROUP_POLICY`

**Defaults:** open

**Used at:**
- `gateway/config.py:1855`
- `gateway/platforms/yuanbao.py:4594`

## `YUANBAO_HOME_CHANNEL`

**Purpose:** ------------------------------------------------------------------

**Used at:**
- `gateway/config.py:1841`
- `gateway/platforms/yuanbao.py:1590`
- `gateway/platforms/yuanbao.py:1611`
- `gateway/platforms/yuanbao.py:4623`

## `YUANBAO_HOME_CHANNEL_NAME`

**Defaults:** Home

**Used at:**
- `gateway/config.py:1846`

## `YUANBAO_HOME_CHANNEL_THREAD_ID`

**Used at:**
- `gateway/config.py:1847`

## `YUANBAO_ROUTE_ENV`

**Used at:**
- `gateway/config.py:1838`

## `YUANBAO_WS_URL`

**Used at:**
- `gateway/config.py:1832`

## `_XAVANI_GATEWAY`

**Purpose:** where it was already set correctly by gateway/run.py's config bridge.

**Used at:**
- `cli.py:574`
- `gateway/run.py:547`

## `all_proxy`

**Used at:**
- `gateway/platforms/qqbot/adapter.py:472`

## `https_proxy`

**Used at:**
- `gateway/platforms/qqbot/adapter.py:470`

## `no_proxy`

**Used at:**
- `gateway/platforms/base.py:448`

## `wss_proxy`

**Used at:**
- `gateway/platforms/qqbot/adapter.py:468`
