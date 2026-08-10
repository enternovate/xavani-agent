"""Tests for scripts/gen_completions.py — shell completion generator.

S3-1 (backlog F127): emits bash/zsh/fish completions derived from the
CLI's own command registry (xavani_cli.commands.COMMAND_REGISTRY).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "gen_completions.py"

SLASH_COMMANDS = (
    "/help",
    "/new",
    "/clear",
    "/history",
    "/save",
    "/retry",
    "/undo",
    "/title",
    "/status",
    "/config",
    "/model",
    "/profile",
    "/skills",
    "/memory",
    "/tools",
    "/exit",
    "/background",
    "/agents",
    "/rollback",
    "/snapshot",
)


def run_generator(outdir: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--outdir", str(outdir)],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=120,
    )


def emitted(outdir: Path) -> dict[str, Path]:
    files = {
        "bash": outdir / "bash" / "xavani.bash",
        "zsh": outdir / "zsh" / "_xavani",
        "fish": outdir / "fish" / "xavani.fish",
    }
    assert all(p.exists() for p in files.values()), "generator did not emit all three files"
    return files


def test_generator_emits_nonempty_completion_files(tmp_path: Path) -> None:
    result = run_generator(tmp_path)
    assert result.returncode == 0, result.stderr
    for path in emitted(tmp_path).values():
        assert path.read_text(encoding="utf-8").strip(), f"{path.name} is empty"


def test_bash_has_completion_function_registration(tmp_path: Path) -> None:
    run_generator(tmp_path)
    text = emitted(tmp_path)["bash"].read_text(encoding="utf-8")
    assert "complete -F" in text or "_xavani" in text


def test_zsh_uses_compdef_or_arguments(tmp_path: Path) -> None:
    run_generator(tmp_path)
    text = emitted(tmp_path)["zsh"].read_text(encoding="utf-8")
    assert "compdef" in text or "_arguments" in text


def test_fish_uses_complete_c(tmp_path: Path) -> None:
    run_generator(tmp_path)
    text = emitted(tmp_path)["fish"].read_text(encoding="utf-8")
    assert "complete -c xavani" in text


def test_slash_commands_appear_in_emitted_files(tmp_path: Path) -> None:
    run_generator(tmp_path)
    files = emitted(tmp_path)
    for path in files.values():
        text = path.read_text(encoding="utf-8")
        present = [cmd for cmd in SLASH_COMMANDS if cmd in text]
        assert len(present) >= 5, (
            f"{path.name} contains fewer than 5 documented slash commands: {present}"
        )
