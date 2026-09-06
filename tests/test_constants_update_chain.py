from xavani_constants import (
    is_first_party_module,
    iter_xavani_node_dirs,
    partial_update_hint,
    venv_python_path,
)


def test_venv_python_path_joins_bin_python(tmp_path):
    assert venv_python_path(tmp_path / "venv", windows=False) == tmp_path / "venv" / "bin" / "python"


def test_iter_xavani_node_dirs_returns_list(tmp_path):
    assert isinstance(iter_xavani_node_dirs(tmp_path), list)


def test_is_first_party_module_xavani_cli_true_requests_false():
    assert is_first_party_module("xavani_cli") is True
    assert is_first_party_module("requests") is False


def test_partial_update_hint_empty_list_for_value_error():
    assert partial_update_hint(ValueError("boom")) == []
