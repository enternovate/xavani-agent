def test_prompt_size_import_succeeds():
    import xavani_cli.prompt_size
    assert xavani_cli.prompt_size is not None


def test_fmt_kb_returns_string_for_2048():
    from xavani_cli.prompt_size import _fmt_kb
    result = _fmt_kb(2048)
    assert isinstance(result, str)


def test_bytes_returns_positive_int_for_short_string():
    from xavani_cli.prompt_size import _bytes
    result = _bytes("hello")
    assert isinstance(result, int)
    assert result > 0
