# autoresearch — engineering/security

## Goal
Maximize `pass_rate` on security-relevant code paths in `xavani_cli/tools_config.py`. This file manages tool configuration, credential handling, and platform-specific tool gating — all security-sensitive domains.

Higher pass_rate is better. Target: 1.0000 (all security tests must pass).

## Research-Backed Strategies
- **Principle of Least Privilege** (Saltzer & Schroeder, 1975): Tool configuration should not expose more than necessary. Ensure configurable toolset boundaries are tight.
- **Defense in depth**: Add validation layers — type checks, boundary checks, and fallback defaults before data reaches production paths.
- **Input sanitization** (OWASP): Config paths and platform names should be validated early. Prevent injection through config keys.
- **Fail-safe defaults** (Saltzer & Schroeder, 1975): Default configurations should deny access until explicitly granted. Verify `_DEFAULT_OFF_TOOLSETS` and `_TOOLSET_PLATFORM_RESTRICTIONS` are comprehensive.
- **Complete mediation** (Saltzer & Schroeder, 1975): Every access check should be verified, not cached or assumed.

## What the Agent Can Change
- Only `xavani_cli/tools_config.py` — the single file being optimized.
- Add validation, boundary checks, sanitization.
- Improve error messages and exception handling.
- Refactor for clarity without changing behavior.

## What the Agent Cannot Change
- `evaluate.py` — the evaluator is read-only ground truth.
- Dependencies — do not add new packages.
- Any other files in the project.
- The security model itself / authentication mechanisms — the evaluator tests must still pass.

## Strategy
1. First run: establish baseline. Do not change anything.
2. Audit — scan for missing validation, unchecked inputs, overly permissive defaults.
3. Try the most impactful security improvement first.
4. If that works, push further in the same direction.
5. If stuck, try orthogonal: error handling, logging, defensive null checks.
6. Read the git log of previous experiments. Don't repeat failed approaches.

## Simplicity Rule
A small security improvement that adds complexity is still worth it — this is security.
But prefer minimal, auditable changes. A one-line validation is better than a framework.

## Stop When
You don't stop. The human will interrupt you when they're satisfied.
If no improvement in 20+ consecutive runs, change strategy drastically.
