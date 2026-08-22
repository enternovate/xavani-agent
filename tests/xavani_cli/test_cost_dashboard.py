# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import sqlite3

import pytest

from xavani_cli import cost_dashboard


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "state.db"
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE sessions (id TEXT, model TEXT, started_at TEXT, "
        "estimated_cost_usd REAL, input_tokens INTEGER, output_tokens INTEGER)"
    )
    conn.executemany(
        "INSERT INTO sessions VALUES (?,?,?,?,?,?)",
        [
            ("s1", "model-a", "2026-08-21T09:00:00", 0.10, 100, 50),
            ("s2", "model-a", "2026-08-21T15:00:00", 0.20, 200, 60),
            ("s3", "model-b", "2026-08-22T08:00:00", 0.05, 10, 5),
        ],
    )
    conn.commit()
    conn.close()
    return path


class TestCollectRows:
    def test_rows_carry_day_and_totals(self, db):
        rows = cost_dashboard.collect_rows(db)
        assert len(rows) == 3
        assert rows[0] == {
            "id": "s1", "model": "model-a", "started_at": "2026-08-21T09:00:00",
            "day": "2026-08-21", "cost": 0.10, "tokens": 150,
        }

    def test_missing_db_returns_empty(self, tmp_path):
        assert cost_dashboard.collect_rows(tmp_path / "none.db") == []

    def test_null_fields_tolerated(self, tmp_path):
        path = tmp_path / "state.db"
        conn = sqlite3.connect(path)
        conn.execute(
            "CREATE TABLE sessions (id TEXT, model TEXT, started_at TEXT, "
            "estimated_cost_usd REAL, input_tokens INTEGER, output_tokens INTEGER)"
        )
        conn.execute("INSERT INTO sessions VALUES ('x', NULL, NULL, NULL, NULL, NULL)")
        conn.commit()
        conn.close()
        rows = cost_dashboard.collect_rows(path)
        assert rows[0]["model"] == "unknown"
        assert rows[0]["cost"] == 0.0


class TestAggregate:
    def test_group_and_sum(self, db):
        rows = cost_dashboard.collect_rows(db)
        by_model = cost_dashboard.aggregate(rows, "model")
        assert by_model["model-a"] == {"sessions": 2, "cost": pytest.approx(0.30), "tokens": 410}
        by_day = cost_dashboard.aggregate(rows, "day")
        assert set(by_day) == {"2026-08-21", "2026-08-22"}


class TestRender:
    def test_render_has_all_three_tables(self, db):
        text = cost_dashboard.render(db)
        for marker in ("By model:", "By day:", "Last 5 sessions:", "$0.35"):
            assert marker in text

    def test_empty_db_message(self, tmp_path):
        assert "No session cost data" in cost_dashboard.render(tmp_path / "none.db")
