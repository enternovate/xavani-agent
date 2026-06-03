# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Capability parity matrix (v0.4.0 roadmap M2 / U19) + cyber-skills index regression (U5).

This locks in that every capability Xavani is expected to ship is actually present
and loadable, and that the vendored cybersecurity skill pack stays consistent. It is
intentionally **file-existence + light-import + registry-map** based so it never
fails on a missing *optional* runtime dependency (telegram, discord, modal, …) — the
goal is "the capability exists in-tree and the tool registry loads", not "every
optional extra is installed in CI".
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent

# ── Capability surface (verified present at 258ec6b) ──────────────────────────

CORE_TOOLS = [
    "mixture_of_agents_tool", "computer_use_tool", "eval_harness_tool",
    "guidelines_gate_tool", "mcp_tool", "memory_tool", "session_search_tool",
    "delegate_tool", "cronjob_tools", "web_tools", "x_search_tool",
    "image_generation_tool", "video_generation_tool", "vision_tools",
    "tts_tool", "transcription_tools", "voice_mode", "browser_cdp_tool",
    "browser_camofox", "code_execution_tool", "terminal_tool",
    "skill_manager_tool", "send_message_tool", "homeassistant_tool", "discord_tool",
]

PLATFORMS = [
    "telegram", "discord", "slack", "whatsapp", "signal", "matrix", "mattermost",
    "feishu", "dingtalk", "wecom", "bluebubbles", "sms", "email", "homeassistant",
    "webhook", "api_server",
]

RUNTIME_BACKENDS = [
    "local", "docker", "ssh", "modal", "daytona", "singularity",
    "vercel_sandbox", "hibernation",
]

# Dependency-light local subsystems that must import cleanly (no optional extras).
LIGHT_IMPORTS = [
    "xavani_learner.skill_orchestrator",
    "xavani_registry.local_registry",
    "tools.registry",
]


@pytest.mark.parametrize("tool", CORE_TOOLS)
def test_core_tool_module_present(tool: str) -> None:
    assert (REPO / "tools" / f"{tool}.py").is_file(), f"missing core tool: tools/{tool}.py"


@pytest.mark.parametrize("platform", PLATFORMS)
def test_platform_adapter_present(platform: str) -> None:
    assert (REPO / "gateway" / "platforms" / f"{platform}.py").is_file(), (
        f"missing platform adapter: gateway/platforms/{platform}.py"
    )


@pytest.mark.parametrize("backend", RUNTIME_BACKENDS)
def test_runtime_backend_present(backend: str) -> None:
    assert (REPO / "tools" / "environments" / f"{backend}.py").is_file(), (
        f"missing runtime backend: tools/environments/{backend}.py"
    )


@pytest.mark.parametrize("module", LIGHT_IMPORTS)
def test_light_subsystem_imports(module: str) -> None:
    import importlib

    importlib.import_module(module)


def test_tool_registry_loads_full_surface() -> None:
    """The tool registry discovers a substantial tool surface (not a partial load)."""
    import tools.registry as registry

    # Tools self-register only after discovery imports their modules.
    registry.discover_builtin_tools()
    tool_map = registry.registry.get_tool_to_toolset_map()
    assert isinstance(tool_map, dict)
    assert len(tool_map) >= 30, f"registry only loaded {len(tool_map)} tools"


def test_deliberate_stubs_remain_stubs() -> None:
    """R2: skills_hub + weixin must stay stubs (string marker check)."""
    for rel in ("tools/skills_hub.py", "gateway/platforms/weixin.py"):
        text = (REPO / rel).read_text(encoding="utf-8").lower()
        assert "stub" in text, f"{rel} no longer reads as a stub (R2 violation)"


# ── Cyber-skills index regression (U5) ────────────────────────────────────────

CYBER_DIR = REPO / "optional-skills" / "cybersecurity"


def test_cyber_skills_present_and_manifest_consistent() -> None:
    assert CYBER_DIR.is_dir(), "optional-skills/cybersecurity missing"
    on_disk = len(list(CYBER_DIR.rglob("SKILL.md")))
    assert on_disk >= 700, f"expected ~754 cyber skills, found {on_disk}"
    manifest = json.loads((CYBER_DIR / "IMPORT_MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["total_skills"] == on_disk, (
        f"manifest total_skills={manifest['total_skills']} != on-disk {on_disk}"
    )


def test_cyber_skills_attribution_present() -> None:
    assert (CYBER_DIR / "NOTICE").is_file()
    assert (CYBER_DIR / "ATTRIBUTION.md").is_file()


def test_cyber_skills_indexed_when_built() -> None:
    """If the website skills index has been generated, cyber skills must be in it."""
    index = REPO / "website" / "src" / "data" / "skills.json"
    if not index.exists():
        pytest.skip("website skills.json not generated in this checkout")
    rows = json.loads(index.read_text(encoding="utf-8"))
    cyber = sum(1 for s in rows if isinstance(s, dict) and s.get("category") == "cybersecurity")
    assert cyber >= 700, f"website index only has {cyber} cybersecurity skills"
