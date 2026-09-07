def test_nous_account_imports():
    import xavani_cli.nous_account as mod

    assert mod is not None


def test_nous_account_exposes_main_entries():
    from xavani_cli import nous_account

    assert callable(nous_account.get_nous_portal_account_info)
    assert callable(nous_account.nous_portal_topup_url)
    assert callable(nous_account.reset_nous_portal_account_info_cache)


def test_topup_url_falls_back_to_portal():
    from xavani_cli.nous_account import nous_portal_topup_url

    url = nous_portal_topup_url(None)
    assert isinstance(url, str)
    assert "nousresearch.com" not in url
