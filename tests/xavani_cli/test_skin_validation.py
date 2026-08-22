# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from pathlib import Path

import pytest

from xavani_cli import skin_engine


VALID_SKIN = """
name: test-skin
colors:
  banner_title: "#ff0000"
  ui_accent: "#00ff00"
  ui_ok: "#00ff00"
  ui_error: "#ff0000"
  ui_warn: "#ffff00"
branding:
  agent_name: "Test"
"""


class TestValidateSkinData:
    def test_valid_skin_has_no_problems(self):
        import yaml

        assert skin_engine.validate_skin_data(yaml.safe_load(VALID_SKIN)) == []

    def test_non_mapping_reports_problem(self):
        assert skin_engine.validate_skin_data(["nope"]) == [
            "skin definition is not a mapping"
        ]

    def test_missing_name_reported(self):
        problems = skin_engine.validate_skin_data({"colors": {}, "branding": {}})
        assert any("name" in p for p in problems)

    def test_missing_color_key_reported(self):
        import yaml

        data = yaml.safe_load(VALID_SKIN)
        del data["colors"]["ui_error"]
        problems = skin_engine.validate_skin_data(data)
        assert any("colors.ui_error" in p for p in problems)

    def test_missing_branding_agent_name_reported(self):
        import yaml

        data = yaml.safe_load(VALID_SKIN)
        del data["branding"]["agent_name"]
        problems = skin_engine.validate_skin_data(data)
        assert any("branding.agent_name" in p for p in problems)


class TestLoadSkinStrict:
    def test_builtin_skin_loads(self):
        config = skin_engine.load_skin_strict("xavani-darkblue")
        assert config is not None

    def test_unknown_skin_raises(self):
        with pytest.raises(skin_engine.SkinValidationError, match="not found"):
            skin_engine.load_skin_strict("no-such-skin-anywhere")

    def test_broken_user_skin_raises_with_problems(self, tmp_path, monkeypatch):
        broken = tmp_path / "broken.yaml"
        broken.write_text("description: no name or colors\n", encoding="utf-8")
        monkeypatch.setattr(skin_engine, "_skins_dir", lambda: tmp_path)
        with pytest.raises(skin_engine.SkinValidationError, match="missing"):
            skin_engine.load_skin_strict("broken")

    def test_shipped_skins_all_pass_strict_validation(self):
        skins_dir = Path(__file__).resolve().parents[2] / "xavani_cli" / "skins"
        for yaml_file in sorted(skins_dir.glob("*.yaml")):
            import yaml

            data = yaml.safe_load(yaml_file.read_text(encoding="utf-8"))
            problems = skin_engine.validate_skin_data(data)
            assert problems == [], f"{yaml_file.name}: {problems}"
