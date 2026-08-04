# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""D06: install-time EULA/consent for auto-installs tests."""

import pytest

import tools.install_consent as ic
from tools.install_consent import (
    consent_log_entries,
    consent_snapshot,
    record_consent,
    require_consent,
    revoke_consent,
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    store = tmp_path / "install_consents.json"
    monkeypatch.setattr(ic, "_consent_path", lambda: store)
    yield store
    try:
        store.unlink(missing_ok=True)
    except OSError:
        pass


# ── consent gate ────────────────────────────────────────────────────


def test_ungated_component_never_requires_consent(_isolated):
    assert require_consent("some-other-tool", scope="cli") is False


def test_gated_component_requires_consent_first(_isolated):
    assert require_consent("tirith", scope="cli") is True


def test_consent_recorded_then_not_required(_isolated):
    record_consent("tirith", scope="cli", version="1.2.3")
    assert require_consent("tirith", scope="cli") is False


def test_scope_isolation(_isolated):
    """CLI consent does not cover the gateway scope."""
    record_consent("tirith", scope="cli")
    assert require_consent("tirith", scope="cli") is False
    assert require_consent("tirith", scope="gateway") is True


def test_revoke_consent(_isolated):
    record_consent("tirith", scope="cli")
    assert revoke_consent("tirith", scope="cli") is True
    assert require_consent("tirith", scope="cli") is True
    assert revoke_consent("tirith", scope="cli") is False


# ── persistence ─────────────────────────────────────────────────────


def test_consent_persists_across_reload(_isolated):
    record_consent("tirith", scope="cli", version="9.9")
    snapshot = consent_snapshot()
    assert "tirith::cli" in snapshot
    assert snapshot["tirith::cli"]["version"] == "9.9"


def test_consent_log_entries_sorted(_isolated):
    record_consent("tirith", scope="cli")
    record_consent("tirith", scope="gateway")
    entries = consent_log_entries()
    assert len(entries) == 2
    assert {e["scope"] for e in entries} == {"cli", "gateway"}


def test_empty_snapshot(_isolated):
    assert consent_snapshot() == {}
    assert consent_log_entries() == []


# ── tirith integration ──────────────────────────────────────────────


def test_install_skipped_without_consent(_isolated, monkeypatch):
    from tools.tirith_security import _install_tirith

    monkeypatch.delenv("XAVANI_ALLOW_AUTO_INSTALL", raising=False)
    path, reason = _install_tirith()
    assert path is None
    assert reason == "consent_required"


def test_install_proceeds_with_explicit_env(_isolated, monkeypatch):
    from tools.tirith_security import _install_tirith

    monkeypatch.setenv("XAVANI_ALLOW_AUTO_INSTALL", "1")
    # Short-circuit platform detection so no network is touched — the
    # gate must pass first, then the flow fails on platform instead.
    monkeypatch.setattr("tools.tirith_security._detect_target", lambda: None)
    path, reason = _install_tirith()
    assert reason == "unsupported_platform"


def test_install_proceeds_with_recorded_consent(_isolated, monkeypatch):
    from tools.tirith_security import _install_tirith

    record_consent("tirith", scope="cli")
    monkeypatch.setattr("tools.tirith_security._detect_target", lambda: None)
    path, reason = _install_tirith()
    assert reason == "unsupported_platform"
