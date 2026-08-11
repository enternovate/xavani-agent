# Memory Recall Precision Benchmark

> Harness: `scripts/memory_benchmark/runner.py` — measures how precisely
> `MemoryManager.search()` (`xavani_memory/manager.py`) recalls seeded
> facts from a throwaway SQLite store, across exact-term, partial-term,
> and unrelated query variants. Backlog item E124.

## Run

```bash
# Results table + exit 0 (no API key, no network, CI-safe)
python3 scripts/memory_benchmark/runner.py

# Fewer facts, or a different search limit k
python3 scripts/memory_benchmark/runner.py --facts 10 --limit 5

# Benchmark the FTS5 backend instead of the default substring scan
XAVANI_MEMORY_FTS5=1 python3 scripts/memory_benchmark/runner.py

# Thresholds enforced as tests:
python3 -m pytest tests/test_memory_benchmark.py -q
```

## Methodology

### 1. Seed a fresh store with facts

The harness generates N distinct fact sentences (default 20), each
carrying exactly one unique term (e.g. `Fact 1: the kangaroo population
survey finished on day 1 with 200 sightings.`). Terms are drawn from a
fixed list of 20 distinct words, so no fact is a substring of another
and a query can only ever match its own target fact. The store lives in
a fresh temp directory (`MemoryManager(memory_dir=..., auto_maintenance=
False)`), and `XAVANI_HOME` is repointed to that temp root for the
duration so the B02 fact extractor's summary file cannot touch the real
`~/.xavani`. Every seeded fact also carries a unique day number and
sighting count.

### 2. Query variants

For each seeded fact, two queries are issued against the real
`MemoryManager.search(query, limit)` API:

| variant | query | expectation |
|---|---|---|
| exact | the full unique term (`kangaroo`) | the seeded fact is the hit |
| partial | the first 4 characters of the term (`kanga`) | prefix probe — backend-dependent |
| unrelated | a term present in no fact (`giraffe`, `harbour`) | zero hits |

The partial variant deliberately queries the API as a user would — no
trailing `*` wildcard is added. Under the default **substring** backend
this matches the seeded fact; under **FTS5** it returns no hits (FTS5
matches whole tokens, not prefixes), which is itself a useful
measurement of what the API contract delivers.

### 3. Score per query

For each query, with k = the search limit (default 10):

- **hits** — number of entries returned,
- **relevant** — entries whose `user_input` contains the target term
  (the unique term only ever appears in the target fact),
- **precision@k** — relevant / hits (0.0 when no hits are returned),
- **recall@k** — 1.0 iff the target fact appears in the top-k results.

Aggregates are reported per variant (mean precision over queries,
micro-averaged precision over hits) plus an overall row. The runner
prints the per-query and aggregate tables and exits 0; pass thresholds
live in `tests/test_memory_benchmark.py`, not in the exit code.

## Determinism

The default backend is the substring scan (`XAVANI_MEMORY_FTS5` unset),
which is deterministic on any sqlite build. The test assertions hold
under both backends — an exact-term query always retrieves its seeded
fact and an unrelated query always returns no hits — so the suite does
not depend on whether the local sqlite was compiled with FTS5.

## Baseline results — 2026-08-11 (substring backend, deterministic)

| variant | queries | hits | relevant | precision@k | recall@k |
|---|---|---|---|---|---|
| exact | 20 | 20 | 20 | 1.000 | 1.000 |
| partial | 20 | 20 | 20 | 1.000 | 1.000 |
| unrelated | 2 | 0 | 0 | 0.000 | 0.000 |
| overall | 42 | 40 | 40 | 1.000 | 1.000 |
