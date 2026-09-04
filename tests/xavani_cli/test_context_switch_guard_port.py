import importlib


def test_context_switch_guard_import_succeeds():
    mod = importlib.import_module("xavani_cli.context_switch_guard")
    assert mod is not None


def test_threshold_tokens_returns_positive_int():
    from xavani_cli.context_switch_guard import _threshold_tokens

    assert _threshold_tokens(200000, 0.5) > 0
    assert isinstance(_threshold_tokens(200000, 0.5), int)


def test_merge_preflight_compression_warning_callable():
    from xavani_cli.context_switch_guard import merge_preflight_compression_warning

    assert callable(merge_preflight_compression_warning)
