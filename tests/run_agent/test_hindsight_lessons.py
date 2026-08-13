# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Focused tests for completed-task hindsight lesson retention."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

import run_agent
from agent.background_review import write_hindsight_lesson

@pytest.fixture
def agent():
    return SimpleNamespace(_memory_enabled=True, _memory_store=object())


@pytest.mark.unit
def test_completed_task_extracts_and_writes_a_concise_lesson(agent):
    with patch("tools.memory_tool.memory_tool") as memory_write:
        memory_write.return_value = '{"success": true, "staged": false}'

        assert write_hindsight_lesson(
            agent,
            task_id="task-42",
            final_response="Implemented the retry guard.\nLesson: keep retries bounded.",
        ) is True

    memory_write.assert_called_once()
    call = memory_write.call_args.kwargs
    assert call["action"] == "add"
    assert call["target"] == "memory"
    assert call["store"] is agent._memory_store
    assert "task-42" in call["content"]
    assert "keep retries bounded" in call["content"]


@pytest.mark.unit
@pytest.mark.parametrize("final_response", ["", "   ", "(empty)", "Lesson: (empty)"])
def test_empty_or_sentinel_lesson_content_does_not_write(agent, final_response):
    with patch("tools.memory_tool.memory_tool") as memory_write:
        assert write_hindsight_lesson(
            agent,
            task_id="task-42",
            final_response=final_response,
        ) is False

    memory_write.assert_not_called()


@pytest.mark.unit
def test_missing_task_id_does_not_write(agent):
    with patch("tools.memory_tool.memory_tool") as memory_write:
        assert write_hindsight_lesson(
            agent,
            task_id="",
            final_response="Implemented the task.",
        ) is False

    memory_write.assert_not_called()


@pytest.mark.unit
@pytest.mark.parametrize(
    ("completed", "interrupted"),
    [(False, False), (True, True)],
)
def test_failed_or_interrupted_task_does_not_write(agent, completed, interrupted):
    with patch("tools.memory_tool.memory_tool") as memory_write:
        assert write_hindsight_lesson(
            agent,
            task_id="task-42",
            final_response="The task stopped before completion.",
            completed=completed,
            interrupted=interrupted,
        ) is False

    memory_write.assert_not_called()


@pytest.mark.unit
def test_disabled_memory_preserves_no_write_behavior(agent):
    agent._memory_enabled = False
    with patch("tools.memory_tool.memory_tool") as memory_write:
        assert write_hindsight_lesson(
            agent,
            task_id="task-42",
            final_response="Completed the task.",
        ) is False

    memory_write.assert_not_called()


@pytest.mark.unit
def test_memory_write_failure_is_best_effort(agent):
    with patch("tools.memory_tool.memory_tool", side_effect=RuntimeError("disk full")):
        assert write_hindsight_lesson(
            agent,
            task_id="task-42",
            final_response="Completed the task.",
        ) is False


@pytest.mark.integration
def test_conversation_loop_completion_writes_bounded_hindsight_lesson():
    with (
        patch("run_agent.get_tool_definitions", return_value=[]),
        patch("run_agent.check_toolset_requirements", return_value={}),
        patch("run_agent.OpenAI"),
    ):
        loop_agent = run_agent.AIAgent(
            api_key="test-key-1234567890",
            base_url="https://openrouter.ai/api/v1",
            quiet_mode=True,
            skip_context_files=True,
            skip_memory=True,
        )
    loop_agent.client = MagicMock()
    loop_agent._cached_system_prompt = "You are helpful."
    loop_agent._use_prompt_caching = False
    loop_agent.tool_delay = 0
    loop_agent.compression_enabled = False
    loop_agent.save_trajectories = False
    loop_agent._memory_enabled = True
    loop_agent._memory_store = SimpleNamespace(memory_char_limit=80)
    loop_agent.client.chat.completions.create.return_value = SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(content="A" * 500, tool_calls=None),
                finish_reason="stop",
            )
        ],
        model="test/model",
        usage=None,
    )

    with (
        patch("tools.memory_tool.memory_tool") as memory_write,
        patch.object(loop_agent, "_persist_session"),
        patch.object(loop_agent, "_save_trajectory"),
        patch.object(loop_agent, "_cleanup_task_resources"),
    ):
        memory_write.return_value = '{"success": true, "staged": false}'
        result = loop_agent.run_conversation("complete this", task_id="task-e113")

    assert result["completed"] is True
    content = memory_write.call_args.kwargs["content"]
    assert len(content) <= loop_agent._memory_store.memory_char_limit


@pytest.mark.unit
def test_lesson_content_fits_the_store_memory_limit(agent):
    agent._memory_store = SimpleNamespace(memory_char_limit=80)
    with patch("tools.memory_tool.memory_tool") as memory_write:
        memory_write.return_value = '{"success": true, "staged": false}'

        assert write_hindsight_lesson(
            agent,
            task_id="task-42",
            final_response="A" * 500,
        ) is True

    content = memory_write.call_args.kwargs["content"]
    assert len(content) <= agent._memory_store.memory_char_limit
