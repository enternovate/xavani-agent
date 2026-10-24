# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Explicit workflow skill loading with host receipts.

Selecting a business workflow loads the *declared* skill bodies — not just a
suggestion list — and records a receipt with the content hash for each body.
Receipts live on the agent, survive context compression, and force a reload
before a consequential action.

Resolution deliberately reuses the existing discovery rules (``skill_view``:
local skills dir, ``skills.external_dirs``, disabled-skill and platform
rules).  This module adds no second filesystem search order.  Canonical
catalog paths are never executed; they are only looked up and read.
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from agent.workflow_catalog import WORKFLOWS, skill_lookup_name

logger = logging.getLogger(__name__)

# Marker left behind when compression prunes a loaded skill body.
PRUNED_MARKER = "[SKILL_PRUNED]"
# Below this window only the current step's skills are loaded.
SMALL_CONTEXT_TOKENS = 32_000
# config.yaml: skills.workflow_overrides.<canonical path> = approved skill
OVERRIDE_CONFIG_KEY = "workflow_overrides"

MODE_ASK = "ask"
MODE_PLAN = "plan"
MODE_BUILD = "build"
MODE_REVIEW = "review"
MODES = (MODE_ASK, MODE_PLAN, MODE_BUILD, MODE_REVIEW)
# Modes that change backend permissions: they refuse to start without the
# declared skills loaded.  Ask/Plan/Review explain the gap instead.
MODES_REQUIRING_SKILLS = frozenset((MODE_BUILD,))

RELOAD_INSTRUCTION = (
    "The skill bodies for this workflow are no longer in context. Before any "
    "consequential action, reload each skill below with "
    'skill_view(name="<lookup name>") and confirm its content hash matches '
    "the receipt. A body whose hash changed must be re-read before use."
)

RECEIPT_HEADER = "[Workflow skill receipt — recorded by the host]"


class WorkflowSkillError(ValueError):
    """A required workflow skill is unavailable, disabled, or unreadable."""

    def __init__(
        self,
        workflow_id: str,
        identifier: str,
        reason: str,
        detail: str = "",
    ) -> None:
        self.workflow_id = workflow_id
        self.identifier = identifier
        self.reason = reason
        self.detail = detail
        prefix = (
            "Required skill content unavailable"
            if reason in {"pruned", "empty"}
            else "Required skill unavailable"
        )
        message = f"{prefix}: {identifier} (reason: {reason})"
        if detail:
            message = f"{message} — {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class LoadedSkill:
    path: str
    sha256: str
    content: str
    resolved: str = ""


@dataclass(frozen=True)
class SkillResolution:
    """Outcome of resolving one canonical skill path."""

    identifier: str
    path: str | None = None
    reason: str = ""
    detail: str = ""
    name: str = ""


@dataclass(frozen=True)
class MissingPrerequisite:
    identifier: str
    reason: str
    detail: str = ""

    def describe(self) -> str:
        suffix = f" ({self.detail})" if self.detail else ""
        return f"{self.identifier} [{self.reason}]{suffix}"


@dataclass(frozen=True)
class WorkflowSelection:
    workflow_id: str
    name: str
    checks: tuple[str, ...]
    external_actions: bool
    mode: str
    skills: tuple[LoadedSkill, ...]
    declared: tuple[str, ...]
    deferred: tuple[str, ...]
    missing: tuple[MissingPrerequisite, ...]
    step_index: int = 0
    small_context: bool = False

    @property
    def blocked(self) -> bool:
        return bool(self.missing) and self.mode in MODES_REQUIRING_SKILLS

    @property
    def consequential(self) -> bool:
        return self.external_actions or self.mode in MODES_REQUIRING_SKILLS

    def explanation(self) -> str:
        """Explain what is missing and what a consequential mode would need."""
        if not self.missing:
            return ""
        prerequisites = "; ".join(item.describe() for item in self.missing)
        mode_note = (
            f"{self.mode} mode is blocked until every required skill loads."
            if self.mode in MODES_REQUIRING_SKILLS
            else (
                f"{self.mode} mode can continue read-only and explain the gap, "
                "but build mode stays blocked until every required skill loads."
            )
        )
        return (
            f"Workflow \"{self.name}\" is missing required skills: "
            f"{prerequisites}. {mode_note} Recovery: install or enable the "
            "skill (see `xavani skills`) or configure an approved override "
            "under skills.workflow_overrides in the active profile's "
            "config.yaml, then select the workflow again."
        )


# ── Resolution through the existing discovery rules ────────────────────────


def profile_skill_overrides() -> dict[str, str]:
    """Return the active profile's approved skill overrides.

    Read from the profile-scoped ``skills.workflow_overrides`` mapping in
    config.yaml: ``<canonical catalog path> -> <skill name or path>``.  An
    override takes precedence over the catalog path it replaces and is the
    approved way to point a workflow at a vetted replacement skill.
    """
    try:
        from agent.skill_preprocessing import load_skills_config

        raw = load_skills_config().get(OVERRIDE_CONFIG_KEY)
    except Exception:
        return {}
    if not isinstance(raw, dict):
        return {}
    overrides: dict[str, str] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not isinstance(value, str):
            continue
        if key.strip() and value.strip():
            overrides[key.strip()] = value.strip()
    return overrides


def _reason_from_error(error: str) -> str:
    lowered = (error or "").lower()
    if "is disabled" in lowered:
        return "disabled"
    if "not supported on this platform" in lowered:
        return "unsupported"
    if "ambiguous skill name" in lowered:
        return "ambiguous"
    if "not found" in lowered:
        return "missing"
    return "unavailable"


def resolve_skill_path(relative_name: str) -> SkillResolution:
    """Resolve a skill lookup name through the existing discovery rules."""
    try:
        from tools.skills_tool import SKILLS_DIR, skill_view

        payload = json.loads(skill_view(relative_name, preprocess=False))
    except Exception as exc:  # discovery unavailable — never guess a path
        logger.debug("skill discovery failed for %s: %s", relative_name, exc)
        return SkillResolution(relative_name, None, "unavailable", str(exc))

    if not payload.get("success"):
        error = str(payload.get("error") or "")
        return SkillResolution(
            relative_name,
            None,
            _reason_from_error(error),
            error,
        )

    skill_dir = payload.get("skill_dir")
    if skill_dir:
        index_file = Path(str(skill_dir)) / "SKILL.md"
    else:
        index_file = Path(str(SKILLS_DIR)) / str(payload.get("path") or "")
    return SkillResolution(
        relative_name,
        str(index_file),
        "",
        "",
        str(payload.get("name") or ""),
    )


def resolve_skill_file(identifier: str) -> SkillResolution:
    """Resolve a canonical catalog path, honouring the profile override.

    A declared override is authoritative: when it does not resolve the failure
    is reported as ``override_unavailable`` instead of silently falling back
    to the catalog path the user replaced.
    """
    override = profile_skill_overrides().get(identifier)
    target = override or identifier
    lookup = skill_lookup_name(target) or target
    resolution = resolve_skill_path(lookup)
    if override and resolution.path is None:
        return SkillResolution(
            identifier,
            None,
            "override_unavailable",
            f"approved override {override!r} did not resolve ({resolution.reason})",
        )
    return replace(resolution, identifier=identifier)


# ── Loading ────────────────────────────────────────────────────────────────


def _read_skill(workflow_id: str, identifier: str, resolved_path: str) -> LoadedSkill:
    path = Path(resolved_path)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowSkillError(workflow_id, identifier, "unreadable", str(exc)) from exc
    if not content.strip():
        raise WorkflowSkillError(workflow_id, identifier, "empty")
    if PRUNED_MARKER in content:
        raise WorkflowSkillError(workflow_id, identifier, "pruned")
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return LoadedSkill(identifier, digest, content, str(path))


def load_skill_identifiers(
    workflow_id: str,
    identifiers: tuple[str, ...],
    resolve_skill=None,
) -> tuple[LoadedSkill, ...]:
    """Load *identifiers*, stopping at the first unavailable skill."""
    resolver = resolve_skill or resolve_skill_file
    loaded: list[LoadedSkill] = []
    for identifier in identifiers:
        resolved = resolver(identifier)
        path = getattr(resolved, "path", resolved)
        if path is None:
            raise WorkflowSkillError(
                workflow_id,
                identifier,
                getattr(resolved, "reason", "") or "unavailable",
                getattr(resolved, "detail", ""),
            )
        loaded.append(_read_skill(workflow_id, identifier, str(path)))
    return tuple(loaded)


def load_workflow_skills(workflow_id: str, resolve_skill=None) -> tuple[LoadedSkill, ...]:
    """Load every skill declared by *workflow_id* (raises when one is missing)."""
    workflow = WORKFLOWS[workflow_id]
    return load_skill_identifiers(workflow_id, tuple(workflow.skills), resolve_skill)


# ── Selection ──────────────────────────────────────────────────────────────


def select_workflow(
    workflow_id: str,
    *,
    mode: str = MODE_ASK,
    step_index: int = 0,
    context_window_tokens: int | None = None,
    resolve_skill=None,
) -> WorkflowSelection:
    """Select a workflow and load the skills the current step needs.

    A small context window loads only the skill for *step_index*; everything
    else is deferred.  A mode in :data:`MODES_REQUIRING_SKILLS` raises
    :class:`WorkflowSkillError` when a required skill does not load.  The
    remaining modes return a selection that explains the gap.
    """
    if mode not in MODES:
        raise ValueError(f"Unknown mode: {mode}")
    workflow = WORKFLOWS.get(workflow_id)
    if workflow is None:
        raise ValueError(f"Unknown workflow: {workflow_id}")

    declared = tuple(workflow.skills)
    small_context = (
        context_window_tokens is not None and context_window_tokens < SMALL_CONTEXT_TOKENS
    )
    index = max(0, min(int(step_index), max(len(declared) - 1, 0)))
    if small_context:
        wanted = declared[index : index + 1]
        deferred = declared[:index] + declared[index + 1 :]
    else:
        wanted = declared
        deferred = ()

    skills: list[LoadedSkill] = []
    missing: list[MissingPrerequisite] = []
    for identifier in wanted:
        try:
            skills.extend(load_skill_identifiers(workflow_id, (identifier,), resolve_skill))
        except WorkflowSkillError as exc:
            missing.append(MissingPrerequisite(identifier, exc.reason, exc.detail))

    if missing and mode in MODES_REQUIRING_SKILLS:
        first = missing[0]
        raise WorkflowSkillError(workflow_id, first.identifier, first.reason, first.detail)

    return WorkflowSelection(
        workflow_id=workflow_id,
        name=workflow.name,
        checks=tuple(workflow.checks),
        external_actions=bool(workflow.external_actions),
        mode=mode,
        skills=tuple(skills),
        declared=declared,
        deferred=deferred,
        missing=tuple(missing),
        step_index=index,
        small_context=small_context,
    )


# ── Receipts ───────────────────────────────────────────────────────────────


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class WorkflowReceipt:
    """Host record that a canonical skill body was loaded into context."""

    workflow_id: str
    path: str
    resolved: str
    sha256: str
    loaded_at: str
    origin: str = "host"
    pruned: bool = False


class WorkflowSkillState:
    """Per-agent receipt store for explicitly loaded workflow skills.

    The store is the host's record: it holds the canonical path, the resolved
    absolute path, and the content hash of every skill body the workflow
    loaded.  Bodies are kept in memory so a compressed (pruned) body can be
    reloaded before a consequential action.
    """

    def __init__(self) -> None:
        self._receipts: dict[str, WorkflowReceipt] = {}
        self._contents: dict[str, str] = {}
        self._workflow_id: str = ""
        self._revision: int = 0

    @property
    def workflow_id(self) -> str:
        return self._workflow_id

    @property
    def revision(self) -> int:
        return self._revision

    def record(
        self,
        workflow_id: str,
        skills: tuple[LoadedSkill, ...],
    ) -> tuple[WorkflowReceipt, ...]:
        stamp = _now()
        for skill in skills:
            self._receipts[skill.path] = WorkflowReceipt(
                workflow_id=workflow_id,
                path=skill.path,
                resolved=skill.resolved,
                sha256=skill.sha256,
                loaded_at=stamp,
            )
            self._contents[skill.path] = skill.content
        self._workflow_id = workflow_id
        self._revision += 1
        return self.receipts(workflow_id)

    def receipts(self, workflow_id: str | None = None) -> tuple[WorkflowReceipt, ...]:
        values = tuple(self._receipts.values())
        if workflow_id is None:
            return values
        return tuple(r for r in values if r.workflow_id == workflow_id)

    def content(self, path: str) -> str:
        return self._contents.get(path, "")

    def reload_instruction(self) -> str:
        return RELOAD_INSTRUCTION

    def all_pruned(self) -> bool:
        receipts = self.receipts()
        return bool(receipts) and all(r.pruned for r in receipts)

    def mark_pruned(self) -> None:
        """Mark every loaded body as no longer present in context."""
        for path, receipt in self._receipts.items():
            self._receipts[path] = replace(receipt, pruned=True)

    def clear(self, workflow_id: str | None = None) -> None:
        for path, receipt in list(self._receipts.items()):
            if workflow_id is None or receipt.workflow_id == workflow_id:
                self._receipts.pop(path, None)
                self._contents.pop(path, None)

    def receipt_block(self) -> str:
        """Deterministic receipt text (no clock reads after recording)."""
        receipts = self.receipts()
        if not receipts:
            return ""
        lines = [RECEIPT_HEADER, f"workflow: {self._workflow_id}"]
        for receipt in receipts:
            state = "pruned" if receipt.pruned else "loaded"
            lines.append(
                f"- {receipt.path} sha256:{receipt.sha256} state:{state} "
                f"origin:{receipt.origin} loaded_at:{receipt.loaded_at}"
            )
        return "\n".join(lines)

    def context_block(self) -> str:
        block = self.receipt_block()
        if not block:
            return ""
        if self.all_pruned():
            return f"{block}\n{RELOAD_INSTRUCTION}"
        return block

    def refresh_at_boundary(self, resolve_skill=None) -> tuple[tuple[str, str], ...]:
        """Re-read loaded skills at a safe task boundary.

        Returns ``(path, new_sha256)`` for every body whose content changed.
        A body that can no longer be loaded is marked pruned so the next
        consequential action has to reload it.
        """
        changed: list[tuple[str, str]] = []
        for path, receipt in list(self._receipts.items()):
            try:
                skill = load_skill_identifiers(
                    receipt.workflow_id, (path,), resolve_skill
                )[0]
            except WorkflowSkillError as exc:
                logger.warning("workflow skill %s unavailable at boundary: %s", path, exc)
                self._receipts[path] = replace(receipt, pruned=True)
                continue
            self._contents[path] = skill.content
            if skill.sha256 != receipt.sha256:
                changed.append((path, skill.sha256))
            self._receipts[path] = replace(
                receipt,
                sha256=skill.sha256,
                resolved=skill.resolved,
                loaded_at=_now(),
                pruned=False,
            )
        return tuple(changed)

    def reload_pruned(self, resolve_skill=None) -> tuple[LoadedSkill, ...]:
        """Reload every pruned body; raise when one cannot be reloaded."""
        reloaded: list[LoadedSkill] = []
        for path, receipt in list(self._receipts.items()):
            if not receipt.pruned:
                continue
            skill = load_skill_identifiers(receipt.workflow_id, (path,), resolve_skill)[0]
            self._receipts[path] = replace(
                receipt,
                sha256=skill.sha256,
                resolved=skill.resolved,
                loaded_at=_now(),
                pruned=False,
            )
            self._contents[path] = skill.content
            reloaded.append(skill)
        return tuple(reloaded)


# ── Agent-facing helpers ───────────────────────────────────────────────────


def workflow_state(agent) -> WorkflowSkillState | None:
    """Return the agent's receipt store, if the host attached one."""
    state = getattr(agent, "_workflow_skill_state", None)
    return state if isinstance(state, WorkflowSkillState) else None


def record_selection(agent, selection: WorkflowSelection) -> tuple[WorkflowReceipt, ...]:
    """Record the loaded content hashes of *selection* on the host."""
    state = workflow_state(agent)
    if state is None:
        return ()
    return state.record(selection.workflow_id, selection.skills)


def workflow_context_block(agent) -> str:
    """Receipt (+ reload instruction) for injection into the turn messages.

    Never part of the system prompt: the system prompt must stay byte-stable
    within the active turn.
    """
    state = workflow_state(agent)
    return state.context_block() if state is not None else ""


def refresh_workflow_skills_at_boundary(agent, resolve_skill=None) -> tuple[tuple[str, str], ...]:
    """Apply on-disk skill edits at a safe task boundary."""
    state = workflow_state(agent)
    return state.refresh_at_boundary(resolve_skill) if state is not None else ()


def ensure_workflow_skills_loaded(agent, resolve_skill=None) -> tuple[LoadedSkill, ...]:
    """Reload pruned bodies before a consequential action."""
    state = workflow_state(agent)
    return state.reload_pruned(resolve_skill) if state is not None else ()


def retain_workflow_receipts(agent, messages: list) -> bool:
    """Keep receipts and the reload instruction across compression.

    Called by :func:`agent.conversation_compression.compress_context` after the
    summariser runs: the loaded bodies are no longer in context, so every
    receipt is marked pruned and the receipt block plus reload instruction is
    re-injected as a message.
    """
    state = workflow_state(agent)
    if state is None or not state.receipts():
        return False
    state.mark_pruned()
    messages.append({"role": "user", "content": state.context_block()})
    return True
