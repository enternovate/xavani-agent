---
title: Omera API
sidebar_position: 12
---

# Omera API

Omera is the Xavani service surface. It speaks the OpenAI chat-completions wire format and adds server-side research.

## Authentication

Every request carries a bearer token. Set the token in the gateway environment.

```text
Authorization: Bearer <service key>
```

A missing or wrong key returns HTTP 401 with `{"error": {"message": "Unauthorized.", "type": "authentication_error"}}`.

## Endpoints

### `GET /health`

Returns the liveness payload. This route needs no key.

### `GET /v1/capabilities`

Returns the service contract.

```json
{
  "object": "xavani.api_server.capabilities",
  "model": "omera",
  "auth": {"type": "bearer", "required": true},
  "features": {
    "chat_completions": true,
    "chat_completions_streaming": true,
    "responses_api": false,
    "run_submission": false
  }
}
```

### `POST /v1/chat/completions`

Request fields:

| Field | Type | Notes |
| --- | --- | --- |
| `model` | string | Required. |
| `messages` | array | Required. Max 40 messages. |
| `stream` | bool | Optional. Server-sent events when true. |
| `xavani_research` | bool | Optional. Runs the research chain before the answer. |

Limits: request body 256 KiB. 8,000 characters per message. 32,000 characters in total.

Response:

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "model": "omera",
  "choices": [{"index": 0, "message": {"role": "assistant", "content": "..."}, "finish_reason": "stop"}],
  "xavani": {"completed": true, "partial": false, "failed": false}
}
```

A stream ends with `data: [DONE]`.

## Research mode

Set `xavani_research` to true to search, fetch, and extract pages on the server. The search chain tries the configured providers in order. With no provider keys, the keyless mode still returns answers.

`GET /v1/capabilities` reports the active providers and the page limit.

## Errors

Errors use one shape:

```json
{"error": {"message": "text", "type": "invalid_request_error"}}
```

The service rejects stateful fields. Omera keeps no session, no profile, and no run state between requests.

## Self-hosting

Two files hold the deployment:

- `render.yaml` and `requirements-omera.txt` for the Render service.
- `deploy/vercel-edge/` for the Vercel edge host.

The edge host forwards to the Render service. It answers 401 without the service key.
