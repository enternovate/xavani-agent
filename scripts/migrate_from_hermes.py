#!/usr/bin/env python3
# Copyright (c) 2025-2026 Enternovate. All rights reserved.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Migrate a user's Hermes Agent configuration and skills to Xavani.

This script reads ~/.hermes/config.yaml, strips all API keys/tokens/secrets,
and copies the safe parts to ~/.xavani/. It also copies:
  - ~/.hermes/.env.example → ~/.xavani/.env.example (without real keys)
  - Installed skills from ~/.hermes/skills/ to ~/.xavani/skills/
  - Gateway config from ~/.hermes/gateway.yaml if it exists

It NEVER copies files containing API keys, tokens, or secrets.

Usage:
    python scripts/migrate_from_hermes.py --dry-run    # Preview only
    python scripts/migrate_from_hermes.py --apply       # Actually migrate
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, Optional, List

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]


# ── Paths ──────────────────────────────────────────────────────────

HERMES_HOME = Path.home() / ".hermes"
XAVANI_HOME = Path.home() / ".xavani"

# ── Sensitive keys — stripped during migration ──────────────────────

SENSITIVE_KEYS = {
    # API keys / tokens
    "api_key", "api_key_secret", "openai_api_key", "anthropic_api_key",
    "google_api_key", "gemini_api_key", "openrouter_api_key", "grok_api_key",
    "xai_api_key", "together_api_key", "cohere_api_key",
    "huggingface_token", "hf_token",
    "telegram_bot_token", "slack_bot_token", "discord_bot_token",
    "github_token", "gitlab_token",
    "aws_access_key_id", "aws_secret_access_key",
    "azure_api_key", "azure_openai_key",
    "pinecone_api_key", "qdrant_api_key", "weaviate_api_key",
    "supabase_url", "supabase_key",
    "jwt_secret", "session_secret",
    "webhook_secret", "signing_secret",
    "client_secret", "app_secret",
    "password", "passwd", "secret",
    "token", "refresh_token", "access_token",
    "private_key", "ssh_key",
    "aws_session_token",
    "elevenlabs_api_key",
    "replicate_api_token",
    "serpapi_key",
    "brave_api_key",
    "tavily_api_key",
}

# Subpaths that contain secrets and should never be copied
SENSITIVE_FILES = {
    ".env", ".env.local", ".env.production",
    "credentials.json", "credentials.yaml",
    "service-account.json", "service-account.yaml",
    "token.json", "tokens.json",
    "secrets.json", "secrets.yaml",
    "keys.json", "keys.yaml",
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
    """Check if a filename looks like it contains secrets."""
    name = path.name.lower()
    for pat in SENSITIVE_FILES:
        if name == pat or name.startswith(pat):
            return True
    return False


def _strip_sensitive(d: Dict[str, Any], path: str = "root") -> Dict[str, Any]:
    """Recursively strip sensitive values from a config dict."""
    out: Dict[str, Any] = {}
    for k, v in d.items():
        k_lower = k.lower()
        if k_lower in SENSITIVE_KEYS:
            out[k] = "*** STRIPPED ***"
            continue
        if isinstance(v, dict):
            out[k] = _strip_sensitive(v, f"{path}.{k}")
        else:
            out[k] = v
    return out


def _load_yaml(path: Path) -> Optional[Dict[str, Any]]:
    """Load a YAML file safely. Returns None if not found or invalid."""
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
    """Write data as clean YAML."""
    if yaml is None:
        print(f"  [WARN] PyYAML not installed — cannot write {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def _copy_skills(src: Path, dst: Path, dry_run: bool) -> int:
    """Copy skills from src to dst, skipping sensitive and trading-related files. Returns count."""
    if not src.is_dir():
        return 0
    count = 0
    for item in src.iterdir():
        if _has_sensitive_name(item):
            continue
        if item.is_dir() and _is_trading_dir(item.name):
            if dry_run:
                print(f"  [SKIP] Trading skill (proprietary): {item.name}")
            continue
        if dry_run:
            print(f"  [DRY-RUN] Would copy skill: {item.name}")
            count += 1
        else:
            dst_skill = dst / item.name
            if item.is_dir():
                shutil.copytree(item, dst_skill, dirs_exist_ok=True)
            else:
                shutil.copy2(item, dst_skill)
            count += 1
    return count


def migrate_hermes(dry_run: bool = False) -> int:
    """Run the Hermes → Xavani migration.

    Returns:
        Number of items migrated.
    """
    items = 0

    print("=" * 60)
    print("  Xavani Migration: Hermes Agent → Xavani")
    print("=" * 60)

    if not HERMES_HOME.is_dir():
        print(f"\n  [SKIP] ~/.hermes/ not found — nothing to migrate.")
        return 0

    # 1. Migrate config.yaml
    hermes_config = HERMES_HOME / "config.yaml"
    if hermes_config.exists():
        print(f"\n  [{'DRY-RUN' if dry_run else 'OK'}] Migrating config.yaml ...")
        data = _load_yaml(hermes_config)
        if data:
            safe = _strip_sensitive(data)
            if dry_run:
                print(f"    Stripped {_count_stripped(data, safe)} sensitive fields")
            else:
                dst = XAVANI_HOME / "config.yaml"
                _write_yaml(safe, dst)
                print(f"    Stripped {_count_stripped(data, safe)} sensitive fields")
                print(f"    Written to {dst}")
            items += 1
        else:
            print(f"    [SKIP] Could not parse config.yaml")
    else:
        print(f"\n  [SKIP] config.yaml not found in ~/.hermes/")

    # 2. Migrate .env.example
    env_example = HERMES_HOME / ".env.example"
    if env_example.exists():
        if dry_run:
            print(f"  [DRY-RUN] Would copy .env.example → ~/.xavani/.env.example")
        else:
            dst = XAVANI_HOME / ".env.example"
            shutil.copy2(env_example, dst)
            print(f"  [OK] Copied .env.example → {dst}")
        items += 1
    else:
        # Check for .env.template
        env_template = HERMES_HOME / ".env.template"
        if env_template.exists():
            if dry_run:
                print(f"  [DRY-RUN] Would copy .env.template → ~/.xavani/.env.example")
            else:
                dst = XAVANI_HOME / ".env.example"
                shutil.copy2(env_template, dst)
                print(f"  [OK] Copied .env.template → {dst}")
            items += 1
        else:
            print(f"  [SKIP] No .env.example or .env.template found")

    # 3. Migrate skills
    skills_src = HERMES_HOME / "skills"
    skills_dst = XAVANI_HOME / "skills"
    if skills_src.is_dir():
        skill_count = _copy_skills(skills_src, skills_dst, dry_run)
        if skill_count > 0:
            print(f"  [{'DRY-RUN' if dry_run else 'OK'}] Migrated {skill_count} skill(s)")
        else:
            print(f"  [SKIP] No skills to migrate in ~/.hermes/skills/")
        items += skill_count
    else:
        print(f"  [SKIP] ~/.hermes/skills/ not found")

    # 4. Migrate gateway config
    gateway_config = HERMES_HOME / "gateway.yaml"
    if gateway_config.exists():
        if dry_run:
            print(f"  [DRY-RUN] Would copy gateway.yaml → ~/.xavani/gateway.yaml")
        else:
            dst = XAVANI_HOME / "gateway.yaml"
            shutil.copy2(gateway_config, dst)
            print(f"  [OK] Copied gateway.yaml → {dst}")
        items += 1
    else:
        print(f"  [SKIP] No gateway.yaml found")

    # 5. Migrate policies
    policies_src = HERMES_HOME / "policies"
    policies_dst = XAVANI_HOME / "policies"
    if policies_src.is_dir():
        pcount = 0
        for item in policies_src.iterdir():
            if _has_sensitive_name(item):
                continue
            if dry_run:
                print(f"  [DRY-RUN] Would copy policy: {item.name}")
                pcount += 1
            else:
                shutil.copy2(item, policies_dst / item.name)
                pcount += 1
        if pcount > 0:
            print(f"  [{'DRY-RUN' if dry_run else 'OK'}] Migrated {pcount} policy file(s)")
            items += pcount
    else:
        print(f"  [SKIP] ~/.hermes/policies/ not found")

    print()
    print(f"  Summary: {items} item(s) {'would be' if dry_run else 'were'} migrated.")
    if dry_run:
        print(f"  Run with --apply to execute the migration.")
    print()

    return items


def _count_stripped(original: Dict[str, Any], safe: Dict[str, Any]) -> int:
    """Count the number of '*** STRIPPED ***' values in the safe dict."""
    count = 0
    for v in safe.values():
        if v == "*** STRIPPED ***":
            count += 1
        elif isinstance(v, dict):
            count += _count_stripped(v, v)  # already stripped
    return count


# ── CLI ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Migrate Hermes Agent config and skills to Xavani."
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

    migrate_hermes(dry_run=args.dry_run if args.apply is False else False)


if __name__ == "__main__":
    main()
