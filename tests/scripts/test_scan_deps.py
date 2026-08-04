# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""G09: autonomous dependency security scanning tests."""

import json

import pytest

from scripts import scan_deps


def _osv_output(pkg_name="requests", version="2.31.0", vuln_id="OSV-2024-1"):
    return json.dumps({
        "results": [
            {
                "packages": [
                    {
                        "package": {"name": pkg_name, "version": version},
                        "vulnerabilities": [
                            {"id": vuln_id, "severity": [{"score": "7.5"}],
                             "summary": "test vulnerability"}
                        ],
                    }
                ]
            }
        ]
    })


# ── scan_lockfile ───────────────────────────────────────────────────


def test_scan_lockfile_missing_returns_empty(tmp_path):
    res = scan_deps.scan_lockfile(tmp_path / "nope.lock")
    assert res["findings"] == []


def test_scan_lockfile_parses_findings(tmp_path, monkeypatch):
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1  # findings found
            stdout = _osv_output()
            stderr = ""
        return R()

    monkeypatch.setattr(scan_deps, "_run", fake_run)
    res = scan_deps.scan_lockfile(lockfile)
    assert len(res["findings"]) == 1
    assert res["findings"][0]["package"] == "requests"
    assert res["findings"][0]["id"] == "OSV-2024-1"


def test_scan_lockfile_clean(tmp_path, monkeypatch):
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = json.dumps({"results": []})
            stderr = ""
        return R()

    monkeypatch.setattr(scan_deps, "_run", fake_run)
    assert scan_deps.scan_lockfile(lockfile)["findings"] == []


def test_scan_lockfile_error_captured(tmp_path, monkeypatch):
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 2  # hard failure
            stdout = ""
            stderr = "osv-scanner: no such binary"
        return R()

    monkeypatch.setattr(scan_deps, "_run", fake_run)
    res = scan_deps.scan_lockfile(lockfile)
    assert res["error"] and "no such binary" in res["error"]


def test_scan_lockfile_unparseable(tmp_path, monkeypatch):
    lockfile = tmp_path / "uv.lock"
    lockfile.write_text("fake", encoding="utf-8")

    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = "not json at all"
            stderr = ""
        return R()

    monkeypatch.setattr(scan_deps, "_run", fake_run)
    res = scan_deps.scan_lockfile(lockfile)
    assert res["error"] == "unparseable output"


# ── summarize ───────────────────────────────────────────────────────


def test_summarize_aggregates():
    results = [
        {"lockfile": "a", "findings": [
            {"package": "requests", "id": "OSV-1"},
            {"package": "requests", "id": "OSV-2"},
        ], "error": None},
        {"lockfile": "b", "findings": [
            {"package": "flask", "id": "OSV-3"},
        ], "error": None},
    ]
    summary = scan_deps.summarize(results)
    assert summary["total_vulnerabilities"] == 3
    assert summary["affected_packages"] == 2
    assert summary["by_package"]["requests"] == ["OSV-1", "OSV-2"]


def test_summarize_empty():
    summary = scan_deps.summarize([])
    assert summary["total_vulnerabilities"] == 0


# ── auto-PR gating ──────────────────────────────────────────────────


def test_auto_pr_disabled_by_default(monkeypatch):
    monkeypatch.delenv("XAVANI_AUTO_DEP_PR", raising=False)
    assert scan_deps.auto_pr_enabled() is False


def test_auto_pr_enabled_with_env(monkeypatch):
    monkeypatch.setenv("XAVANI_AUTO_DEP_PR", "1")
    assert scan_deps.auto_pr_enabled() is True


def test_open_remediation_pr_skipped_when_disabled(monkeypatch):
    monkeypatch.delenv("XAVANI_AUTO_DEP_PR", raising=False)
    summary = {"total_vulnerabilities": 3, "affected_packages": 1,
               "by_package": {"requests": ["OSV-1"]}}
    assert scan_deps.open_remediation_pr(summary) is None


def test_open_remediation_pr_skipped_when_clean(monkeypatch):
    monkeypatch.setenv("XAVANI_AUTO_DEP_PR", "1")
    summary = {"total_vulnerabilities": 0, "affected_packages": 0, "by_package": {}}
    assert scan_deps.open_remediation_pr(summary) is None


def test_open_remediation_pr_creates_pr(monkeypatch):
    monkeypatch.setenv("XAVANI_AUTO_DEP_PR", "1")
    summary = {"total_vulnerabilities": 1, "affected_packages": 1,
               "by_package": {"requests": ["OSV-1"]}}
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        class R:
            returncode = 0
            stdout = "https://github.com/org/repo/pull/42"
            stderr = ""
        return R()

    monkeypatch.setattr(scan_deps, "_run", fake_run)
    url = scan_deps.open_remediation_pr(summary)
    assert url == "https://github.com/org/repo/pull/42"
    assert any("pr" in c and "create" in c for c in calls)
