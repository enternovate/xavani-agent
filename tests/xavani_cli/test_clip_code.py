# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from xavani_cli import clip_code


class TestLastCodeBlock:
    def test_last_fenced_block_wins(self):
        text = "first:\n```py\na = 1\n```\nthen:\n```js\nlet b = 2;\n```"
        assert clip_code.last_code_block(text) == "let b = 2;"

    def test_indented_block_without_fences(self):
        text = "run this:\n\n    cmd --flag\n    cmd2 --flag2\n\ndone."
        assert "cmd --flag" in clip_code.last_code_block(text)

    def test_no_block_returns_none(self):
        assert clip_code.last_code_block("just prose") is None
        assert clip_code.last_code_block("") is None


class TestCopyText:
    def test_empty_rejected(self):
        assert clip_code.copy_text("  ") is False

    def test_injected_copier_used(self):
        sent = {}
        ok = clip_code.copy_text(
            "payload", copier=lambda t: (sent.update(t=t) or True)
        )
        assert ok is True
        assert sent["t"] == "payload"

    def test_injected_copier_failure(self):
        assert clip_code.copy_text("x", copier=lambda t: False) is False


class TestCopyLastCodeBlock:
    def test_success_path(self):
        ok, block = clip_code.copy_last_code_block(
            "text\n```\ndo it\n```",
            copier=lambda t: True,
        )
        assert ok is True
        assert block == "do it"

    def test_no_block_reason(self):
        ok, reason = clip_code.copy_last_code_block(
            "no code", copier=lambda t: True
        )
        assert ok is False
        assert reason == "no code block found"

    def test_clipboard_unavailable_reason(self):
        ok, reason = clip_code.copy_last_code_block(
            "```\nx\n```", copier=lambda t: False
        )
        assert ok is False
        assert reason == "no clipboard tool available"
