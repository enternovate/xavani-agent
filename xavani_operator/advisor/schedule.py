# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Advisor schedule — the cron specs for the daily rituals (v1.0.0 ③).

Defines the three recurring jobs the Companion runs and a helper to register them
with the existing cron store (``cron/jobs.py``). The specs are pure data so they
can be asserted in tests without creating real jobs (which would write to
``~/.xavani/cron``). Registration is a thin, opt-in wrapper. Zero-LLM here (R10);
the jobs themselves may invoke the agent at run time.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AdvisorJob:
    """A single scheduled advisor ritual."""

    name: str
    schedule: str  # cron expression understood by cron.jobs.parse_schedule
    purpose: str


def advisor_jobs() -> list[AdvisorJob]:
    """The three rituals: morning brief, hourly chase (waking hours), 8pm error log."""
    return [
        AdvisorJob("xavani.advisor.morning_brief", "0 8 * * *", "Send the daily brief."),
        AdvisorJob("xavani.advisor.hourly_chase", "0 9-21 * * *", "Nudge today's open tasks."),
        AdvisorJob("xavani.advisor.evening", "0 20 * * *", "8pm error log + tomorrow's plan."),
    ]


def register_advisor_jobs(*, deliver: str = "telegram", create_job=None) -> list[dict]:
    """Register the advisor rituals with the cron store. Opt-in (has side effects).

    ``create_job`` defaults to ``cron.jobs.create_job``; tests pass a fake. Returns
    the created job dicts. The agent prompt for each job is self-contained so the
    scheduler can run it unattended.
    """
    if create_job is None:  # pragma: no cover - exercised via the real CLI, not unit tests
        from cron.jobs import create_job as _cj

        create_job = _cj

    prompts = {
        "xavani.advisor.morning_brief": (
            "Compose and send my morning brief: perceive the repo/goals, get the Oracle's "
            "wisdom verdict and the quantum decision, and deliver thoughts + recommendations."
        ),
        "xavani.advisor.hourly_chase": (
            "Check today's open tasks from my plan and, if any remain, send a short nudge."
        ),
        "xavani.advisor.evening": (
            "Run the 8pm ritual: ask the daily error-log questions, store my answers, and "
            "capture tomorrow's plan into the goals ledger."
        ),
    }
    created: list[dict] = []
    for job in advisor_jobs():
        created.append(
            create_job(
                prompt=prompts[job.name],
                schedule=job.schedule,
                name=job.name,
                deliver=deliver,
            )
        )
    return created
