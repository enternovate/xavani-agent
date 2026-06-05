# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Scaffolding for `xavani operator init` (v0.7.0 operator U5).

Writes a commented starter ``xavani.product.yaml`` so a user can "plug in" the
operator in one command and then fill in goals/channels/brand. The starter is
guaranteed to be a *valid* config (it round-trips through
:func:`xavani_operator.config.load_product_config`).

Pure, local, deterministic — no LLM, no network (R10).
"""

from __future__ import annotations

from pathlib import Path

CONFIG_FILENAME = "xavani.product.yaml"
DEFAULT_NAME = "My Product"

_TEMPLATE = """# xavani.product.yaml — plug Xavani's operator into your product.
# The operator reads this to decide what to build and how to promote, then
# proposes plans you approve. Fill in goals/channels/brand; the rest has safe
# defaults. See planning/v0.7.0/DESIGN.md for the full field reference.

product:
  name: {name}
  description: ""        # one line: what it is
  repo: "."             # path to the repo the operator works in
  stack: []              # e.g. [python, react, postgres]

goals: []                # ranked objectives (priority 1 = highest)
  # - id: launch
  #   intent: ship and announce v1 onboarding
  #   priority: 1
  #   success_metric: signups

channels: []             # where to promote / communicate
  # - platform: x        # x | discord | telegram | email | blog
  #   handle: "@you"
  #   cadence: daily

brand:
  voice: ""             # how outward content should sound
  dos: []
  donts: []

constraints:
  no_touch_paths: []     # paths the operator must never modify
  content_policy: ""

budgets:
  llm_tokens_per_day: 0      # 0 = unlimited
  spend_per_day: 0           # 0 = unlimited
  max_actions_per_cycle: 10

approval:
  tier_overrides: {{}}        # e.g. {{post_external: 2}}  (0 auto .. 3 block)
  auto_window: 0             # seconds a Tier-1 action waits for a veto

schedule:
  cycle_cadence: ""         # cron expr for continuous `xavani operator run`
  watchers: []               # repo | issues | metrics
"""


def _yaml_double_quote(value: str) -> str:
    """Render ``value`` as a safe YAML double-quoted scalar."""
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def starter_product_yaml(name: str = DEFAULT_NAME) -> str:
    """Return the text of a valid starter ``xavani.product.yaml``."""
    return _TEMPLATE.format(name=_yaml_double_quote(name or DEFAULT_NAME))


def init_product_config(
    directory: str | Path,
    name: str | None = None,
    force: bool = False,
) -> Path:
    """Write a starter config into ``directory``; return its path.

    Raises :class:`FileExistsError` if a config already exists and ``force`` is
    not set, so we never silently clobber a user's product file.
    """
    d = Path(directory)
    d.mkdir(parents=True, exist_ok=True)
    path = d / CONFIG_FILENAME
    if path.exists() and not force:
        raise FileExistsError(
            f"{path} already exists — pass force=True (or --force) to overwrite"
        )
    path.write_text(starter_product_yaml(name or DEFAULT_NAME), encoding="utf-8")
    return path
