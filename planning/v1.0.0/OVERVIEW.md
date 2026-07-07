<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Spec for the v1.0.0 "Quantum Sentience" program.
     Pairs with the other files in planning/v1.0.0/. Authored by the curator agent after the
     2026-06-11 vision brief. Keep untracked unless the user commits. The USER controls all pushes. -->

# Xavani v1.0.0 — "QUANTUM SENTIENCE"

> **Vision (user, 2026-06-11):** four out-of-this-world major updates — quantum-inspired
> decision-making, a consequence-conscious "soul" that learns from how the great rose *and*
> fell, a 24/7 personal advisor that routes every task to the best available model and runs an
> 8pm error-log ritual, and a fully-redesigned Enternovate dashboard. *"The only thing I do is
> give you a vision and you make it happen."* The agent is curator, designer, and PM.

## The four majors (at a glance)

| # | Name | Package | One line |
|---|---|---|---|
| ① | **Quantum Decision Cortex** | `xavani_operator/quantum/` | Holds candidate strategies in **superposition**, simulates outcomes, lets risks **interfere**, **collapses** to the best — deterministic, with an optional real-QPU accelerator. |
| ② | **The Oracle** | `xavani_wisdom/` | A conscience: a corpus of **ascent & downfall** patterns (Solomon, Bezos, Buffett, Enron, WeWork…), a deterministic downfall-detector, and consequence projection. Learns from the agent's own faults. |
| ③ | **The Always-On Companion** | `xavani_operator/{daemon,advisor}/` + `model_router.py` | 24/7 daemon that's *active only when producing results*; intelligent **model routing**; daily brief + **8pm error log** + **hourly task-chase**, over Telegram. |
| ④ | **Mission Control** | `web/` + `xavani_cli/web_server.py` | The whole thing made visible: an **Enternovate deep-navy** dashboard surfacing the waveform, the wisdom verdicts, the daily counsel, and operator health. |

## How they interlock — the "sentient loop"

```
            ┌──────────────── 24/7 daemon (③) ────────────────┐
            ▼                                                  │
 Perceive → Opportunities → ② Oracle scores consequences  ──┐  │
                              │                              ▼  │
                       ① Quantum Cortex: superpose → simulate(②) → interfere → collapse
                              │                              │  │
                              ▼                              │  │
            Propose ──► [tiered approval] ──► Act ──► Verify ─┘  │
                              │                              │  │
            ③ Daily brief / 8pm error log / reminders ◄──────┘  │
                              │                                 │
            ② learns the agent's own fault-patterns ────────────┘
                              │
            ④ Mission Control renders every step in Enternovate navy
```

- **②→①**: the Oracle's `consequence.py` + downfall detector feed the Cortex's branch scoring, so
  the collapse favours decisions that avoid known failure signatures.
- **①→③**: the chosen decision + its waveform flow into the daily brief and the operator's proposals.
- **③→②**: the 8pm error log + cycle outcomes become *personalised* downfall signatures the Oracle
  watches for next time (the agent learning from its own faults).
- **everything→④**: all of it is read-only-surfaced on the dashboard.

## Version plan

`v0.6.0` (current string) → **Phase 0** finishes the v0.7.0 Operator roadmap (M7) → **v0.9.0** →
the four majors → **v1.0.0 "Quantum Sentience"**.

Build order inside v1.0.0: **② Oracle core → ① Quantum Cortex → ③ Companion → ④ Dashboard**
(each consumes the previous). Each update is one PR-sized change + its tests + its Verify;
milestones are independently releasable.

## Definition of done (global)

```
python3 -m pytest -q                                    # full suite green, no new skips
python3 -m pytest -k "no_llm or quantum or oracle or router"   # zero model calls in decision paths (R10)
python3 -c "import xavani_operator.quantum, xavani_wisdom, model_router; print('OK')"
xavani doctor                                           # passes incl. operator + model-client guards
xavani operator quantum --explain                       # prints last decision's superposition→collapse
xavani model route email                                # best AVAILABLE reasoning model, no API call
cd web && npm run build                                 # dashboard builds; Enternovate theme is default
grep -rniE '\b(nous|hermes)\b' <changed files>          # only existing LICENSE/README attribution (R1)
```

See `DESIGN.md` for architecture, `ROADMAP.md` for the numbered updates, `BRAND.md` for the
dashboard design system, and `00-PRIOR-RECONCILIATION.md` for the Phase-0 audit. The house rules
(R1–R10) carried from `planning/v0.7.0/DESIGN.md §8` are restated in `DESIGN.md §1` and are
**non-negotiable** — most importantly **R10 (deterministic-first)** and **R7 (append-only soul)**.
