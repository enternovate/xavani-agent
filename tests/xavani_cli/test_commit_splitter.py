# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

import pytest

from xavani_cli.commit_splitter import (
    Change,
    CycleError,
    build_import_graph,
    classify,
    detect_cycles,
    filter_lockfiles,
    is_lockfile,
    split_plan,
)


class TestClassify:
    def test_all_kinds(self):
        assert classify("xavani_cli/foo.py") == "source"
        assert classify("tests/xavani_cli/test_foo.py") == "test"
        assert classify("xavani_cli/test_foo.py") == "test"
        assert classify("README.md") == "docs"
        assert classify("docs/guide.md") == "docs"
        assert classify("CHANGELOG.md") == "docs"
        assert classify("pyproject.toml") == "config"
        assert classify("ci/workflow.yaml") == "config"
        assert classify(".env.example") == "config"

    def test_all_lockfile_names(self):
        for name in (
            "uv.lock", "package-lock.json", "poetry.lock",
            "pnpm-lock.yaml", "Pipfile.lock",
        ):
            assert is_lockfile(f"lockdir/{name}"), name
            assert classify(f"lockdir/{name}") == "lock"

    def test_filter_lockfiles(self):
        changes = [
            Change("uv.lock", "lock"),
            Change("a.py", "source"),
            Change("poetry.lock", "lock"),
        ]
        kept = filter_lockfiles(changes)
        assert [c.path for c in kept] == ["a.py"]


class TestImportGraph:
    def test_full_module_import(self):
        graph = build_import_graph({
            "xavani_cli/a.py": "from xavani_cli import b\n",
            "xavani_cli/b.py": "x = 1\n",
        })
        assert graph["xavani_cli/a.py"] == {"xavani_cli/b.py"}
        assert graph["xavani_cli/b.py"] == set()

    def test_leaf_module_import(self):
        graph = build_import_graph({
            "pkg_one/mod.py": "import helper\n",
            "pkg_two/helper.py": "y = 2\n",
        })
        assert graph["pkg_one/mod.py"] == {"pkg_two/helper.py"}

    def test_syntax_error_is_empty_edges(self):
        graph = build_import_graph({
            "broken.py": "def (:\n",
            "ok.py": "import broken\n",
        })
        assert graph["broken.py"] == set()
        assert graph["ok.py"] == {"broken.py"}

    def test_from_import_submodule_resolves(self):
        graph = build_import_graph({
            "pkg/base.py": "X = 1\n",
            "pkg/app.py": "from pkg import base\n",
        })
        assert graph["pkg/app.py"] == {"pkg/base.py"}


class TestDetectCycles:
    def test_cycle_raises_with_path(self):
        graph = {
            "a.py": {"b.py"},
            "b.py": {"c.py"},
            "c.py": {"a.py"},
        }
        with pytest.raises(CycleError, match="a.py -> b.py -> c.py -> a.py"):
            detect_cycles(graph)

    def test_acyclic_passes(self):
        detect_cycles({
            "a.py": {"b.py"},
            "b.py": set(),
        })


def _src(path: str) -> Change:
    return Change(path, "source")


class TestSplitPlan:
    def test_rejects_lockfile_changes(self):
        with pytest.raises(ValueError, match="uv.lock"):
            split_plan([Change("uv.lock", "lock")])

    def test_source_groups_with_same_stem_test(self):
        plan = split_plan([
            _src("xavani_cli/foo.py"),
            Change("tests/xavani_cli/test_foo.py", "test"),
        ])
        assert len(plan) == 1
        assert plan[0]["files"] == ["xavani_cli/foo.py", "tests/xavani_cli/test_foo.py"]

    def test_dependency_first_ordering(self):
        contents = {
            "pkg/base.py": "X = 1\n",
            "pkg/app.py": "from pkg import base\n",
        }
        plan = split_plan(
            [_src("pkg/app.py"), _src("pkg/base.py")], contents=contents
        )
        assert [g["files"][0] for g in plan] == ["pkg/base.py", "pkg/app.py"]

    def test_cycle_rejected(self):
        contents = {
            "a.py": "import b\n",
            "b.py": "import a\n",
        }
        with pytest.raises(CycleError):
            split_plan([_src("a.py"), _src("b.py")], contents=contents)

    def test_trailing_groups_order(self):
        plan = split_plan([
            _src("m.py"),
            Change("tests/test_other.py", "test"),
            Change("NOTES.md", "docs"),
            Change("pyproject.toml", "config"),
        ])
        assert [g["reason"] for g in plan] == [
            "core module m",
            "supporting tests",
            "docs",
            "config",
        ]

    def test_deterministic_tie_break(self):
        plan_one = split_plan([_src("b.py"), _src("a.py")])
        plan_two = split_plan([_src("a.py"), _src("b.py")])
        assert plan_one == plan_two
