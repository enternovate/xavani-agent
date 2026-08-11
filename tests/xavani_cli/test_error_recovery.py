# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C20: error recovery map — error category to actionable fix."""

import pytest

from xavani_cli.error_recovery import (
    format_recovery,
    recovery_categories,
    suggest_recovery,
)

pytestmark = pytest.mark.unit


def test_config_error_matches():
    s = suggest_recovery("Failed to parse config.yaml: mapping values not allowed")
    assert s is not None
    assert s["category"] == "config_invalid"
    assert "xavani validate" in s["action"]


def test_credential_error_matches():
    s = suggest_recovery("openai API key is invalid: 401 Unauthorized")
    assert s is not None
    assert s["category"] == "credentials_invalid"
    assert ".env" in s["action"]


def test_timeout_error_matches():
    s = suggest_recovery("HTTPSConnectionPool: Read timed out.")
    assert s is not None
    assert s["category"] == "timeout"


def test_network_error_matches():
    s = suggest_recovery("Connection refused: proxy.example.com:443")
    assert s is not None
    assert s["category"] == "network_unreachable"


def test_rate_limit_matches():
    s = suggest_recovery("429 Too Many Requests")
    assert s is not None
    assert s["category"] == "rate_limited"


def test_sandbox_error_matches():
    s = suggest_recovery("execute_code sandbox is unavailable in this environment")
    assert s is not None
    assert s["category"] == "sandbox_unavailable"


def test_state_corruption_matches():
    s = suggest_recovery("Session database not available: database is locked")
    assert s is not None
    assert s["category"] == "state_corrupt"


def test_missing_dependency_matches():
    s = suggest_recovery("ModuleNotFoundError: No module named 'fire'")
    assert s is not None
    assert s["category"] == "missing_dependency"


def test_permission_error_matches():
    s = suggest_recovery("PermissionError: [Errno 13] Permission denied: '/root/.xavani'")
    assert s is not None
    assert s["category"] == "permission_denied"


def test_disk_full_matches():
    s = suggest_recovery("OSError: [Errno 28] No space left on device")
    assert s is not None
    assert s["category"] == "disk_full"


def test_unknown_error_returns_none():
    assert suggest_recovery("weird exotic failure nobody has seen") is None
    assert suggest_recovery("") is None


def test_format_recovery_block():
    block = format_recovery("Failed to parse config.yaml")
    assert block.startswith("\nRecovery:")
    assert "xavani validate" in block


def test_format_recovery_empty_for_unknown():
    assert format_recovery("mystery glitch") == ""


def test_categories_are_unique():
    cats = recovery_categories()
    assert len(cats) == len(set(cats))
    assert "config_invalid" in cats


def test_crash_handler_emits_recovery(monkeypatch, capsys):
    """xavani.main() prints a recovery block for known crash errors."""
    import xavani

    def boom():
        raise TimeoutError("Read timed out after 60 seconds")

    monkeypatch.setattr(xavani, "_maybe_delegate_to_full_cli", lambda: False)
    # main() does `import fire` then `fire.Fire(...)` — patch the module.
    monkeypatch.setattr("fire.Fire", lambda fn: boom())

    with pytest.raises(SystemExit):
        xavani.main()
    err = capsys.readouterr().err
    assert "Recovery:" in err
    assert "timeout" in err.lower()
