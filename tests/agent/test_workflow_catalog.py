# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Catalog tests for the business workflow skill paths (R3 Task 17)."""

from pathlib import Path

from agent.workflow_catalog import WORKFLOWS, get_workflow, skill_lookup_name

EXPECTED_WORKFLOW_IDS = {
    "finance",
    "invoices",
    "daily",
    "inbox",
    "meetings",
    "sales",
    "people",
    "procurement",
    "compliance",
    "engineering",
    "executive",
    "incidents",
}


def test_catalog_skill_paths_exist():
    root = Path(__file__).resolve().parents[2]
    assert len(WORKFLOWS) == 12
    for workflow in WORKFLOWS.values():
        assert workflow.checks
        for skill in workflow.skills:
            assert (root / skill).is_file(), skill


def test_catalog_covers_the_declared_workflow_scope():
    assert set(WORKFLOWS) == EXPECTED_WORKFLOW_IDS


def test_catalog_marks_workflows_with_external_actions():
    flagged = {key for key, workflow in WORKFLOWS.items() if workflow.external_actions}
    assert flagged == {"inbox", "sales", "procurement"}


def test_skill_paths_are_canonical_not_display_names():
    for workflow in WORKFLOWS.values():
        for skill in workflow.skills:
            assert skill.endswith("/SKILL.md"), skill
            assert "/" in skill.strip("/SKILL.md"), skill
            assert "\\" not in skill


def test_skill_lookup_name_strips_the_index_file():
    assert (
        skill_lookup_name("oag_skills/finance/dcf-model/SKILL.md")
        == "oag_skills/finance/dcf-model"
    )
    assert skill_lookup_name("skills/email/himalaya") == "skills/email/himalaya"


def test_unknown_workflow_is_rejected():
    try:
        get_workflow("payroll")
    except ValueError as exc:
        assert "Unknown workflow: payroll" in str(exc)
    else:  # pragma: no cover - the catalog must not hold this key
        raise AssertionError("unknown workflow id was accepted")
