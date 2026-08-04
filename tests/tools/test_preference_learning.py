# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""C08: per-user preference learning tests."""

import pytest

import tools.preference_learning as pl
from tools.preference_learning import (
    all_preferences,
    extract_preferences,
    learn_from_message,
    preferences_for,
)


@pytest.fixture(autouse=True)
def _isolated(tmp_path, monkeypatch):
    store = tmp_path / "user_preferences.json"
    monkeypatch.setattr(pl, "_prefs_path", lambda home=None: store)
    yield store
    try:
        store.unlink(missing_ok=True)
    except OSError:
        pass


# ── extraction ──────────────────────────────────────────────────────


def test_always_use_extracted():
    statements = extract_preferences("Always use pytest for running tests.")
    assert statements
    assert any("Always use pytest" in s for s in statements)


def test_i_prefer_extracted():
    statements = extract_preferences("I prefer concise responses.")
    assert statements
    assert any("I prefer concise" in s for s in statements)


def test_stop_doing_extracted():
    statements = extract_preferences("Stop using markdown tables in replies.")
    assert statements
    assert any("Stop using markdown" in s for s in statements)


def test_from_now_on_extracted():
    statements = extract_preferences("From now on, use British spelling.")
    assert statements


def test_one_off_request_not_learned():
    assert extract_preferences("Use pytest for this one test, please.") == []


def test_plain_question_not_learned():
    assert extract_preferences("What is the weather today?") == []


def test_vague_object_filtered():
    assert extract_preferences("Always use it.") == []  # no learnable object


def test_no_duplicates():
    statements = extract_preferences(
        "Always use ruff. Always use ruff for linting."
    )
    assert len(statements) == len(set(statements))


# ── learning + persistence ─────────────────────────────────────────


def test_learn_and_recall(_isolated):
    learned = learn_from_message("user-1", "Always use pytest for tests.")
    assert learned
    # Extraction strips trailing punctuation.
    assert "Always use pytest for tests" in preferences_for("user-1")


def test_learned_per_user_isolated(_isolated):
    learn_from_message("user-A", "I prefer blue themes.")
    assert preferences_for("user-A")
    assert preferences_for("user-B") == []


def test_repeat_confirms_not_duplicated(_isolated):
    learn_from_message("user-1", "Always use pytest for tests.")
    learned_again = learn_from_message("user-1", "Always use pytest for tests.")
    assert learned_again == []  # already known; count incremented
    assert len(preferences_for("user-1")) == 1


def test_persistence_across_load(_isolated):
    learn_from_message("user-1", "I prefer concise responses.")
    assert "I prefer concise responses" in preferences_for("user-1")


def test_all_preferences_shape(_isolated):
    learn_from_message("user-1", "Always use pytest for tests.")
    learn_from_message("user-2", "I prefer TypeScript.")
    all_prefs = all_preferences()
    assert set(all_prefs.keys()) == {"user-1", "user-2"}


def test_most_confirmed_first(_isolated):
    learn_from_message("user-1", "I prefer blue themes.")
    learn_from_message("user-1", "Always use ruff.")
    learn_from_message("user-1", "Always use ruff.")  # confirm twice
    ordered = preferences_for("user-1")
    assert ordered[0] == "Always use ruff"  # stored punctuation-stripped


def test_plain_message_learns_nothing(_isolated):
    assert learn_from_message("user-1", "Just checking in.") == []
    assert preferences_for("user-1") == []
