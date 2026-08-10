"""Tests for hashline stale-tag recovery and no-op loop guard (Task 17).

Covers snapshot-chain recovery of stale section tags (unique-safe remap only,
fail closed with guidance otherwise), the NoopGuard escalation ladder (soft
warning twice, hard error on the third identical byte-identical payload, reset
on any successful change), and the apply_sections integration wiring.
"""

import pytest

from tools.hashline import parse
from tools.hashline.apply import ApplyError, apply_sections
from tools.hashline.guard import NoopGuard
from tools.hashline.snapshots import SnapshotStore, compute_tag


def make_store(path, content, ranges):
    store = SnapshotStore()
    store.record(path, content, ranges=ranges)
    return store


# ---------------------------------------------------------------------------
# stale-tag recovery
# ---------------------------------------------------------------------------


def test_stale_tag_recovers_when_range_unchanged():
    # Model read v1; the file drifted (import sys prepended) and the store
    # head is v2. The anchored range 3..4 is unchanged in the drift, just
    # shifted +1 — recovery remaps and applies against the head.
    store = make_store(
        "f.py", "import os\n\ndef main():\n    pass\n", [(1, 4)]
    )
    tag1 = store.get("f.py").tag
    store.record(
        "f.py",
        "import sys\nimport os\n\ndef main():\n    pass\n",
        ranges=[(1, 5)],
    )
    tag2 = store.get("f.py").tag
    assert tag1 != tag2

    res = apply_sections(
        parse(f"[f.py#{tag1}]\nPUT 3.=4:\n+def main():\n+    return 42\n"),
        store,
    )
    assert res.error is None
    (fr,) = res.results
    assert fr.preview == "import sys\nimport os\n\ndef main():\n    return 42\n"
    assert store.get("f.py").content == fr.preview.encode("utf-8")
    assert fr.tag == store.get("f.py").tag  # fresh tag recorded
    assert fr.tag != tag1
    assert fr.tag == compute_tag(fr.preview)
    assert any("recover" in w.lower() for w in res.warnings)


def test_stale_tag_target_changed_raises_guidance():
    # The targeted line (2) changed in the drift: no unchanged-run mapping
    # exists, so recovery must fail closed with re-read guidance.
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    tag1 = store.get("f.py").tag
    store.record("f.py", "a\nX\nc\n", ranges=[(1, 3)])

    with pytest.raises(ApplyError, match="re-read|recover|stale|mismatch"):
        apply_sections(parse(f"[f.py#{tag1}]\nPUT 2.=2:\n+Y\n"), store)


def test_stale_tag_ambiguous_context_raises_guidance():
    # "beta" survived the drift but its context duplicated above it, so the
    # anchor's unique interpretation is no longer provable — fail closed.
    store = make_store("f.py", "alpha\nbeta\n", [(1, 2)])
    tag1 = store.get("f.py").tag
    store.record("f.py", "alpha\ngamma\nalpha\nbeta\n", ranges=[(1, 4)])

    with pytest.raises(ApplyError, match="re-read|recover|stale|unique"):
        apply_sections(parse(f"[f.py#{tag1}]\nPUT 2.=2:\n+BETA2\n"), store)


def test_fresh_tag_not_stale_skips_recovery():
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    tag = store.get("f.py").tag
    res = apply_sections(parse(f"[f.py#{tag}]\nPUT 2.=2:\n+B\n"), store)
    assert res.error is None
    assert res.results[0].preview == "a\nB\nc\n"
    assert not any("recover" in w.lower() for w in res.warnings)


# ---------------------------------------------------------------------------
# NoopGuard
# ---------------------------------------------------------------------------


def test_noop_guard_escalates_then_resets():
    guard = NoopGuard()
    assert guard.record("f.py", "payload-a") == (1, False)
    assert guard.record("f.py", "payload-a") == (2, False)
    assert "no-op detected (repeated 2x)" in guard.warning("f.py", 2)
    assert guard.record("f.py", "payload-a") == (3, True)
    assert "repeated 3x" in guard.hard_error("f.py", 3)

    # A successful change resets the counter.
    guard.reset("f.py")
    assert guard.record("f.py", "payload-a") == (1, False)


def test_noop_guard_different_payload_resets():
    # A different payload is model progress (omp: hash change earns a fresh
    # soft hint), so the counter restarts at 1.
    guard = NoopGuard()
    assert guard.record("f.py", "aaa") == (1, False)
    assert guard.record("f.py", "aaa") == (2, False)
    assert guard.record("f.py", "bbb") == (1, False)


def test_noop_guard_is_per_path():
    guard = NoopGuard()
    assert guard.record("a.py", "p") == (1, False)
    assert guard.record("a.py", "p") == (2, False)
    assert guard.record("b.py", "p") == (1, False)  # separate counter


# ---------------------------------------------------------------------------
# apply_sections integration
# ---------------------------------------------------------------------------


def test_apply_sections_noop_returns_guard_warning_then_hard_error():
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    guard = NoopGuard()
    tag = store.get("f.py").tag
    noop_patch = f"[f.py#{tag}]\nPUT 1.=3:\n+a\n+b\n+c\n"  # byte-identical

    # 1st no-op: soft warning, no error, nothing written.
    res1 = apply_sections(parse(noop_patch), store, guard=guard)
    assert res1.error is None
    assert any("no-op" in w for w in res1.warnings)
    assert res1.results == []

    # 2nd identical no-op: repeated-count warning.
    res2 = apply_sections(parse(noop_patch), store, guard=guard)
    assert res2.error is None
    assert any("no-op detected (repeated 2x)" in w for w in res2.warnings)

    # 3rd identical no-op: hard error.
    with pytest.raises(ApplyError, match="repeated 3x"):
        apply_sections(parse(noop_patch), store, guard=guard)


def test_apply_sections_successful_change_resets_guard():
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    guard = NoopGuard()

    tag = store.get("f.py").tag
    res = apply_sections(
        parse(f"[f.py#{tag}]\nPUT 1.=3:\n+x\n+y\n+z\n"), store, guard=guard
    )
    assert res.error is None  # real change

    # Same payload again is now a no-op, but the successful change reset the
    # guard: warning (count 1), not an escalation.
    tag = store.get("f.py").tag
    noop_patch = f"[f.py#{tag}]\nPUT 1.=3:\n+x\n+y\n+z\n"
    res = apply_sections(parse(noop_patch), store, guard=guard)
    assert res.error is None
    assert any("no-op" in w for w in res.warnings)
    assert not any("repeated" in w for w in res.warnings)


def test_apply_sections_without_guard_still_rejects_noop():
    # Legacy behavior preserved: without a guard, the first byte-identical
    # no-op is an ApplyError (existing engine contract).
    store = make_store("f.py", "a\nb\nc\n", [(1, 3)])
    tag = store.get("f.py").tag
    with pytest.raises(ApplyError, match="no-op"):
        apply_sections(
            parse(f"[f.py#{tag}]\nPUT 1.=3:\n+a\n+b\n+c\n"), store
        )


# ---------------------------------------------------------------------------
# regressions from code-quality review (safety class: wrong remap)
# ---------------------------------------------------------------------------


def test_recovery_line1_anchor_remaps_correctly():
    # C1: anchor starts at line 1 (no above-context); drift prepends lines.
    # The mapped line must be matches[0] + 1 (unconditional).
    store = make_store("f.py", "p\nq\n", [(1, 2)])
    tag1 = store.get("f.py").tag
    store.record("f.py", "x0\nx1\np\nq\n", ranges=[(1, 4)])
    tag2 = store.get("f.py").tag
    assert tag1 != tag2

    res = apply_sections(
        parse(f"[f.py#{tag1}]\nPUT 1.=2:\n+P\n+Q\n"),
        store,
    )
    assert res.error is None
    (fr,) = res.results
    assert fr.preview == "x0\nx1\nP\nQ\n"


def test_recovery_out_of_range_stale_tag_fails_closed():
    # C2: model wrote a range past the OLD snapshot's EOF; with a stale tag
    # the malformed range must be rejected, never silently truncated/remapped.
    store = make_store("f.py", "a\nb\nc\nd\ne\n", [(1, 5)])
    tag1 = store.get("f.py").tag
    store.record("f.py", "a\nb\nc\nd\ne\nx\ny\nz\n", ranges=[(1, 8)])

    with pytest.raises(ApplyError, match="out of range|re-read"):
        apply_sections(
            parse(f"[f.py#{tag1}]\nPUT 4.=6:\n+Z\n+Y\n+Z\n"),
            store,
        )


def test_guard_not_advanced_when_patch_fails_validation():
    # M1: a no-op section followed by an invalid section must NOT advance
    # the guard counter (the patch never applies).
    store = make_store("a.py", "x\ny\n", [(1, 2)])
    store.record("b.py", "u\nv\n", [(1, 2)])
    guard = NoopGuard()
    ta = store.get("a.py").tag
    tb = store.get("b.py").tag
    patch = (
        f"[a.py#{ta}]\nPUT 1.=2:\n+x\n+y\n"   # byte-identical no-op
        f"[b.py#{tb}]\nPUT 5.=5:\n+oops\n"    # out of range -> fails
    )
    with pytest.raises(ApplyError):
        apply_sections(parse(patch), store, guard=guard)
    assert guard.count("a.py") == 0  # never recorded
