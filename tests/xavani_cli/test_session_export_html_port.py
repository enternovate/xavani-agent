import importlib


def test_session_export_html_imports():
    mod = importlib.import_module("xavani_cli.session_export_html")
    assert mod is not None


def test_sessions_to_html_renders_static_session():
    mod = importlib.import_module("xavani_cli.session_export_html")
    session = {
        "id": "abc123",
        "title": "Hello",
        "messages": [
            {"role": "user", "content": "hi there", "timestamp": "2026-01-01T00:00:00"},
            {"role": "assistant", "content": "hello back", "timestamp": "2026-01-01T00:00:01"},
        ],
    }
    out = mod.sessions_to_html([session])
    assert isinstance(out, str)
    assert "Hello" in out
    assert "hi there" in out
    assert "hello back" in out
