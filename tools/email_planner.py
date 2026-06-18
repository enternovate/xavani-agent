#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Email & day planner — triage the inbox, extract action items, plan the day.

Extends the "organize everything" idea (see tools/file_organizer.py) from
files to the user's *time and attention*:

  * **triage**   — sort the inbox into Action-Required / Awaiting-Reply / FYI /
                   Newsletter / Receipt / Social, ranked by urgency.
  * **actions**  — pull to-dos and deadlines out of mail into the task list.
  * **draft**    — produce reply *drafts* for action-required mail.
  * **plan_day** — one unified plan that merges email actions + calendar +
                   tasks + the files needing tidying.

Safety: the engine is read + draft ONLY. It never sends, deletes, or modifies
mail — sending stays an explicit, user-confirmed step through the existing
google-workspace ``gmail reply`` command. The core triage/extraction/plan
functions are pure (operate on plain message dicts) so they're fully testable
and provider-agnostic; the Gmail/Calendar adapters are thin read-only wrappers
over the ``google_api.py`` CLI.
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


# ---------------------------------------------------------------------------
# Triage vocabulary
# ---------------------------------------------------------------------------
CATEGORIES = [
    "Action Required", "Awaiting Reply", "FYI",
    "Newsletter", "Receipt", "Social", "Other",
]

_NEWSLETTER_LABELS = {"CATEGORY_PROMOTIONS", "CATEGORY_UPDATES", "CATEGORY_FORUMS"}
_SOCIAL_LABELS = {"CATEGORY_SOCIAL"}
_SOCIAL_DOMAINS = ("facebook", "twitter", "x.com", "linkedin", "instagram",
                   "tiktok", "reddit", "pinterest")
_BULK_SENDER_HINTS = ("noreply", "no-reply", "do-not-reply", "donotreply",
                      "newsletter", "notifications", "mailer", "news@", "updates@")
_RECEIPT_HINTS = ("receipt", "invoice", "order #", "your order", "payment",
                  "tax invoice", "statement", "order confirmation")
_URGENT_HINTS = ("urgent", "asap", "immediately", "eod", "end of day",
                 "deadline", "today", "right away", "critical", "time-sensitive")
# Phrases that signal the sender is asking *me* to do something.
_REQUEST_PHRASES = ("can you", "could you", "would you", "please", "let me know",
                    "send me", "get back to me", "review", "confirm", "approve",
                    "sign off", "respond", "reply", "action required",
                    "follow up", "need", "kindly")
# Phrases used to pull individual asks out of a body for the reply scaffold.
_ASK_PHRASES = ("can you", "could you", "would you", "please", "let me know",
                "send me", "review", "confirm", "approve", "sign", "need", "by ")


# ---------------------------------------------------------------------------
# Sender parsing helpers
# ---------------------------------------------------------------------------

def _addr(from_field: str) -> str:
    """Extract the bare email address (lowercased) from a From header."""
    m = re.search(r"<([^>]+)>", from_field or "")
    if m:
        return m.group(1).strip().lower()
    return (from_field or "").strip().lower()


def _display_name(from_field: str) -> str:
    """Extract a human display name from a From header."""
    f = (from_field or "").strip()
    m = re.match(r'\s*"?([^"<]+?)"?\s*<', f)
    if m:
        return m.group(1).strip()
    if "@" in f and "<" not in f:
        return f.split("@")[0]
    return f


def _first_name(from_field: str) -> str:
    name = _display_name(from_field).replace(".", " ").replace("_", " ").strip()
    parts = name.split()
    return parts[0] if parts else "there"


# ---------------------------------------------------------------------------
# Date understanding
# ---------------------------------------------------------------------------
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday",
             "saturday", "sunday"]
_MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
           "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}


def _parse_due(text: str, now: datetime) -> Optional[str]:
    """Best-effort extraction of a due date from *text*, as ISO 'YYYY-MM-DD'.

    Understands explicit ISO dates, today/tomorrow/EOD, weekday names
    ("by Friday"), and month-name dates ("June 20"). Returns None when no
    date is found. Deterministic given *now*.
    """
    text_l = (text or "").lower()
    today = now.date()

    m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
    if m:
        return m.group(1)

    if "tomorrow" in text_l:
        return (today + timedelta(days=1)).isoformat()
    if "today" in text_l or re.search(r"\beod\b", text_l) or "end of day" in text_l:
        return today.isoformat()

    for i, wd in enumerate(_WEEKDAYS):
        if re.search(rf"\b{wd}\b", text_l) or re.search(rf"\b{wd[:3]}\b", text_l):
            delta = (i - today.weekday()) % 7
            if delta == 0:
                delta = 7  # "Friday" said on a Friday means next Friday
            return (today + timedelta(days=delta)).isoformat()

    def _month_date(month_abbr: str, day: int) -> Optional[str]:
        try:
            d = date(today.year, _MONTHS[month_abbr], day)
        except (ValueError, KeyError):
            return None
        if d < today:
            try:
                d = date(today.year + 1, _MONTHS[month_abbr], day)
            except ValueError:
                return None
        return d.isoformat()

    m = re.search(r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2})\b",
                  text_l)
    if m:
        return _month_date(m.group(1), int(m.group(2)))
    m = re.search(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\b",
                  text_l)
    if m:
        return _month_date(m.group(2), int(m.group(1)))
    return None


# ---------------------------------------------------------------------------
# Triage
# ---------------------------------------------------------------------------

@dataclass
class TriagedEmail:
    id: str
    sender: str
    subject: str
    category: str
    priority: int
    reasons: list[str] = field(default_factory=list)
    date: str = ""


def _score(category: str, text: str, labels: set, to: str,
           me: Optional[str], now: datetime) -> int:
    """Urgency score 0-100 from category + content signals."""
    base = {"Action Required": 35, "Awaiting Reply": 20, "FYI": 15,
            "Newsletter": 0, "Receipt": 0, "Social": 0, "Other": 5}
    score = base.get(category, 5)
    if any(u in text for u in _URGENT_HINTS):
        score += 25
    due = _parse_due(text, now)
    if due:
        try:
            days = (date.fromisoformat(due) - now.date()).days
            if days <= 1:
                score += 20
            elif days <= 3:
                score += 10
        except ValueError:
            pass
    if me and me in to:
        score += 10
    if "?" in text:
        score += 8
    if "UNREAD" in labels:
        score += 5
    if category in ("Newsletter", "Social"):
        score = min(score, 20)
    if category == "Receipt":
        score = min(score, 25)
    return max(0, min(100, score))


def triage_message(msg: dict, *, me: Optional[str] = None,
                   now: Optional[datetime] = None) -> TriagedEmail:
    """Classify one message dict into a category with a priority score."""
    now = now or datetime.now()
    me_l = (me or "").lower()
    labels = set(msg.get("labels") or [])
    frm = msg.get("from", "") or ""
    addr = _addr(frm)
    subject = msg.get("subject", "") or ""
    snippet = msg.get("snippet", "") or ""
    to = (msg.get("to", "") or "").lower()
    text = f"{subject} {snippet}".lower()
    reasons: list[str] = []

    is_from_me = bool(me_l and me_l in addr)
    if "SENT" in labels or is_from_me:
        category = "Awaiting Reply"
        reasons.append("you sent this — awaiting their reply")
    elif (labels & _SOCIAL_LABELS) or any(d in addr for d in _SOCIAL_DOMAINS):
        category = "Social"
    elif any(h in text for h in _RECEIPT_HINTS):
        category = "Receipt"
    elif (labels & _NEWSLETTER_LABELS) or any(h in addr for h in _BULK_SENDER_HINTS) \
            or "unsubscribe" in text:
        category = "Newsletter"
    else:
        direct = bool(me_l and me_l in to)
        has_ask = ("?" in text) or any(p in text for p in _REQUEST_PHRASES)
        if has_ask and (direct or not me_l):
            category = "Action Required"
            reasons.append("addressed to you with a request")
        elif direct or not me_l:
            category = "FYI"
        else:
            category = "Other"

    priority = _score(category, text, labels, to, me_l, now)
    return TriagedEmail(id=str(msg.get("id", "")), sender=frm, subject=subject,
                        category=category, priority=priority, reasons=reasons,
                        date=msg.get("date", ""))


def triage(messages: list[dict], *, me: Optional[str] = None,
           now: Optional[datetime] = None) -> list[TriagedEmail]:
    """Triage a batch, returned highest-priority first."""
    now = now or datetime.now()
    triaged = [triage_message(m, me=me, now=now) for m in messages]
    triaged.sort(key=lambda t: -t.priority)
    return triaged


# ---------------------------------------------------------------------------
# Action item extraction + reply drafting
# ---------------------------------------------------------------------------

@dataclass
class ActionItem:
    title: str
    due: Optional[str]
    email_id: str
    subject: str
    sender: str
    priority: int


def detect_asks(text: str) -> list[str]:
    """Pull the sentences that look like requests/questions out of *text*."""
    sentences = re.split(r"(?<=[.?!])\s+", (text or "").strip())
    asks: list[str] = []
    for s in sentences:
        sl = s.lower()
        if "?" in s or any(p in sl for p in _ASK_PHRASES):
            cleaned = s.strip()
            if cleaned:
                asks.append(cleaned)
    return asks


def extract_action_items(messages: list[dict], *, me: Optional[str] = None,
                         now: Optional[datetime] = None) -> list[ActionItem]:
    """Turn action-required emails into dated action items, soonest-due first."""
    now = now or datetime.now()
    items: list[ActionItem] = []
    for m in messages:
        t = triage_message(m, me=me, now=now)
        if t.category != "Action Required":
            continue
        subject = m.get("subject", "") or "(no subject)"
        sender = _display_name(m.get("from", ""))
        due = _parse_due(f"{subject} {m.get('snippet', '')}", now)
        items.append(ActionItem(
            title=f"Reply to {sender}: {subject}",
            due=due, email_id=str(m.get("id", "")), subject=subject,
            sender=sender, priority=t.priority,
        ))
    items.sort(key=lambda a: (a.due or "9999-12-31", -a.priority))
    return items


def reply_scaffold(msg: dict, *, me_name: Optional[str] = None) -> str:
    """Build a reply *draft skeleton* for a message. Never sends."""
    first = _first_name(msg.get("from", ""))
    asks = detect_asks(f"{msg.get('subject', '')} {msg.get('snippet', '')}")
    lines = [f"Hi {first},", ""]
    if asks:
        lines.append("Thanks for your email — quick responses below:")
        for a in asks:
            lines.append(f"  • [re: {a}] — ")
    else:
        lines.append("Thanks for your email. ")
    lines += ["", "Best,", me_name or ""]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Unified day plan
# ---------------------------------------------------------------------------

@dataclass
class DayPlan:
    date: str
    schedule: list = field(default_factory=list)
    priorities: list = field(default_factory=list)
    inbox_attention: dict = field(default_factory=dict)
    files_pending: int = 0
    todos: list = field(default_factory=list)

    def render(self) -> str:
        lines = [f"📅 Plan for {self.date}", ""]
        if self.schedule:
            lines.append("🗓️  Schedule:")
            for e in self.schedule:
                start = str(e.get("start", ""))
                clock = start[11:16] if len(start) >= 16 else start
                lines.append(f"   {clock}  {e.get('summary', '(busy)')}")
            lines.append("")
        lines.append("✅ Top priorities:")
        if self.priorities:
            for p in self.priorities[:10]:
                due = f"  (due {p['due']})" if p.get("due") else ""
                src = "📧" if p.get("source") == "email" else "📋"
                lines.append(f"   {src} {p['title']}{due}")
        else:
            lines.append("   (nothing pressing)")
        lines += [
            "",
            f"📥 Inbox: {self.inbox_attention.get('action_required', 0)} need action",
            f"🗂️  Files to tidy: {self.files_pending}",
        ]
        return "\n".join(lines)


def build_day_plan(*, action_items: Optional[list] = None,
                   todos: Optional[list] = None,
                   events: Optional[list] = None,
                   files_pending: int = 0,
                   now: Optional[datetime] = None) -> DayPlan:
    """Merge email actions, tasks, calendar and files into one ordered plan."""
    now = now or datetime.now()
    action_items = action_items or []
    todos = todos or []
    events = events or []

    priorities: list[dict] = []
    for a in action_items:
        priorities.append({"title": a.title, "due": a.due, "priority": a.priority,
                           "source": "email", "email_id": a.email_id})
    for t in todos:
        if t.get("status") in ("pending", "in_progress"):
            priorities.append({"title": t.get("content", ""), "due": None,
                               "priority": 50, "source": "todo", "id": t.get("id")})
    priorities.sort(key=lambda p: (p["due"] or "9999-12-31", -p["priority"]))

    schedule = sorted(events, key=lambda e: str(e.get("start", "")))
    inbox = {"action_required": len(action_items),
             "top": [a.title for a in action_items[:3]]}
    return DayPlan(date=now.date().isoformat(), schedule=schedule,
                   priorities=priorities, inbox_attention=inbox,
                   files_pending=files_pending, todos=todos)


# ---------------------------------------------------------------------------
# Read-only Gmail / Calendar adapters (via the google-workspace CLI)
# ---------------------------------------------------------------------------

def _gws_dir() -> Path:
    home = os.environ.get("XAVANI_HOME") or str(Path.home() / ".xavani")
    for base in (Path(home), Path(__file__).resolve().parents[1]):
        cand = base / "skills" / "productivity" / "google-workspace" / "scripts"
        if (cand / "google_api.py").exists():
            return cand
    return Path(__file__).resolve().parents[1] / "skills" / "productivity" / "google-workspace" / "scripts"


def _run(script: str, args: list[str]) -> tuple[bool, object]:
    """Run a google-workspace script, returning (ok, parsed_json_or_text)."""
    path = _gws_dir() / script
    if not path.exists():
        return False, f"{script} not found"
    try:
        proc = subprocess.run(
            [sys.executable, str(path), *args],
            capture_output=True, text=True, timeout=60,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        return False, str(exc)
    out = (proc.stdout or "").strip()
    try:
        return proc.returncode == 0, json.loads(out)
    except json.JSONDecodeError:
        return proc.returncode == 0, out


def gmail_auth_ok() -> bool:
    """True when google-workspace OAuth is set up."""
    ok, data = _run("setup.py", ["--check"])
    text = data if isinstance(data, str) else json.dumps(data)
    return "AUTHENTICATED" in str(text).upper() and "NOT_AUTH" not in str(text).upper()


def fetch_inbox(query: str = "in:inbox newer_than:7d", max_results: int = 25) -> list[dict]:
    ok, data = _run("google_api.py", ["gmail", "search", query, "--max", str(max_results)])
    return data if ok and isinstance(data, list) else []


def fetch_events() -> list[dict]:
    ok, data = _run("google_api.py", ["calendar", "list"])
    return data if ok and isinstance(data, list) else []


def _my_email() -> Optional[str]:
    e = os.environ.get("XAVANI_USER_EMAIL")
    if e:
        return e
    try:
        from xavani_cli.config import load_config
        cfg = load_config() or {}
        val = cfg.get("user_email")
        return val if isinstance(val, str) else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Agent tools: plan_emails + plan_day
# ---------------------------------------------------------------------------
from tools.registry import registry, tool_error, tool_result


def _not_connected_result(mode: str) -> str:
    return tool_result(
        mode=mode, connected=False,
        message=("Gmail isn't connected yet. Authorize once with the "
                 "google-workspace skill (scripts/setup.py), then retry. "
                 "Generic IMAP via the himalaya skill also works."),
    )


def plan_emails_tool(args: dict, store=None) -> str:
    """Handler for the ``plan_emails`` tool (triage / actions / draft)."""
    mode = (args.get("mode") or "triage").lower()
    query = args.get("query") or "in:inbox newer_than:7d"
    max_results = int(args.get("max") or 25)
    me = _my_email()

    if not gmail_auth_ok():
        return _not_connected_result(mode)

    messages = fetch_inbox(query, max_results)

    if mode == "triage":
        ranked = triage(messages, me=me)
        by_category: dict[str, int] = {}
        for t in ranked:
            by_category[t.category] = by_category.get(t.category, 0) + 1
        top = [{"id": t.id, "from": _display_name(t.sender), "subject": t.subject,
                "category": t.category, "priority": t.priority} for t in ranked[:15]]
        return tool_result(mode="triage", connected=True, count=len(ranked),
                           by_category=by_category, top=top,
                           note="Read-only. Use mode='actions' to turn these into "
                                "tasks, or mode='draft' for reply drafts.")

    if mode == "actions":
        items = extract_action_items(messages, me=me)
        created = 0
        if args.get("create_tasks", True) and store is not None and items:
            store.write(
                [{"id": f"email-{it.email_id}",
                  "content": it.title + (f" (due {it.due})" if it.due else ""),
                  "status": "pending"} for it in items],
                merge=True,
            )
            created = len(items)
        return tool_result(
            mode="actions", connected=True, found=len(items), tasks_created=created,
            action_items=[{"title": it.title, "due": it.due, "email_id": it.email_id,
                           "priority": it.priority} for it in items],
            note=("Added to your task list." if created
                  else "Extracted. Pass create_tasks=true to add them to your task list."),
        )

    if mode == "draft":
        me_name = args.get("me_name") or (_display_name(me) if me else None)
        by_id = {str(m.get("id", "")): m for m in messages}
        ranked = [t for t in triage(messages, me=me) if t.category == "Action Required"]
        drafts = []
        for t in ranked[:10]:
            m = by_id.get(t.id, {})
            drafts.append({"email_id": t.id, "to": _addr(t.sender),
                           "subject": "Re: " + t.subject,
                           "draft": reply_scaffold(m, me_name=me_name)})
        return tool_result(
            mode="draft", connected=True, count=len(drafts), drafts=drafts,
            note="DRAFTS ONLY — nothing was sent. Review/edit, then send with the "
                 "google-workspace 'gmail reply' command after the user confirms.",
        )

    return tool_error("Unknown mode. Use one of: triage, actions, draft.")


def plan_day_tool(args: dict, store=None) -> str:
    """Handler for the ``plan_day`` tool — the unified daily plan."""
    me = _my_email()
    connected = gmail_auth_ok()
    messages = fetch_inbox("in:inbox newer_than:7d", 25) if connected else []
    actions = extract_action_items(messages, me=me)
    events = fetch_events() if connected else []
    todos = store.read() if store is not None else []

    try:
        from tools.file_organizer import organize_folders, default_target_folders
        files_pending = len(organize_folders(default_target_folders(), dry_run=True).moved)
    except Exception:
        files_pending = 0

    plan = build_day_plan(action_items=actions, todos=todos, events=events,
                          files_pending=files_pending)
    active_todos = len([t for t in todos if t.get("status") in ("pending", "in_progress")])
    return tool_result(
        mode="plan_day", date=plan.date, connected_to_gmail=connected,
        plan=plan.render(),
        counts={"email_actions": len(actions), "events": len(events),
                "tasks": active_todos, "files_to_tidy": files_pending},
        note=("" if connected else "Gmail not connected — email & calendar omitted. "
              "Run google-workspace setup to include them."),
    )


def _check_planner_reqs() -> bool:
    """Always available — the tools self-report when Gmail isn't connected."""
    return True


PLAN_EMAILS_SCHEMA = {
    "name": "plan_emails",
    "description": (
        "Triage and plan the user's Gmail inbox (read-only + drafts; NEVER sends). "
        "Modes:\n"
        "  triage   — sort the inbox into Action-Required / Awaiting-Reply / FYI / "
        "Newsletter / Receipt / Social, ranked by urgency (default).\n"
        "  actions  — extract to-dos & deadlines from action-required mail; with "
        "create_tasks=true they're added to the session task list.\n"
        "  draft    — produce reply DRAFTS for action-required mail (you review and "
        "send manually via google-workspace 'gmail reply').\n"
        "Requires the google-workspace integration to be authorized; if it isn't, the "
        "tool says so and explains setup. Uses Gmail search syntax for 'query'."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["triage", "actions", "draft"],
                     "description": "What to do (default 'triage').", "default": "triage"},
            "query": {"type": "string",
                      "description": "Gmail search query (default 'in:inbox newer_than:7d')."},
            "max": {"type": "integer", "description": "Max messages to scan (default 25).",
                    "default": 25},
            "create_tasks": {"type": "boolean",
                             "description": "actions mode: add extracted items to the task "
                                            "list (default true).", "default": True},
        },
        "required": [],
    },
}

PLAN_DAY_SCHEMA = {
    "name": "plan_day",
    "description": (
        "Build one unified 'plan my day' that merges email action items + calendar "
        "events + the task list + files needing tidying into a single prioritized, "
        "rendered plan. Read-only. Gracefully degrades when Gmail/Calendar isn't "
        "connected (it just omits those sections). Use this when the user asks to "
        "'plan my day', 'what should I focus on', or 'organize everything'."
    ),
    "parameters": {"type": "object", "properties": {}, "required": []},
}


def _handle_plan_emails(args, **kw):
    return plan_emails_tool(args or {}, store=kw.get("store"))


def _handle_plan_day(args, **kw):
    return plan_day_tool(args or {}, store=kw.get("store"))


registry.register(name="plan_emails", toolset="todo", schema=PLAN_EMAILS_SCHEMA,
                  handler=_handle_plan_emails, check_fn=_check_planner_reqs,
                  emoji="📧", max_result_size_chars=60_000)
registry.register(name="plan_day", toolset="todo", schema=PLAN_DAY_SCHEMA,
                  handler=_handle_plan_day, check_fn=_check_planner_reqs,
                  emoji="🗓️", max_result_size_chars=40_000)


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        prog="xavani-plan",
        description="Xavani email & day planner — triage, extract tasks, plan the day.",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_tri = sub.add_parser("triage", help="triage the inbox (read-only)")
    p_tri.add_argument("--query", default="in:inbox newer_than:7d")
    p_tri.add_argument("--max", type=int, default=25)

    p_act = sub.add_parser("actions", help="extract action items from the inbox")
    p_act.add_argument("--query", default="in:inbox newer_than:7d")
    p_act.add_argument("--max", type=int, default=25)

    sub.add_parser("plan-day", help="render the unified daily plan")

    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if args.cmd == "triage":
        print(plan_emails_tool({"mode": "triage", "query": args.query, "max": args.max}))
        return 0
    if args.cmd == "actions":
        print(plan_emails_tool({"mode": "actions", "query": args.query,
                                "max": args.max, "create_tasks": False}))
        return 0
    if args.cmd == "plan-day":
        print(plan_day_tool({}))
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
