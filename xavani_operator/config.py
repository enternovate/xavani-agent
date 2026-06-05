# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Product-config loader for the operator (v0.7.0 operator U2).

Parses and validates ``xavani.product.yaml`` — the file you point the operator at
when you "plug it in". It describes *what* the product is, *what* you want, *where*
to promote, *how* it should behave (brand, constraints, budgets), and *when* to
run (schedule). Validation is via pydantic v2 so mistakes surface as actionable
errors rather than mysterious ``KeyError``s deep in the loop.

Pure parsing/validation — **no LLM, no network** (R10). Mirrors the repo's yaml
conventions (``pyyaml`` ``safe_load``; data lives under the repo / ``~/.xavani``).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError, model_validator


class ConfigError(Exception):
    """Raised when ``xavani.product.yaml`` is present but invalid."""


class ProductInfo(BaseModel):
    """Identity of the product being operated."""

    name: str
    description: str = ""
    repo: str = "."
    stack: list[str] = Field(default_factory=list)


class Goal(BaseModel):
    """A ranked objective the operator works toward."""

    id: str
    intent: str = ""
    priority: int = 3  # 1 = highest
    success_metric: str = ""


class Channel(BaseModel):
    """A promotion / comms channel (x, discord, telegram, email, blog, …)."""

    platform: str
    handle: str = ""
    cadence: str = ""


class Brand(BaseModel):
    """Voice and guardrails for any generated outward content."""

    voice: str = ""
    tone: str = ""
    dos: list[str] = Field(default_factory=list)
    donts: list[str] = Field(default_factory=list)
    assets: list[str] = Field(default_factory=list)


class Constraints(BaseModel):
    """Hard limits the operator must respect."""

    no_touch_paths: list[str] = Field(default_factory=list)
    allowed_actions: list[str] = Field(default_factory=list)
    content_policy: str = ""


class Budgets(BaseModel):
    """Cost / action ceilings (0 = unlimited)."""

    llm_tokens_per_day: int = 0
    spend_per_day: float = 0.0
    max_actions_per_cycle: int = 10


class Approval(BaseModel):
    """Approval posture: per-action tier overrides + veto/quiet settings."""

    tier_overrides: dict[str, int] = Field(default_factory=dict)
    auto_window: int = 0  # seconds a Tier-1 action waits for a veto before proceeding
    quiet_hours: str = ""


class Schedule(BaseModel):
    """When the operator runs and what wakes it up."""

    cycle_cadence: str = ""  # cron expression for continuous mode
    watchers: list[str] = Field(default_factory=list)


class ProductConfig(BaseModel):
    """The validated whole-product configuration."""

    product: ProductInfo
    goals: list[Goal] = Field(default_factory=list)
    channels: list[Channel] = Field(default_factory=list)
    brand: Brand = Field(default_factory=Brand)
    constraints: Constraints = Field(default_factory=Constraints)
    budgets: Budgets = Field(default_factory=Budgets)
    approval: Approval = Field(default_factory=Approval)
    schedule: Schedule = Field(default_factory=Schedule)

    @model_validator(mode="before")
    @classmethod
    def _blank_sections_use_defaults(cls, data: object) -> object:
        """Treat an empty/commented-out section (YAML null) as "use the default".

        A user who comments out every goal leaves ``goals:`` → ``None``; rather
        than error, drop such keys so the field's default applies. ``product``
        stays required: a null ``product`` is dropped, then flagged as missing.
        """
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if v is not None}
        return data


def load_product_config(path: str | Path) -> ProductConfig:
    """Load + validate ``xavani.product.yaml`` at ``path``.

    Raises :class:`FileNotFoundError` if the file is absent, and
    :class:`ConfigError` if it is present but unparseable or invalid.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"product config not found: {p}")
    try:
        raw = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"could not parse {p.name}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError(f"{p.name} must be a mapping at the top level")
    try:
        return ProductConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid {p.name}:\n{exc}") from exc
