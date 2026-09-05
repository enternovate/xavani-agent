from __future__ import annotations


def test_update_contract_import_succeeds():
    import xavani_cli.update_contract as update_contract

    assert update_contract is not None


def test_update_contract_exposes_main_entry():
    import xavani_cli.update_contract as update_contract

    assert callable(update_contract.evaluate_update_admission)
