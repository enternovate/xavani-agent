# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Session-level token and cost budget governor.

Monitors cumulative token usage and estimated cost within a session.
Warns at configurable thresholds and can request context trimming when
the budget is exceeded.

Designed to be called from the conversation loop after each model
response to track cumulative usage against a per-session budget.

Usage:
    governor = SessionBudgetGovernor(budget_usd=1.0)
    governor.record_usage(usage_dict)
    if governor.is_over_budget():
        # trim context or warn
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


@dataclass
class SessionUsage:
    """Cumulative usage for a session."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    total_cost_usd: float = 0.0
    turn_count: int = 0


@dataclass
class SessionBudgetGovernor:
    """Monitors token usage and cost against a per-session budget.

    Budgets are optional — set to 0 or None to disable that limit.
    """

    budget_usd: float = 0.0
    budget_input_tokens: int = 0
    budget_output_tokens: int = 0
    warn_threshold: float = 0.8  # Warn at 80% of budget
    usage: SessionUsage = field(default_factory=SessionUsage)
    _warned: bool = False

    def record_usage(self, usage: Dict[str, Any]) -> None:
        """Record usage from a model response.

        Expected keys: input_tokens, output_tokens, cache_read_tokens, cost_usd.
        Missing keys default to 0.
        """
        self.usage.input_tokens += usage.get("input_tokens", 0) or 0
        self.usage.output_tokens += usage.get("output_tokens", 0) or 0
        self.usage.cache_read_tokens += usage.get("cache_read_tokens", 0) or 0
        self.usage.total_cost_usd += usage.get("cost_usd", 0.0) or 0.0
        self.usage.turn_count += 1

    def is_over_budget(self) -> bool:
        """Check if any budget is exceeded."""
        if self.budget_usd > 0 and self.usage.total_cost_usd >= self.budget_usd:
            return True
        if self.budget_input_tokens > 0 and self.usage.input_tokens >= self.budget_input_tokens:
            return True
        if self.budget_output_tokens > 0 and self.usage.output_tokens >= self.budget_output_tokens:
            return True
        return False

    def should_warn(self) -> bool:
        """Check if we're approaching the budget threshold."""
        if self._warned:
            return False

        if self.budget_usd > 0 and self.usage.total_cost_usd >= self.budget_usd * self.warn_threshold:
            self._warned = True
            return True
        if self.budget_input_tokens > 0 and self.usage.input_tokens >= self.budget_input_tokens * self.warn_threshold:
            self._warned = True
            return True
        if self.budget_output_tokens > 0 and self.usage.output_tokens >= self.budget_output_tokens * self.warn_threshold:
            self._warned = True
            return True
        return False

    def status(self) -> Dict[str, Any]:
        """Return current budget status."""
        cost_pct = (
            (self.usage.total_cost_usd / self.budget_usd * 100)
            if self.budget_usd > 0 else 0
        )
        input_pct = (
            (self.usage.input_tokens / self.budget_input_tokens * 100)
            if self.budget_input_tokens > 0 else 0
        )
        output_pct = (
            (self.usage.output_tokens / self.budget_output_tokens * 100)
            if self.budget_output_tokens > 0 else 0
        )

        return {
            "turns": self.usage.turn_count,
            "input_tokens": self.usage.input_tokens,
            "output_tokens": self.usage.output_tokens,
            "cache_read_tokens": self.usage.cache_read_tokens,
            "total_cost_usd": round(self.usage.total_cost_usd, 6),
            "budget_usd": self.budget_usd,
            "budget_input_tokens": self.budget_input_tokens,
            "budget_output_tokens": self.budget_output_tokens,
            "cost_pct": f"{cost_pct:.1f}%",
            "input_pct": f"{input_pct:.1f}%",
            "output_pct": f"{output_pct:.1f}%",
            "over_budget": self.is_over_budget(),
        }

    def format_warning(self) -> str:
        """Format a human-readable budget warning."""
        s = self.status()
        lines = [f"⚠ Session budget warning (turn {s['turns']}):"]
        if self.budget_usd > 0:
            lines.append(f"  Cost: ${s['total_cost_usd']:.4f} / ${self.budget_usd:.2f} ({s['cost_pct']})")
        if self.budget_input_tokens > 0:
            lines.append(f"  Input tokens: {s['input_tokens']:,} / {self.budget_input_tokens:,} ({s['input_pct']})")
        if self.budget_output_tokens > 0:
            lines.append(f"  Output tokens: {s['output_tokens']:,} / {self.budget_output_tokens:,} ({s['output_pct']})")
        return "\n".join(lines)
