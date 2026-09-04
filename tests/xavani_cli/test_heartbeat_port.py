def test_heartbeat_import_succeeds():
    import xavani_cli.heartbeat as hb

    assert hb is not None


def test_parse_interval_one_minute_returns_60():
    from xavani_cli.heartbeat import parse_interval

    assert parse_interval("1m") == 60


def test_format_interval_90_nonempty():
    from xavani_cli.heartbeat import format_interval

    assert format_interval(90) != ""
