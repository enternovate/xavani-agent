<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Spec for major ① — the Quantum Decision Cortex. -->

# ① Quantum Decision Cortex — `xavani_operator/quantum/`

## Purpose

The operator's `decide.py` currently ranks opportunities and picks the top one. The Cortex replaces
that single choice with a **quantum-inspired** procedure: hold the top-K strategies in
**superposition**, **simulate** each one's outcomes, let correlated risks **interfere**, then
**collapse** to a measured decision. It is the user's "compare the pattern brought forth by outcomes
of decisions" — every decision's branches and its realised outcome are recorded and compared.

Everything is **deterministic and zero-LLM (R10)**. Real quantum hardware is an *optional accelerator*
for the combinatorial sub-problem, gated by credentials exactly like model-provider keys.

## Core data structures (`state.py`)

```python
@dataclass(frozen=True)
class Branch:
    id: str                      # opportunity / strategy id (stable, for tie-break)
    opportunity: Opportunity     # reuse xavani_operator.types.Opportunity
    amplitude: float             # real, >= 0; |amplitude|^2 is the (pre-norm) probability weight
    expected_value: float        # filled by simulate
    risk: float                  # filled by simulate (downfall-weighted)

@dataclass(frozen=True)
class Superposition:
    branches: tuple[Branch, ...]
    seed: int                    # deterministic RNG seed (default: hash of perception snapshot)
```

## Algorithm (each step a pure function)

1. **`state.superpose(opportunities, k, seed) -> Superposition`** — take top-K opportunities; seed
   initial amplitudes from their existing scores (sqrt of normalised score). Deterministic.
2. **`simulate.rollout(branch, ctx, n, seed) -> Outcome`** — seeded Monte-Carlo (stdlib `random`
   with the branch seed): sample n outcome scenarios, each scored by `wisdom.consequence.project`
   (major ②). Returns mean `expected_value` and `risk` (tail/variance). No model calls.
3. **`interference.matrix(branches) -> list[list[float]]`** — pairwise correlation from shared
   signals/risks. Strategies that share a failure mode **reinforce** that risk (constructive on the
   risk axis → amplitudes damped); genuine hedges **cancel** risk (destructive → amplitudes boosted).
4. **`collapse.measure(superposition, interference) -> Decision`** — Born-rule weighting:
   `p_i ∝ |amplitude_i|^2 · f(expected_value_i, risk_i, interference)`. Returns the ranked branches
   and the chosen one. **Deterministic measurement** (argmax with alphabetical id tie-break — no RNG
   in the final pick), so the same inputs always collapse to the same decision.
5. **`outcome_patterns.record(decision, realized_outcome)`** — persist branches + the realised result
   to the operator state store; `compare()` surfaces which branch-archetypes pay off over time and
   returns weight deltas for `learn.py`.

## QUBO / real-quantum path (`qubo.py` + `backends/`)

Some operator decisions are combinatorial — *which subset of today's tasks, under a time/energy
budget, maximises value?* `qubo.build(items, budget, value, conflict) -> QUBO` formulates it; a
backend solves it:

- **`backends/inspired.py`** — classical simulated annealing, **default, always-on**, stdlib + numpy.
- **`backends/{qiskit_aer,ibm_quantum,braket,dwave}.py`** — optional, **lazy-imported**, each guarded
  so a missing SDK never breaks import.
- **`backends/select_backend() -> Backend`** — mirrors provider auto-detect: returns the best backend
  whose SDK **and** credentials are present (`IBM_QUANTUM_TOKEN`, `AWS_*`, `DWAVE_API_TOKEN`), else
  `inspired`. The result is identical in shape regardless of backend, so callers are backend-agnostic.

## Wiring

- `decide.py`: behind `config.quantum.enabled` (default true), after the existing ranking, call the
  Cortex to re-rank + record the waveform to `state.py`. The returned `Intent` is unchanged in type,
  so `propose.py` and everything downstream are untouched.
- `learn.py`: consume `outcome_patterns.compare()` deltas alongside the existing weight updates.
- CLI (`xavani_operator/cli.py`): `xavani operator quantum [--last] [--explain]` prints the last
  decision's superposition, interference, and collapse as a readable table.

## Tests (`tests/operator/quantum/`)

- `test_collapse_deterministic` — same Superposition+interference → identical Decision, twice.
- `test_no_llm` — monkeypatch the model chokepoint to raise; run superpose→simulate→interfere→collapse;
  assert it never trips.
- `test_backend_fallback` — no creds → `select_backend()` is `inspired`; faked creds env + stubbed SDK
  → correct backend name; missing SDK still imports.
- `test_qubo_small` — a tiny knapsack-style instance solved by `inspired` matches the brute-force optimum.
- `test_outcome_patterns_roundtrip` — record + reload + compare returns stable deltas.

## Definition of done

`python3 -c "import xavani_operator.quantum"` · the five tests green · `xavani operator quantum
--explain` renders · zero new heavy deps required to run (quantum extra optional) · R8 header on every
new file · no `nous`/`hermes`.
