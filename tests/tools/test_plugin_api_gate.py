# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C12: plugin API versioning gate tests."""

import pytest

from tools.plugin_api_gate import (
    PLUGIN_API_VERSION,
    check_plugin_api_version,
    gate_plugin_load,
)


# ── verdicts ────────────────────────────────────────────────────────


def test_current_version_compatible():
    verdict = check_plugin_api_version({"api_version": PLUGIN_API_VERSION})
    assert verdict["compatible"] is True
    assert verdict["reason"] == ""


def test_missing_api_version_rejected():
    verdict = check_plugin_api_version({})
    assert verdict["compatible"] is False
    assert "no api_version" in verdict["reason"]


def test_older_version_rejected():
    verdict = check_plugin_api_version({"api_version": "0.0.9"})
    assert verdict["compatible"] is False
    assert "does not match" in verdict["reason"]


def test_future_version_rejected():
    verdict = check_plugin_api_version({"api_version": "99.0.0"})
    assert verdict["compatible"] is False


def test_malformed_version_rejected():
    verdict = check_plugin_api_version({"api_version": "not-a-version"})
    assert verdict["compatible"] is False
    assert "not a valid version" in verdict["reason"]


def test_alt_key_names_supported():
    assert check_plugin_api_version({"apiVersion": PLUGIN_API_VERSION})["compatible"]
    assert check_plugin_api_version({"xavani_api_version": PLUGIN_API_VERSION})["compatible"]


def test_non_dict_manifest_rejected():
    verdict = check_plugin_api_version(None)  # type: ignore[arg-type]
    assert verdict["compatible"] is False


# ── gate helper ─────────────────────────────────────────────────────


def test_gate_raises_on_incompatible():
    with pytest.raises(ValueError, match="api_version"):
        gate_plugin_load({"api_version": "0.0.9"})


def test_gate_passes_on_compatible():
    gate_plugin_load({"api_version": PLUGIN_API_VERSION})  # must not raise


# ── plugin manager integration ─────────────────────────────────────


def test_manifest_parse_accepts_api_version(tmp_path):
    from xavani_cli.plugins import PluginManager

    plugin_dir = tmp_path / "good-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(
        f"name: good-plugin\napi_version: {PLUGIN_API_VERSION}\n",
        encoding="utf-8",
    )
    mgr = PluginManager()
    manifests = mgr._scan_directory_level(tmp_path, "user", skip_names=None, prefix="", depth=0)
    assert len(manifests) == 1
    assert manifests[0].api_version == PLUGIN_API_VERSION


def test_manifest_parse_rejects_bad_version(tmp_path):
    from xavani_cli.plugins import PluginManager

    plugin_dir = tmp_path / "bad-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(
        "name: bad-plugin\napi_version: 0.0.9\n",
        encoding="utf-8",
    )
    mgr = PluginManager()
    manifests = mgr._scan_directory_level(tmp_path, "user", skip_names=None, prefix="", depth=0)
    assert manifests == []


def test_bundled_plugins_exempt(tmp_path):
    """Bundled plugins (source='bundled') skip the gate — they ship
    with the runtime and are always compatible."""
    from xavani_cli.plugins import PluginManager

    plugin_dir = tmp_path / "bundled-plugin"
    plugin_dir.mkdir()
    (plugin_dir / "plugin.yaml").write_text(
        "name: bundled-plugin\n",  # no api_version
        encoding="utf-8",
    )
    mgr = PluginManager()
    manifests = mgr._scan_directory_level(tmp_path, "bundled", skip_names=None, prefix="", depth=0)
    assert len(manifests) == 1
