# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""CLI dispatch for `xavani operator` (v0.7.0 operator U5, U22, U28, U29).

Thin command layer wired into ``xavani_cli/main.py``. Heavy logic lives in the
package so this module stays import-light and the CLI starts fast.
``cmd_operator`` is the single entry point argparse dispatches to.

Subcommands:
  init       scaffold xavani.product.yaml                       (M0)
  status     read-only view of the product                      (M0)
  perceive   print the deterministic state snapshot             (M1)
  decide     rank opportunities (dry-run)                       (M1)
  propose    perceive→decide→make a tier-tagged proposal        (M2)
  proposals  list proposals (pending by default)                (M2)
  approve    approve a proposal by id                           (M2)
  reject     reject a proposal by id                            (M2)
  (cycle / run execute approved plans — arrive in M3)
"""

from __future__ import annotations

from typing import Any


def cmd_operator(args: Any) -> None:
    """Dispatch a ``xavani operator <subcommand>`` invocation."""
    command = getattr(args, "operator_command", None)
    handler = {
        "init": _cmd_init,
        "status": _cmd_status,
        "perceive": _cmd_perceive,
        "decide": _cmd_decide,
        "propose": _cmd_propose,
        "proposals": _cmd_proposals,
        "approve": _cmd_approve,
        "reject": _cmd_reject,
        "cycle": _cmd_cycle,
        "run": _cmd_run,
    }.get(command)
    if handler is None:
        _print_usage()
    else:
        handler(args)


# --- config helpers ---------------------------------------------------------

def _resolve_config_path(args: Any):
    from pathlib import Path

    from xavani_operator.scaffold import CONFIG_FILENAME

    base = Path(getattr(args, "path", ".") or ".")
    return base / CONFIG_FILENAME if base.is_dir() else base


def _load_or_report(args: Any):
    from xavani_operator.config import ConfigError, load_product_config
    from xavani_operator.scaffold import CONFIG_FILENAME

    cfg_path = _resolve_config_path(args)
    if not cfg_path.exists():
        print(f"No {CONFIG_FILENAME} at {cfg_path} — run `xavani operator init`.")
        return None
    try:
        return load_product_config(cfg_path)
    except ConfigError as exc:
        print(f"✗ {cfg_path} is invalid:\n{exc}")
        return None


def _open_queue():
    from xavani_operator.approval_queue import ApprovalQueue
    from xavani_operator.audit import AuditLog
    from xavani_operator.state import OperatorState

    st = OperatorState()
    return ApprovalQueue(st, audit=AuditLog(st))


# --- M0/M1 commands ---------------------------------------------------------

def _cmd_init(args: Any) -> None:
    from xavani_operator.scaffold import init_product_config

    path = getattr(args, "path", ".") or "."
    name = getattr(args, "name", None)
    force = bool(getattr(args, "force", False))
    try:
        written = init_product_config(path, name=name, force=force)
    except FileExistsError as exc:
        print(f"⚠  {exc}")
        return
    print(f"✓ Wrote {written}")
    print("  Next: edit goals/channels/brand, then `xavani operator propose`.")


def _cmd_status(args: Any) -> None:
    cfg = _load_or_report(args)
    if cfg is None:
        return
    from xavani_operator.approval_queue import ApprovalQueue
    from xavani_operator.loop import last_checkpoint
    from xavani_operator.state import OperatorState
    from xavani_operator.types import ProposalStatus

    cadence = cfg.schedule.cycle_cadence or "(manual)"
    print(f"Operator → {cfg.product.name}")
    print(
        f"  goals: {len(cfg.goals)} · channels: {len(cfg.channels)} · "
        f"cadence: {cadence} · repo: {cfg.product.repo}"
    )
    st = OperatorState()
    pending = ApprovalQueue(st).list(ProposalStatus.PENDING)
    print(f"  pending approvals: {len(pending)}")
    cp = last_checkpoint(st)
    if cp:
        print(f"  last cycle: {cp['cycle_id']} — {cp.get('notes', '')}")


def _cmd_cycle(args: Any) -> None:
    cfg = _load_or_report(args)
    if cfg is None:
        return
    from xavani_operator.loop import run_cycle
    from xavani_operator.state import OperatorState
    from xavani_operator.workstreams.build import build_handlers
    from xavani_operator.workstreams.build import register as register_build
    from xavani_operator.workstreams.promote import promote_handlers
    from xavani_operator.workstreams.promote import register as register_promote

    register_build()    # taste-integrated planning for build work
    register_promote()  # brand-voiced planning for promote work
    if getattr(args, "execute", False):
        from xavani_operator.workstreams.build_effectors import tool_build_effectors
        from xavani_operator.workstreams.promote_effectors import tool_promote_effectors

        state = OperatorState()
        handlers = {
            **build_handlers(tool_build_effectors(cfg.product.repo or ".")),
            **promote_handlers(tool_promote_effectors(cfg, state=state)),
        }
        print(f"Running one operator cycle for {cfg.product.name} (real build+promote effectors)…")
        run_cycle(cfg, state, handlers=handlers, sender=print)
    else:
        print(f"Running one operator cycle for {cfg.product.name} (safe dry steps)…")
        run_cycle(cfg, OperatorState(), sender=print)
        print("  (safe Tier-0/1 stubs ran; pass --execute for real build+promote effectors)")


def _cmd_run(args: Any) -> None:
    cfg = _load_or_report(args)
    if cfg is None:
        return
    from xavani_operator.continuous import run_continuous
    from xavani_operator.loop import run_cycle
    from xavani_operator.state import OperatorState
    from xavani_operator.workstreams.build import register as register_build
    from xavani_operator.workstreams.promote import register as register_promote

    register_build()
    register_promote()
    state = OperatorState()
    iterations = int(getattr(args, "iterations", 1) or 1)
    interval = float(getattr(args, "interval", 60.0))
    print(
        f"Operator running continuously for {cfg.product.name} — "
        f"{iterations} tick(s), {interval:g}s interval (honours quiet hours + backpressure)…"
    )
    outcomes = run_continuous(
        cfg, state,
        run_once=lambda: run_cycle(cfg, state, sender=print),
        iterations=iterations,
        interval=interval,
    )
    for i, outcome in enumerate(outcomes, 1):
        print(f"  tick {i}: {outcome['status']}")


def _cmd_perceive(args: Any) -> None:
    cfg = _load_or_report(args)
    if cfg is None:
        return
    from xavani_operator.perceive import perceive

    p = perceive(cfg)
    repo = p.repo
    print(f"Perception of {cfg.product.name}  [hash {p.content_hash}]")
    if repo.get("is_git"):
        state = "dirty" if repo["dirty"] else "clean"
        print(f"  repo: branch {repo['branch']} · {state} ({repo['dirty_files']} files)")
    else:
        print("  repo: (not a git repo)")
    tests = p.tests
    test_line = f"{tests['failing']} failing" if tests.get("known") else "unknown (no pytest cache)"
    print(f"  tests: {test_line}")
    print(f"  issues: {len(p.issues)} TODO/FIXME marker(s)")
    print(f"  channels: {', '.join(p.channels) or '(none)'}")


def _cmd_decide(args: Any) -> None:
    cfg = _load_or_report(args)
    if cfg is None:
        return
    from xavani_operator.decide import decide
    from xavani_operator.opportunities import detect
    from xavani_operator.perceive import perceive

    opps = detect(perceive(cfg), cfg)
    if not opps:
        print("No opportunities right now — nothing to propose.")
        return
    print(f"Ranked opportunities for {cfg.product.name} (dry-run, no action):")
    for o in opps:
        print(f"  [{o.score:.2f}] {o.workstream}/{o.kind} — {o.rationale}")
    intent = decide(opps, cfg)
    top = intent.opportunity
    print(f"→ would act on: {top.workstream}/{top.kind}")


# --- M2 commands ------------------------------------------------------------

def _cmd_propose(args: Any) -> None:
    cfg = _load_or_report(args)
    if cfg is None:
        return
    from xavani_operator.approval_queue import gate
    from xavani_operator.decide import decide
    from xavani_operator.notify import format_approval_request
    from xavani_operator.opportunities import detect
    from xavani_operator.perceive import perceive
    from xavani_operator.propose import make_proposal
    from xavani_operator.types import ProposalStatus

    intent = decide(detect(perceive(cfg), cfg), cfg)
    if intent is None:
        print("No opportunities right now — nothing to propose.")
        return
    proposal = make_proposal(intent, ctx={"tier_overrides": cfg.approval.tier_overrides})
    queue = _open_queue()
    queue.enqueue(proposal)
    if gate(proposal) == ProposalStatus.APPROVED:
        queue.approve(proposal.id)
        print(f"✓ Proposed + auto-approved {proposal.id} (all steps safe).")
        print("  Run `xavani operator cycle` to execute (arrives in M3).")
    else:
        print(f"📋 Proposed {proposal.id} — needs your approval:\n")
        print(format_approval_request(proposal, cfg))


def _cmd_proposals(args: Any) -> None:
    from xavani_operator.types import ProposalStatus

    queue = _open_queue()
    show_all = bool(getattr(args, "all", False))
    proposals = queue.list(None if show_all else ProposalStatus.PENDING)
    if not proposals:
        print("No proposals." if show_all else "No pending proposals.")
        return
    for p in proposals:
        opp = p.intent.opportunity
        print(f"  {p.id}  [{p.status.value}]  {opp.workstream}/{opp.kind} — {opp.rationale}")


def _cmd_approve(args: Any) -> None:
    _decide_proposal(args, approve=True)


def _cmd_reject(args: Any) -> None:
    _decide_proposal(args, approve=False)


def _decide_proposal(args: Any, approve: bool) -> None:
    pid = getattr(args, "proposal_id", None)
    if not pid:
        print("Usage: xavani operator approve|reject <proposal_id>")
        return
    queue = _open_queue()
    result = queue.approve(pid) if approve else queue.reject(pid)
    if result is None:
        print(f"No such proposal: {pid}")
        return
    verb = "✓ Approved" if approve else "✗ Rejected"
    print(f"{verb} {pid} (status: {result.status.value})")
    if approve:
        print("  It will run on the next `xavani operator cycle` (M3).")


def _print_usage() -> None:
    print("xavani operator — autonomous build + promote (it proposes, you approve)")
    print("  init       scaffold xavani.product.yaml")
    print("  status     show the operator's view of this product")
    print("  perceive   print the deterministic state snapshot")
    print("  decide     rank opportunities (dry-run)")
    print("  propose    make a tier-tagged proposal from the top opportunity")
    print("  proposals  list proposals (pending by default; --all for every)")
    print("  approve    approve a proposal: xavani operator approve <id>")
    print("  reject     reject a proposal:  xavani operator reject <id>")
    print("  cycle      run one full Perceive→…→Learn cycle")
    print("  run        run continuously (quiet-hours + backpressure aware)")
