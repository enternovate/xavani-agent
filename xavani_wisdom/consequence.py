# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Consequence projection — deterministic 2nd/3rd-order effects of a decision (v1.0.0 ②).

Given a decision *context* (a plain dict — see :func:`project`), this computes a
:class:`ConsequenceReport`: how reversible it is, who it affects, its time horizon,
its tail risk, whether it ignores base rates, and a rough expected value vs. risk.
It also runs the deterministic downfall matcher (:func:`detect_downfall`) so a plan
that smells like a known failure pattern (overextension, leverage, fraud, hubris)
carries higher risk.

This is the input the Quantum Decision Cortex (major ①) consumes when it simulates
and scores each branch — so the agent's decisions are *conscious of consequences*
and biased away from the patterns that destroyed the great.

**Pure Python, zero model calls (R10).** Same input → same output, always.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

from xavani_wisdom.patterns import WisdomPattern, load_corpus, match

# Affected-party sets by blast radius. "public" is the widest (an outward,
# irreversible act touches the most people).
_AFFECTED = {
    "local": ["you"],
    "team": ["you", "team"],
    "public": ["you", "team", "users", "public"],
}

# Phrases that signal someone is explicitly waving away the base rate / history.
_BASE_RATE_DENIAL = (
    "this time is different",
    "base rate",
    "rules don't apply",
    "rules dont apply",
    "nothing can go wrong",
    "can't lose",
    "cant lose",
    "guaranteed",
)


@dataclass
class ConsequenceReport:
    """Deterministic projection of a decision's downstream effects (all 0..1 unless noted)."""

    reversibility: float  # 1.0 = fully reversible, 0.0 = irreversible
    horizon: str  # "now" | "quarter" | "years"
    affected: list[str] = field(default_factory=list)
    tail_risk: float = 0.0
    base_rate_flag: bool = False
    expected_value: float = 0.5
    risk: float = 0.0
    downfall_signals: list[str] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _clamp(x: float) -> float:
    return max(0.0, min(1.0, x))


def detect_downfall(
    ctx: dict,
    patterns: list[WisdomPattern] | None = None,
    *,
    min_score: int = 2,
) -> list[str]:
    """Return the sorted downfall **signal tags** a decision context matches.

    Deterministic. Combines (a) any explicit ``signals`` the caller already put in
    ``ctx`` with (b) the signals of downfall patterns whose overlap with
    ``ctx['text']`` is at least ``min_score``. The threshold (default 2) means a
    single incidental word never raises a failure alarm — a downfall signature
    needs a real, repeated tell. Zero model calls.
    """
    if patterns is None:
        patterns = load_corpus()
    text = str(ctx.get("text", ""))
    found: set[str] = set(ctx.get("signals", []) or [])
    if text.strip():
        for pat, score in match(text, patterns, kind="downfall"):
            # Personalised self-fault patterns ("you've made this exact mistake
            # before") flag eagerly — one hit is enough; general historical
            # patterns need a stronger, repeated tell (min_score).
            is_self_fault = "self_fault" in pat.signals
            if score >= min_score or (is_self_fault and score >= 1):
                found.update(pat.signals)
    return sorted(found)


def project(ctx: dict, patterns: list[WisdomPattern] | None = None) -> ConsequenceReport:
    """Project the consequences of a decision context. Pure + deterministic (R10).

    Recognised ``ctx`` keys (all optional, with safe defaults):
        text:       str   free description of the decision/plan
        reversible: bool  can it be undone cheaply? (default True)
        cost:       float resource cost 0..1 (default 0.0)
        value:      float upside if it works 0..1 (default 0.5)
        scope:      str   "local" | "team" | "public" (default "local")
        horizon:    str   "now" | "quarter" | "years" (default "quarter")
        signals:    list[str] explicit downfall signal tags to include
    """
    text = str(ctx.get("text", ""))
    reversible = bool(ctx.get("reversible", True))
    cost = _clamp(float(ctx.get("cost", 0.0)))
    value = _clamp(float(ctx.get("value", 0.5)))
    scope = str(ctx.get("scope", "local"))
    horizon = str(ctx.get("horizon", "quarter"))

    signals = detect_downfall(ctx, patterns)
    base_rate_flag = any(p in text.lower() for p in _BASE_RATE_DENIAL)

    # Reversibility: irreversible actions start low and drop with each downfall signal.
    reversibility = 1.0 if reversible else _clamp(0.4 - 0.1 * len(signals))

    # Tail risk grows with downfall signals, irreversibility, and cost.
    tail_risk = _clamp(0.15 * len(signals) + (0.0 if reversible else 0.4) + 0.2 * cost)

    # Overall risk blends the tail, irreversibility, and base-rate denial.
    risk = _clamp(0.5 * tail_risk + 0.3 * (1.0 - reversibility) + 0.2 * (1.0 if base_rate_flag else 0.0))

    # Expected value = upside discounted by risk (never below 0).
    expected_value = _clamp(value - 0.5 * risk)

    findings: list[str] = [f"downfall signal: {s}" for s in signals]
    if not reversible:
        findings.append("irreversible action — weigh carefully before committing")
    if base_rate_flag:
        findings.append("language dismisses the base rate / history — classic overconfidence tell")
    if scope == "public" and risk >= 0.5:
        findings.append("high-risk and outward-facing — this is where reputations are lost")

    return ConsequenceReport(
        reversibility=reversibility,
        horizon=horizon,
        affected=list(_AFFECTED.get(scope, ["you"])),
        tail_risk=tail_risk,
        base_rate_flag=base_rate_flag,
        expected_value=expected_value,
        risk=risk,
        downfall_signals=signals,
        findings=findings,
    )
