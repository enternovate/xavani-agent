---
name: ai-native-ui
description: >
  AI-native UI skill: a catalog of agent-chat interface primitives from
  beautifului.dev (Loading State, Thinking, Streaming Text, Approval Card,
  Tool Chips, Task Rows, Chat, Prompt Bar, Recommendation Card, Context
  Cards, tables, and more) with transcript composition rules, trust and
  safety requirements for state-mutating agent actions, Xavani surface
  mappings, and dark-mode-first design token guidance. Use when building
  or reviewing any agent chat surface, TUI web view, or dashboard that
  renders AI agent activity.
version: 1.0.0
author: Xavani Agent
license: MIT
metadata:
  xavani:
    tags: [ui, chat, streaming, approvals, human-in-the-loop, design-tokens]
    related_skills: [personal-assistant]
---

# AI-Native UI

You are designing or reviewing an interface that renders AI agent
activity. The reference catalog is beautifului.dev — "Beautiful UI:
Crafted primitives for AI-native interfaces" by Turbo. Every primitive
below is a concrete component with defined states; your job is to pick
the right ones, stack them in the right order, and never let the agent
act on the world without an Approval Card.

## 1. When to Load This Skill

Load when doing any of:

1. Building or modifying an agent chat surface, TUI web view, or
   dashboard that shows agent activity (tool calls, reasoning, tasks).
2. Reviewing an existing agent UI for missing states — hidden failures,
   unconfirmed mutations, unexplained tool calls.
3. Wiring a new agent capability into a surface and deciding how its
   progress, results, and confirmation gate should render.

Skip for static marketing pages, forms, or non-agent dashboards.

## 2. Primitive Catalog

Each entry: what it is, when to use it, key state/props.

### Transcript primitives

| Primitive | Use when | Key state / props |
|---|---|---|
| Loading State | Work started but nothing to show yet | pixel-grid loader or shimmer, elapsed time; variants: Drive Dots, Orbit Surfer |
| Thinking | Model is reasoning and the user may want detail | expandable trace container; children: Thinking Steps, Reasoning, Search, Coding |
| Streaming Text | Answer tokens are arriving | streamed text, inline sources, per-message actions, follow-up suggestions |
| Tool Chips | Tool calls or code edits happened | compact chip per call: tool name, args summary, status; click to expand result |
| Task Rows | Multi-step work runs as trackable tasks | label, status `running\|failed\|completed`, progress detail, count |
| Context Cards | Retrieved knowledge grounds the answer | chunk excerpt, source title + link, relevance order |

### Input primitives

| Primitive | Use when | Key state / props |
|---|---|---|
| Chat | A persistent conversation panel is the surface | tabbed threads, reasoning replies, composer |
| Prompt Bar | The user composes requests | text input, @ sources, / commands, model picker, dictation; variant: Rounded Pill |
| Selection Actions | Bulk operations on listed items | selection set, action bar with enabled/disabled actions |

### Decision and output primitives

| Primitive | Use when | Key state / props |
|---|---|---|
| Approval Card | The agent proposes an action that mutates state | question, options list, selected option, on-accept callback |
| Recommendation Card | The agent suggests a next step | suggestion body, confidence meter, actions |
| Diff Table | Code or document changes need review | before/after rows, line-level add/remove markers |
| Records Table | Structured results come back from tools | columns, rows, sort, empty state |
| Filter Table | Many records need narrowing | filter inputs, live row count |
| Flowchart | A plan or workflow needs visual structure | nodes, edges, current-step highlight |
| Insight Cards | Aggregate findings deserve emphasis | headline metric, supporting detail, drill-down |
| Code Block | Code is shown or copied | language tag, copy button, optional filename |
| Fine-tune Card | Training/fine-tune jobs are surfaced | job config, status, metrics |
| Sidebar Nav | Many surfaces or threads need structure | sections, active item, collapse state |
| Search | The user must find past content | query input, scoped results, highlight |

## 3. Composition Rules

A transcript is a stack, not a free-for-all. Order within one turn:

1. **Loading State** first — from request until first meaningful signal.
2. **Thinking** replaces it once reasoning starts; keep collapsed by
   default, expandable on click. Nest Thinking Steps, Reasoning, Search,
   and Coding inside it as they occur.
3. **Tool Chips** appear as each tool call fires — before its results
   stream. One chip per call, in call order.
4. **Context Cards** attach directly beneath the answer they grounded,
   above any actions; never float them at the top of the thread detached
   from their answer.
5. **Streaming Text** renders the answer as tokens arrive, with inline
   sources linked to the Context Cards below.
6. Close the turn with per-message **actions** and follow-up suggestions.

Placement rules:

- **Approval Card interrupts**: it pauses the stream at the point of the
  proposed action. Nothing after the mutation executes until accept.
  Resume the transcript below it on acceptance.
- **Task Rows** replace a chain of >3 Tool Chips: collapse the chips into
  one task row with live progress detail and a count.
- **Recommendation Card** goes after the answer, never mid-stream.
- **Diff Table** follows the Tool Chip that produced the edit, before any
  Approval Card that asks to keep or revert it.
- **Records/Filter Tables** replace raw JSON dumps of tool output.
- **Flowchart** only for plans with branching or parallel steps; linear
  plans stay as Task Rows.

## 4. Trust and Safety Rules

Non-negotiable. A review that violates any of these fails.

1. Any agent action that mutates state — writes files, sends messages,
   spends money, deletes data, calls external services — REQUIRES an
   Approval Card with explicit options before execution. No silent
   mutations, no auto-accept timers.
2. Every tool call renders as a Tool Chip BEFORE its results stream.
   The user must always see what the agent is about to do or just did.
3. Task Rows expose failure states. A failed task shows `failed` status
   with its error detail — never silently converts to completed, never
   hides the row. Failure visibility outranks visual tidiness.
4. Reasoning traces (Thinking) are inspectable: collapsible, not
   absent. An answer without an inspectable trail loses trust.
5. Context Cards carry real sources. Unattributed retrieved knowledge
   is a defect; every card links its origin.
6. Approval Card options are exhaustive and reversible where possible:
   include an explicit reject path, and prefer "apply / edit / discard"
   over bare yes/no for destructive actions.
7. Confidence meters on Recommendation Cards reflect actual evaluation
   scores, not decoration. If no score exists, omit the meter.

## 5. Xavani Surface Mapping

Map primitives to Xavani's surfaces as follows:

- **TUI chat panel** → Chat + Streaming Text + Thinking. Reasoning
  replies render collapsed by default in the narrow panel; inline
  sources degrade to bracketed references when width is tight.
- **Prompt bar** → Prompt Bar with @ sources mapped to Xavani context
  providers (files, skills, sessions) and / commands mapped to the
  slash-command registry. Rounded Pill variant for the compact footer
  composer.
- **Kanban / delegation views** → Task Rows. Each delegated subagent
  task is one row: label = task title, status running|failed|completed,
  progress detail = current step or error, count = active task total.
  Failed delegation rows stay visible with retry actions.
- **Compression and tool loops** → Thinking traces. Context-compression
  events and multi-step tool loops render as expandable Thinking Steps
  so users can audit what was summarized away or which tools ran.
- **Skill installs and gateway operations** → Approval Card before any
  install/config mutation; Tool Chips for each step of the operation;
  Insight Cards for post-install summaries.
- **Code review flows** → Diff Table inside the chat panel, gated by an
  Approval Card for apply/revert.
- **Dark-blue skin** → all primitives inherit the skin's design tokens
  (section 6); no hardcoded colors in primitive implementations.

## 6. Design Tokens Guidance

- **Dark-mode-first**: design every primitive against a dark background
  first; light theme is the port, not the source. Never assume white.
- **High-contrast text**: body text meets WCAG AA on the dark surface;
  muted text stays legible (no gray-on-gray below 4.5:1 for body).
- **Monospace for code and diffs**: Code Blocks, Diff Tables, tool args,
  and log lines use the monospace family; prose uses the sans family.
  Never mix them within one block.
- **Compact row density**: Task Rows, Records Tables, and Filter Tables
  use tight vertical rhythm (~32px rows) so long transcripts fit; pad up
  only for Approval Cards and Recommendation Cards, which are decision
  points and deserve emphasis.
- **Status color semantics are fixed**: running = accent blue, failed =
  red, completed = green, pending approval = amber. Reuse across all
  primitives; do not introduce per-component palettes.
- **Motion is informative only**: shimmer and loaders communicate
  elapsed effort; no decorative animation on static content.

## 7. Review Checklist

When reviewing an agent UI, verify in order:

1. Every mutating action passes through an Approval Card.
2. Tool calls visible as chips before results.
3. Failures rendered, not swallowed.
4. Transcript order matches section 3.
5. Sources attributed on Context Cards and Streaming Text.
6. Dark-mode-first tokens applied; monospace/code separation intact.
