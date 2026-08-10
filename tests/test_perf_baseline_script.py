import subprocess, sys

def test_baseline_script_runs_and_emits_json():
    out = subprocess.run(
        [sys.executable, "scripts/perf_baseline.py", "--quick"],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0
    import json
    data = json.loads(out.stdout)
    for key in ("startup_seconds", "system_prompt_tokens", "tool_schema_tokens", "tools_sent"):
        assert key in data
