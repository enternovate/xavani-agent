# Tests for the update-time bytecode cache clearing.
from xavani_cli.main import _clear_bytecode_cache


def _make_pycache(root, rel_path):
    """Create a __pycache__ directory with a fake bytecode file."""
    target = root / rel_path / "__pycache__"
    target.mkdir(parents=True)
    (target / "x.cpython-313.pyc").write_bytes(b"\x00\x01")


def test_clear_bytecode_cache_removes_pycache_dirs(tmp_path):
    _make_pycache(tmp_path, "pkg")
    _make_pycache(tmp_path, "pkg/sub")

    removed = _clear_bytecode_cache(tmp_path)

    assert removed == 2
    assert not (tmp_path / "pkg" / "__pycache__").exists()
    assert not (tmp_path / "pkg" / "sub" / "__pycache__").exists()


def test_clear_bytecode_cache_skips_build_artifact_dirs(tmp_path):
    # Build output and dependency dirs never contain importable bytecode.
    # The update walk must not descend into them: they can hold gigabytes
    # of files and stall the update on slow disks.
    _make_pycache(tmp_path, "src")
    for artifact in [
        "build",
        "dist",
        ".next",
        ".docusaurus",
        "node_modules",
        ".venv",
        ".git",
        "website/build",
        "web/node_modules/pkg",
    ]:
        _make_pycache(tmp_path, artifact)

    removed = _clear_bytecode_cache(tmp_path)

    assert removed == 1  # only src/__pycache__ is removed
    for artifact in [
        "build",
        "dist",
        ".next",
        ".docusaurus",
        "node_modules",
        ".venv",
        ".git",
        "website/build",
        "web/node_modules/pkg",
    ]:
        assert (tmp_path / artifact / "__pycache__").exists(), artifact


def test_clear_bytecode_cache_returns_zero_for_empty_tree(tmp_path):
    assert _clear_bytecode_cache(tmp_path) == 0


def test_clear_bytecode_cache_handles_missing_root(tmp_path):
    missing = tmp_path / "does-not-exist"
    assert _clear_bytecode_cache(missing) == 0
