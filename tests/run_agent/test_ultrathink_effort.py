"""Ultrathink effort-raise tests (run_agent._apply_magic_keywords)."""

from unittest.mock import MagicMock

import run_agent as ra


def _agent(reasoning_config=None):
    agent = MagicMock()
    agent.reasoning_config = reasoning_config
    # Bind the real effort-raise so the mock doesn't swallow it.
    agent._raise_reasoning_effort_for_turn = (
        lambda: ra.AIAgent._raise_reasoning_effort_for_turn(agent)
    )
    return agent


def _apply(agent, message):
    return ra.AIAgent._apply_magic_keywords(agent, message)


class TestEffortRaise:
    def test_ultrathink_raises_medium_to_high(self):
        agent = _agent({"effort": "medium"})
        _apply(agent, "please ultrathink this problem")
        assert agent.reasoning_config["effort"] == "high"

    def test_high_stays_high(self):
        agent = _agent({"effort": "high"})
        _apply(agent, "ultrathink this")
        assert agent.reasoning_config["effort"] == "high"

    def test_none_config_left_alone(self):
        # No explicit config = provider default path; do not invent one.
        agent = _agent(None)
        out = _apply(agent, "ultrathink this")
        assert "ultrathink" not in out
        assert agent.reasoning_config is None

    def test_non_magic_message_untouched(self):
        agent = _agent({"effort": "low"})
        out = _apply(agent, "just answer plainly")
        assert agent.reasoning_config["effort"] == "low"
        assert "answer plainly" in out

    def test_directive_note_appended(self):
        agent = _agent({"effort": "medium"})
        out = _apply(agent, "ultrathink this")
        assert "system note" in out
