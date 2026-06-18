# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Tests for the email/day planner engine (tools/email_planner.py).

The engine is provider-agnostic and PURE — it operates on plain message
dicts (the shape google_api.py's `gmail search` returns) and never touches
the network or sends anything. Triage, action extraction, reply scaffolding
and the unified day plan are all deterministic given a fixed `now`.
"""

from datetime import datetime

import pytest

from tools import email_planner as ep


# A fixed "now": Thursday 2026-06-18.
NOW = datetime(2026, 6, 18, 9, 0, 0)
ME = "mushwanageorge66@gmail.com"


def _msg(**over):
    base = {
        "id": "x", "threadId": "t", "from": "Alice Boss <alice@company.com>",
        "to": ME, "subject": "Hello", "date": "Thu, 18 Jun 2026 08:00:00 +0000",
        "snippet": "Just saying hi.", "labels": ["INBOX", "UNREAD"],
    }
    base.update(over)
    return base


# ---------------------------------------------------------------------------
# triage_message — categorization
# ---------------------------------------------------------------------------

def test_triage_action_required():
    m = _msg(subject="Need the Q4 report by tomorrow",
             snippet="Can you send it? It's urgent.")
    t = ep.triage_message(m, me=ME, now=NOW)
    assert t.category == "Action Required"
    assert t.priority >= 50


def test_triage_newsletter():
    m = _msg(subject="50% off this week!",
             snippet="Unsubscribe at any time.",
             labels=["INBOX", "CATEGORY_PROMOTIONS"])
    m["from"] = "Acme Deals <noreply@acme.com>"
    t = ep.triage_message(m, me=ME, now=NOW)
    assert t.category == "Newsletter"
    assert t.priority < 30


def test_triage_receipt():
    m = _msg(subject="Your order #12345 — Receipt",
             snippet="Thanks for your payment of R450.")
    m["from"] = "orders@shop.com"
    t = ep.triage_message(m, me=ME, now=NOW)
    assert t.category == "Receipt"


def test_triage_social():
    m = _msg(subject="You have 3 new connections",
             labels=["INBOX", "CATEGORY_SOCIAL"])
    m["from"] = "LinkedIn <notifications@linkedin.com>"
    t = ep.triage_message(m, me=ME, now=NOW)
    assert t.category == "Social"


def test_triage_fyi_when_direct_but_no_ask():
    m = _msg(subject="Notes from today", snippet="Sharing the notes for reference.")
    t = ep.triage_message(m, me=ME, now=NOW)
    assert t.category == "FYI"


def test_triage_awaiting_reply_for_sent():
    m = _msg(subject="Following up", labels=["SENT"], to="bob@company.com")
    m["from"] = ME
    t = ep.triage_message(m, me=ME, now=NOW)
    assert t.category == "Awaiting Reply"


# ---------------------------------------------------------------------------
# triage (batch) — sorting by priority
# ---------------------------------------------------------------------------

def test_triage_sorts_action_above_newsletter():
    urgent = _msg(id="1", subject="URGENT: approve the invoice today",
                  snippet="Please approve by EOD.")
    news = _msg(id="2", subject="Weekly digest", snippet="unsubscribe",
                labels=["INBOX", "CATEGORY_PROMOTIONS"])
    news["from"] = "noreply@news.com"
    ranked = ep.triage([news, urgent], me=ME, now=NOW)
    assert [t.id for t in ranked][0] == "1"     # urgent first
    assert ranked[0].priority > ranked[1].priority


# ---------------------------------------------------------------------------
# detect_asks
# ---------------------------------------------------------------------------

def test_detect_asks_pulls_questions_and_requests():
    text = "Can you send the report? The weather is nice. Please review the deck."
    asks = ep.detect_asks(text)
    assert any("report" in a.lower() for a in asks)
    assert any("review" in a.lower() for a in asks)
    assert all("weather" not in a.lower() for a in asks)   # filler dropped


# ---------------------------------------------------------------------------
# _parse_due — date understanding
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("text,expected", [
    ("please reply today", "2026-06-18"),
    ("need it by tomorrow", "2026-06-19"),
    ("due 2026-07-01 latest", "2026-07-01"),
    ("can you finish by Friday?", "2026-06-19"),   # next Friday from Thu 18th
    ("send by June 20", "2026-06-20"),
])
def test_parse_due(text, expected):
    assert ep._parse_due(text, NOW) == expected


def test_parse_due_none_when_absent():
    assert ep._parse_due("no dates here at all", NOW) is None


# ---------------------------------------------------------------------------
# extract_action_items
# ---------------------------------------------------------------------------

def test_extract_action_items_with_due():
    m = _msg(id="42", subject="Send the Q4 report",
             snippet="Can you send the Q4 report by tomorrow?")
    items = ep.extract_action_items([m], me=ME, now=NOW)
    assert len(items) == 1
    item = items[0]
    assert item.email_id == "42"
    assert item.due == "2026-06-19"
    assert "report" in item.title.lower() or "report" in item.subject.lower()


def test_extract_skips_newsletters():
    m = _msg(subject="Weekly digest", snippet="unsubscribe",
             labels=["INBOX", "CATEGORY_PROMOTIONS"])
    m["from"] = "noreply@news.com"
    assert ep.extract_action_items([m], me=ME, now=NOW) == []


# ---------------------------------------------------------------------------
# reply_scaffold — draft skeleton, never sends
# ---------------------------------------------------------------------------

def test_reply_scaffold_greets_sender_by_first_name():
    m = _msg(subject="Quick question", snippet="Could you confirm the date?")
    draft = ep.reply_scaffold(m, me_name="George")
    assert isinstance(draft, str) and draft
    assert "Alice" in draft          # sender's first name in the greeting
    assert "George" in draft         # sign-off


# ---------------------------------------------------------------------------
# build_day_plan — unified, ordered, rendered
# ---------------------------------------------------------------------------

def test_build_day_plan_orders_and_renders():
    actions = [
        ep.ActionItem(title="Reply to Alice: report", due="2026-06-18",
                      email_id="1", subject="report", sender="Alice", priority=80),
        ep.ActionItem(title="Reply to Bob: contract", due="2026-06-25",
                      email_id="2", subject="contract", sender="Bob", priority=60),
    ]
    todos = [{"id": "a", "content": "Call accountant", "status": "pending"}]
    events = [{"summary": "Team standup", "start": "2026-06-18T10:00:00Z",
               "end": "2026-06-18T10:30:00Z"}]
    plan = ep.build_day_plan(action_items=actions, todos=todos,
                             events=events, files_pending=5, now=NOW)

    # soonest-due action ranks first
    assert plan.priorities[0]["title"].startswith("Reply to Alice")
    text = plan.render()
    assert "Team standup" in text
    assert "5" in text                       # files-pending count surfaced
    assert "Call accountant" in text


def test_build_day_plan_empty_is_safe():
    plan = ep.build_day_plan(now=NOW)
    assert isinstance(plan.render(), str)


# ---------------------------------------------------------------------------
# the engine must expose NO send capability (read + draft only)
# ---------------------------------------------------------------------------

def test_engine_has_no_send_function():
    for forbidden in ("send_email", "send_reply", "send", "delete_email"):
        assert not hasattr(ep, forbidden), f"engine must not expose {forbidden}()"
