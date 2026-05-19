# Token Optimizer — Feature Roadmap

Research from: Andrej Karpathy, Yoav Goldberg, Philipp Schmid, Sebastian Raschka, Lianmin Ding (vLLM), Oriol Vinyals

## Built (v1)

- [x] Multi-provider token counter (tiktoken for OpenAI, char-estimation for Anthropic/Gemini/DeepSeek)
- [x] Cost estimator with 2025-06 pricing table across all major providers
- [x] Prompt compression (4 levels: none, light, moderate, aggressive)
- [x] Model cost comparison (find cheapest model for a prompt)
- [x] Filler phrase removal (30+ patterns)
- [x] Whitespace normalization and comment stripping
- [x] LLMLingua integration (optional, aggressive level)
- [x] Response decompression (expand abbreviations back)
- [x] CLI entry point (count, compare, compress, breakdown)
- [x] TokenOptimizer class for programmatic use
- [x] Detailed token breakdowns across providers

## Next (v2)

- [ ] Intelligent model router — classify prompt complexity, route simple tasks to cheap models
- [ ] System prompt caching — auto-inject Anthropic cache_control, deduplicate system prompts across requests
- [ ] Cascading executor — try cheap model first, validate output, escalate if quality insufficient
- [ ] Budget enforcer — per-user/per-project spending limits with automatic model downgrade
- [ ] Context window manager — smart context pruning with priority tagging (critical/standard/evictable)
- [ ] Adaptive compression — different levels for different sections (aggressive on system prompt, light on user input)

## Future (v3)

- [ ] Thinking budget controller — limit token expenditure per agent step
- [ ] KV cache reuse coordinator — detect shared contexts, route to same serving instance
- [ ] Continuous batching proxy — accumulate requests for batch processing discounts
- [ ] Provider-aware prompt rewriter — rewrite prompts to minimize tokens for specific tokenizers
- [ ] Multi-modal token estimator — costs for images, PDFs, audio inputs
- [ ] PagedAttention client — gateway-level awareness of KV cache page usage

## Research Sources

- Karpathy: nanoGPT, minbpe, "Software 2.0", tokenization deep-dives
- Goldberg: NLP pipeline optimization, structured prediction, LLM probing
- Schmid: HuggingFace Optimum, quantization (bitsandbytes, GPTQ), TGI serving
- Raschka: Build LLM From Scratch, PyTorch Lightning, quality-over-quantity optimizations
- Ding: vLLM, PagedAttention, continuous batching, prefix caching
- Vinyals: Gemini multi-modal tokens, MoE routing, adaptive compute budgets