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

The Blueprint applies with no secret input. `API_SERVER_KEY` is generated.
All other keys are optional. Without them the service runs in research mode.

| Key | Default | Purpose |
|---|---|---|
| `API_SERVER_KEY` | generated | Bearer key for Omera |
| `API_SERVER_KEY_PREVIOUS` | empty | old key during rotation |
| `INFERENCE_BASE_URL` | Gemini OpenAI-compatible | model endpoint when a key exists |
| `INFERENCE_API_KEY` | empty | enables model mode |
| `INFERENCE_MODEL` | `gemini-2.5-flash` | primary model |
| `INFERENCE_FALLBACK_MODELS` | `gemini-2.5-flash-lite` | model fallback |
| `KEYLESS_MODEL` | `off` | `on` tries a no-key model |
| `KEYLESS_MODEL_URL` | Pollinations | keyless endpoint |
| `KEYLESS_MODEL_NAME` | `openai-fast` | keyless model id |
| `TAVILY_API_KEY` | empty | optional search upgrade |
| `EXA_API_KEY` | empty | optional search upgrade |
| `RESEARCH_PROVIDER` | `tavily,exa,ddgs,bing` | search order |
| `JINA_READER` | `auto` | page fallback |
| `RESEARCH_MAX_PAGES` | `1` | pages per answer |
| `RESEARCH_BUDGET_MS` | `6000` | research time budget |

## Modes

- `model`: an inference key exists. Replies come from the model.
- `keyless`: `KEYLESS_MODEL=on`. A no-key endpoint answers. It allows about one
  reply every 30 seconds per IP, so a shared host can hit the limit.
- `research`: no model. The answer is assembled from live sources and cites
  them. This is the default and the fallback.

`/health` reports the current mode. A keyless failure pauses that path for
120 seconds, so the next request answers in about 2 seconds.

## Rotate the service key

1. `API_SERVER_KEY_PREVIOUS` = current key.
2. `API_SERVER_KEY` = new key.
3. Deploy.
4. Update `XAVANI_API_KEY` in the Omera Vercel project.
5. After 24 hours, clear `API_SERVER_KEY_PREVIOUS`.
