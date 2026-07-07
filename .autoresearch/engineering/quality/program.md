# autoresearch — engineering/quality

## Goal
Maximize `pass_rate` (test suite pass rate) across the xavani-agent codebase. Target file: `toolsets.py` — the central tool definition registry (871 lines).

Higher pass_rate is better Target: 1.0000 (100% green).

## Research-Backed Strategies
- **Cyclomatic complexity reduction** (McCabe, 1976): Extract over-complex tool definitions into smaller, testable helper functions. Each toolset definition should be a simple data structure, not a computation.
- **Single Responsibility Principle** (Martin, 2003): Each toolset should have one clear purpose. If a toolset mixes concerns, split it.
- **Duplicate elimination** (Fowler, 1999): Repeated tool names across toolsets increase maintenance surface area. Extract common patterns.
- **Consistent naming** (Clean Code, Martin 2008): Tool names should follow uniform conventions so they're predictable.

## What the Agent Can Change
- Only `toolsets.py` — the single file being optimized.
- Reorder, rename, restructure toolset definitions.
- Add/remove tool entries when they're truly redundant or missing.

## What the Agent Cannot Change
- `evaluate.py` — the evaluator is read-only ground truth.
- Dependencies — do not add new packages.
- Any other files in the project.

## Strategy
1. First run: establish baseline. Do not change anything.
2. Profile — count lines per toolset, identify the largest definitions.
3. Try low-hanging fruit first: duplicate entries, inconsistent naming.
4. If that works, push further: extract shared subsets, simplify includes.
5. If stuck, try orthogonal: reformat for readability, add comments.
6. Read the git log of previous experiments. Don't repeat failed approaches.

## Simplicity Rule
A small improvement that adds ugly complexity is NOT worth it.
Equal performance with simpler code IS worth it.
Removing code that gets same results is the best outcome.

## Stop When
You don't stop. The human will interrupt you when they're satisfied.
If no improvement in 20+ consecutive runs, change strategy drastically.
