from __future__ import annotations


def test_update_receipt_import_succeeds():
    import xavani_cli.update_receipt as update_receipt

    assert update_receipt is not None


def test_update_receipt_exposes_main_entry():
    import xavani_cli.update_receipt as update_receipt

    assert callable(update_receipt.begin_update_receipt)
