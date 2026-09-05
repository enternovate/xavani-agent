import importlib


def test_kanban_transfer_imports():
    mod = importlib.import_module("xavani_cli.kanban_transfer")
    assert mod is not None


def test_archive_format_value():
    mod = importlib.import_module("xavani_cli.kanban_transfer")
    assert mod.ARCHIVE_FORMAT == "xavani-kanban-board"


def test_main_transfer_entry_exposed():
    mod = importlib.import_module("xavani_cli.kanban_transfer")
    assert callable(getattr(mod, "export_board", None))
    assert callable(getattr(mod, "import_board", None))
