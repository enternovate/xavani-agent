# Provider Quirks Reference

Every row below documents a real provider behavior that xavani-agent works
around in code. The **Source ref** column points at the code comment or
behavior that grounds the row — if a ref stops existing, delete the row
(the guard test `tests/test_provider_quirks_doc.py` enforces this).

| Provider | Quirk | Symptom | Mitigation (in codebase) | Source ref |
|---|---|---|---|---|
| DeepSeek (v4 thinking) | `reasoning_content` must be echoed back on every assistant tool-call message; empty string rejected | HTTP 400 "The reasoning_content in the thinking mode must be passed back to the API" on history replay | `_copy_reasoning_content_for_api` copies streamed reasoning or pads with a single space (refs #15250, #17400, #17341) | agent/chat_completion_helpers.py:570 |
| Kimi / Moonshot | Anthropic-compatible `/coding` endpoint requires assistant tool-call messages to carry `reasoning_content` when thinking is enabled | HTTP 400 on replayed tool-call history | Preserve unsigned thinking blocks synthesised from `reasoning_content` (refs xavani-agent#13848, #17057) | agent/anthropic_adapter.py:1688 |
| Gemini 3 | Thinking signature rides inside tool-call `extra_content.google.thought_signature`, not a top-level field | Signature lost on conversion → multi-turn reasoning continuity breaks | `_tool_call_extra_signature` reads `extra_content` and re-attaches the signature on translate/replay | agent/gemini_native_adapter.py:225 |
| MiniMax (M2.7 via NVIDIA NIM) | Resends the full tool name in every streaming chunk (not just the first) | Naive `+=` concatenation produces `"read_fileread_file"` | Tool name is **assigned** (not appended) from the delta each chunk (OpenAI Node SDK / LiteLLM / Vercel AI pattern) | agent/chat_completion_helpers.py:1480 |
| Ollama (GLM models) | Conservative `finish_reason: "stop"` misreport: response was actually truncated, not naturally complete | Truncated text treated as a complete turn → no retry | `_should_treat_stop_as_truncated` re-classifies stop as length when the visible text lacks a natural sentence ending | run_agent.py:1092 |
| Mistral / Fireworks (strict APIs) | Reject unknown fields on replayed messages | HTTP 400 on `finish_reason`, `call_id`, `response_item_id`, `_thinking_prefill` | Strip Codex Responses fields and finish_reason before send (`_should_sanitize_tool_calls`) | agent/conversation_loop.py:837 |
| OpenAI Codex Responses API | Assistant message items must be replayed verbatim (id/phase) for prefix-cache hits | Flattening items to plain text degrades/breaks prefix caching | Preserve `codex_message_items` on replay instead of flattening (refs OpenAI docs) | agent/chat_completion_helpers.py:631 |
| OpenRouter | Response cache status exposed via `x-openrouter-cache-status` header | No visibility into cache savings | `_check_openrouter_cache_status` reads the header and counts HITs in `_or_cache_hits` | run_agent.py:2066 |
| MiniMax (Anthropic-compatible) | Rejects the `fine-grained-tool-streaming` beta on tool-use requests | Tool-use requests fail with beta present | Beta omitted for MiniMax endpoints (`_is_minimax_anthropic_endpoint`) | agent/anthropic_adapter.py:271 |
| Ollama (num_ctx) | Silently truncates responses when the conversation exceeds the runtime `num_ctx` | Silent truncation, no error | `num_ctx` read from Modelfile parameters (runtime limit) rather than GGUF training max | agent/model_metadata.py:1141 |
