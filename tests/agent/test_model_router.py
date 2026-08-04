# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""B05: model router V2 — cost-aware + latency-aware routing."""

from agent.model_router import CostLatencyRouter, ProviderStats


def _providers():
    return [
        ProviderStats(
            name="cheap-slow", latency_sla_ms=5000,
            cost_per_1k_input=0.1, cost_per_1k_output=0.2,
        ),
        ProviderStats(
            name="pricey-fast", latency_sla_ms=2000,
            cost_per_1k_input=2.0, cost_per_1k_output=6.0,
        ),
    ]


# ── routing decisions ───────────────────────────────────────────────


def test_routes_to_cheapest_when_all_comply():
    router = CostLatencyRouter(_providers())
    # Both meet SLA (no observations -> fail-open); cheapest wins.
    assert router.route(1000, 500) == "cheap-slow"


def test_routes_around_sla_violation():
    router = CostLatencyRouter(_providers())
    router.record_call("cheap-slow", 9000)  # blows its 5s SLA
    assert router.route(1000, 500) == "pricey-fast"


def test_no_provider_meets_sla_returns_none():
    router = CostLatencyRouter(_providers())
    router.record_call("cheap-slow", 9000)
    router.record_call("pricey-fast", 9000)
    assert router.route(1000, 500) is None


def test_empty_router_returns_none():
    assert CostLatencyRouter().route(100, 100) is None


def test_exclude_removes_provider():
    router = CostLatencyRouter(_providers())
    assert router.route(100, 100, exclude=["cheap-slow"]) == "pricey-fast"


def test_exclude_all_returns_none():
    router = CostLatencyRouter(_providers())
    assert router.route(100, 100, exclude=["cheap-slow", "pricey-fast"]) is None


# ── stats + cost estimation ─────────────────────────────────────────


def test_estimated_cost():
    p = ProviderStats("p", cost_per_1k_input=1.0, cost_per_1k_output=2.0)
    assert p.estimated_cost_usd(1000, 500) == 1.0 + 1.0
    assert p.estimated_cost_usd(0, 0) == 0.0


def test_avg_latency_and_sla():
    p = ProviderStats("p", latency_sla_ms=1000)
    assert p.avg_latency_ms() is None
    assert p.meets_sla() is True  # fail-open
    p.record(500)
    p.record(1500)
    assert p.avg_latency_ms() == 1000.0
    assert p.meets_sla() is True  # exactly at SLA counts as compliant
    p.record(3000)
    assert p.meets_sla() is False


def test_rolling_window_bounded():
    p = ProviderStats("p")
    for i in range(200):
        p.record(float(i))
    assert len(p._samples) == 50


def test_register_replaces_provider():
    router = CostLatencyRouter()
    router.register(ProviderStats("a", cost_per_1k_input=1.0))
    router.register(ProviderStats("a", cost_per_1k_input=0.5))
    assert router.stats_snapshot()["a"]["cost_per_1k_input"] == 0.5


def test_stats_snapshot_shape():
    router = CostLatencyRouter(_providers())
    router.record_call("cheap-slow", 100.0)
    snap = router.stats_snapshot()
    assert set(snap.keys()) == {"cheap-slow", "pricey-fast"}
    assert snap["cheap-slow"]["samples"] == 1
    assert snap["cheap-slow"]["avg_latency_ms"] == 100.0
    assert snap["pricey-fast"]["avg_latency_ms"] is None


def test_deterministic_tie_break():
    router = CostLatencyRouter([
        ProviderStats("b-provider", cost_per_1k_input=1.0),
        ProviderStats("a-provider", cost_per_1k_input=1.0),
    ])
    # Equal cost + equal (no) latency -> alphabetical.
    assert router.route(100, 100) == "a-provider"
