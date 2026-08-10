"""Append-only guard for oag_skills/MANIFEST.json (Cap migration-journal pattern).

The skills index is tooling-generated (scripts/build_skills_index.py) and
consumed at runtime by xavani_learner/. A skill that disappears or changes
identity between the committed manifest and the working tree can strand
users on a stale index. The guard allows NEW entries (append-only journal)
but rejects REMOVED or MODIFIED entries by skill name key.

The real file is never touched: the mutation tests operate on in-memory
copies of a small seed fixture.
"""

from __future__ import annotations

import copy
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_REL = "oag_skills/MANIFEST.json"
FIXTURE = Path(__file__).resolve().parents[0] / "fixtures" / "manifest-mutation" / "seed.json"

# Fields that make an entry "modified" when they change. The index schema
# today only carries description/category/name; version/path are reserved
# for future schema versions, so the guard already knows about them.
_COMPARE_FIELDS = ("description", "version", "path")


def _index_skills(manifest: dict) -> dict[str, dict]:
    return {entry["name"]: entry for entry in manifest["skills"]}


def append_only_violations(head_entries: dict[str, dict], work_entries: dict[str, dict]) -> list[str]:
    """Return human-readable violations of the append-only contract.

    Empty list means the working side is a valid append-only evolution of
    the head side.
    """
    violations: list[str] = []
    for name, head_entry in head_entries.items():
        work_entry = work_entries.get(name)
        if work_entry is None:
            violations.append(f"skill '{name}' was REMOVED from the manifest")
            continue
        for field in _COMPARE_FIELDS:
            if head_entry.get(field) != work_entry.get(field):
                violations.append(
                    f"skill '{name}' was MODIFIED (field '{field}' changed)"
                )
    return violations


def _load_manifest(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def test_real_manifest_is_append_only() -> None:
    head_raw = subprocess.run(
        ["git", "-C", str(REPO_ROOT), "show", f"HEAD:{MANIFEST_REL}"],
        capture_output=True,
        text=True,
        check=True,
        timeout=10,
    ).stdout
    head_entries = _index_skills(json.loads(head_raw))
    work_entries = _index_skills(_load_manifest(REPO_ROOT / MANIFEST_REL))

    violations = append_only_violations(head_entries, work_entries)
    assert violations == [], "manifest journal violations:\n" + "\n".join(violations)


def _load_seed() -> dict:
    return _load_manifest(FIXTURE)


def test_guard_catches_removal() -> None:
    seed = _load_seed()
    mutated = copy.deepcopy(seed)
    removed_name = mutated["skills"][0]["name"]
    del mutated["skills"][0]

    violations = append_only_violations(
        _index_skills(seed), _index_skills(mutated)
    )
    assert any(removed_name in v and "REMOVED" in v for v in violations)


def test_guard_catches_modification() -> None:
    seed = _load_seed()
    mutated = copy.deepcopy(seed)
    target = mutated["skills"][1]
    target["description"] = "Rewritten description pretending to be an update."

    violations = append_only_violations(
        _index_skills(seed), _index_skills(mutated)
    )
    assert any(target["name"] in v and "MODIFIED" in v for v in violations)


def test_guard_allows_new_entries() -> None:
    seed = _load_seed()
    mutated = copy.deepcopy(seed)
    mutated["skills"].append(
        {
            "name": "fixture-skill-new",
            "description": "Brand-new skill — allowed in an append-only journal.",
            "category": "fixtures",
        }
    )

    violations = append_only_violations(
        _index_skills(seed), _index_skills(mutated)
    )
    assert violations == []
