def test_moa_cmd_imports():
    import xavani_cli.moa_cmd as moa_cmd

    assert moa_cmd is not None


def test_cmd_moa_is_callable():
    from xavani_cli.moa_cmd import cmd_moa

    assert callable(cmd_moa)
