# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G01: autonomous diagnosis tests."""

from tools.auto_diagnosis import _health_score, diagnose, diagnose_from_modules


# ── health scoring ─────────────────────────────────────────────────


def test_error_budget_score():
    assert _health_score("error_budget_remaining", 0.8) == 0.8
    assert _health_score("error_budget_remaining", 0.1) == 0.1
    assert _health_score("error_budget_remaining", -1) == 0.0
    assert _health_score("error_budget_remaining", 2) == 1.0


def test_cost_burn_score():
    assert _health_score("cost_burn_exceeded", True) == 0.0
    assert _health_score("cost_burn_exceeded", False) == 1.0


def test_tool_health_score():
    assert _health_score("tool_health_ok", {"ok": 8, "total": 10}) == 0.8
    assert _health_score("tool_health_ok", {"ok": 0, "total": 2}) == 0.0
    assert _health_score("tool_health_ok", {"ok": 0, "total": 0}) == 1.0


def test_struggling_tasks_score():
    assert _health_score("struggling_tasks", 0) == 1.0
    assert _health_score("struggling_tasks", 5) == 0.0
    assert _health_score("struggling_tasks", 2) == 0.6


def test_error_rate_score():
    assert _health_score("error_rate", 0.0) == 1.0
    assert _health_score("error_rate", 1.0) == 0.0
    assert _health_score("error_rate", 0.25) == 0.75


def test_unknown_signal_none():
    assert _health_score("mystery", 42) is None


def test_none_value_none():
    assert _health_score("error_budget_remaining", None) is None


# ── diagnosis ──────────────────────────────────────────────────────


def test_all_healthy():
    report = diagnose({
        "error_budget_remaining": 0.9,
        "cost_burn_exceeded": False,
        "struggling_tasks": 0,
        "error_rate": 0.01,
    })
    assert report["healthy"] is True
    assert report["issues"] == []
    assert report["overall_score"] > 0.7


def test_critical_issue_detected():
    report = diagnose({"error_budget_remaining": 0.1})
    assert report["healthy"] is False
    assert report["issues"][0]["signal"] == "error_budget_remaining"
    assert report["issues"][0]["severity"] == "critical"


def test_warning_severity():
    report = diagnose({"error_budget_remaining": 0.5})
    assert report["issues"][0]["severity"] == "warning"


def test_issues_sorted_worst_first():
    report = diagnose({
        "cost_burn_exceeded": True,  # score 0.0
        "error_budget_remaining": 0.5,  # score 0.5
    })
    assert report["issues"][0]["signal"] == "cost_burn_exceeded"


def test_unknown_signals_ignored():
    report = diagnose({"mystery": 42, "error_budget_remaining": 0.8})
    assert report["healthy"] is True


def test_empty_signals_healthy():
    report = diagnose({})
    assert report["healthy"] is True
    assert report["overall_score"] == 1.0


def test_diagnose_from_modules_never_raises():
    report = diagnose_from_modules()
    assert "overall_score" in report
    assert "issues" in report
    assert "healthy" in report
