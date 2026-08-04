# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C18: env var documentation generator tests."""

from pathlib import Path

from scripts.generate_env_docs import (
    render_markdown,
    scan_codebase,
    _purpose_hint,
    _GETENV_RE,
    _ENVIRON_GET_RE,
    _SESSION_ENV_RE,
)


# ── regex coverage ──────────────────────────────────────────────────


def test_getenv_regex():
    assert _GETENV_RE.findall('x = os.getenv("XAVANI_HOME", "/tmp")') == ["XAVANI_HOME"]
    assert _GETENV_RE.findall("os.getenv('FOO')") == ["FOO"]


def test_environ_get_regex():
    assert _ENVIRON_GET_RE.findall('os.environ.get("XAVANI_SESSION_KEY")') == [
        "XAVANI_SESSION_KEY"
    ]
    assert _ENVIRON_GET_RE.findall('os.environ["DO_NOT_TRACK"]') == []


def test_session_env_regex():
    assert _SESSION_ENV_RE.findall('get_session_env("XAVANI_SESSION_PLATFORM", "")') == [
        "XAVANI_SESSION_PLATFORM"
    ]
    assert _SESSION_ENV_RE.findall('get_env_value("XAVANI_TOKEN_BUDGET")') == [
        "XAVANI_TOKEN_BUDGET"
    ]


# ── purpose hint extraction ─────────────────────────────────────────


def test_purpose_hint_from_comment():
    lines = [
        "# The home directory for all xavani state.",
        "home = os.getenv(\"XAVANI_HOME\", \"~/.xavani\")",
    ]
    assert "home directory" in _purpose_hint(lines, 1)


def test_purpose_hint_empty_without_comment():
    lines = ["x = os.getenv(\"XAVANI_HOME\")"]
    assert _purpose_hint(lines, 0) == ""


# ── scan_codebase over a fixture tree ───────────────────────────────


def test_scan_finds_env_vars(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "mod.py").write_text(
        '# API key for the test provider.\n'
        'key = os.getenv("TEST_API_KEY", "default-key")\n'
        'token = os.environ.get("TEST_TOKEN")\n'
        'plat = get_session_env("TEST_PLATFORM", "")\n',
        encoding="utf-8",
    )
    found = scan_codebase(tmp_path)
    assert "TEST_API_KEY" in found
    assert "TEST_TOKEN" in found
    assert "TEST_PLATFORM" in found
    assert "default-key" in found["TEST_API_KEY"]["defaults"]
    assert found["TEST_API_KEY"]["hints"]
    assert any("mod.py:2" in loc for loc in found["TEST_API_KEY"]["locations"])


def test_scan_skips_venv_and_node_modules(tmp_path):
    (tmp_path / ".venv").mkdir(parents=True)
    (tmp_path / ".venv" / "hidden.py").write_text(
        'os.getenv("SHOULD_NOT_APPEAR")', encoding="utf-8"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "x.py").write_text(
        'os.getenv("ALSO_NOT")', encoding="utf-8"
    )
    (tmp_path / "real.py").write_text(
        'os.getenv("REAL_VAR")', encoding="utf-8"
    )
    found = scan_codebase(tmp_path)
    assert "REAL_VAR" in found
    assert "SHOULD_NOT_APPEAR" not in found
    assert "ALSO_NOT" not in found


# ── markdown rendering ──────────────────────────────────────────────


def test_render_markdown_lists_env_vars():
    found = {
        "XAVANI_HOME": {
            "defaults": {"~/.xavani"},
            "locations": ["xavani_constants.py:47"],
            "hints": ["The xavani home directory."],
        }
    }
    md = render_markdown(found)
    assert "## `XAVANI_HOME`" in md
    assert "~/.xavani" in md
    assert "xavani_constants.py:47" in md
    assert "The xavani home directory." in md
    assert "AUTO-GENERATED" in md


# ── canonical output ────────────────────────────────────────────────


def test_canonical_env_docs_generated():
    """docs/reference/env-vars.md exists and contains real env vars."""
    path = Path("docs/reference/env-vars.md")
    assert path.exists(), "run scripts/generate_env_docs.py to regenerate"
    text = path.read_text(encoding="utf-8")
    assert "## `XAVANI_HOME`" in text
    assert "## `XAVANI_DISABLE_TELEMETRY`" in text
