# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B05: model router V2 — cost-aware + latency-aware.

Tracks per-provider latency and $/token from real calls, then routes
each request to the cheapest provider that meets the latency SLA.

The router is a pure decision engine: it takes candidate providers
(name, base_url, cost_per_1k_input, cost_per_1k_output, latency_sla_ms)
and observed stats, and returns the best pick. Callers wire it into
their own request path — the router never opens sockets itself.

When a candidate has no observed latency yet (first use), it is assumed
to meet the SLA (fail-open — a brand-new provider shouldn't be locked
out). Ties go to the cheaper provider; a final tie breaks
alphabetically for determinism.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProviderStats:
    """Rolling latency + cost observations for one provider."""

    name: str
    latency_sla_ms: float = 5000.0          # SLA this provider must meet
    cost_per_1k_input: float = 0.0          # USD per 1k input tokens
    cost_per_1k_output: float = 0.0         # USD per 1k output tokens
    # Rolling window (ms) — ring of recent latency samples.
    _samples: List[float] = field(default_factory=list)
    _max_samples: int = 50

    def record(self, latency_ms: float) -> None:
        """Record one observed call latency."""
        self._samples.append(latency_ms)
        if len(self._samples) > self._max_samples:
            self._samples.pop(0)

    def avg_latency_ms(self) -> Optional[float]:
        """Mean observed latency, or None with no observations."""
        if not self._samples:
            return None
        return sum(self._samples) / len(self._samples)

    def meets_sla(self) -> bool:
        """True when observed latency is within the SLA.

        Fail-open: no observations yet -> assumed compliant.
        """
        avg = self.avg_latency_ms()
        if avg is None:
            return True
        return avg <= self.latency_sla_ms

    def estimated_cost_usd(
        self, input_tokens: int, output_tokens: int
    ) -> float:
        """Estimated cost of a call with the given token counts."""
        return (
            input_tokens / 1000.0 * self.cost_per_1k_input
            + output_tokens / 1000.0 * self.cost_per_1k_output
        )


class CostLatencyRouter:
    """Route a call to the cheapest SLA-compliant provider."""

    def __init__(self, providers: Optional[List[ProviderStats]] = None):
        self._providers: Dict[str, ProviderStats] = {}
        self._lock = threading.Lock()
        for p in providers or []:
            self._providers[p.name] = p

    def register(self, provider: ProviderStats) -> None:
        """Register or replace a provider's stats."""
        with self._lock:
            self._providers[provider.name] = provider

    def record_call(self, name: str, latency_ms: float) -> None:
        """Record an observed call latency for a provider."""
        with self._lock:
            provider = self._providers.get(name)
        if provider is not None:
            provider.record(latency_ms)

    def route(
        self,
        input_tokens: int,
        output_tokens: int,
        *,
        exclude: Optional[List[str]] = None,
    ) -> Optional[str]:
        """Pick the cheapest SLA-compliant provider name.

        Returns None when no provider is registered or none meets the
        SLA. ``exclude`` removes providers (e.g. a provider currently
        rate-limited or in cooldown).
        """
        excluded = set(exclude or [])
        with self._lock:
            candidates = list(self._providers.values())
        viable = [
            p for p in candidates
            if p.name not in excluded and p.meets_sla()
        ]
        if not viable:
            return None

        def _key(p: ProviderStats):
            cost = p.estimated_cost_usd(input_tokens, output_tokens)
            return (cost, p.avg_latency_ms() or 0.0, p.name)

        best = min(viable, key=_key)
        return best.name

    def stats_snapshot(self) -> Dict[str, Any]:
        """Serializable view of every provider's stats."""
        with self._lock:
            return {
                name: {
                    "avg_latency_ms": p.avg_latency_ms(),
                    "meets_sla": p.meets_sla(),
                    "cost_per_1k_input": p.cost_per_1k_input,
                    "cost_per_1k_output": p.cost_per_1k_output,
                    "latency_sla_ms": p.latency_sla_ms,
                    "samples": len(p._samples),
                }
                for name, p in sorted(self._providers.items())
            }
