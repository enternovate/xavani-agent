# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Ollama Cloud provider profile."""

from providers import register_provider
from providers.base import ProviderProfile

ollama_cloud = ProviderProfile(
    name="ollama-cloud",
    aliases=("ollama_cloud",),
    default_aux_model="nemotron-3-nano:30b",
    env_vars=("OLLAMA_API_KEY",),
    base_url="https://ollama.com/v1",
)

register_provider(ollama_cloud)
