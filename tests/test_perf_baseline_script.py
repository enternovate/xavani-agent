import importlib.util
import json
import subprocess, sys
from pathlib import Path
from types import SimpleNamespace

def test_baseline_script_runs_and_emits_json():
    out = subprocess.run(
        [sys.executable, "scripts/perf_baseline.py", "--quick"],
        capture_output=True, text=True, timeout=120,
    )
    assert out.returncode == 0
    data = json.loads(out.stdout)
    for key in ("startup_seconds", "system_prompt_tokens", "tool_schema_tokens", "tools_sent"):
        assert key in data

def test_import_bootstrap_and_failed_startup_handling(monkeypatch, capsys):
    """Bare-checkout bootstrap puts REPO_ROOT on sys.path; when every startup
    repeat fails the script still exits 0 with startup_seconds=null +
    startup_error."""
    spec = importlib.util.spec_from_file_location(
        "perf_baseline_test",
        str(Path(__file__).resolve().parent.parent / "scripts" / "perf_baseline.py"),
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # ITEM 1: bootstrap inserts repo root at the front of sys.path.
    assert sys.path[0] == str(mod.REPO_ROOT)

    # ITEM 2: simulate every startup repeat failing (nonzero exit).
    monkeypatch.setattr(
        mod.subprocess, "run",
        lambda *a, **k: SimpleNamespace(returncode=1, stderr="boom"),
    )
    monkeypatch.setattr(mod, "measure_system_prompt_tokens", lambda: 100)
    monkeypatch.setattr(mod, "measure_tool_schema", lambda: (200, 3))
    monkeypatch.setattr(mod.sys, "argv", ["perf_baseline.py", "--quick"])
    assert mod.main() == 0
    data = json.loads(capsys.readouterr().out)
    assert data["startup_seconds"] is None
    assert data["startup_error"]
