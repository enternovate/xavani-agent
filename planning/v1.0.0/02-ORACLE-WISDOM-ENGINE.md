<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Spec for major ② — the Oracle wisdom engine. -->

# ② The Oracle — Consequence-Conscious Wisdom Engine — `xavani_wisdom/`

## Purpose

Give the agent a **conscience** and a memory of how the great rose **and** fell, so its advice avoids
the patterns that destroyed them. This is the user's "be conscious of consequences… study what caused
the downfall… learn from King Solomon and the best… how they rose AND how they fell… also learn from
its own faults." Built as a sibling package to `xavani_memory/` and `xavani_learner/`.

**Zero-LLM (R10)** except `research.py` (distils public playbooks) and the advice *copy* in ③'s brief.
The soul layer is **append-only (R7)** — never a `default_soul.py` rewrite.

## The corpus (`corpus/ascent/*.yaml`, `corpus/downfall/*.yaml`)

One YAML file per pattern. Schema (mirrors `xavani_learner/style_profile.py` loaders):

```yaml
id: solomon-downfall-overreach
kind: downfall                 # ascent | downfall
figure: King Solomon
domain: leadership             # leadership | finance | product | ethics | ops
era: c. 970–931 BC
what_they_did: >
  United kingdom, unrivalled wisdom and wealth; then heavy forced labour, crushing
  taxation, and foreign cults late in his reign.
the_signal:                    # the small, observable pattern to watch for
  - success funding ever-larger commitments (overextension)
  - burden shifted onto the base that made you (taxation/forced labour)
  - drifting from the principles that earned the rise
the_lesson: >
  Peak success is when overreach and principle-drift are most dangerous; the bill comes
  due later (the kingdom split under Rehoboam, after his death).
detector_pattern:              # deterministic match hints for detectors/downfall.py
  signals: [overextension, base_burden, principle_drift, succession_gap]
  keywords: [expand, scale fast, raise more, defer cost, ignore base]
sources: [Kings, Chronicles]   # attribution only; no copyrighted text stored
```

**Seed set (curate ~15–20):**
- *Ascent:* Solomon (wisdom/justice, trade alliances), Bezos (Day-1, customer obsession, long-term,
  regret-minimisation), Buffett (circle of competence, margin of safety, patience, reputation),
  plus archetypes (compounding, focus, durable moats, owner mindset).
- *Downfall:* Solomon (overreach + base-burden + principle-drift), Kodak / Nokia / Blockbuster
  (disruption denial, complacency), Lehman / LTCM (leverage + tail blindness), Enron / Theranos
  (fraud, metric theatre), WeWork (founder excess, governance), Icarus archetype (hubris).

## Modules

- **`patterns.py`** — `AscentPattern` / `DownfallPattern` dataclasses + a YAML loader + a
  deterministic `match(text|decision_ctx, patterns) -> ranked` (keyword/signal overlap; mirror the
  skill-router scoring). Pure stdlib.
- **`consequence.py`** — `project(decision_ctx) -> ConsequenceReport`: deterministic 2nd/3rd-order
  effects — reversibility (0–1), affected parties, time-horizon (now/quarter/years), tail-risk,
  base-rate flag. Produces the `expected_value`/`risk` inputs the Quantum Cortex (①) consumes.
- **`detectors/downfall.py`** — `detect(decision_ctx) -> list[Finding]`, registered in the `agent`
  detector registry. Flags matches to downfall signatures (overextension, single-point dependency,
  leverage, ignoring base rates, succession gap, ethics red flag, principle-drift). **Zero-LLM.**
- **`self_faults.py`** — `update(error_log_entries, cycle_outcomes) -> list[DownfallPattern]`: turns
  the agent's *own* recurring mistakes (from ③'s 8pm error log) into personalised downfall signatures
  the detector then watches for. This is "learn from its own faults."
- **`research.py`** — `study(goal) -> list[AscentPattern]`: gather public playbooks via existing
  `tools/web_tools.py` / exa / the `deep-research` skill; the LLM **distils** the best path
  (generate-only), stored as reusable ascent patterns. The selection/ranking afterwards is deterministic.
- **`advisor_lens.py`** — `verdict(decision_ctx) -> WisdomVerdict`: fuse consequence + downfall
  findings + best-matching ascent pattern into one object the daily brief (③) and dashboard (④) render.

## Soul (R7-safe)

Add `skills/research-guidelines/conscience.md` (frontmatter per the loader contract) encoding the
consequence-awareness + downfall-avoidance values. `xavani_cli/research_guidelines.py` already
**appends** guideline blocks to SOUL.md — register the pack there. Also ship `xavani_wisdom/wisdom.md`
(a readable digest of the corpus) the agent can consult. **No change to `default_soul.py`** beyond
what the loader appends; a test asserts the base identity block is byte-identical.

## Tests (`tests/wisdom/`)

- `test_corpus_loads` — every YAML parses into a pattern; required fields present.
- `test_downfall_detector_no_llm` — monkeypatch model chokepoint to raise; detector runs; finds the
  planted overreach signature; never trips the chokepoint.
- `test_consequence_deterministic` — same ctx → same ConsequenceReport, twice.
- `test_self_faults_learn` — feed synthetic repeated errors → a personalised pattern is emitted and
  subsequently detected.
- `test_soul_append_safe` — composing soul with the conscience pack leaves the identity block unchanged.

## Definition of done

`python3 -c "import xavani_wisdom"` · tests green · detector registered + visible to `xavani doctor`
· corpus attributes sources, stores no copyrighted text (R1/copyright-safety) · R8 headers · soul
identity intact.
