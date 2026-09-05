from xavani_cli.linux_desktop_entry import (
    DESKTOP_ENTRY_NAME,
    render_desktop_entry,
)


def test_import_succeeds():
    assert DESKTOP_ENTRY_NAME is not None
    assert render_desktop_entry is not None


def test_entry_uses_xavani_branding():
    assert DESKTOP_ENTRY_NAME == "xavani.desktop"
    rendered = render_desktop_entry("xavani desktop", "xavani")
    assert "[Desktop Entry]" in rendered
    assert "Xavani" in rendered
    assert "Hermes" not in rendered
