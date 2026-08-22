# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import pytest

from xavani_cli import macros


@pytest.fixture
def macros_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("XAVANI_MACROS_DIR", str(tmp_path / "macros"))
    return tmp_path / "macros"


class TestDefine:
    def test_define_and_load_roundtrip(self, macros_dir):
        macros.define_macro("weekly", ["review commits", "draft plan"])
        record = macros.load_macro("weekly")
        assert record["steps"] == ["review commits", "draft plan"]

    def test_rejects_blank_steps(self, macros_dir):
        with pytest.raises(macros.MacroError, match="non-empty"):
            macros.define_macro("blank", ["", "  "])

    def test_rejects_overwrite_without_flag(self, macros_dir):
        macros.define_macro("dup", ["one"])
        with pytest.raises(macros.MacroError, match="already exists"):
            macros.define_macro("dup", ["two"])
        macros.define_macro("dup", ["two"], overwrite=True)
        assert macros.load_macro("dup")["steps"] == ["two"]

    def test_rejects_bad_names(self, macros_dir):
        for bad in ("Has-Caps", "-lead", "x" * 40, ""):
            with pytest.raises(macros.MacroError, match="invalid macro name"):
                macros.define_macro(bad, ["step"])


class TestRender:
    def test_numbered_steps(self, macros_dir):
        macros.define_macro("tri", ["a", "b"])
        assert macros.render_macro("tri") == "1. a\n2. b"

    def test_unknown_macro_raises(self, macros_dir):
        with pytest.raises(macros.MacroError, match="no macro"):
            macros.render_macro("ghost")


class TestListRemove:
    def test_list_reports_step_counts(self, macros_dir):
        macros.define_macro("alpha", ["s1", "s2"])
        macros.define_macro("beta", ["s1"])
        listed = macros.list_macros()
        assert {m["name"]: m["steps"] for m in listed} == {"alpha": 2, "beta": 1}

    def test_remove_true_false(self, macros_dir):
        macros.define_macro("gone", ["step"])
        assert macros.remove_macro("gone") is True
        assert macros.remove_macro("gone") is False
