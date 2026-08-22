# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Atomic commit splitter: plan ordered commits from changed files.

Pure logic over a change list. Lockfiles are excluded from analysis,
sources group with their same-stem test files, and groups order
dependency-first via a parsed import graph. Dependency cycles among
changed sources are rejected before any ordering.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass

_LOCKFILE_NAMES = {
    "uv.lock",
    "package-lock.json",
    "poetry.lock",
    "pnpm-lock.yaml",
    "Pipfile.lock",
}

_KIND_RE_TESTS = re.compile(r"(?:^|/)tests/|/test_[^/]+\.py$")
_KIND_RE_DOCS = re.compile(r"\.md$|^docs/|CHANGELOG")
_KIND_RE_CONFIG = re.compile(r"pyproject\.toml$|\.(?:yaml|yml|json)$|^\.env")


class CycleError(ValueError):
    """Raised when changed sources form a dependency cycle."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        shown = " -> ".join(cycle + [cycle[0]])
        super().__init__(f"dependency cycle among changed files: {shown}")


@dataclass
class Change:
    path: str
    kind: str


def classify(path: str) -> str:
    """Classify a path as source, test, docs, config, or lock."""
    name = path.rsplit("/", 1)[-1]
    if name in _LOCKFILE_NAMES:
        return "lock"
    if _KIND_RE_TESTS.search(path) or name.startswith("test_"):
        return "test"
    if _KIND_RE_DOCS.search(path):
        return "docs"
    if _KIND_RE_CONFIG.search(path):
        return "config"
    return "source"


def is_lockfile(path: str) -> bool:
    """True for dependency lockfiles, which never join a split plan."""
    return path.rsplit("/", 1)[-1] in _LOCKFILE_NAMES


def filter_lockfiles(changes: list[Change]) -> list[Change]:
    """Drop lockfile changes from the plan input."""
    return [c for c in changes if not is_lockfile(c.path)]


def _module_name(path: str) -> str:
    stem = path.removesuffix(".py").replace("/", ".")
    if stem.endswith(".__init__"):
        stem = stem[: -len(".__init__")]
    return stem


def _leaf_module(path: str) -> str:
    return _module_name(path).rsplit(".", 1)[-1]


def build_import_graph(sources: dict[str, str]) -> dict[str, set[str]]:
    """Map each source file to the other changed source files it imports.

    An import edge matches when the imported dotted name equals a
    changed file's full module name or its leaf module name.
    """
    modules = {_module_name(p): p for p in sources}
    leaves: dict[str, str] = {}
    for module, path in modules.items():
        leaves.setdefault(_leaf_module(path), path)

    graph: dict[str, set[str]] = {p: set() for p in sources}
    for path, text in sources.items():
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported.add(alias.name)
            elif isinstance(node, ast.ImportFrom):
                base = node.module or ""
                for alias in node.names:
                    if node.level and not base:
                        imported.add(alias.name)
                    else:
                        imported.add(base)
                        imported.add(f"{base}.{alias.name}")
        for name in imported:
            target = modules.get(name) or leaves.get(name.rsplit(".", 1)[-1])
            if target and target != path:
                graph[path].add(target)
    return graph


def detect_cycles(graph: dict[str, set[str]]) -> None:
    """Raise :class:`CycleError` when the graph contains a directed cycle."""
    state: dict[str, int] = {}
    stack: list[str] = []

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for nxt in sorted(graph.get(node, ())):
            mark = state.get(nxt, 0)
            if mark == 1:
                start = stack.index(nxt)
                raise CycleError(stack[start:])
            if mark == 0:
                visit(nxt)
        stack.pop()
        state[node] = 2

    for node in sorted(graph):
        if state.get(node, 0) == 0:
            visit(node)


def provider_order(graph: dict[str, set[str]]) -> list[str]:
    """Order sources so imported files come before their importers.

    Deterministic: alphabetical among ready nodes at every step.
    """
    imported_by: dict[str, set[str]] = {n: set() for n in graph}
    pending_deps: dict[str, int] = {}
    for importer, deps in graph.items():
        pending_deps[importer] = len(deps)
        for dep in deps:
            imported_by.setdefault(dep, set()).add(importer)

    ready = sorted(n for n, d in pending_deps.items() if d == 0)
    order: list[str] = []
    while ready:
        node = ready.pop(0)
        order.append(node)
        for importer in sorted(imported_by.get(node, ())):
            pending_deps[importer] -= 1
            if pending_deps[importer] == 0:
                ready.append(importer)
        ready.sort()
    return order


def _stem(path: str) -> str:
    base = path.rsplit("/", 1)[-1]
    if base.endswith(".py"):
        base = base[:-3]
    if base.startswith("test_"):
        base = base[len("test_"):]
    return base


def split_plan(
    changes: list[Change],
    contents: dict[str, str] | None = None,
) -> list[dict]:
    """Plan ordered, atomic commit groups from a change list.

    ``contents`` maps source paths to their file text; pass it so the
    import graph (and therefore cycle rejection and dependency-first
    ordering) reflects real code. Sources travel with their same-stem
    test file; leftover tests form one trailing supporting group, then
    docs, then config. Raises ValueError on lockfile changes (filter
    them first) and CycleError on import cycles among sources.
    """
    locks = [c.path for c in changes if c.kind == "lock"]
    if locks:
        raise ValueError(
            f"lockfiles must be filtered out first: {', '.join(sorted(locks))}"
        )

    source_paths = sorted(c.path for c in changes if c.kind == "source")
    contents = {p: (contents or {}).get(p, "") for p in source_paths}
    graph = build_import_graph(contents)
    detect_cycles(graph)
    rank = {path: i for i, path in enumerate(provider_order(graph))}

    tests_by_stem: dict[str, list[str]] = {}
    loose_tests: list[str] = []
    docs: list[str] = []
    configs: list[str] = []
    for change in changes:
        if change.kind == "test":
            if change.path.rsplit("/", 1)[-1].startswith("test_") and _stem(change.path) in {
                _stem(s) for s in source_paths
            }:
                tests_by_stem.setdefault(_stem(change.path), []).append(change.path)
            else:
                loose_tests.append(change.path)
        elif change.kind == "docs":
            docs.append(change.path)
        elif change.kind == "config":
            configs.append(change.path)

    core_groups: list[tuple[int, str, list[str]]] = []
    consumed_tests: set[str] = set()
    for source in source_paths:
        files = [source]
        for test in sorted(tests_by_stem.get(_stem(source), [])):
            if test not in consumed_tests:
                files.append(test)
                consumed_tests.add(test)
        core_groups.append(
            (rank.get(source, len(rank)), f"core module {_module_name(source)}", files)
        )

    ordered: list[dict] = [
        {"files": files, "reason": reason}
        for _rank, reason, files in sorted(core_groups, key=lambda g: (g[0], g[1]))
    ]
    remaining = sorted(t for v in tests_by_stem.values() for t in v
                       if t not in consumed_tests) + sorted(loose_tests)
    if remaining:
        ordered.append({"files": remaining, "reason": "supporting tests"})
    if docs:
        ordered.append({"files": sorted(docs), "reason": "docs"})
    if configs:
        ordered.append({"files": sorted(configs), "reason": "config"})
    return ordered
