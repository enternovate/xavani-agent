import json
from unittest.mock import patch

import cli as cli_mod
from cli import XavaniCLI


def _make_cli():
    cli = XavaniCLI.__new__(XavaniCLI)
    cli._active_tool_calls = []
    cli._pending_edit_snapshots = {}
    cli._invalidate = lambda: None
    return cli


def test_edit_replace_renders_snapshot_diff_inline(tmp_path):
    target = tmp_path / "note.txt"
    target.write_text("old\n", encoding="utf-8")
    args = {"mode": "replace", "path": str(target), "old_string": "old", "new_string": "new"}
    cli = _make_cli()

    cli._on_tool_start("call-edit", "edit", args)
    target.write_text("new\n", encoding="utf-8")

    with patch.object(cli_mod, "_cprint") as print_fn:
        cli._on_tool_complete("call-edit", "edit", args, json.dumps({"ok": True}))

    output = "\n".join(call.args[0] for call in print_fn.call_args_list)
    assert "review diff" in output
    assert "-old" in output
    assert "+new" in output


def test_edit_patch_renders_result_diff_without_snapshot():
    cli = _make_cli()
    result = json.dumps(
        {
            "success": True,
            "diff": "--- a/note.txt\n+++ b/note.txt\n@@ -1 +1 @@\n-old\n+new\n",
        }
    )

    with patch.object(cli_mod, "_cprint") as print_fn:
        cli._on_tool_complete("call-edit", "edit", {"mode": "patch", "input": "payload"}, result)

    output = "\n".join(call.args[0] for call in print_fn.call_args_list)
    assert "review diff" in output
    assert "-old" in output
    assert "+new" in output


def test_non_edit_tool_keeps_original_display_name():
    cli = _make_cli()
    with patch("agent.display.render_edit_diff_with_delta", return_value=False) as render_diff:
        cli._on_tool_complete("call-search", "web_search", {"query": "x"}, "{}")

    assert render_diff.call_args.args[0] == "web_search"
