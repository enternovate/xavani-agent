# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""xAI (Grok) provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

xai = ProviderProfile(
    name="xai",
    aliases=("grok", "x-ai", "x.ai"),
    api_mode="codex_responses",
    env_vars=("XAI_API_KEY",),
    base_url="https://api.x.ai/v1",
    auth_type="api_key",
)

register_provider(xai)
