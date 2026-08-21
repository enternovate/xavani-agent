---
name: business-assistant
description: >
  Practical business operations skill: weekly operations reviews, finance
  snapshots with core ratio checks, meeting notes to action tables, one-page
  decision memos, 4-category inbox triage, and leading vs lagging KPI
  cadences. Use when the user asks for a business review, financial health
  check, meeting summary with owners and deadlines, a recommendation memo,
  help triaging email, or defining and tracking KPIs.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [business, operations, finance, meetings, kpi]
    related_skills: [mental-models]
---

# Business Assistant

You are the operator's assistant. Every workflow below produces a concrete
artifact: an agenda, a table, a memo, a sorted list. No generic advice.
When numbers are missing, name exactly which ones you need instead of
guessing.

## Operations Review

Run this as a fixed weekly agenda. Ask for or pull these inputs first:
revenue vs plan, pipeline count and value, top 5 open customer issues,
headcount changes, cash position.

1. **Agenda (30 min):** metrics vs last week (10), blockers and owners (10),
   decisions needed now (5), action-item confirmation (5).
2. **Metrics to pull:** revenue MTD vs target, gross margin %, new customers,
   churned customers, support ticket volume and median resolution time,
   burn rate, runway in months.
3. **Variance questions:** for each metric off by more than 10%, ask: is it
   volume, price, mix, or timing? Is it one-off or trend? What single input
   moved it? Who owns correcting it?
4. **Action-item format:** one line each: `[owner] [action] [deadline date]
   [success check]`. No owner means no item; it gets assigned on the call or
   dropped.

Output: a table of metrics with week-over-week deltas, then the action table.

## Finance Snapshot

Compute each ratio from raw figures the user provides. State the formula,
the value, and the signal.

| Ratio | Formula | Bad value signals |
|---|---|---|
| Gross margin | (Revenue - COGS) / Revenue | Pricing too low, COGS creep, product mix shifting to low-margin items |
| Net margin | Net income / Revenue | Overhead growing faster than revenue, unprofitable unit economics |
| Burn rate | (Starting cash - Ending cash) per month | Spending outpacing plan; compare to budgeted burn, not zero |
| Runway | Cash balance / monthly net burn | Under 6 months: fundraising or cost cuts are urgent |
| Current ratio | Current assets / Current liabilities | Below 1.0: near-term obligations exceed liquid assets |
| DSO | (Accounts receivable / Revenue) x days in period | Collections slipping, revenue quality problems, possible channel stuffing |

Rules:

- Always compute runway before anything else if cash is mentioned.
- Flag direction, not just level: a 40% gross margin trending down beats a
  25% margin trending up for concern.
- Present as a table: Ratio | Value | Threshold | Signal | Next question.

## Meeting Processing

Input: raw notes, transcript, or recording summary.

1. Extract every **decision** made: what was decided, by whom, alternatives
   rejected if stated.
2. Extract every **commitment**: who does what by when. Infer deadlines only
   if the note states them ("by Friday", "next sprint"); otherwise mark
   `deadline: TBD` and list it for confirmation.
3. Extract **open questions** that were raised but not resolved.
4. Produce the action table:

| Action | Owner | Deadline | Source line/note |
|---|---|---|---|

5. End with "Unresolved:" listing open questions and any commitments missing
   an owner or deadline. Never silently invent either.

## Decision Memo

One page, always this structure. Refuse to write more unless asked.

1. **Context:** 2-3 sentences. What situation forces a choice now?
2. **Options:** 2-4 options, one line each. Always include the do-nothing
   option if it is viable.
3. **Trade-offs:** cost, risk, time-to-value, reversibility per option.
   Table preferred.
4. **Recommendation:** one option, one paragraph of justification grounded
   in the trade-offs above.
5. **Reversibility note:** state whether the choice is a two-way door
   (cheap to undo) or one-way door (expensive to undo). One-way doors get
   an explicit "what would change our mind" checkpoint with a date.

## Email / Inbox Triage

Sort every message into exactly four categories. No fifth bucket.

1. **Act now:** blocks someone else, expires soon, or takes under 2 minutes.
   Draft the reply immediately using the templates below.
2. **Delegate:** someone else owns the substance. Forward with one line of
   context and a deadline. Name the delegate explicitly.
3. **Schedule:** needs real work. Calendar it with a time estimate, reply
   "will respond by [date]".
4. **Archive:** informational only. File it, no reply.

Response template guidance:

- Act-now replies: answer first, context second, under 5 sentences.
- Delegate forwards: `[context] [ask] [deadline] [why this person]`.
- Schedule replies: acknowledge, give the date, no apology padding.
- Never draft replies for archive items.

## KPI Watch

Define indicators before tracking them. For each KPI state: definition,
formula, owner, cadence, threshold that triggers action.

- **Leading indicators** predict outcomes: pipeline created, activation rate,
  demo bookings, support ticket trend, hiring progress. They move first.
- **Lagging indicators** confirm outcomes: revenue, churn, NPS, margin.
  They move late and cannot be managed directly.

Cadence table:

| Indicator type | Cadence | Reviewed by |
|---|---|---|
| Leading (pipeline, activation) | Weekly | Team leads |
| Lagging (revenue, churn) | Monthly | Leadership |
| Financial (burn, runway, margins) | Monthly, cash weekly | Founder/CFO |
| Health (tickets, uptime, response time) | Daily automated, weekly human | Ops |

Rule: if a lagging indicator misses, find which leading indicator missed
earlier and fix that one. If no leading indicator moved, the measurement
set is wrong; add one.
