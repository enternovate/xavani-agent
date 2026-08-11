# Compaction Quality Eval

> Harness: `scripts/compaction_eval/runner.py` — measures how many seeded
> facts survive the real `ContextCompressor.compress()` path
> (`agent/context_compressor.py`), using deterministic LLM-free scoring.
> Backlog item E120.

## Run

```bash
# Score table + exit 0 (no API key, no network, CI-safe)
python3 scripts/compaction_eval/runner.py

# Thresholds enforced as tests:
python3 -m pytest tests/test_compaction_eval.py -q
```

## Methodology

### 1. Seed a session with facts

The harness generates N distinct fact sentences (default 25), each with
unique values (shipment id, crate count, item id, city, day), and builds
a synthetic session: a system prompt, one user + assistant exchange per
fact, and a final wrap-up user message. Facts are unique and
non-overlapping so the scorer cannot false-positive across them.

### 2. Run the REAL compaction path

`run_compaction()` constructs a real `ContextCompressor` (default
parameters, `faux-model` context window resolved from the local model
metadata table — no network) and calls `compress(messages)` — the actual
production method: tool-result pruning, head/tail protection, window
boundary alignment, `shake()`, serialization, structured summarizer
prompt construction, redaction, summary merge, and tool-pair
sanitization.

Only the summarizer LLM call itself is scripted, at the
`agent.context_compressor.call_llm` seam — the compression analogue of
the faux-provider harness (`tests/harness/faux_provider.py` patches the
`run_agent.OpenAI` transport seam). The scripted summarizer is a pure,
deterministic function of the prompt the real pipeline built: it finds
each seeded fact phrase in that prompt and decides what to reproduce.
The eval therefore measures **pipeline fidelity** (did window selection
and serialization actually deliver the facts to the summarizer?) — not
model capability, which would be nondeterministic.

### 3. Score the compacted summary

The summary is located in the compressed message list via the
`SUMMARY_PREFIX` handoff marker (standalone message or merged-into-tail
forms are both handled; the trailing END-OF-SUMMARY marker is dropped).
Retention is scored with **normalized LLM-free substring matching**:

1. lowercase the text,
2. collapse every whitespace run to a single space,
3. strip punctuation at the edges (`.` `,` `;` `:` `!` `?` `(` `)` `[`
   `]` `{` `}` quotes and backticks),
4. a fact is retained iff its normalized phrase is a substring of the
   normalized summary.

The matcher is deliberately tolerant of re-wrapping ("- Shipment q-1000
..." matches) but strict enough that a summary omitting a fact scores it
missing.

### 4. Two scripted summarizers guard each other

| summarizer | behavior | expected retention |
|---|---|---|
| faithful | reproduces **every** seeded fact found in the prompt | >= 80% (the `RETENTION_PASS` threshold) |
| degraded | reproduces the first **quarter** of found facts | strictly lower than faithful, below the threshold |

The degraded control exists to catch a broken scorer: if matching were
broken in the permissive direction (everything "retained"), degraded
would not score strictly lower; if broken in the strict direction,
faithful would not reach 80%.

## Baseline results — 2026-08-11 (deterministic, no LLM)

| case     | retained | total | retention | facts reaching summarizer |
|----------|----------|-------|-----------|---------------------------|
| faithful | 23       | 25    | 92.0%     | 23                        |
| degraded | 5        | 25    | 20.0%     | 23                        |
| verdict  | PASS     |       |           |                           |

Two facts sit outside the summarizer window by design: the protected
head (system + `protect_first_n` exchanges) and the protected tail (last
3 messages, incl. the final user turn) are never summarized — that is
the compressor's intended behavior, and the eval treats it as part of
what compaction preserves.

## Interpretation

- Faithful retention measures how much of the middle window the real
  pipeline exposes to the summarizer and how faithfully it is carried
  into the handoff summary.
- The eval is deterministic and hermetic: same inputs, same scores, on
  any machine — it is a regression guard for the compaction pipeline,
  not a model benchmark.
- The `seen` column (facts that reached the summarizer prompt) separates
  pipeline loss (window/serialization) from summarizer loss (facts seen
  but omitted).

## Notes

- The runner always exits 0 once the eval ran (the table prints a
  PASS/FAIL verdict); pass thresholds are enforced by
  `tests/test_compaction_eval.py`.
- `--facts N` changes the seed count (default 25). Tests require >= 20
  seeded facts so the 80% threshold has headroom against head/tail
  protection.
- Python stdlib only — no new dependencies.
- No file I/O: nothing to clean up, safe to run in CI.
