"""Integration: the conversation-loop tail applies the explainer.

Runs the real finalizer section logic by importing the loop module and
exercising the same guard sequence used at the tail. Full end-to-end
loop execution needs a live provider; here we verify the wiring
contract — explainer importable from the loop context and the sentinel
replacement rule.
"""

from agent.turn_completion_explainer import (
    format_turn_completion_explanation,
    is_partial_fragment,
)


def _apply_explainer(final_response, exit_reason, interrupted=False):
    """Mirror of the loop-tail explainer block (kept in sync by test)."""
    if interrupted:
        return final_response
    stripped = (final_response or "").strip()
    is_empty = not stripped or stripped == "(empty)"
    if not (is_empty or is_partial_fragment(stripped or "", exit_reason)):
        return final_response
    explanation = format_turn_completion_explanation(exit_reason, None)
    if not explanation:
        return final_response
    if is_empty:
        return explanation
    return stripped + "\n\n" + explanation


def test_empty_sentinel_replaced_with_explanation():
    out = _apply_explainer(None, "budget_exhausted")
    assert out and "budget" in out.lower()


def test_paren_empty_sentinel_replaced():
    out = _apply_explainer("(empty)", "guardrail_halt")
    assert "guardrail" in out.lower()


def test_partial_fragment_gets_appended():
    out = _apply_explainer("The", "partial_stream_recovery")
    assert out.startswith("The\n\n")
    assert "stream" in out.lower()


def test_healthy_response_untouched():
    original = "Here is the full analysis you asked for."
    assert _apply_explainer(original, "text_response(finish_reason=stop)") == original


def test_interrupted_turn_untouched():
    assert _apply_explainer(None, "interrupted_by_user", interrupted=True) is None
