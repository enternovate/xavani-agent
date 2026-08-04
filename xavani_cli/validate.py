# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Pre-flight health check: ``xavani validate``.

Runs a battery of offline checks before go-live:

1. ``config.yaml`` exists and parses as YAML.
2. ``config.yaml`` conforms to the core JSON schema (see
   :mod:`xavani_cli.config_schema`).
3. ``.env`` exists in ``XAVANI_HOME``.
4. Provider API keys are present and non-blank in ``.env``.
5. ``XAVANI_HOME`` is writable.
6. Model registry sanity: a default model is configured and the model
   catalog cache (if present) is valid JSON.

Prints one PASS/FAIL line per check (mirroring ``xavani doctor`` styling)
and returns exit code 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List

import yaml

from xavani_cli.config import get_config_path, get_env_path
from xavani_cli.config_schema import validate_config_schema
from xavani_cli.doctor import (
    Colors,
    _PROVIDER_ENV_HINTS,
    check_fail,
    check_ok,
    check_warn,
    color,
    _section,
)
from xavani_constants import get_xavani_home


def _read_dotenv(path: Path) -> Dict[str, str]:
    """Parse a ``.env`` file into ``{VAR: value}`` (comments/blank skipped)."""
    result: Dict[str, str] = {}
    if not path.is_file():
        return result
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return result
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            result[key] = value.strip()
    return result


def _home_writable(home: Path) -> bool:
    """Probe XAVANI_HOME with a throwaway file (create + delete)."""
    probe = home / f".validate_probe_{os.getpid()}"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except OSError:
        return False


def _check_model_registry(cfg: Any) -> bool:
    """Sanity-check the configured model and the model catalog cache."""
    ok = True

    model_cfg = cfg.get("model") if isinstance(cfg, dict) else None
    default_model = ""
    if isinstance(model_cfg, dict):
        default_model = str(model_cfg.get("default") or "").strip()
    elif isinstance(model_cfg, str):
        default_model = model_cfg.strip()
    if not default_model:
        check_fail(
            "No default model configured",
            "set model.default in config.yaml (e.g. anthropic/claude-sonnet-4)",
        )
        ok = False
    else:
        check_ok(f"Default model configured: {default_model}")

    catalog = get_xavani_home() / "cache" / "model_catalog.json"
    if catalog.exists():
        try:
            json.loads(catalog.read_text(encoding="utf-8"))
            check_ok("Model catalog cache is valid JSON")
        except (json.JSONDecodeError, OSError, UnicodeDecodeError) as e:
            check_fail(
                "Model catalog cache is corrupt",
                f"{catalog} ({e}) — delete the file to refetch",
            )
            ok = False
    return ok


def run_validate(args: Any = None) -> int:
    """Run all pre-flight checks; return 0 on success, 1 on any failure."""
    failures = 0

    print()
    print(color("┌─────────────────────────────────────────────────────────┐", Colors.CYAN))
    print(color("│            ✅ Xavani Pre-flight Validate                 │", Colors.CYAN))
    print(color("└─────────────────────────────────────────────────────────┘", Colors.CYAN))

    home = get_xavani_home()

    # ── 1. config.yaml exists + parses ────────────────────────────────────
    _section("Config")
    config_path = get_config_path()
    config: Any = None
    if not config_path.is_file():
        check_fail("config.yaml missing", f"expected at {config_path}")
        failures += 1
    else:
        try:
            with open(config_path, encoding="utf-8") as f:
                config = yaml.safe_load(f)
            check_ok("config.yaml parses", str(config_path))
            if config is None:
                config = {}
        except yaml.YAMLError as e:
            check_fail("config.yaml is not valid YAML", str(e))
            failures += 1

    # ── 2. config.yaml JSON schema (C13) ──────────────────────────────────
    if config is not None:
        schema_errors = validate_config_schema(config)
        if schema_errors:
            check_fail(
                f"config.yaml schema: {len(schema_errors)} violation(s)",
                schema_errors[0],
            )
            failures += 1
        else:
            check_ok("config.yaml conforms to core JSON schema")

    # ── 3. .env exists ────────────────────────────────────────────────────
    _section("Secrets")
    env_path = get_env_path()
    if env_path.is_file():
        check_ok(".env exists", str(env_path))
    else:
        check_fail(".env missing", f"expected at {env_path} (run `xavani setup`)")
        failures += 1

    # ── 4. provider keys present, non-empty, not whitespace ───────────────
    env_vars = _read_dotenv(env_path)
    present = [k for k in _PROVIDER_ENV_HINTS if k in env_vars]
    blank = [k for k in present if not env_vars[k].strip()]
    non_blank = [k for k in present if env_vars[k].strip()]
    if non_blank:
        check_ok(
            f"{len(non_blank)} provider key(s) present",
            ", ".join(sorted(non_blank)),
        )
        if blank:
            check_warn(
                f"{len(blank)} provider key(s) present but blank",
                ", ".join(sorted(blank)),
            )
    else:
        check_fail(
            "No provider API keys found",
            "add a provider key to .env (e.g. OPENAI_API_KEY=…) or run `xavani setup`",
        )
        failures += 1

    # ── 5. XAVANI_HOME writable ───────────────────────────────────────────
    _section("Environment")
    if _home_writable(home):
        check_ok("XAVANI_HOME writable", str(home))
    else:
        check_fail("XAVANI_HOME not writable", f"check permissions on {home}")
        failures += 1

    # ── 6. model registry sanity ──────────────────────────────────────────
    if config is not None:
        _section("Model registry")
        if not _check_model_registry(config):
            failures += 1

    # ── summary ───────────────────────────────────────────────────────────
    print()
    if failures:
        print(
            color(
                f"  ✗ {failures} check(s) failed — fix the issues above before go-live.",
                Colors.RED,
                Colors.BOLD,
            )
        )
    else:
        print(color("  ✓ All checks passed — ready to go live.", Colors.GREEN, Colors.BOLD))
    print()
    return 0 if failures == 0 else 1
