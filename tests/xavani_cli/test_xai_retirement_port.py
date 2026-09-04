from __future__ import annotations


def test_xai_retirement_import_succeeds():
    import xavani_cli.xai_retirement as m

    assert m is not None


def test_find_retired_xai_refs_empty_config_returns_list():
    from xavani_cli.xai_retirement import find_retired_xai_refs

    assert find_retired_xai_refs({}) == []


def test_retirement_date_nonempty_string():
    from xavani_cli.xai_retirement import RETIREMENT_DATE

    assert isinstance(RETIREMENT_DATE, str)
    assert RETIREMENT_DATE.strip() != ""
