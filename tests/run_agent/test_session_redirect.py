# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""A01: session redirect with lock.

A hard stop (/stop) and an accepted in-turn correction (redirect) share
one lock so the stop can never be replayed as a retry:

- redirect() admits a correction while the turn is active; a second
  redirect concatenates onto the first.
- interrupt(hard_cancel=True) clears any accepted redirect.
- redirect() after a hard stop returns False (the stop won the race).
- clear_interrupt(preserve_redirect=True) keeps the redirect so the loop
  can rebuild the same logical turn.
"""

from unittest.mock import MagicMock, patch

import pytest

from run_agent import AIAgent

pytestmark = pytest.mark.unit


@pytest.fixture()
def agent():
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        a = AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
        a.client = MagicMock()
        return a


def test_redirect_admits_correction(agent):
    assert agent.redirect("use the other file") is True
    assert agent._has_pending_redirect()
    assert agent._interrupt_requested
    assert agent._interrupt_message is None
    assert agent._drain_pending_redirect() == "use the other file"
    assert not agent._has_pending_redirect()


def test_redirect_concatenates_corrections(agent):
    assert agent.redirect("first correction")
    assert agent.redirect("second correction")
    drained = agent._drain_pending_redirect()
    assert "first correction" in drained
    assert "[Additional user correction]" in drained
    assert "second correction" in drained


def test_redirect_rejects_blank(agent):
    assert agent.redirect("   ") is False
    assert not agent._has_pending_redirect()


def test_hard_stop_clears_accepted_redirect(agent):
    assert agent.redirect("accepted correction")
    agent.interrupt(hard_cancel=True)
    assert not agent._has_pending_redirect()
    assert agent._interrupt_requested
    assert agent._hard_interrupt_requested.is_set()


def test_redirect_rejected_after_hard_stop(agent):
    agent.interrupt(hard_cancel=True)
    assert agent.redirect("too late") is False
    assert not agent._has_pending_redirect()


def test_redirect_rejected_after_plain_interrupt(agent):
    # A plain interrupt with a message already claimed the turn.
    agent.interrupt("user typed something")
    assert agent.redirect("correction") is False


def test_clear_interrupt_preserve_redirect(agent):
    assert agent.redirect("keep me")
    assert agent.clear_interrupt(preserve_redirect=True) is True
    assert agent._has_pending_redirect()
    assert not agent._interrupt_requested
    assert agent._drain_pending_redirect() == "keep me"


def test_clear_interrupt_preserve_without_redirect_returns_false(agent):
    assert agent.clear_interrupt(preserve_redirect=True) is False
    # Nothing was cleared — a subsequent hard stop still lands.
    agent.interrupt(hard_cancel=True)
    assert agent._interrupt_requested


def test_clear_interrupt_default_drops_redirect(agent):
    assert agent.redirect("drop me")
    agent.clear_interrupt()
    assert not agent._has_pending_redirect()
    assert not agent._hard_interrupt_requested.is_set()


def test_hard_interrupt_method(agent):
    agent.redirect("accepted")
    agent.hard_interrupt()
    assert agent._hard_interrupt_requested.is_set()
    assert not agent._has_pending_redirect()


def test_soft_interrupt_does_not_set_hard_event(agent):
    agent.interrupt("normal message")
    assert not agent._hard_interrupt_requested.is_set()
    assert agent._interrupt_message == "normal message"
