"""Tests for scripts/tool_payload_report.py.

The report script is the evidence generator for deferred-tool decisions:
it measures the per-turn tool schema token payload, per tool and per
toolset, using the exact OpenAI-style definitions sent to the API.
"""


def test_report_lists_every_tool_with_tokens():
    import subprocess, sys, json
    out = subprocess.run([sys.executable, "scripts/tool_payload_report.py"],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)
    assert data["total_tools"] > 20
    assert data["total_tokens"] > 0
    assert all("name" in t and "tokens" in t for t in data["tools"])


def test_by_toolset_rollup_matches_tool_list():
    """by_toolset counts/tokens must be a lossless rollup of the tools list."""
    import subprocess, sys, json
    out = subprocess.run([sys.executable, "scripts/tool_payload_report.py"],
                         capture_output=True, text=True, timeout=120)
    assert out.returncode == 0, out.stderr
    data = json.loads(out.stdout)

    from collections import Counter
    per_toolset = Counter()
    tokens_per_toolset = Counter()
    for t in data["tools"]:
        ts = t.get("toolset") or "unknown"
        per_toolset[ts] += 1
        tokens_per_toolset[ts] += t["tokens"]

    assert set(per_toolset) == set(data["by_toolset"])
    for ts, info in data["by_toolset"].items():
        assert info["tools"] == per_toolset[ts]
        assert info["tokens"] == tokens_per_toolset[ts]
    assert sum(i["tokens"] for i in data["by_toolset"].values()) == data["total_tokens"]
