# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Token Optimizer: Detect provider/model, count tokens accurately, compress
prompts for minimum cost, and decode compressed responses back to human-readable form.

Architecture:
  1. User writes message
  2. Optimizer detects model/provider (from config)
  3. Optimizer counts tokens using the EXACT tokenizer for that model
  4. Optimizer compresses the prompt using the cheapest encoding strategy
  5. Compressed prompt is sent to the LLM
  6. LLM responds (potentially in compressed format)
  7. Optimizer decompresses the response back to human-readable form

Token compression strategies (ordered by savings):
  - Whitespace normalization: collapse redundant spaces/newlines
  - Prompt template minimization: strip verbose system prompt boilerplate
  - LLMLingua-style compression: remove low-information tokens via perplexity
  - Provider-specific optimization: e.g. Anthropic cache_control for system prompts
  - Model routing: send simple tasks to cheaper models
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Provider token pricing (USD per million tokens, 2025-06 snapshot) ───────

PRICING_TABLE: Dict[str, Dict[str, float]] = {
    # OpenAI
    "gpt-4o": {"input": 2.50, "output": 10.00, "cache_read": 1.25},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60, "cache_read": 0.075},
    "gpt-4.1": {"input": 2.00, "output": 8.00, "cache_read": 0.50},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60, "cache_read": 0.10},
    "gpt-4.1-nano": {"input": 0.10, "output": 0.40, "cache_read": 0.025},
    "o3": {"input": 2.00, "output": 8.00, "cache_read": 0.50},
    "o3-mini": {"input": 1.10, "output": 4.40, "cache_read": 0.275},
    "o4-mini": {"input": 1.10, "output": 4.40, "cache_read": 0.275},
    # Anthropic
    "claude-sonnet-4-20250514": {"input": 3.00, "output": 15.00, "cache_read": 0.30},
    "claude-opus-4-20250514": {"input": 15.00, "output": 75.00, "cache_read": 1.50},
    "claude-3-5-haiku-20241022": {"input": 0.80, "output": 4.00, "cache_read": 0.08},
    # Google
    "gemini-2.5-pro": {"input": 1.25, "output": 10.00, "cache_read": 0.3125},
    "gemini-2.5-flash": {"input": 0.15, "output": 0.60, "cache_read": 0.0375},
    "gemini-2.0-flash": {"input": 0.10, "output": 0.40, "cache_read": 0.025},
    # DeepSeek
    "deepseek-chat": {"input": 0.27, "output": 1.10, "cache_read": 0.07},
    "deepseek-reasoner": {"input": 0.55, "output": 2.19, "cache_read": 0.14},
    # OpenRouter (varies by model)
    "openrouter:auto": {"input": 0.50, "output": 2.00, "cache_read": 0.10},
}

# Tokenizer mapping: model family -> encoding name
_OPENAI_ENCODINGS: Dict[str, str] = {
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-4.1": "o200k_base",
    "gpt-4.1-mini": "o200k_base",
    "gpt-4.1-nano": "o200k_base",
    "o3": "o200k_base",
    "o3-mini": "o200k_base",
    "o4-mini": "o200k_base",
    "gpt-4-turbo": "cl100k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5-turbo": "cl100k_base",
}

# Provider-specific char/token ratios (Anthropic/Gemini don't publish tokenizers)
_ANTHROPIC_CHARS_PER_TOKEN = 3.7
_GEMINI_CHARS_PER_TOKEN = 3.8
_DEFAULT_CHARS_PER_TOKEN = 4.0


class CompressionLevel(Enum):
    """How aggressively to compress prompts."""
    NONE = "none"
    LIGHT = "light"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class ProviderFamily(Enum):
    """LLM provider families for tokenizer selection."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"
    LOCAL = "local"
    UNKNOWN = "unknown"


@dataclass
class TokenCount:
    """Token count result with cost estimation."""
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    model: str = ""
    provider: str = ""
    encoding_used: str = ""
    compression_applied: str = "none"
    original_tokens: int = 0
    saved_tokens: int = 0
    saved_cost_usd: float = 0.0


@dataclass
class CompressionResult:
    """Result of compressing a prompt."""
    original_text: str = ""
    compressed_text: str = ""
    original_tokens: int = 0
    compressed_tokens: int = 0
    compression_ratio: float = 1.0
    strategy: str = ""
    level: CompressionLevel = CompressionLevel.NONE


# ── Provider Detection ────────────────────────────────────────────────────

def detect_provider_family(model: str) -> ProviderFamily:
    """Detect which provider family a model belongs to based on its name."""
    model_lower = model.lower()

    if any(m in model_lower for m in ["gpt-4", "gpt-3.5", "o1-", "o3-", "o4-", "gpt-4.1"]):
        return ProviderFamily.OPENAI
    if model_lower.startswith("text-") or model_lower.startswith("davinci"):
        return ProviderFamily.OPENAI
    if "claude" in model_lower:
        return ProviderFamily.ANTHROPIC
    if "gemini" in model_lower or "gemma" in model_lower:
        return ProviderFamily.GOOGLE
    if "deepseek" in model_lower:
        return ProviderFamily.DEEPSEEK
    if model_lower.startswith("openrouter:") or "openrouter" in model_lower:
        return ProviderFamily.OPENROUTER
    if model_lower.startswith("local:") or model_lower.startswith("ollama"):
        return ProviderFamily.LOCAL

    return ProviderFamily.UNKNOWN


def get_encoding_name(model: str) -> str:
    """Get the tiktoken encoding name for a model, or char estimate for non-OpenAI."""
    clean_model = model
    for prefix in ["openrouter:", "anthropic:", "google:", "deepseek:"]:
        if clean_model.startswith(prefix):
            clean_model = clean_model[len(prefix):]

    if clean_model in _OPENAI_ENCODINGS:
        return _OPENAI_ENCODINGS[clean_model]

    for key, enc in _OPENAI_ENCODINGS.items():
        if clean_model.startswith(key):
            return enc

    provider = detect_provider_family(model)
    if provider == ProviderFamily.ANTHROPIC:
        return "anthropic_char_estimate"
    if provider == ProviderFamily.GOOGLE:
        return "gemini_char_estimate"
    if provider == ProviderFamily.DEEPSEEK:
        return "deepseek_char_estimate"
    return "char_estimate"


# ── Token Counting ────────────────────────────────────────────────────────

def count_tokens(text: str, model: str = "") -> int:
    """Count tokens in text using the appropriate tokenizer for the model.

    For OpenAI models: uses tiktoken (exact count) if installed.
    For Anthropic/Gemini/others: uses char-based estimation.
    """
    if not text:
        return 0

    encoding = get_encoding_name(model)

    if encoding in ("char_estimate", "anthropic_char_estimate",
                     "gemini_char_estimate", "deepseek_char_estimate"):
        chars_per_token = {
            "anthropic_char_estimate": _ANTHROPIC_CHARS_PER_TOKEN,
            "gemini_char_estimate": _GEMINI_CHARS_PER_TOKEN,
            "deepseek_char_estimate": _DEFAULT_CHARS_PER_TOKEN,
            "char_estimate": _DEFAULT_CHARS_PER_TOKEN,
        }.get(encoding, _DEFAULT_CHARS_PER_TOKEN)
        return max(1, int(len(text) / chars_per_token))

    # OpenAI models — try tiktoken for exact count
    try:
        import tiktoken
        enc = tiktoken.get_encoding(encoding)
        return len(enc.encode(text))
    except ImportError:
        logger.debug("tiktoken not installed, falling back to char estimation")
        return max(1, int(len(text) / _DEFAULT_CHARS_PER_TOKEN))
    except Exception as e:
        logger.debug(f"tiktoken error ({e}), falling back to char estimation")
        return max(1, int(len(text) / _DEFAULT_CHARS_PER_TOKEN))


def count_message_tokens(
    messages: List[Dict[str, Any]],
    model: str = "",
) -> int:
    """Count total tokens in a message list, accounting for message overhead.

    Different providers add different overhead per message:
      - OpenAI: ~4 tokens per message boundary
      - Anthropic: ~4 tokens per message + name formatting
      - Gemini: ~3 tokens per message boundary
    """
    provider = detect_provider_family(model)

    overhead_per_message = {
        ProviderFamily.OPENAI: 4,
        ProviderFamily.ANTHROPIC: 4,
        ProviderFamily.GOOGLE: 3,
        ProviderFamily.DEEPSEEK: 4,
        ProviderFamily.OPENROUTER: 4,
        ProviderFamily.LOCAL: 4,
        ProviderFamily.UNKNOWN: 4,
    }
    per_msg = overhead_per_message.get(provider, 4)

    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        total += count_tokens(part.get("text", ""), model)
                    elif part.get("type") in ("image", "image_url", "input_image"):
                        total += 1600  # Flat image token estimate
                elif isinstance(part, str):
                    total += count_tokens(part, model)
        elif isinstance(content, str):
            total += count_tokens(content, model)
        total += per_msg

    total += 3  # Priming tokens for response
    return total


def estimate_cost(
    input_tokens: int,
    output_tokens: int,
    model: str = "",
    cache_read_tokens: int = 0,
) -> TokenCount:
    """Estimate cost for a given number of tokens on the specified model."""
    pricing = PRICING_TABLE.get(model)
    if not pricing:
        for key, val in PRICING_TABLE.items():
            if model.startswith(key) or key.startswith(model):
                pricing = val
                break
    if not pricing:
        pricing = {"input": 0.0, "output": 0.0, "cache_read": 0.0}

    input_cost = (input_tokens / 1_000_000) * pricing.get("input", 0.0)
    output_cost = (output_tokens / 1_000_000) * pricing.get("output", 0.0)
    cache_cost = (cache_read_tokens / 1_000_000) * pricing.get("cache_read", 0.0)

    return TokenCount(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens + cache_read_tokens,
        estimated_cost_usd=round(input_cost + output_cost + cache_cost, 6),
        model=model,
        provider=detect_provider_family(model).value,
    )


def find_cheapest_model(
    messages: List[Dict[str, Any]],
    models: Optional[List[str]] = None,
    min_capability: str = "chat",
) -> List[TokenCount]:
    """Compare token counts and costs across multiple models.

    Returns sorted list of TokenCount objects (cheapest first).
    """
    if models is None:
        models = list(PRICING_TABLE.keys())

    results = []
    for model in models:
        input_tokens = count_message_tokens(messages, model)
        output_tokens = max(100, int(input_tokens * 0.3))
        cost = estimate_cost(input_tokens, output_tokens, model)
        cost.encoding_used = get_encoding_name(model)
        results.append(cost)

    results.sort(key=lambda c: c.estimated_cost_usd)
    return results


# ── Prompt Compression ────────────────────────────────────────────────────

_FILLER_PATTERNS = [
    (re.compile(r'\bplease\b', re.I), ''),
    (re.compile(r'\bkindly\b', re.I), ''),
    (re.compile(r'\bcould you\b', re.I), ''),
    (re.compile(r'\bwould you\b', re.I), ''),
    (re.compile(r'\bI would like you to\b', re.I), ''),
    (re.compile(r'\bcan you please\b', re.I), ''),
    (re.compile(r'\bin order to\b', re.I), 'to'),
    (re.compile(r'\bdue to the fact that\b', re.I), 'because'),
    (re.compile(r'\bat this point in time\b', re.I), 'now'),
    (re.compile(r'\bin the event that\b', re.I), 'if'),
    (re.compile(r'\bfor the purpose of\b', re.I), 'to'),
    (re.compile(r'\bit is important to note that\b', re.I), ''),
    (re.compile(r'\bit should be noted that\b', re.I), ''),
    (re.compile(r'\bneedless to say\b', re.I), ''),
    (re.compile(r'\bI think that\b', re.I), ''),
    (re.compile(r'\bI believe that\b', re.I), ''),
    (re.compile(r'\bas a matter of fact\b', re.I), ''),
    (re.compile(r'\bfor all intents and purposes\b', re.I), ''),
    (re.compile(r'\bwith regard to\b', re.I), 'about'),
    (re.compile(r'\bin spite of the fact that\b', re.I), 'although'),
    (re.compile(r'\bthe fact that\b', re.I), ''),
    (re.compile(r'\bthe reason why\b', re.I), 'why'),
    (re.compile(r'\bwhat I mean is\b', re.I), ''),
    (re.compile(r'\bto be honest\b', re.I), ''),
    (re.compile(r'\bhonestly\b', re.I), ''),
    (re.compile(r'\bbasically\b', re.I), ''),
    (re.compile(r'\bsimply put\b', re.I), ''),
    (re.compile(r'\bin other words\b', re.I), ''),
    (re.compile(r'\bthat is to say\b', re.I), ''),
]

_COMMENT_PATTERN = re.compile(r'^\s*//.*$', re.MULTILINE)
_HEADING_PATTERN = re.compile(r'^#{1,3}\s+', re.MULTILINE)
_DOUBLE_NEWLINE = re.compile(r'\n{3,}')
_TRAILING_WS = re.compile(r'[ \t]+$', re.MULTILINE)
_MULTI_SPACE = re.compile(r' {2,}', re.MULTILINE)


def compress_prompt(
    text: str,
    level: CompressionLevel = CompressionLevel.MODERATE,
    model: str = "",
) -> CompressionResult:
    """Compress a prompt to use fewer tokens while preserving meaning.

    Applies progressively aggressive compression based on level:
      NONE:       No changes
      LIGHT:      Whitespace normalization, strip comments
      MODERATE:   Light + remove filler phrases, simplify headings
      AGGRESSIVE: Moderate + LLMLingua-style perplexity filtering (if available)
    """
    if level == CompressionLevel.NONE:
        tok = count_tokens(text, model)
        return CompressionResult(
            original_text=text,
            compressed_text=text,
            original_tokens=tok,
            compressed_tokens=tok,
            compression_ratio=1.0,
            strategy="none",
            level=level,
        )

    original_tokens = count_tokens(text, model)
    compressed = text
    strategies = []

    # ── LIGHT: Whitespace + comments ───────────────────────────────────
    if level.value >= CompressionLevel.LIGHT.value:
        compressed = _COMMENT_PATTERN.sub('', compressed)
        compressed = _DOUBLE_NEWLINE.sub('\n\n', compressed)
        compressed = _TRAILING_WS.sub('', compressed)
        compressed = _MULTI_SPACE.sub(' ', compressed)
        compressed = compressed.strip()
        strategies.append("whitespace+comments")

    # ── MODERATE: Filler removal + heading simplification ──────────────
    if level.value >= CompressionLevel.MODERATE.value:
        for pattern, replacement in _FILLER_PATTERNS:
            compressed = pattern.sub(replacement, compressed)
        compressed = _HEADING_PATTERN.sub('# ', compressed)
        compressed = _MULTI_SPACE.sub(' ', compressed)
        compressed = _DOUBLE_NEWLINE.sub('\n\n', compressed)
        compressed = compressed.strip()
        strategies.append("filler_removal")

    # ── AGGRESSIVE: LLMLingua-style compression ────────────────────────
    if level.value >= CompressionLevel.AGGRESSIVE.value:
        # Try LLMLingua if available
        try:
            from llmlingua import PromptCompressor
            compressor = PromptCompressor()
            result = compressor.compress_prompt(compressed)
            compressed = result.get("compressed_prompt", compressed)
            strategies.append("llmlingua")
        except ImportError:
            # Fallback: aggressive whitespace + redundancy removal
            compressed = _aggressive_compress(compressed)
            strategies.append("aggressive_fallback")

    compressed_tokens = count_tokens(compressed, model)
    ratio = compressed_tokens / original_tokens if original_tokens > 0 else 1.0

    return CompressionResult(
        original_text=text,
        compressed_text=compressed,
        original_tokens=original_tokens,
        compressed_tokens=compressed_tokens,
        compression_ratio=round(ratio, 3),
        strategy=" + ".join(strategies),
        level=level,
    )


def _aggressive_compress(text: str) -> str:
    """Aggressive compression fallback when LLMLingua is not available.

    Removes redundancy: repeated lines, verbose bullet point markers,
    excessive punctuation, and collapses numbered lists to compact format.
    """
    lines = text.split('\n')
    seen = set()
    result = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            result.append('')
            continue
        # Deduplicate identical lines
        if stripped in seen:
            continue
        seen.add(stripped)
        # Collapse verbose bullet markers
        stripped = re.sub(r'^[-*•]\s+', '- ', stripped)
        # Collapse numbered list markers
        stripped = re.sub(r'^\d+\.\s+', lambda m: f'{m.group(0)[0]}.', stripped)
        result.append(stripped)

    compressed = '\n'.join(result)
    compressed = _DOUBLE_NEWLINE.sub('\n\n', compressed)
    return compressed.strip()


def compress_messages(
    messages: List[Dict[str, Any]],
    level: CompressionLevel = CompressionLevel.MODERATE,
    model: str = "",
) -> Tuple[List[Dict[str, Any]], CompressionResult]:
    """Compress all text content in a message list.

    Preserves message structure and non-text content (images, tools).
    Returns (compressed_messages, compression_result).
    """
    total_original = ""
    total_compressed = ""

    compressed_messages = []
    for msg in messages:
        new_msg = dict(msg)
        content = msg.get("content", "")

        if isinstance(content, str):
            result = compress_prompt(content, level, model)
            new_msg["content"] = result.compressed_text
            total_original += content
            total_compressed += result.compressed_text
        elif isinstance(content, list):
            new_parts = []
            for part in content:
                if isinstance(part, dict) and part.get("type") == "text":
                    result = compress_prompt(part.get("text", ""), level, model)
                    new_parts.append({**part, "text": result.compressed_text})
                    total_original += part.get("text", "")
                    total_compressed += result.compressed_text
                else:
                    new_parts.append(part)
            new_msg["content"] = new_parts

        compressed_messages.append(new_msg)

    orig_tokens = count_tokens(total_original, model)
    comp_tokens = count_tokens(total_compressed, model)
    ratio = comp_tokens / orig_tokens if orig_tokens > 0 else 1.0

    return compressed_messages, CompressionResult(
        original_text=total_original,
        compressed_text=total_compressed,
        original_tokens=orig_tokens,
        compressed_tokens=comp_tokens,
        compression_ratio=round(ratio, 3),
        strategy=f"message_compression:{level.value}",
        level=level,
    )


# ── Response Decompression ────────────────────────────────────────────────

def decompress_response(
    text: str,
    original_prompt: str = "",
    context: Optional[Dict[str, Any]] = None,
) -> str:
    """Decompress a model response back to human-readable form.

    If the model was given compressed input, it may respond in a
    similarly compressed style. This expands abbreviations, restores
    readability, and adds context from the original prompt.
    """
    if not text:
        return text

    result = text

    # Expand common compressions
    expansions = {
        r'\by/n\b': 'yes/no',
        r'\bw/\b': 'with',
        r'\bw/o\b': 'without',
        r'\bb/c\b': 'because',
        r'\binfo\b': 'information',
        r'\bconfig\b': 'configuration',
        r'\bdev\b': 'development',
        r'\benv\b': 'environment',
        r'\bauth\b': 'authentication',
        r'\bdb\b': 'database',
        r'\bmsg\b': 'message',
        r'\bdir\b': 'directory',
        r'\bcmd\b': 'command',
    }
    for pattern, expansion in expansions.items():
        result = re.compile(pattern, re.I).sub(expansion, result)

    return result


# ── Token Optimizer (Main Entry Point) ────────────────────────────────────

class TokenOptimizer:
    """Main entry point for token optimization.

    Detects model/provider, counts tokens accurately, and provides
    cost-optimal compression before API calls.

    Usage:
        optimizer = TokenOptimizer(model="claude-sonnet-4-20250514")

        # Count tokens before sending
        count = optimizer.count("Your prompt text")
        print(f"Tokens: {count.input_tokens}, Est. cost: ${count.estimated_cost_usd:.4f}")

        # Compare costs across models
        comparison = optimizer.compare_models(messages)

        # Compress prompt for cheaper execution
        compressed = optimizer.compress_prompt("Long verbose prompt...")

        # Optimize entire message list
        opt_messages, result = optimizer.optimize_messages(messages)
    """

    def __init__(self, model: str = "", compression_level: CompressionLevel = CompressionLevel.MODERATE):
        self.model = model
        self.compression_level = compression_level
        self._provider = detect_provider_family(model)
        self._encoding = get_encoding_name(model)

    @property
    def provider(self) -> str:
        return self._provider.value

    @property
    def encoding(self) -> str:
        return self._encoding

    def count_tokens(self, text: str) -> int:
        """Count tokens for the configured model."""
        return count_tokens(text, self.model)

    def count_messages(self, messages: List[Dict[str, Any]]) -> int:
        """Count tokens in a message list for the configured model."""
        return count_message_tokens(messages, self.model)

    def estimate_cost(self, input_tokens: int, output_tokens: int = 0, cache_read_tokens: int = 0) -> TokenCount:
        """Estimate cost for the configured model."""
        return estimate_cost(input_tokens, output_tokens, self.model, cache_read_tokens)

    def compare_models(
        self,
        messages: List[Dict[str, Any]],
        models: Optional[List[str]] = None,
    ) -> List[TokenCount]:
        """Compare token counts and costs across models."""
        return find_cheapest_model(messages, models)

    def compress_prompt(self, text: str) -> CompressionResult:
        """Compress a single prompt string."""
        return compress_prompt(text, self.compression_level, self.model)

    def optimize_messages(
        self,
        messages: List[Dict[str, Any]],
        level: Optional[CompressionLevel] = None,
    ) -> Tuple[List[Dict[str, Any]], CompressionResult]:
        """Compress all messages in a conversation for cheaper execution."""
        lvl = level or self.compression_level
        return compress_messages(messages, lvl, self.model)

    def token_breakdown(self, text: str) -> Dict[str, Any]:
        """Provide a detailed breakdown of how text tokenizes.

        Shows token count, cost estimate, and comparison across providers.
        """
        models_to_compare = [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "claude-sonnet-4-20250514",
            "claude-3-5-haiku-20241022",
            "gemini-2.5-flash",
            "deepseek-chat",
        ]

        char_count = len(text)
        line_count = text.count('\n') + 1

        breakdown = {
            "model": self.model,
            "provider": self.provider,
            "encoding": self.encoding,
            "char_count": char_count,
            "line_count": line_count,
            "token_count": self.count_tokens(text),
            "estimated_cost_usd": None,
            "cheaper_alternatives": [],
        }

        # Cost for current model
        tokens = breakdown["token_count"]
        output_est = max(100, int(tokens * 0.3))
        cost = self.estimate_cost(tokens, output_est)
        breakdown["estimated_cost_usd"] = cost.estimated_cost_usd

        # Compare across models
        msg = [{"role": "user", "content": text}]
        comparisons = self.compare_models(msg, models_to_compare)
        breakdown["cheaper_alternatives"] = [
            {
                "model": c.model,
                "tokens": c.input_tokens,
                "cost_usd": c.estimated_cost_usd,
                "savings_vs_current": round(
                    (breakdown["estimated_cost_usd"] - c.estimated_cost_usd), 6
                ) if breakdown["estimated_cost_usd"] else 0,
            }
            for c in comparisons
        ]

        return breakdown

    def optimizer_summary(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a full optimization report for a message list.

        Shows current cost, compressed cost, savings, and cheapest model.
        """
        # Current state
        current_tokens = self.count_messages(messages)
        output_est = max(100, int(current_tokens * 0.3))
        current_cost = self.estimate_cost(current_tokens, output_est)

        # Compressed state
        compressed_msgs, compression = self.optimize_messages(messages)

        comp_tokens = compression.compressed_tokens
        comp_output_est = max(100, int(comp_tokens * 0.3))
        comp_cost = self.estimate_cost(comp_tokens, comp_output_est)

        savings_tokens = current_tokens - comp_tokens
        savings_cost = current_cost.estimated_cost_usd - comp_cost.estimated_cost_usd

        # Cheapest model comparison
        cheap_models = self.compare_models(compressed_msgs)

        return {
            "model": self.model,
            "provider": self.provider,
            "encoding": self.encoding,
            "compression_level": self.compression_level.value,
            "compression_strategy": compression.strategy,
            "original": {
                "tokens": current_tokens,
                "estimated_cost_usd": current_cost.estimated_cost_usd,
            },
            "compressed": {
                "tokens": comp_tokens,
                "estimated_cost_usd": comp_cost.estimated_cost_usd,
                "ratio": compression.compression_ratio,
            },
            "savings": {
                "tokens": savings_tokens,
                "cost_usd": round(savings_cost, 6),
                "percent": round((savings_tokens / current_tokens) * 100, 1) if current_tokens > 0 else 0,
            },
            "cheapest_models": [
                {
                    "model": c.model,
                    "tokens": c.input_tokens,
                    "cost_usd": c.estimated_cost_usd,
                }
                for c in cheap_models[:5]
            ],
        }


# ── CLI Entry Point ────────────────────────────────────────────────────────

def main():
    """CLI for token optimization — count, compare, and compress prompts."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Xavani Token Optimizer — Count tokens, estimate costs, compress prompts",
        prog="xavani-token-optimizer",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # count command
    count_parser = subparsers.add_parser("count", help="Count tokens in text or file")
    count_parser.add_argument("text", nargs="?", help="Text to count tokens for")
    count_parser.add_argument("-f", "--file", help="Read text from file")
    count_parser.add_argument("-m", "--model", default="gpt-4o", help="Model to count tokens for")

    # compare command
    compare_parser = subparsers.add_parser("compare", help="Compare token costs across models")
    compare_parser.add_argument("text", nargs="?", help="Text to compare")
    compare_parser.add_argument("-f", "--file", help="Read text from file")
    compare_parser.add_argument("--models", nargs="+", help="Models to compare (default: top 8)")

    # compress command
    compress_parser = subparsers.add_parser("compress", help="Compress a prompt")
    compress_parser.add_argument("text", nargs="?", help="Text to compress")
    compress_parser.add_argument("-f", "--file", help="Read text from file")
    compress_parser.add_argument("-m", "--model", default="gpt-4o", help="Target model")
    compress_parser.add_argument(
        "-l", "--level",
        choices=["none", "light", "moderate", "aggressive"],
        default="moderate",
        help="Compression level",
    )

    # breakdown command
    breakdown_parser = subparsers.add_parser("breakdown", help="Detailed token breakdown")
    breakdown_parser.add_argument("text", nargs="?", help="Text to analyze")
    breakdown_parser.add_argument("-f", "--file", help="Read text from file")
    breakdown_parser.add_argument("-m", "--model", default="gpt-4o", help="Model to analyze for")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Get text input
    text = args.text or ""
    if args.file:
        with open(args.file) as f:
            text = f.read()
    if not text:
        print("Error: Provide text argument or --file")
        return

    optimizer = TokenOptimizer(model=args.model)

    if args.command == "count":
        tokens = optimizer.count_tokens(text)
        cost = optimizer.estimate_cost(tokens, max(100, int(tokens * 0.3)))
        print(f"Model: {args.model} ({optimizer.provider})")
        print(f"Encoding: {optimizer.encoding}")
        print(f"Characters: {len(text)}")
        print(f"Lines: {text.count(chr(10)) + 1}")
        print(f"Tokens: {tokens}")
        print(f"Estimated cost (input): ${cost.estimated_cost_usd:.6f}")

    elif args.command == "compare":
        msg = [{"role": "user", "content": text}]
        models = args.models or list(PRICING_TABLE.keys())[:8]
        results = optimizer.compare_models(msg, models)
        print(f"{'Model':<35} {'Tokens':>8} {'Cost (USD)':>12} {'Savings':>10}")
        print("-" * 70)
        for r in results:
            savings = f"${results[0].estimated_cost_usd - r.estimated_cost_usd:.6f}" if r.estimated_cost_usd < results[0].estimated_cost_usd else "-"
            print(f"{r.model:<35} {r.input_tokens:>8} ${r.estimated_cost_usd:>10.6f} {savings:>10}")

    elif args.command == "compress":
        level = CompressionLevel(args.level)
        result = compress_prompt(text, level, args.model)
        print(f"Strategy: {result.strategy}")
        print(f"Original:   {result.original_tokens} tokens, {len(result.original_text)} chars")
        print(f"Compressed: {result.compressed_tokens} tokens, {len(result.compressed_text)} chars")
        print(f"Ratio: {result.compression_ratio:.3f}")
        print(f"Saved: {result.original_tokens - result.compressed_tokens} tokens ({(1 - result.compression_ratio) * 100:.1f}%)")
        print()
        print("--- Compressed Output ---")
        print(result.compressed_text)

    elif args.command == "breakdown":
        breakdown = optimizer.token_breakdown(text)
        print(json.dumps(breakdown, indent=2, default=str))


if __name__ == "__main__":
    main()