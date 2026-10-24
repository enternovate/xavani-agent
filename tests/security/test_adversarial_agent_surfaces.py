# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Adversarial corpus for the agent-side trust surfaces (R1 Task 28a-agent).

METHODOLOGY
-----------
Each test is an *executable attack case* against one live trust surface, in
the CyberGym style: a concrete adversary action plus a hard assertion on the
*defensive* outcome.  A case PASSES when the defense holds; if an attack
succeeds the case is a **finding**, not a test tweak.  Surfaces:

  * RECEIPTS  — ``agent/verification_receipts.py`` + ``agent/completion_contract.py``
  * CONTRACT  — ``agent/completion_contract.py::decide_completion``
  * HASHLINE  — ``tools/hashline/*`` driven through ``tools/edit_tool.py``
  * APPROVAL  — ``tools/approval.py`` (pattern-scoped command authorization)

Runs with **no network and no real model**: the agent-loop case uses the
faux-provider harness (``tests/harness/faux_provider.py``); every other case
drives the real public functions.  ``tests/conftest.py`` supplies the
hermetic env — per-test ``XAVANI_HOME`` tempdir (so the receipt store and
snapshot registry never touch the real ``~/.xavani``), credential scrubbing,
and state resets.

FINDINGS (attacks that succeed -- documented as explicit cases below)
--------------------------------------------------------------------
The corpus asserts the defense where it holds and *pins the observed
behaviour* where it does not, so the gap is recorded rather than hidden.
Each such case is named ``..._is_a_documented_limitation`` and carries a
``DOCUMENTED FINDING`` docstring with severity + file:line evidence:

  * F1 ``test_attack_approval_swapped_command_same_pattern_...`` --
    approval authorization is bound to the matched *pattern description*,
    not to a per-command digest, so a session/always approval of one
    command auto-authorizes any other command in the same class
    (``tools/approval.py:561`` key, ``:1253`` check).  Severity LOW / by
    design (the user approves the class; the hardline floor is unaffected).
  * F2 ``test_attack_receipts_db_consistent_forgery_...`` and
    ``test_attack_receipts_in_process_host_receipt_...`` -- the SQLite
    receipt store carries no MAC/signature; a well-formed payload tamper
    (status AND exit_code flipped together) or a direct in-process
    ``origin='host'`` append is indistinguishable from a runner receipt
    (``tools/verification_receipts.py:74``).  Severity LOW: local, host-only,
    write-access-already-implies-compromise; the ``passed => exit_code == 0``
    invariant (``agent/completion_contract.py:105``) still catches sloppy
    tampering (see the status-only flip case).
  * F3 ``test_attack_hashline_disk_drift_without_reread_...`` -- an external
    write between read and edit is NOT a stale-tag refusal: ``apply_sections``
    validates against the in-memory snapshot (``tools/hashline/apply.py:360``),
    not the live file, and drift surfaces only as an mtime warning
    (``tools/file_tools.py:991``).  The edit wins and overwrites the external
    change.  Severity LOW: the edit writes only the content the task
    OBSERVED, so an attacker cannot inject content through this vector (their
    change is discarded); impact is loss of a concurrent writer's change.
"""

import json
import os
import sqlite3
import time
from dataclasses import asdict

import pytest

from agent.completion_contract import (
    CheckReceipt,
    CompletionContract,
    decide_completion,
)
from agent.verification_receipts import ReceiptStore
from agent.verification_runner import (
    current_revision,
    note_work_change,
    run_host_check,
    run_required_checks,
    set_completion_contract,
)

from tools import approval

from tests.agent.test_completion_contract_wiring import (
    attach_contract as wiring_attach_contract,
    make_agent,
)
from tests.agent.test_verification_receipts import make_receipt
from tests.agent.test_verification_runner import _StubAgent
from tests.harness.faux_provider import ScriptedSession
from tests.tools.test_hashline_visible_ranges import (
    NOT_SEEN,
    READ_FIRST,
    _FakeFileOps,
    _edit,
    _install_ops,
    _read,
    _tag_of,
    _write,
)


# ===========================================================================
# Shared builders
# ===========================================================================


def make_contract(**changes) -> CompletionContract:
    """A work contract; defaults to one required check (``unit``)."""
    values = dict(
        contract_id="contract-1",
        session_id="session-1",
        workspace_id="workspace-1",
        workflow_id="engineering",
        goal="Pass the required checks.",
        required_checks=("unit",),
        required_skills=(),
        allowed_actions=(),
        approved_at="2026-01-01T00:00:00Z",
        revision="r1",
    )
    values.update(changes)
    return CompletionContract(**values)


def _passed_execute(argv, cwd):  # pragma: no cover - trivial
    return {"exit_code": 0}


def _tamper_payload(path, receipt_id: str, payload: dict) -> None:
    """Rewrite an existing receipt row's payload bytes (out-of-band tamper)."""
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE verification_receipts SET payload = ? WHERE receipt_id = ?",
            (json.dumps(payload), receipt_id),
        )
        connection.commit()
    finally:
        connection.close()


# ===========================================================================
# RECEIPTS -- the store only ever holds host-origin evidence
# ===========================================================================


def test_attack_receipts_model_origin_append_rejected(tmp_path):
    """A model-authored receipt (origin='model') must be refused up front.

    The adversary crafts a receipt that is host-shaped in every field --
    command, cwd, hashes, timestamps, a clean exit 0 -- and only the origin
    label betrays it.  The store must reject on the origin alone and must
    not so much as create the database file.
    """
    path = tmp_path / "receipts.sqlite3"
    store = ReceiptStore(path)
    forged = make_receipt(origin="model")

    with pytest.raises(ValueError):
        store.append(forged)

    assert not path.exists(), "a rejected receipt must not create the store"


@pytest.mark.parametrize(
    "spoofed_origin",
    ["Host", "HOST", "host ", " host", "host\n", "hosty", "model", "host_host"],
)
def test_attack_receipts_spoofed_origin_label_rejected(tmp_path, spoofed_origin):
    """Origin matching is exact: look-alike labels must not slip through.

    An attacker tries to defeat a naive ``origin.lower().startswith('host')``
    or ``origin.strip()`` check with case/whitespace/substring variants.  The
    guard compares against the literal ``"host"`` (``verification_receipts.py``
    ``append``), so every variant is refused.
    """
    store = ReceiptStore(tmp_path / "receipts.sqlite3")
    with pytest.raises(ValueError):
        store.append(make_receipt(origin=spoofed_origin))


def test_attack_receipts_cross_contract_check_id_rejected(tmp_path):
    """A receipt may not claim a check_id that belongs to another contract.

    Contract A requires ``unit``; contract B requires ``lint``.  The attacker
    asks the host runner to execute B's check ``lint`` *under A's identity* --
    a receipt that would let A borrow B's evidence.  ``run_host_check`` must
    reject any check_id not in the contract's ``required_checks``.
    """
    contract_a = make_contract(required_checks=("unit",))
    contract_b = make_contract(contract_id="contract-2", required_checks=("lint",))

    # Positive control: A's own check is accepted.
    ok = run_host_check(contract_a, "unit", ("pytest",), "cwd", "r1:0", _passed_execute)
    assert ok.check_id == "unit" and ok.contract_id == "contract-1"

    # The attack: B's check id under A's contract.
    with pytest.raises(ValueError):
        run_host_check(contract_a, "lint", ("ruff",), "cwd", "r1:0", _passed_execute)

    # And symmetrically, A's check under B.
    with pytest.raises(ValueError):
        run_host_check(contract_b, "unit", ("pytest",), "cwd", "r1:0", _passed_execute)


def test_attack_receipts_crafted_duplicate_id_rejected(tmp_path):
    """A crafted duplicate receipt_id must not overwrite the recorded receipt.

    The attacker replays the first receipt's id with a *different* check and a
    passing status, hoping a second insert overwrites or shadows the first.
    The ``receipt_id`` UNIQUE constraint must reject it and keep the original.
    """
    store = ReceiptStore(tmp_path / "receipts.sqlite3")
    store.append(make_receipt())

    with pytest.raises(sqlite3.IntegrityError):
        store.append(
            make_receipt(check_id="lint", status="passed", exit_code=0)
        )

    assert store.for_contract("contract-1") == (make_receipt(),)


def test_attack_receipts_db_status_flip_detected(tmp_path):
    """An out-of-band status flip alone is caught by the decode invariant.

    The attacker edits the stored payload to turn a FAILED check into
    ``status='passed'`` while leaving ``exit_code=1``.  ``CheckReceipt``
    enforces ``status == 'passed' => exit_code == 0`` on decode
    (``completion_contract.py:105``), so the row raises instead of being
    served as evidence.
    """
    path = tmp_path / "receipts.sqlite3"
    store = ReceiptStore(path)
    failed = make_receipt(status="failed", exit_code=1)
    store.append(failed)

    payload = asdict(failed)
    payload["status"] = "passed"  # exit_code deliberately left at 1
    _tamper_payload(path, "receipt-1", payload)

    with pytest.raises(ValueError):
        store.for_contract("contract-1")


def test_attack_receipts_db_consistent_forgery_is_a_documented_limitation(tmp_path):
    """DOCUMENTED FINDING F2 (severity: LOW) -- tamper is not integrity-checked.

    The attacker flips *both* ``status`` and ``exit_code`` so the payload
    stays internally consistent.  The store has no MAC/HMAC/signature over
    the payload (``tools/verification_receipts.py`` -- the row is plain JSON
    in a local SQLite file), so the forged passing receipt is decoded and
    served unchanged.  This case pins that behaviour so the gap is visible.

    Scope assessment: the store is host-only, local, single-file; a writer
    able to rewrite it already has filesystem access equivalent to full
    compromise, so this is a LIMITATION of convenience, not a remote attack
    path.  The invariant check (previous case) limits sloppy tampering.
    """
    path = tmp_path / "receipts.sqlite3"
    store = ReceiptStore(path)
    failed = make_receipt(status="failed", exit_code=1)
    store.append(failed)

    payload = asdict(failed)
    payload["status"] = "passed"
    payload["exit_code"] = 0
    _tamper_payload(path, "receipt-1", payload)

    stored = store.for_contract("contract-1")
    assert len(stored) == 1
    assert stored[0].status == "passed", (
        "DOCUMENTED FINDING F2: a consistent payload forgery is undetectable"
    )
    assert stored[0].origin == "host"


def test_attack_receipts_in_process_host_receipt_is_a_documented_limitation(tmp_path):
    """DOCUMENTED FINDING F2 (severity: LOW) -- provenance is by convention.

    The store authenticates nothing about the *writer*: ``append`` only
    checks the receipt's ``origin`` field equals ``"host"``
    (``tools/verification_receipts.py:74``).  A malicious in-process caller
    that constructs a ``CheckReceipt`` with ``origin='host'`` and never goes
    near ``run_host_check`` gets its evidence accepted.  The defense is that
    only the runner builds host receipts -- a convention enforced by code
    review, not cryptography.  Same scope argument as F2 above.
    """
    store = ReceiptStore(tmp_path / "receipts.sqlite3")
    forged = CheckReceipt(
        receipt_id="forged-1",
        contract_id="contract-1",
        check_id="unit",
        workspace_id="workspace-1",
        revision="r1:0",
        command_argv=("true",),
        cwd="/",
        exit_code=0,
        status="passed",
        artifact_hashes=(),
        started_at="2026-01-01T00:00:00Z",
        finished_at="2026-01-01T00:00:01Z",
        origin="host",  # the lie the store cannot detect
    )

    store.append(forged)

    assert store.for_contract("contract-1") == (forged,), (
        "DOCUMENTED FINDING F2: the store trusts the origin label"
    )


# ===========================================================================
# CONTRACT -- pass requires current, contract-matched host evidence
# ===========================================================================


def test_attack_contract_stale_revision_receipts_do_not_decide():
    """Receipts from revision r1:0 must not pass a decision at r1:1.

    The work product changes after the checks ran (``note_work_change``), so
    the evidence is stale.  ``decide_completion`` must ignore every receipt
    whose ``revision`` differs from the current revision and return
    ``unverified`` -- never ``passed``.
    """
    agent = _StubAgent()
    contract = make_contract()
    set_completion_contract(agent, contract, {"unit": ("pytest",)}, execute=_passed_execute)

    receipts = run_required_checks(agent, "task-1")
    assert [r.revision for r in receipts] == ["r1:0"]
    assert decide_completion(contract, receipts, current_revision(agent)).state == "passed"

    note_work_change(agent)
    assert current_revision(agent) == "r1:1"

    decision = decide_completion(contract, receipts, current_revision(agent))
    assert decision.state == "unverified"
    assert decision.missing_checks == ("unit",)


def test_attack_contract_cancelled_receipt_never_passes():
    """A cancelled check must resolve to blocked, never to passed.

    The adversary turns the required check into a cancellation (user aborted
    mid-run).  A cancelled receipt is not evidence of success: the decision
    must be ``blocked`` and must never be ``passed``, even though a receipt
    for the check exists.
    """
    contract = make_contract()

    def cancelled(argv, cwd):
        return {"cancelled": True}

    receipt = run_host_check(contract, "unit", ("pytest",), "cwd", "r1:0", cancelled)
    assert receipt.status == "cancelled"
    assert receipt.exit_code is None

    decision = decide_completion(contract, (receipt,), "r1:0")
    assert decision.state == "blocked"
    assert decision.state != "passed"


def test_attack_contract_zero_receipts_never_passes():
    """A contract with no receipts is unverified/missing -- never passed.

    The attacker asserts completion with no evidence at all.  Every required
    check is reported missing and the state is ``unverified``.
    """
    contract = make_contract(required_checks=("unit", "lint"))

    decision = decide_completion(contract, (), "r1:0")

    assert decision.state == "unverified"
    assert decision.missing_checks == ("unit", "lint")


@pytest.mark.parametrize(
    "receipt_kwargs,label",
    [
        ({"workspace_id": "workspace-OTHER"}, "foreign workspace"),
        ({"origin": "model"}, "model origin"),
        ({"contract_id": "contract-OTHER"}, "foreign contract"),
    ],
)
def test_attack_contract_foreign_or_model_receipt_is_not_evidence(receipt_kwargs, label):
    """A passing receipt that does not match contract/workspace/origin is void.

    Even a clean ``status='passed'`` receipt contributes no evidence unless
    its contract_id, workspace_id and origin all match the live contract.
    """
    contract = make_contract()
    passing = run_host_check(
        contract, "unit", ("pytest",), "cwd", "r1:0", _passed_execute
    )
    from dataclasses import replace

    impostor = replace(passing, **receipt_kwargs)

    decision = decide_completion(contract, (impostor,), "r1:0")

    assert decision.state == "unverified", label
    assert decision.missing_checks == ("unit",)


# ===========================================================================
# HASHLINE PROVENANCE -- a tag authorizes only what this task observed
# ===========================================================================


@pytest.fixture(autouse=True)
def _clean_task_stores():
    yield
    from tools.hashline.snapshots import task_stores

    for tid in ("task-a", "task-b", "task-attacker"):
        task_stores.discard(tid)


def test_attack_hashline_forged_tag_refused(tmp_path, monkeypatch):
    """A random 4-hex tag that was never minted must be refused.

    The adversary guesses a plausible tag and edits a line the task DID read.
    Because the tag is not in the task's snapshot store, the edit fails closed
    with the read-first contract and writes nothing.
    """
    f = _write(tmp_path, "forged.py", [f"line {i}" for i in range(1, 6)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    _read(f, "task-a")  # a real snapshot exists; the forged tag is not it

    out = _edit(f, "A1B2", "PUT 2.=2:\n+FORGED\n", task_id="task-a")

    assert "error" in out, out
    assert READ_FIRST in out["error"], out
    assert f.read_text(encoding="utf-8").splitlines()[1] == "line 2"


def test_attack_hashline_cross_task_tag_refused(tmp_path, monkeypatch):
    """Task B may not use a tag minted by task A's read.

    An attacker (or a sibling subagent) obtains a valid header from another
    task and replays it.  Snapshots are task-scoped, so task B has no
    observation and the edit is refused.
    """
    f = _write(tmp_path, "cross.py", [f"line {i}" for i in range(1, 6)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    _, header = _read(f, "task-a")
    tag = _tag_of(header)

    out = _edit(f, tag, "PUT 2.=2:\n+STOLEN\n", task_id="task-b")

    assert "error" in out, out
    assert READ_FIRST in out["error"], out
    assert f.read_text(encoding="utf-8").splitlines()[1] == "line 2"

    from tools.hashline.snapshots import task_stores

    assert task_stores.for_task("task-b").get(str(f)) is None


def test_attack_hashline_replay_after_successful_edit_refused(tmp_path, monkeypatch):
    """Replaying a tag after a successful edit must be refused until a re-read.

    After an edit the store head carries the *fresh* tag but an empty
    ``visible_ranges`` -- the edit must never widen what the task observed.
    So both the original (now stale) tag AND the fresh head tag are refused
    for a further edit, until the task re-reads.
    """
    f = _write(tmp_path, "replay.py", [f"line {i}" for i in range(1, 6)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    _, header = _read(f, "task-a")
    original_tag = _tag_of(header)

    first = _edit(f, original_tag, "PUT 2.=2:\n+FIRST\n", task_id="task-a")
    assert first.get("ok") is True, first

    from tools.hashline.snapshots import task_stores

    head = task_stores.for_task("task-a").get(str(f))
    assert head is not None and head.visible_ranges == ()
    assert head.tag != original_tag

    # Replay of the original tag -> stale, refused.
    replayed = _edit(f, original_tag, "PUT 2.=2:\n+SECOND\n", task_id="task-a")
    assert "error" in replayed, replayed

    # Replay with the fresh head tag -> authorizes no line, refused.
    fresh = _edit(f, head.tag, "PUT 2.=2:\n+THIRD\n", task_id="task-a")
    assert "error" in fresh, fresh
    assert NOT_SEEN in fresh["error"], fresh

    assert f.read_text(encoding="utf-8").splitlines()[1] == "FIRST"


def test_attack_hashline_disk_drift_without_reread_is_a_documented_limitation(
    tmp_path, monkeypatch
):
    """DOCUMENTED FINDING F3 (severity: LOW) -- drift is warned, not blocked.

    The attacker rewrites the file on disk *after* the task read it and
    *before* the edit, without the task re-reading.  ``apply_sections``
    resolves the section against the in-memory snapshot
    (``tools/hashline/apply.py:360``), not the live file, so the tag still
    matches and the edit APPLIES against the observed content -- overwriting
    the attacker's change.  The drift is surfaced only as an mtime warning
    (``tools/file_tools.py:991``, "Does not block").

    Scope assessment: this does NOT let an attacker inject content -- the
    write is derived solely from content the task observed, so the attacker's
    bytes are discarded.  The impact is loss of a concurrent/legitimate
    writer's change.  A re-read makes the old tag stale and refuses (see
    ``test_hashline_visible_ranges.py::test_stale_tag_after_content_change_cannot_authorize``).
    """
    f = _write(tmp_path, "drift.py", [f"line {i}" for i in range(1, 6)])
    _install_ops(monkeypatch, _FakeFileOps(f.read_text(encoding="utf-8")))
    _, header = _read(f, "task-a")
    tag = _tag_of(header)

    # Attacker writes the file on disk, then forces a distinct mtime.
    f.write_text(
        "\n".join(["line 1", "ATTACK", "line 3", "line 4", "line 5"]) + "\n",
        encoding="utf-8",
    )
    future = time.time() + 5
    os.utime(f, (future, future))

    out = _edit(f, tag, "PUT 2.=2:\n+MODEL\n", task_id="task-a")

    assert out.get("ok") is True, (
        "DOCUMENTED FINDING F3: disk drift between read and edit is not blocked"
    )
    assert "was modified since you last read" in (out.get("_warning") or ""), out
    # The edit was built from the OBSERVED snapshot: attacker bytes are gone.
    assert f.read_text(encoding="utf-8").splitlines()[1] == "MODEL"


# ===========================================================================
# APPROVAL / CANCEL BINDING
# ===========================================================================
#
# ``tools/approval.py`` binds no per-command digest: recognition returns a
# *pattern description* as the key (line 561), and authorization is a
# membership test of that key in the session/permanent set (line 1253).  The
# two cases below pin the real guarantee (different class -> refused) and the
# real gap (same class -> cross-authorized).


_CMD_A = "rm -rf /tmp/a-dangerous"
_CMD_B = "rm -rf /home/important"      # same pattern class as A
_CMD_OTHER = "chmod -R 777 /"          # a different pattern class


def test_attack_approval_swapped_command_different_pattern_refused():
    """Approving one pattern class must not authorize a different class.

    The attacker gets ``rm -rf ...`` approved for the session, then swaps in a
    command from a different class (``chmod -R 777 /``).  The different
    pattern key is not in the approved set, so it is NOT authorized.
    """
    scope = "agent-session-approval"
    is_dangerous, key_a, _ = approval.detect_dangerous_command(_CMD_A)
    is_other, key_other, _ = approval.detect_dangerous_command(_CMD_OTHER)
    assert is_dangerous and is_other
    assert key_a != key_other

    approval.approve_session(scope, key_a)

    assert approval.is_approved(scope, key_a) is True
    assert approval.is_approved(scope, key_other) is False

    approval.clear_session(scope)


def test_attack_approval_swapped_command_same_pattern_is_a_documented_limitation():
    """DOCUMENTED FINDING F1 (severity: LOW / by design) -- no per-command digest.

    The attacker gets ``rm -rf /tmp/a-dangerous`` approved for the session
    (the user chose "session"/"always" after reading the description), then
    swaps in ``rm -rf /home/important`` -- a different command entirely.  Both
    map to the same pattern key ``'delete in root path'``
    (``tools/approval.py:561``), so ``is_approved`` returns True for the
    swapped command and it runs with NO new prompt (``tools/approval.py:1253``).
    There is no command digest binding the approval to the bytes the user saw.

    Scope assessment: the approval UI shows the *class* description the user
    accepts, so this is pattern-scoped consent, not a bypass of the prompt.
    The hardline floor still blocks catastrophic commands unconditionally
    (see the next case).  Severity LOW: broad but user-visible authorization.
    """
    scope = "agent-session-approval"
    _, key_a, desc_a = approval.detect_dangerous_command(_CMD_A)
    _, key_b, desc_b = approval.detect_dangerous_command(_CMD_B)
    assert key_a == key_b == "delete in root path", (key_a, key_b)
    assert desc_a == desc_b

    approval.approve_session(scope, key_a)

    assert approval.is_approved(scope, key_b) is True, (
        "DOCUMENTED FINDING F1: a same-pattern swapped command is authorized"
    )

    approval.clear_session(scope)


def test_attack_approval_approved_pattern_cannot_unlock_hardline_command():
    """A session approval must not unlock the unconditional hardline floor.

    The attacker permanently allowlists the ``format filesystem`` pattern and
    then issues ``mkfs.ext4``.  Hardline detection runs before the allowlist
    check, so the command is denied regardless of approval state.
    """
    command = "mkfs.ext4 /dev/sda1"
    _, pattern_key, _ = approval.detect_dangerous_command(command)
    approval.approve_session(approval.get_current_session_key(), pattern_key)
    approval.approve_permanent(pattern_key)

    result = approval.check_dangerous_command(command, "local")

    assert result["approved"] is False, result

    approval.clear_session(approval.get_current_session_key())
    approval._permanent_approved.discard(pattern_key)


# ===========================================================================
# CANCELLATION IN THE LOOP -- a cancelled check never yields a passed state
# ===========================================================================


def test_attack_cancelled_check_in_loop_never_passes(make_agent):
    """A partial pass plus a cancellation must not finalize as verified.

    The contract requires two checks; the host runs ``unit`` to success and
    ``lint`` is cancelled.  A naive "any clean receipt => done" reading would
    finalize verified; the loop must instead report ``blocked`` and never
    ``passed``.  (Single-check cancellation is covered by
    ``test_completion_contract_wiring.py::test_cancelled_check_blocks_without_repairs``;
    this is the stronger partial-pass + cancel vector.)
    """
    session = ScriptedSession()
    session.text("done")
    agent = make_agent(session)

    def execute(argv, cwd):
        if argv == ("pytest",):
            return {"exit_code": 0}
        return {"cancelled": True}

    wiring_attach_contract(
        agent,
        execute,
        checks=(("unit", ("pytest",)), ("lint", ("ruff",))),
    )
    result = agent.run_conversation("finish the task")

    assert result["verification_state"] == "blocked"
    assert result["verification_state"] != "passed"
    assert result["failed_checks"] == ["lint"]
