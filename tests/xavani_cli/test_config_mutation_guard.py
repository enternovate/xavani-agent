import pytest

from xavani_cli.config import _load_user_config_for_mutation, require_readable_config_before_write


def test_require_readable_config_before_write_missing_returns_empty(tmp_path):
    assert require_readable_config_before_write(tmp_path / "config.yaml") == {}


def test_require_readable_config_before_write_unparseable_raises(tmp_path):
    bad = tmp_path / "config.yaml"
    bad.write_text(":\n: bad: [unclosed", encoding="utf-8")
    with pytest.raises(RuntimeError):
        require_readable_config_before_write(bad)


def test_load_user_config_for_mutation_missing_returns_empty(tmp_path):
    assert _load_user_config_for_mutation(tmp_path / "config.yaml") == {}
