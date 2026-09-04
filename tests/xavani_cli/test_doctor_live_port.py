import importlib


def test_doctor_live_imports():
    mod = importlib.import_module("xavani_cli.doctor_live")
    assert mod is not None


def test_default_probe_timeout_positive():
    mod = importlib.import_module("xavani_cli.doctor_live")
    assert isinstance(mod.DEFAULT_PROBE_TIMEOUT, (int, float))
    assert mod.DEFAULT_PROBE_TIMEOUT > 0


def test_classify_http_pass_on_200():
    mod = importlib.import_module("xavani_cli.doctor_live")

    class _Resp:
        status_code = 200

    result = mod._classify_http("Probe", _Resp(), "SOME_KEY")
    assert result.status == "pass"
    assert result.name == "Probe"
