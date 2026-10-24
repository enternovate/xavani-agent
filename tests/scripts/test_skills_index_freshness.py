# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Freshness watchdog: an empty published body is a pending deploy, not a crash."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load_module():
    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "_freshness_under_test",
        root / "scripts" / "check_skills_index_freshness.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _write(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_empty_published_body_is_pending(monkeypatch, tmp_path, capsys):
    module = _load_module()
    local = tmp_path / "skills-index.json"
    _write(local, {"skills": [], "generated_at": "2026-10-24T00:00:00Z"})
    monkeypatch.setattr(module, "LOCAL_PATH", local)
    monkeypatch.setattr(module, "read_published", lambda url: b"")
    assert module.main() == 0
    assert "PENDING-DEPLOYMENT" in capsys.readouterr().out


def test_timestamp_does_not_count_as_drift(monkeypatch, tmp_path, capsys):
    module = _load_module()
    local = tmp_path / "skills-index.json"
    _write(local, {"skills": [{"name": "a"}], "generated_at": "2026-10-24"})
    monkeypatch.setattr(module, "LOCAL_PATH", local)
    published = json.dumps({"skills": [{"name": "a"}], "generated_at": "2026-01-01"}).encode()
    monkeypatch.setattr(module, "read_published", lambda url: published)
    assert module.main() == 0
    assert "FRESH" in capsys.readouterr().out


def test_content_drift_is_stale(monkeypatch, tmp_path, capsys):
    module = _load_module()
    local = tmp_path / "skills-index.json"
    _write(local, {"skills": [{"name": "a"}]})
    monkeypatch.setattr(module, "LOCAL_PATH", local)
    published = json.dumps({"skills": [{"name": "b"}]}).encode()
    monkeypatch.setattr(module, "read_published", lambda url: published)
    assert module.main() == 1
    assert "STALE" in capsys.readouterr().out
