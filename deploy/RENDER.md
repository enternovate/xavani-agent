# Xavani Omera on Render (free)

- Service: `xavani-omera`
- Plan: Free. 512 MB RAM, 0.1 CPU, 750 instance-hours per month.
- Runtime: Python 3.12. No Docker.
- Branch: `feat/omera-api-mode`
- Auto-deploy: off. Deploy from the dashboard after approval.
- Status: configuration committed. The Render app is not created yet.

## Deploy

1. Render Dashboard -> `New` -> `Blueprint`.
2. Select the repository and the branch above.
3. Enter the two secret values: `API_SERVER_KEY`, `INFERENCE_API_KEY`.
4. Apply. The first build takes 2 to 4 minutes.

## Inspect

- Dashboard -> `xavani-omera` -> `Logs`.
- `curl -s https://xavani-omera.onrender.com/health`

## Limits

- Sleeps after 15 minutes with no inbound traffic.
- UptimeRobot pings `/health` every 5 minutes. That keeps it awake.
- 750 instance-hours per month. An always-awake month uses 720 to 744.
- Render may restart the service at any time.
- Do not create a second free service on the same workspace.

## Environment

| Key | Value |
|---|---|
| `API_SERVER_KEY` | long random service key |
| `API_SERVER_KEY_PREVIOUS` | old key during rotation, else empty |
| `INFERENCE_BASE_URL` | `https://generativelanguage.googleapis.com/v1beta/openai` |
| `INFERENCE_API_KEY` | Gemini AI Studio key |
| `INFERENCE_MODEL` | `gemini-2.5-flash` |
| `INFERENCE_FALLBACK_MODELS` | `gemini-2.5-flash-lite` |
| `TAVILY_API_KEY` | free Tavily key, 1,000 credits per month |
| `EXA_API_KEY` | free Exa key, $10 monthly credit |
| `RESEARCH_PROVIDER` | `tavily,exa,ddgs` |
| `JINA_READER` | `auto` |
| `RESEARCH_MAX_PAGES` | `2` |
| `RESEARCH_BUDGET_MS` | `6000` |

## Rotate the service key

1. `API_SERVER_KEY_PREVIOUS` = current key.
2. `API_SERVER_KEY` = new key.
3. Deploy.
4. Update `XAVANI_API_KEY` in the Omera Vercel project.
5. After 24 hours, clear `API_SERVER_KEY_PREVIOUS`.
