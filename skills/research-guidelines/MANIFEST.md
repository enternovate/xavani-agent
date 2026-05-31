---
name: research-guidelines-manifest
description: Mandatory research-and-engineering principles loaded into every Xavani session in perpetuity.
mandatory: true
loading: bootstrap
version: 1.0
---

# Research Guidelines — Mandatory Loadout

These guideline packs are **always loaded** into the Xavani agent's working
context. They encode the operating principles of twenty-one thinkers whose
work has set the highest bar in their respective fields — ten modern AI
researchers and engineering practitioners, five general-purpose research
methodologists, and six software design and craftsmanship leaders.

The pack is modelled on the format pioneered by
[multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
— minimal, principle-driven, evaluation-focused. Each file is a single
self-contained doc with YAML frontmatter and bullet-point principles,
heuristics, anti-patterns, and trigger conditions.

## Loading priority

| Priority | File | Domain |
|---:|---|---|
| 100 | [karpathy-guidelines.md](karpathy-guidelines.md) | ai-engineering |
| 95  | [hamming-guidelines.md](hamming-guidelines.md)   | research-methodology |
| 95  | [knuth-guidelines.md](knuth-guidelines.md)       | software-craft |
| 95  | [popper-guidelines.md](popper-guidelines.md)     | research-methodology |
| 95  | [polya-guidelines.md](polya-guidelines.md)       | problem-solving |
| 95  | [tukey-guidelines.md](tukey-guidelines.md)       | data-analysis |
| 90  | [lecun-guidelines.md](lecun-guidelines.md)       | ai-architecture |
| 90  | [hinton-guidelines.md](hinton-guidelines.md)     | ai-research |
| 90  | [sutskever-guidelines.md](sutskever-guidelines.md) | ai-research |
| 90  | [olah-guidelines.md](olah-guidelines.md)         | ai-interpretability |
| 90  | [hassabis-guidelines.md](hassabis-guidelines.md) | ai-research |
| 90  | [chollet-guidelines.md](chollet-guidelines.md)   | ai-research |
| 90  | [weng-guidelines.md](weng-guidelines.md)         | ai-engineering |
| 90  | [huyen-guidelines.md](huyen-guidelines.md)       | ml-systems |
| 90  | [yan-guidelines.md](yan-guidelines.md)           | ai-engineering |
| 88  | [beck-guidelines.md](beck-guidelines.md)         | software-craft |
| 87  | [hickey-guidelines.md](hickey-guidelines.md)     | software-design |
| 86  | [fowler-guidelines.md](fowler-guidelines.md)     | software-craft |
| 85  | [carmack-guidelines.md](carmack-guidelines.md)   | software-craft |
| 85  | [kernighan-pike-guidelines.md](kernighan-pike-guidelines.md) | software-craft |
| 84  | [dijkstra-guidelines.md](dijkstra-guidelines.md) | software-craft |

Higher priority loads first; ties are broken alphabetically.

## How the agent uses them

1. **Bootstrap.** `xavani_cli/research_guidelines.py` reads every
   `*-guidelines.md` in this directory at startup, parses the YAML
   frontmatter, sorts by priority, and exposes them via
   `load_mandatory_guidelines()` and `compose_system_prompt_block()`.

2. **System prompt injection.** `xavani_cli/default_soul.py` prepends a
   condensed reference block — one heading per guideline plus a single
   summary line — so the agent always knows what's mandatory and where
   to look for the full text.

3. **On-demand expansion.** When the active task triggers a `When to
   invoke` condition, the agent reads the full guideline file before
   acting. The condensed block is the index; the full files are the
   long-form context.

## Adding a new guideline pack

1. Drop a new `<lastname>-guidelines.md` into this directory with valid
   frontmatter (`name, description, domain, mandatory, priority,
   version, sources`).
2. Add an entry to the table above.
3. Run `pytest tests/xavani_cli/test_research_guidelines.py` to verify
   the file is discovered and its frontmatter parses.

## Why these twenty-one

The six original AI researchers (Karpathy, LeCun, Hinton, Sutskever, Olah,
Hassabis) cover modern frontier AI from six complementary angles:
engineering pragmatism, architectural conviction, foundational
intuition, scaling philosophy, interpretability, and general-purpose
agentic systems.

The four new AI/ML practitioners (Chollet, Weng, Huyen, Yan) extend
the pack into applied AI engineering: generalisation measurement,
LLM pipeline design, production ML systems, and LLM product patterns.

The five methodologists (Hamming, Knuth, Popper, Pólya, Tukey) cover
the research traditions every engineer should keep alive:
prioritisation, software craft, falsifiability, problem decomposition,
and exploratory data analysis.

The six software design and craftsmanship leaders (Beck, Hickey,
Fowler, Carmack, Kernighan & Pike, Dijkstra) bring discipline to how
code is written: test-driven development, simplicity over ease,
refactoring rigour, performance awareness, Unix philosophy, and
mathematical correctness.

Together they form the **highest-form research and engineering toolkit**
the Xavani agent uses to reason about its own work — applied in
perpetuity, by design, not by reminder.
