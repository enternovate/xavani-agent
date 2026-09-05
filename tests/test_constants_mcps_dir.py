from pathlib import Path

from xavani_constants import get_optional_mcps_dir


def test_get_optional_mcps_dir_imports():
    assert callable(get_optional_mcps_dir)


def test_get_optional_mcps_dir_default_ends_with_optional_mcps(tmp_path, monkeypatch):
    monkeypatch.delenv("XAVANI_OPTIONAL_MCPS", raising=False)
    monkeypatch.setattr("xavani_constants._get_packaged_data_dir", lambda _name: None)
    assert str(get_optional_mcps_dir(default=Path(tmp_path))).endswith("optional-mcps") or str(
        get_optional_mcps_dir()
    ).endswith("optional-mcps")
