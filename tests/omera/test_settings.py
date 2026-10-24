import pytest

from xavani_omera.config import Settings


def test_missing_key_is_not_configured():
    settings = Settings.from_env({})
    assert settings.configured is False


def test_reads_required_values():
    settings = Settings.from_env({
        "API_SERVER_KEY": "x" * 32,
        "INFERENCE_BASE_URL": "https://example.invalid/v1/",
        "INFERENCE_API_KEY": "k",
        "INFERENCE_MODEL": "model",
    })
    assert settings.configured is True
    assert settings.model_name == "omera"
    assert settings.max_tokens == 2048
    assert settings.inference_base_url == "https://example.invalid/v1"


def test_rejects_a_short_key():
    with pytest.raises(ValueError):
        Settings.from_env({"API_SERVER_KEY": "short"}).validate()


def test_reads_the_previous_key():
    settings = Settings.from_env({
        "API_SERVER_KEY": "x" * 32,
        "API_SERVER_KEY_PREVIOUS": "y" * 32,
        "INFERENCE_API_KEY": "k",
        "INFERENCE_MODEL": "model",
    })
    assert settings.api_key_previous == "y" * 32


def test_configured_without_a_model_key():
    settings = Settings.from_env({"API_SERVER_KEY": "x" * 32})
    assert settings.configured is True
    assert settings.model_available is False
    settings.validate()
