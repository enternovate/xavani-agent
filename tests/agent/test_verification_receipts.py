# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Behavior tests for the SQLite verification receipt store."""

import json
import sqlite3
from dataclasses import asdict

import pytest

from agent.completion_contract import CheckReceipt
from agent.verification_receipts import ReceiptStore


def make_receipt(**changes):
    values = dict(
        receipt_id="receipt-1",
        contract_id="contract-1",
        check_id="unit",
        workspace_id="workspace-1",
        revision="r1",
        command_argv=("python3", "-m", "pytest"),
        cwd="/workspace",
        exit_code=0,
        status="passed",
        artifact_hashes=(("report.json", "a" * 64),),
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        origin="host",
    )
    values.update(changes)
    return CheckReceipt(**values)


def insert_raw_payload(path, receipt_id, payload):
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "INSERT INTO verification_receipts (receipt_id, contract_id, payload)"
            " VALUES (?, ?, ?)",
            (receipt_id, "contract-1", payload),
        )
        connection.commit()
    finally:
        connection.close()


class TestPersistence:
    def test_round_trip_returns_the_stored_receipt(self, tmp_path):
        store = ReceiptStore(tmp_path / "receipts.sqlite3")
        receipt = make_receipt()
        store.append(receipt)
        assert store.for_contract(receipt.contract_id) == (receipt,)

    def test_receipt_survives_reopening_the_store(self, tmp_path):
        path = tmp_path / "receipts.sqlite3"
        receipt = make_receipt()
        ReceiptStore(path).append(receipt)
        assert ReceiptStore(path).for_contract(receipt.contract_id) == (receipt,)

    def test_distinct_store_paths_are_isolated(self, tmp_path):
        first = ReceiptStore(tmp_path / "first.sqlite3")
        second = ReceiptStore(tmp_path / "second.sqlite3")
        first.append(make_receipt(receipt_id="receipt-first"))
        second.append(make_receipt(receipt_id="receipt-second"))
        assert [r.receipt_id for r in first.for_contract("contract-1")] == ["receipt-first"]
        assert [r.receipt_id for r in second.for_contract("contract-1")] == ["receipt-second"]

    def test_duplicate_receipt_id_is_rejected_and_keeps_the_first_value(self, tmp_path):
        store = ReceiptStore(tmp_path / "receipts.sqlite3")
        store.append(make_receipt())
        with pytest.raises(sqlite3.IntegrityError):
            store.append(make_receipt(check_id="lint"))
        assert store.for_contract("contract-1") == (make_receipt(),)

    def test_unknown_contract_id_returns_empty(self, tmp_path):
        store = ReceiptStore(tmp_path / "receipts.sqlite3")
        store.append(make_receipt())
        assert store.for_contract("contract-unknown") == ()

    def test_receipts_come_back_in_append_order(self, tmp_path):
        store = ReceiptStore(tmp_path / "receipts.sqlite3")
        store.append(make_receipt(receipt_id="receipt-b"))
        store.append(make_receipt(receipt_id="receipt-a", check_id="lint"))
        assert [r.receipt_id for r in store.for_contract("contract-1")] == [
            "receipt-b",
            "receipt-a",
        ]

    def test_round_trip_keeps_no_exit_code_and_hash_pairs(self, tmp_path):
        store = ReceiptStore(tmp_path / "receipts.sqlite3")
        receipt = make_receipt(
            status="blocked",
            exit_code=None,
            artifact_hashes=(("report.json", "a" * 64), ("log.txt", "b" * 64)),
        )
        store.append(receipt)
        stored = store.for_contract("contract-1")[0]
        assert stored == receipt
        assert stored.artifact_hashes[1] == ("log.txt", "b" * 64)
        assert stored.exit_code is None


    def test_read_of_missing_store_returns_empty_without_creating_it(self, tmp_path):
        path = tmp_path / "receipts.sqlite3"
        assert ReceiptStore(path).for_contract("contract-1") == ()
        assert not path.exists()

    def test_append_creates_parent_directories(self, tmp_path):
        store = ReceiptStore(tmp_path / "nested" / "receipts.sqlite3")
        store.append(make_receipt())
        assert store.for_contract("contract-1") == (make_receipt(),)


class TestWriteValidation:
    def test_model_origin_receipt_is_rejected_without_creating_the_store(self, tmp_path):
        path = tmp_path / "receipts.sqlite3"
        store = ReceiptStore(path)
        with pytest.raises(ValueError):
            store.append(make_receipt(origin="model"))
        assert not path.exists()

    def test_non_receipt_value_is_rejected_without_creating_the_store(self, tmp_path):
        path = tmp_path / "receipts.sqlite3"
        store = ReceiptStore(path)
        with pytest.raises(ValueError):
            store.append("not-a-receipt")
        assert not path.exists()

    def test_oversized_payload_is_rejected(self, tmp_path):
        store = ReceiptStore(tmp_path / "receipts.sqlite3")
        with pytest.raises(ValueError):
            store.append(make_receipt(cwd="/" + "x" * 70000))


class TestReadFailures:
    def test_row_missing_fields_raises_value_error(self, tmp_path):
        path = tmp_path / "receipts.sqlite3"
        store = ReceiptStore(path)
        store.append(make_receipt())
        insert_raw_payload(path, "receipt-bad", json.dumps({"receipt_id": "receipt-bad"}))
        with pytest.raises(ValueError):
            store.for_contract("contract-1")

    @pytest.mark.parametrize("field,value", [
        ("command_argv", "python3"),
        ("artifact_hashes", "not-a-list"),
        ("artifact_hashes", ["ab"]),
    ])
    def test_well_shaped_row_with_wrongly_typed_fields_raises(self, tmp_path, field, value):
        path = tmp_path / "receipts.sqlite3"
        store = ReceiptStore(path)
        store.append(make_receipt())
        payload = asdict(make_receipt())
        payload["receipt_id"] = "receipt-bad"
        payload[field] = value
        insert_raw_payload(path, "receipt-bad", json.dumps(payload))
        with pytest.raises(ValueError):
            store.for_contract("contract-1")

    def test_row_without_a_json_object_raises_value_error(self, tmp_path):
        path = tmp_path / "receipts.sqlite3"
        store = ReceiptStore(path)
        store.append(make_receipt())
        insert_raw_payload(path, "receipt-bad", json.dumps(["receipt-bad"]))
        with pytest.raises(ValueError):
            store.for_contract("contract-1")
