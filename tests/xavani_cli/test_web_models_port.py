from __future__ import annotations


def test_web_models_import_succeeds():
    import xavani_cli.web_models as web_models

    assert web_models is not None


def test_web_models_config_update_imports_from_ported_module():
    from xavani_cli.web_models import ConfigUpdate

    assert ConfigUpdate is not None
