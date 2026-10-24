# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""SQLite persistence for host verification receipts.

The store only ever holds host-origin evidence: a receipt produced by a
model is rejected before any file is created, so a reopened store can be
trusted as a record of what the host actually ran.
"""

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Iterator, Tuple

from agent.completion_contract import CheckReceipt

_SCHEMA = """
CREATE TABLE IF NOT EXISTS verification_receipts (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    receipt_id TEXT NOT NULL UNIQUE,
    contract_id TEXT NOT NULL,
    payload TEXT NOT NULL
)
"""

_INSERT = (
    "INSERT INTO verification_receipts (receipt_id, contract_id, payload) VALUES (?, ?, ?)"
)
_SELECT_BY_CONTRACT = (
    "SELECT payload FROM verification_receipts WHERE contract_id = ? ORDER BY seq"
)

_MAX_PAYLOAD_BYTES = 65536


def _decode(payload: str) -> CheckReceipt:
    try:
        values = json.loads(payload)
        if not isinstance(values, dict):
            raise TypeError("receipt payload shall be an object")
        argv = values["command_argv"]
        hashes = values["artifact_hashes"]
        if not isinstance(argv, (list, tuple)):
            raise TypeError("command_argv shall be a sequence")
        if not isinstance(hashes, (list, tuple)):
            raise TypeError("artifact_hashes shall be a sequence")
        for pair in hashes:
            if not isinstance(pair, (list, tuple)) or len(pair) != 2:
                raise TypeError("artifact hashes shall be pairs")
        values["command_argv"] = tuple(argv)
        values["artifact_hashes"] = tuple(tuple(pair) for pair in hashes)
        return CheckReceipt(**values)
    except (json.JSONDecodeError, KeyError, TypeError) as error:
        raise ValueError("The stored receipt payload is malformed.") from error


class ReceiptStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            yield connection
        finally:
            connection.close()

    def append(self, receipt: CheckReceipt) -> None:
        if not isinstance(receipt, CheckReceipt) or receipt.origin != "host":
            raise ValueError("The receipt store shall only append host receipts.")
        payload = json.dumps(asdict(receipt), sort_keys=True, allow_nan=False)
        if len(payload.encode("utf-8")) > _MAX_PAYLOAD_BYTES:
            raise ValueError("The receipt payload shall not exceed 65536 bytes.")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as connection:
            connection.execute(_SCHEMA)
            with connection:
                connection.execute(
                    _INSERT, (receipt.receipt_id, receipt.contract_id, payload)
                )

    def for_contract(self, contract_id: str) -> Tuple[CheckReceipt, ...]:
        if not self.path.exists():
            return ()
        with self._connection() as connection:
            connection.execute(_SCHEMA)
            rows = connection.execute(_SELECT_BY_CONTRACT, (contract_id,)).fetchall()
        return tuple(_decode(row[0]) for row in rows)
