"""Environment settings for the Omera API surface."""
from __future__ import annotations

import os
from dataclasses import dataclass

MIN_KEY_LENGTH = 32


@dataclass(frozen=True)
class Settings:
    api_key: str
    model_name: str
    inference_base_url: str
    inference_api_key: str
    inference_model: str
    inference_fallback_models: str
    max_tokens: int
    api_key_previous: str = ""

    @property
    def configured(self) -> bool:
        return bool(self.api_key and self.inference_api_key and self.inference_model)

    def validate(self) -> None:
        """Raise when the service key cannot protect the endpoint."""
        if len(self.api_key) < MIN_KEY_LENGTH:
            raise ValueError("API_SERVER_KEY_TOO_SHORT")
        if not self.inference_api_key:
            raise ValueError("INFERENCE_API_KEY_MISSING")

    @classmethod
    def from_env(cls, env=None) -> "Settings":
        resolved = env if env is not None else os.environ
        try:
            max_tokens = int(resolved.get("INFERENCE_MAX_TOKENS", "2048"))
        except ValueError:
            max_tokens = 2048
        return cls(
            api_key=(resolved.get("API_SERVER_KEY") or "").strip(),
            model_name=(resolved.get("XAVANI_MODEL_NAME") or "omera").strip(),
            inference_base_url=(
                resolved.get("INFERENCE_BASE_URL") or "https://openrouter.ai/api/v1"
            ).rstrip("/"),
            inference_api_key=(resolved.get("INFERENCE_API_KEY") or "").strip(),
            inference_model=(resolved.get("INFERENCE_MODEL") or "").strip(),
            inference_fallback_models=(
                resolved.get("INFERENCE_FALLBACK_MODELS") or ""
            ).strip(),
            max_tokens=max(256, min(8192, max_tokens)),
            api_key_previous=(resolved.get("API_SERVER_KEY_PREVIOUS") or "").strip(),
        )
