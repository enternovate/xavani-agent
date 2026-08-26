"""Turn-completion explainer tests.

The explainer guarantees the agent never ends a turn silently: when the
final response is empty or a truncated fragment, it produces an
actionable explanation derived from ``_turn_exit_reason``.
"""

import pytest

from agent.turn_completion_explainer import (
    format_turn_completion_explanation,
    is_partial_fragment,
    turn_completion_explainer_enabled,
)


class TestFormatExplanation:
    def test_empty_response_returns_explanation(self):
        text = format_turn_completion_explanation(
            "empty_response_exhausted", cause=None
        )
        assert isinstance(text, str)
        assert len(text) > 20
        assert "retr" in text.lower()  # retry/retries/retried

    def test_text_response_exit_returns_none(self):
        assert (
            format_turn_completion_explanation(
                "text_response(finish_reason=stop)", cause=None
            )
            is None
        )

    def test_retries_exhausted_names_the_count(self):
        text = format_turn_completion_explanation(
            "all_retries_exhausted_no_response",
            cause="HTTP 429: rate limit",
        )
        assert "429" in text
        assert "retr" in text.lower()  # retry/retries/retried

    def test_budget_exhausted_mentions_budget(self):
        text = format_turn_completion_explanation(
            "budget_exhausted", cause=None
        )
        assert "budget" in text.lower()

    def test_interrupted_by_user_is_respectful(self):
        text = format_turn_completion_explanation(
            "interrupted_by_user", cause=None
        )
        assert "interrupt" in text.lower()

    def test_guardrail_halt_mentions_guardrail(self):
        text = format_turn_completion_explanation("guardrail_halt", cause=None)
        assert "guardrail" in text.lower()

    def test_max_iterations_reports_counts(self):
        text = format_turn_completion_explanation(
            "max_iterations_reached(25/25)", cause=None
        )
        assert "25/25" in text

    def test_partial_stream_recovery(self):
        text = format_turn_completion_explanation(
            "partial_stream_recovery", cause=None
        )
        assert "stream" in text.lower()

    def test_unknown_reason_gets_generic_but_useful_text(self):
        text = format_turn_completion_explanation(
            "some_future_reason", cause=None
        )
        assert isinstance(text, str)
        assert len(text) > 10


class TestPartialFragment:
    @pytest.mark.parametrize(
        "text,expected",
        [
            ("", False),
            ("(empty)", False),
            ("The", False),  # lone word = complete answer, not truncation
            ("The file is", True),  # multi-word fragment mid-sentence
            ("Done.", False),  # terminal punctuation
            ("A" * 30, False),  # longer than 24 chars
            ("Sure!", False),
            ("Working on it?", False),
            ("done", False),  # lone word = complete answer, not truncation
            ("OK", False),
        ],
    )
    def test_classification(self, text, expected):
        assert is_partial_fragment(text, exit_reason="error_near_max_iterations(x)") == expected

    def test_short_fragment_with_punctuation_is_not_partial(self):
        # A real terse answer keeps its text.
        assert is_partial_fragment("No.", exit_reason="error_near_max_iterations(x)") is False

    def test_text_response_exit_never_partial(self):
        assert is_partial_fragment("The", exit_reason="text_response(finish_reason=stop)") is False


class TestEnabledGate:
    def test_default_on(self, monkeypatch):
        monkeypatch.delenv("XAVANI_TURN_EXPLAINER", raising=False)
        import agent.turn_completion_explainer as tce

        tce._enabled_cache = None  # reset memo
        assert turn_completion_explainer_enabled() is True

    def test_env_off(self, monkeypatch):
        monkeypatch.setenv("XAVANI_TURN_EXPLAINER", "0")
        import agent.turn_completion_explainer as tce

        tce._enabled_cache = None
        assert turn_completion_explainer_enabled() is False

    def test_config_off(self, monkeypatch):
        monkeypatch.delenv("XAVANI_TURN_EXPLAINER", raising=False)
        import agent.turn_completion_explainer as tce

        tce._enabled_cache = None
        monkeypatch.setattr(
            "xavani_cli.config.load_config",
            lambda: {"display": {"turn_completion_explainer": False}},
        )
        assert turn_completion_explainer_enabled() is False
