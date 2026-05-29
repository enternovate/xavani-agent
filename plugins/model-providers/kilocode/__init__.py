# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Kilo Code provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

kilocode = ProviderProfile(
    name="kilocode",
    aliases=("kilo-code", "kilo", "kilo-gateway"),
    env_vars=("KILOCODE_API_KEY",),
    base_url="https://api.kilo.ai/api/gateway",
    default_aux_model="google/gemini-3-flash-preview",
)

register_provider(kilocode)
