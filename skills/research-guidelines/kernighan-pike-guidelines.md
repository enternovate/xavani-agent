---
name: kernighan-pike-guidelines
description: Kernighan and Pike's principles for programming craft — clarity over cleverness, simplicity in design, the Unix philosophy, and the discipline of writing programs that other people can read.
domain: software-craft
mandatory: true
priority: 85
version: 1.0
sources:
  - "The Practice of Programming (Addison-Wesley, 1999)"
  - "The Unix Programming Environment (Prentice Hall, 1984)"
  - "Software Tools (Addison-Wesley, 1976)"
  - "Brian Kernighan — several talks on programming style"
---

# Kernighan & Pike — Operating Guidelines

> "Controlling complexity is the essence of computer programming."

## Core Principles (always-on)

1. **Clarity beats cleverness.** Write code that is obvious. If you have to explain it, rewrite it. Clever code is hard to debug, hard to modify, and hard to hand off. The best code reads like prose.

2. **Do one thing well.** A program should do one thing, do it well, and compose with other programs. If a function does two things, split it. If a module does three things, decompose it.

3. **Interfaces should be narrow and deep.** A good interface has few functions, but each one does a lot. Wide, shallow interfaces are confusing — too many entry points, too little power.

4. **Test with real data, not synthetic.** Synthetic data tests your assumptions. Real data tests your program. Use real inputs whenever possible; if you must generate test data, make it look like production.

5. **Simplicity of implementation is a feature.** The simplest correct implementation is the best one. Complexity is a cost — in maintenance, in debugging, in onboarding. Pay it only when the problem demands it.

6. **Document the why, not the what.** The code tells you what it does. Comments should tell you why it does it. If the "why" is obvious, do not add a comment. If it is not, the comment prevents the next person from introducing a bug.

## Heuristics for the agent

- Before writing a comment explaining code, **ask: can I rewrite the code to not need the comment?**
- If a function has more than 3 parameters, **consider whether a data structure would be clearer**.
- When choosing between two designs, **pick the one that is easier to explain in a sentence**.
- If you are writing boilerplate, **ask whether a tool or script could generate it** — and whether the tool is worth the maintenance cost.
- When debugging, **read the error message carefully** — it usually tells you exactly what is wrong.

## Anti-patterns to reject

- "It's more efficient this way" — show the measurement. If you cannot, clarity wins.
- "The comment explains it" — if the code needs a comment, the code might need rewriting.
- "We need this for generality" — generality is a cost. Is there a concrete use case?
- "It's a one-off" — one-offs become permanent. Write it clean the first time.

## When to invoke

- Writing any new code or module.
- Designing an API or interface.
- When you catch yourself writing a clever trick instead of clear code.
