#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Migrate a user's OpenClaw Agent configuration and data to Xavani.

This script looks for ~/.openclaw/config.yaml and migrates compatible settings
to ~/.xavani/. It also copies installed skills and prints a mapping of
OpenClaw concepts to their Xavani equivalents.

Usage:
    python scripts/migrate_from_openclaw.py --dry-run   # Preview only
    python scripts/migrate_from_openclaw.py --apply      # Actually migrate
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ── Paths ──────────────────────────────────────────────────────────

OPENCLAW_HOME = Path.home() / ".openclaw"
XAVANI_HOME = Path.home() / ".xavani"

# ── Concept mapping (OpenClaw → Xavani) ────────────────────────────

CONCEPT_MAP = {
    # Config keys
    "provider": "XAVANI_PROVIDER",
    "model": "XAVANI_MODEL",
    "temperature": "config: temperature",
    "max_tokens": "config: max_tokens",
    "system_prompt": "config: system_prompt",
    "workspace": "config: workspace_dir",
    "theme": "skin selection (/skin <name>)",
    "skin": "skin selection (/skin <name>)",

    # File locations
    "~/.openclaw/config.yaml": "~/.xavani/config.yaml",
    "~/.openclaw/.env": "~/.xavani/.env",
    "~/.openclaw/skills/": "~/.xavani/skills/",
    "~/.openclaw/logs/": "~/.xavani/logs/",
    "~/.openclaw/memory/": "~/.xavani/data/ (memory via Xavani Memory)",
    "~/.openclaw/SOUL.md": "~/.xavani/config.yaml (persona section)",
    "~/.openclaw/USER.md": "~/.xavani/config.yaml (user_profile section)",
    "~/.openclaw/MEMORY.md": "~/.xavani/data/ (memory store)",

    # Commands
    "/claw-settings": "/help (or individual settings commands)",
    "/claw-skill": "/install <skill>",
    "/claw-forget": "/memory reset",
    "/claw-status": "/status",
    "/claw-update": "xavani update (via pip)",
    "/claw-backup": "/backup",

    # Concepts
    "ClawHub skills registry": "Skills Registry (/install to browse)",
    "SOUL.md persona": "Persona section in config.yaml",
    "USER.md user profile": "User profile in config.yaml",
    "MEMORY.md long-term memory": "Xavani Memory (episodic + procedural)",
    "OpenClaw plugin system": "Xavani Plugin System (plugins/)",
    "Gateway (OpenClaw Connect)": "Gateway (MCP proxy on localhost:8080)",
}

SENSITIVE_FILE_PATTERNS = {
    ".env", ".env.local", ".env.production",
    "credentials.json", "token.json", "secrets.json", "keys.json",
}

# Trading-related directory names — proprietary to Enternovate, excluded
TRADING_DIR_PATTERNS = {"trading", "deriv-trading", "backtest", "backtesting", "forex", "deriv"}


def _is_trading_dir(name: str) -> bool:
    """Check if a directory name matches a trading-related pattern."""
    name_lower = name.lower()
    for pat in TRADING_DIR_PATTERNS:
        if name_lower == pat or name_lower.startswith(pat + "-") or name_lower.endswith("-" + pat):
            return True
    return False


def _has_sensitive_name(path: Path) -> bool:
    name = path.name.lower()
    for pat in SENSITIVE_FILE_PATTERNS:
        if name == pat or name.startswith(pat):
            return True
    return False


def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    if yaml is None:
        print(f"  [WARN] PyYAML not installed — skipping {path}")
        return None
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"  [WARN] Could not parse {path}: {e}")
        return None


def _write_yaml(data: Dict[str, Any], path: Path) -> None:
    if yaml is None:
        print(f"  [WARN] PyYAML not installed — cannot write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _map_config(openclaw_config: Dict[str, Any]) -> Dict[str, Any]:
    """Map OpenClaw config keys to Xavani equivalents."""
    mapping: Dict[str, Any] = {}

    # Map top-level settings
    key_map = {
        "provider": ("provider", str),
        "model": ("model", str),
        "temperature": ("temperature", float),
        "max_tokens": ("max_tokens", int),
        "workspace": ("workspace_dir", str),
    }

    for oc_key, (x_key, x_type) in key_map.items():
        if oc_key in openclaw_config:
            try:
                mapping[x_key] = x_type(openclaw_config[oc_key])
            except (ValueError, TypeError):
                pass  # skip uncastable values

    return mapping


def print_concept_map():
    """Print the OpenClaw → Xavani concept mapping."""
    print()
    print("  OpenClaw Concept                 →  Xavani Equivalent")
    print("  " + "-" * 65)
    for oc, xa in sorted(CONCEPT_MAP.items()):
        print(f"  {oc:<35} →  {xa}")
    print()


def migrate_openclaw(dry_run: bool = False) -> int:
    """Run the OpenClaw → Xavani migration.

    Returns:
        Number of items migrated.
    """
    items = 0

    print("=" * 60)
    print("  Xavani Migration: OpenClaw Agent → Xavani")
    print("=" * 60)

    if not OPENCLAW_HOME.is_dir():
        print(f"\n  [SKIP] ~/.openclaw/ not found — nothing to migrate.")
        return 0

    # 1. Concept mapping
    print("\n  Concept Mapping:")
    print_concept_map()

    # 2. Migrate config.yaml
    oc_config = OPENCLAW_HOME / "config.yaml"
    if oc_config.exists():
        print(f"\n  [{'DRY-RUN' if dry_run else 'OK'}] Migrating config.yaml ...")
        data = _load_yaml(oc_config)
        if data:
            mapped = _map_config(data)
            if dry_run:
                if mapped:
                    print(f"    Would set: {', '.join(mapped.keys())}")
                else:
                    print(f"    No compatible settings found")
            else:
                if mapped:
                    dst = XAVANI_HOME / "config.yaml"
                    dst.parent.mkdir(parents=True, exist_ok=True)

                    # Merge with existing config if present
                    existing = _load_yaml(dst) or {}
                    existing.update(mapped)
                    _write_yaml(existing, dst)
                    print(f"    Set: {', '.join(mapped.keys())}")
                    print(f"    Written to {dst}")
                else:
                    print(f"    No compatible settings to migrate")
            items += 1
        else:
            print(f"    [SKIP] Could not parse config.yaml")
    else:
        print(f"\n  [SKIP] config.yaml not found in ~/.openclaw/")

    # 3. Migrate skills
    skills_src = OPENCLAW_HOME / "skills"
    skills_dst = XAVANI_HOME / "skills"
    if skills_src.is_dir():
        skill_count = 0
        for item in skills_src.iterdir():
            if _has_sensitive_name(item):
                continue
            if item.is_dir() and _is_trading_dir(item.name):
                if dry_run:
                    print(f"  [SKIP] Trading skill (proprietary): {item.name}")
                continue
            if dry_run:
                print(f"  [DRY-RUN] Would copy skill: {item.name}")
                skill_count += 1
            else:
                dst = skills_dst / item.name
                if item.is_dir():
                    shutil.copytree(item, dst, dirs_exist_ok=True)
                else:
                    shutil.copy2(item, dst)
                skill_count += 1
        if skill_count > 0:
            print(f"  [{'DRY-RUN' if dry_run else 'OK'}] Migrated {skill_count} skill(s)")
        else:
            print(f"  [SKIP] No skills to migrate in ~/.openclaw/skills/")
        items += skill_count
    else:
        print(f"  [SKIP] ~/.openclaw/skills/ not found")

    # 4. Migrate SOUL.md (persona)
    soul_file = OPENCLAW_HOME / "SOUL.md"
    if soul_file.exists():
        if dry_run:
            print(f"  [DRY-RUN] Would read SOUL.md and store persona in config")
        else:
            soul_content = soul_file.read_text(encoding="utf-8", errors="replace")
            dst_config = XAVANI_HOME / "config.yaml"
            existing = _load_yaml(dst_config) or {}
            if "persona" not in existing:
                existing["persona"] = {}
            existing["persona"]["soul"] = soul_content.strip()
            _write_yaml(existing, dst_config)
            print(f"  [OK] Migrated SOUL.md → persona section in config.yaml")
        items += 1
    else:
        print(f"  [SKIP] ~/.openclaw/SOUL.md not found")

    # 5. Migrate USER.md
    user_file = OPENCLAW_HOME / "USER.md"
    if user_file.exists():
        if dry_run:
            print(f"  [DRY-RUN] Would read USER.md and store profile in config")
        else:
            user_content = user_file.read_text(encoding="utf-8", errors="replace")
            dst_config = XAVANI_HOME / "config.yaml"
            existing = _load_yaml(dst_config) or {}
            if "user_profile" not in existing:
                existing["user_profile"] = {}
            existing["user_profile"]["description"] = user_content.strip()
            _write_yaml(existing, dst_config)
            print(f"  [OK] Migrated USER.md → user_profile in config.yaml")
        items += 1
    else:
        print(f"  [SKIP] ~/.openclaw/USER.md not found")

    print()
    print(f"  Summary: {items} item(s) {'would be' if dry_run else 'were'} migrated.")
    if dry_run:
        print(f"  Run with --apply to execute the migration.")
    print()

    return items


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Migrate OpenClaw Agent config and data to Xavani."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be migrated (default)",
    )
    group.add_argument(
        "--apply",
        action="store_true",
        help="Actually perform the migration",
    )
    args = parser.parse_args()

    migrate_openclaw(dry_run=args.dry_run if args.apply is False else False)


if __name__ == "__main__":
    main()
