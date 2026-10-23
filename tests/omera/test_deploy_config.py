from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]


def render_config() -> dict:
    return yaml.safe_load((ROOT / "render.yaml").read_text())


def service() -> dict:
    return render_config()["services"][0]


def test_one_free_python_web_service():
    assert service()["type"] == "web"
    assert service()["runtime"] == "python"
    assert service()["plan"] == "free"
    assert service()["healthCheckPath"] == "/health"


def test_binds_the_render_port_on_all_interfaces():
    command = service()["startCommand"]
    assert "0.0.0.0" in command
    assert "$PORT" in command


def test_build_uses_the_omera_requirements():
    assert "requirements-omera.txt" in service()["buildCommand"]


def test_requirements_cover_the_runtime():
    text = (ROOT / "requirements-omera.txt").read_text()
    for package in ("fastapi", "uvicorn", "httpx", "ddgs"):
        assert package in text


def test_python_version_is_pinned():
    env = {item["key"]: item.get("value") for item in service()["envVars"]}
    assert env["PYTHON_VERSION"].startswith("3.12")


def test_research_chain_is_configured():
    env = {item["key"]: item.get("value") for item in service()["envVars"]}
    assert env["RESEARCH_PROVIDER"] == "tavily,exa,ddgs,bing"
    assert env["JINA_READER"] == "auto"


def test_blueprint_needs_no_manual_input():
    """A free deploy must apply without a model or search key."""
    items = {item["key"]: item for item in service()["envVars"]}
    assert items["API_SERVER_KEY"]["generateValue"] is True
    assert items["KEYLESS_MODEL"]["value"] == "off"
    assert items["KEYLESS_MODEL_URL"]["value"] == "https://text.pollinations.ai/openai"
    for item in service()["envVars"]:
        assert item.get("sync") is not True
        assert item["key"] not in {"INFERENCE_API_KEY", "TAVILY_API_KEY", "EXA_API_KEY"}
