# Xavani Operator

The **autonomy layer** for Xavani Agent (v0.7.0+). Plug it into a product and it
runs an approve-gated control loop: it **perceives** the product's state,
**decides** what is most worth doing, **proposes** a concrete plan, waits for you
to **approve**, then **acts** (build *and* promote), **verifies**, **reports**,
and **learns**.

> **You don't tell it what to do — it proposes, you approve.**

## Quick start

```bash
xavani operator init             # scaffold xavani.product.yaml in the current repo
$EDITOR xavani.product.yaml       # fill in goals / channels / brand
xavani operator perceive          # what the operator sees (deterministic, zero-LLM)
xavani operator decide            # how it ranks what to do (dry-run)
xavani operator propose           # turn the top opportunity into a tier-tagged plan
xavani operator proposals         # list plans awaiting your approval
xavani operator approve <id>      # approve a plan  (reject <id> to decline)
# (xavani operator cycle / run execute approved plans — arrive in M3)
```

## Approval workflow (M2)

1. **propose** runs perceive → decide → generates a concrete plan whose every step
   is tagged with an approval **tier**.
2. If the plan is all-safe (Tier 0/1) it **auto-approves**. If any step is
   outward-facing/risky (Tier ≥ 2) it lands in the queue as **pending** and you're
   notified (on your channel, once the gateway sender is wired in M3).
3. **proposals** lists what's waiting; **approve**/**reject** decide it.
4. Every enqueue/approve/reject is written to a **hash-chained audit log**
   (`xavani_operator/audit.py`) so the agent's actions are tamper-evident.

## How it works

```
Perceive → Opportunities → Decide → Propose ──► Approval Queue (tiered)
   (det)        (det)        (det)   (LLM gen)         │ you approve
                                                       ▼
                       Learn ◄─ Report ◄─ Verify ◄─ Act
```

Everything except **Propose** is pure Python and makes **zero** model calls
(R10) — so the always-on loop is cheap. The LLM is used only to *generate* plans,
code, and copy. See `planning/v0.7.0/DESIGN.md` for the full architecture.

## Tiered approval

| Tier | Examples | Behavior |
|---|---|---|
| **0 Auto** | read repo, run tests/lint, draft to staging, commit to a work branch | runs silently |
| **1 Notify** | open a *draft* PR, create an issue | runs, pings you, veto window |
| **2 Approve** | merge/deploy, post to a channel, spend, external send, delete | blocks for approval |
| **3 Block** | force-push, prod data ops, payments | per-action confirm, always |

Approve a *plan* once → Tier 0/1 steps run and listed Tier-2 steps are
pre-authorized; **Tier-3 always re-confirms**. Override any action's tier in
`approval.tier_overrides`.

## `xavani.product.yaml` reference

| Section | Field | Meaning |
|---|---|---|
| `product` | `name` *(required)* | product name |
| | `description` | one-line summary |
| | `repo` | path to the repo the operator works in (default `.`) |
| | `stack` | e.g. `[python, react, postgres]` |
| `goals[]` | `id`, `intent`, `priority` (1=highest), `success_metric` | ranked objectives |
| `channels[]` | `platform` (`x`/`discord`/`telegram`/`email`/`blog`), `handle`, `cadence` | where to promote |
| `brand` | `voice`, `tone`, `dos[]`, `donts[]`, `assets[]` | guardrails for generated content |
| `constraints` | `no_touch_paths[]`, `allowed_actions[]`, `content_policy` | hard limits |
| `budgets` | `llm_tokens_per_day`, `spend_per_day`, `max_actions_per_cycle` | ceilings (`0` = unlimited) |
| `approval` | `tier_overrides{}`, `auto_window`, `quiet_hours` | approval posture |
| `schedule` | `cycle_cadence` (cron), `watchers[]` | when it runs |

Blank/omitted sections fall back to safe defaults; only `product.name` is required.

## Module map

| Module | Role | Milestone |
|---|---|---|
| `types.py` | shared dataclasses (`Perception`, `Opportunity`, `Proposal`, …) | M0 |
| `config.py` | load + validate `xavani.product.yaml` | M0 |
| `state.py` | persistent JSON state under `~/.xavani/operator/` | M0 |
| `tiers.py` | deterministic action-class → approval-tier classifier | M0 |
| `scaffold.py` | `xavani operator init` starter generator | M0 |
| `perceive.py` | read-only signal collectors → `Perception` (+ content hash) | M1 |
| `opportunities.py` | deterministic perception → ranked opportunities | M1 |
| `decide.py` | rank → chosen `Intent` | M1 |
| `workstreams/base.py` | `Workstream` protocol + registry | M1 |
| `propose.py` | intent → tier-tagged plan (the injectable LLM seam) | M2 |
| `approval_queue.py` | proposal queue + tiered gate (auto / approve / block) | M2 |
| `audit.py` | hash-chained tamper-evident log | M2 |
| `notify.py` | render + deliver approval requests (injectable sender) | M2 |
| `cli.py` | `xavani operator` command dispatch | M0+ |

`act` / `verify` / `report` / `learn` / `loop` (executing approved plans) land in
M3 (`planning/v0.7.0/ROADMAP.md`).

---
Built by [Enternovate](https://enternovate.com) — Open source. Private. Local.
