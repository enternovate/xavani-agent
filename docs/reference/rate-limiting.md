# Rate limiting & 429 backoff

Audit of how the agent detects and reacts to HTTP 429 (Too Many Requests),
rate-limit headers, and credential rotation. Last audited: 2026-08-10
(S3-7 / backlog J229).

## How a 429 flows through the system

1. **Detection** — `agent/error_classifier.py` classifies `status_code == 429`
   as `FailoverReason.rate_limit` (line ~710). Two special cases force a 429:
   Copilot/GitHub Models `RateLimitError` that omits `status_code`, and the
   Anthropic long-context tier gate (429 "extra usage" + "long context").
   Billing-as-400 patterns are also folded into `rate_limit` so they get the
   same backoff treatment.
2. **Retry decision** — the conversation loop (`agent/conversation_loop.py`,
   ~line 2965) computes the wait before the next attempt via
   `agent.retry_utils.rate_limit_backoff_delay(headers, retry_count)`:
   - If the response carries a parseable `Retry-After` header, that delay is
     used, capped at 120 s.
   - Otherwise a jittered exponential backoff is used
     (`jittered_backoff`, base 2.0 s, cap 60 s) — the jitter decorrelates
     concurrent sessions hitting the same provider.
3. **Credential rotation** — yes, on 429. `try_activate_fallback`
   (`agent/chat_completion_helpers.py`) marks the primary provider in cooldown
   (`_rate_limited_until = now + 60s`) before switching to the next fallback
   chain entry. The credential pool path (`run_agent.py` →
   `recover_with_credential_pool`) can rotate same-provider credentials and
   will wait out a `Retry-After` window when a pooled OAuth credential still
   looks usable (CloudCode/Gemini account-level throttles skip this and go
   straight to the configured fallback).

## Retry-After parsing

`agent/retry_utils.parse_retry_after(raw, max_delay=120.0)` accepts both RFC
7231 formats:

- **Delta-seconds**: `Retry-After: 5` → 5.0 s
- **HTTP-date**: `Retry-After: Wed, 21 Oct 2015 07:28:00 GMT` → seconds until
  that instant (assumed UTC when no zone is present)

Malformed, empty, or negative values return `None` so the caller falls back
to the jittered default instead of sleeping forever (huge value) or not at
all (negative). Values are capped at `max_delay` (120 s by default; the
conversation loop previously capped inline at 120 s — unchanged behaviour).

## x-ratelimit-* headers

`agent/rate_limit_tracker.py::parse_rate_limit_headers` parses the
12-header Nous/OpenRouter schema (`x-ratelimit-limit/-remaining/-reset-*`
for requests/tokens per minute and per hour) and `run_agent.py` caches the
result via `_capture_rate_limits` for the `/usage` command. These headers
drive **display only** — the reset-seconds values are not currently used to
compute backoff delays.

## Remaining gaps (not yet addressed)

- `agent/gemini_native_adapter.py` parses `Retry-After` inline (numeric
  seconds only, ~line 748) instead of using `parse_retry_after`; HTTP-date
  responses from Gemini fall back to the fixed path there.
- `x-ratelimit-reset-*` seconds are not consulted when `Retry-After` is
  absent — a provider that only sends reset headers gets the generic jittered
  backoff.
- The gateway Telegram path (`gateway/run.py`, `status_code == 429`) and
  platform adapters (Slack, Discord, Signal) each keep their own retry/backoff
  policies; they predate this central helper and are not wired to it.
