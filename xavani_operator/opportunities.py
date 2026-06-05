# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Deterministic opportunity rule engine (v0.7.0 operator U15–U18).

Turns a :class:`~xavani_operator.types.Perception` into a ranked list of
:class:`~xavani_operator.types.Opportunity` — the candidate things worth doing.
This is the operator *deciding what could be done*, and it is **pure Python with
zero model calls** (R10): rules are simple, auditable functions of the perceived
state and the product config. The LLM only enters later, in ``propose``, to turn
the chosen opportunity into a concrete plan.

Each workstream contributes rules: ``build`` (fix tests, pay down TODOs, ship
goals), ``promote`` (announce notable changes, keep channel cadence), and ``ops``
(housekeeping). Scores are in roughly [0, 1]; ``detect`` aggregates and sorts
deterministically (score desc, then id) so the same state always ranks the same.
"""

from __future__ import annotations

from typing import Callable

from xavani_operator.types import Opportunity

_NOTABLE_COMMIT_KEYWORDS = ("release", "launch", "ship", "feat", "v0.", "v1.", "announce")


def _priority_score(priority: int) -> float:
    """Map a goal priority (1 = highest) to a score in [0.3, 0.95]."""
    return max(0.3, min(0.95, 1.0 - 0.1 * (priority - 1)))


def build_opportunities(perception, config) -> list[Opportunity]:
    """Software-lifecycle opportunities: failing tests, TODO debt, goal features."""
    opps: list[Opportunity] = []
    tests = perception.tests or {}
    if tests.get("known") and tests.get("failing", 0) > 0:
        n = int(tests["failing"])
        opps.append(Opportunity(
            id="build:fix-tests", kind="fix_tests", workstream="build",
            score=min(1.0, 0.7 + 0.05 * n),
            rationale=f"{n} failing test(s) in the last run", payload={"failing": n},
        ))
    if perception.issues:
        n = len(perception.issues)
        opps.append(Opportunity(
            id="build:address-todos", kind="address_todos", workstream="build",
            score=min(0.6, 0.2 + 0.02 * n),
            rationale=f"{n} TODO/FIXME marker(s) in the tree", payload={"count": n},
        ))
    for goal in config.goals:
        opps.append(Opportunity(
            id=f"build:goal:{goal.id}", kind="build_feature", workstream="build",
            score=_priority_score(goal.priority),
            rationale=f"goal: {goal.intent or goal.id}", payload={"goal_id": goal.id},
        ))
    return opps


def promote_opportunities(perception, config) -> list[Opportunity]:
    """Growth opportunities: announce notable changes, keep channel cadence."""
    opps: list[Opportunity] = []
    for commit in (perception.repo or {}).get("recent_commits", []):
        if any(kw in commit.lower() for kw in _NOTABLE_COMMIT_KEYWORDS):
            opps.append(Opportunity(
                id="promote:announce", kind="announce", workstream="promote",
                score=0.55, rationale=f"notable change: {commit}", payload={"commit": commit},
            ))
            break
    if config.channels:
        opps.append(Opportunity(
            id="promote:cadence", kind="cadence_content", workstream="promote",
            score=0.4, rationale=f"{len(config.channels)} channel(s) configured",
            payload={"channels": [c.platform for c in config.channels]},
        ))
    return opps


def ops_opportunities(perception, config) -> list[Opportunity]:
    """Operational opportunities: housekeeping when the tree drifts."""
    opps: list[Opportunity] = []
    repo = perception.repo or {}
    if repo.get("dirty") and repo.get("dirty_files", 0) >= 10:
        opps.append(Opportunity(
            id="ops:tree-drift", kind="housekeeping", workstream="ops",
            score=0.3, rationale=f"{repo['dirty_files']} uncommitted files",
            payload={"dirty_files": repo["dirty_files"]},
        ))
    return opps


# Built-in rule set. Workstream packs (M4/M5) can supply richer rules.
DEFAULT_RULES: list[Callable] = [
    build_opportunities,
    promote_opportunities,
    ops_opportunities,
]


def detect(perception, config, rules: list[Callable] | None = None) -> list[Opportunity]:
    """Run all rules and return opportunities sorted by score desc, then id asc."""
    active = DEFAULT_RULES if rules is None else rules
    opps: list[Opportunity] = []
    for rule in active:
        opps.extend(rule(perception, config))
    opps.sort(key=lambda o: (-o.score, o.id))
    return opps
