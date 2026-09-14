# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Canonical business workflow catalog.

Every workflow names the skill files it requires by canonical skill path, not
by display name alone.  A canonical path is a path relative to a skill root,
ending in ``SKILL.md`` (e.g. ``oag_skills/finance/dcf-model/SKILL.md``).

The catalog also declares the objective checks that gate each workflow.  It
holds data only — resolution and loading live in :mod:`agent.workflow_skills`.
"""

from __future__ import annotations

from dataclasses import dataclass

SKILL_INDEX_FILENAME = "SKILL.md"


@dataclass(frozen=True)
class Workflow:
    name: str
    skills: tuple[str, ...]
    checks: tuple[str, ...]
    external_actions: bool = False


# The 12-workflow scope is explicit; it does not track the size of the general
# skill library.
WORKFLOWS = {
    "finance": Workflow("Finance analysis", (
        "oag_skills/finance/3-statement-model/SKILL.md",
        "oag_skills/finance/dcf-model/SKILL.md",
        "oag_skills/finance/excel-author/SKILL.md",
    ), ("source_schema", "financial_reconciliation", "artifact_open")),
    "invoices": Workflow("Invoice review", (
        "oag_skills/workflow-packs/invoice-extraction/SKILL.md",
    ), ("source_schema", "invoice_totals", "invoice_duplicates")),
    "daily": Workflow("Daily operations", (
        "oag_skills/business/business-assistant/SKILL.md",
        "skills/productivity/planner/SKILL.md",
    ), ("source_coverage", "task_owners", "task_duplicates")),
    "inbox": Workflow("Inbox and support", (
        "skills/email/himalaya/SKILL.md",
    ), ("source_coverage", "recipient_scope", "draft_review"), True),
    "meetings": Workflow("Meetings", (
        "oag_skills/workflow-packs/meeting-notes/SKILL.md",
    ), ("source_coverage", "action_citations")),
    "sales": Workflow("Sales and marketing", (
        "oag_skills/business/business-assistant/SKILL.md",
    ), ("source_coverage", "brand_policy", "recipient_scope"), True),
    "people": Workflow("People and administration", (
        "oag_skills/business/business-assistant/SKILL.md",
    ), ("source_coverage", "access_scope", "sensitive_fields")),
    "procurement": Workflow("Procurement and inventory", (
        "oag_skills/business/business-assistant/SKILL.md",
    ), ("source_schema", "quantity_units", "order_duplicates"), True),
    "compliance": Workflow("Legal and compliance support", (
        "skills/software-development/security-review/SKILL.md",
        "oag_skills/business/business-assistant/SKILL.md",
    ), ("source_coverage", "jurisdiction", "source_date")),
    "engineering": Workflow("Engineering and design", (
        "skills/software-development/frontend-design/SKILL.md",
        "skills/software-development/api-design-review/SKILL.md",
        "skills/software-development/security-review/SKILL.md",
    ), ("tests", "lint", "build", "security", "visual_review")),
    "executive": Workflow("Executive reporting", (
        "oag_skills/finance/pptx-author/SKILL.md",
        "skills/productivity/powerpoint/SKILL.md",
    ), ("source_coverage", "report_totals", "artifact_open")),
    "incidents": Workflow("Safety and incidents", (
        "skills/software-development/security-review/SKILL.md",
        "oag_skills/security/oss-forensics/SKILL.md",
    ), ("source_coverage", "evidence_integrity", "recovery_proof")),
}


def workflow_ids() -> tuple[str, ...]:
    """Return the catalog keys in declaration order."""
    return tuple(WORKFLOWS)


def get_workflow(workflow_id: str) -> Workflow:
    """Return the workflow for *workflow_id* or raise :class:`ValueError`."""
    try:
        return WORKFLOWS[workflow_id]
    except KeyError as exc:
        raise ValueError(f"Unknown workflow: {workflow_id}") from exc


def skill_lookup_name(skill_path: str) -> str:
    """Return the discovery lookup name for a canonical skill path.

    ``oag_skills/finance/dcf-model/SKILL.md`` -> ``oag_skills/finance/dcf-model``.
    """
    normalized = skill_path.strip().replace("\\", "/").strip("/")
    suffix = f"/{SKILL_INDEX_FILENAME}"
    if normalized.endswith(suffix):
        return normalized[: -len(suffix)]
    if normalized == SKILL_INDEX_FILENAME:
        return ""
    return normalized
