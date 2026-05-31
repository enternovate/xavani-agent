---
name: hickey-guidelines
description: Rich Hickey's principles for software design — simplicity over ease, values over references, data over objects, and the discipline of making things actually simple.
domain: software-design
mandatory: true
priority: 87
version: 1.0
sources:
  - "Simple Made Easy (Strange Loop, 2011)"
  - "The Value of Values (JaxConf, 2012)"
  - "Are We There Yet? (JVM Languages Summit, 2009)"
  - "Rich Hickey — Clojure Design (clojure.org)"
---

# Rich Hickey — Operating Guidelines

> "Simple is not easy. Easy is something you already know how to do. Simple is something that is not intertwined."

## Core Principles (always-on)

1. **Simplicity is objective, ease is subjective.** Simple means one fold, one braid, one concern. Easy means familiar, close at hand. Do not confuse the two — choosing easy over simple creates complexity debt.

2. **Values over references.** A value is a thing that does not change. A reference is a thing that might change behind your back. Prefer immutable data, pure functions, and explicit state transitions over mutable objects.

3. **Data over objects.** Data is open, generic, and inspectable. Objects are closed, specific, and opaque. Represent information as data; add behaviour on top. Do not hide data behind getters and setters.

4. **Complecting is the root of evil.** When two concerns are tangled together (complected), you cannot reason about, test, or change one without touching the other. Separate concerns. Make each thing do one thing.

5. **Design is about making decisions, not deferring them.** Every "we'll make this configurable later" is a decision to increase complexity now for a hypothetical future that may never arrive. Make the decision. Ship the result. Change it later if needed.

6. **Process values, not state.** Given an input value, produce an output value. This is testable, composable, and debuggable. "Update the object's internal state and hope" is none of these.

## Heuristics for the agent

- Before adding a flag or configuration option, **ask: can I just pick the right value now?**
- If a function has side effects, **name them explicitly** and make them the exception, not the rule.
- When choosing a data structure, **prefer maps/vectors over custom classes** — they are inspectable and composable.
- If two things are always used together, **ask whether they are actually one thing** — then make them one, or prove they are separate.
- When you hear "we need this to be flexible," **ask: flexible for what?** If no concrete use case exists, it is not flexibility — it is complexity.

## Anti-patterns to reject

- "It's object-oriented" — if the objects hide data and complect concerns, OO is a liability.
- "We'll make it configurable" — configuration is complexity. Pick a default and ship.
- "It's easier this way" — easy for whom? Easy now often means hard later.
- "The framework handles it" — the framework is a dependency, not an excuse to stop thinking.

## When to invoke

- Designing a new system, module, or API.
- When you feel a design is "getting complicated" — stop and ask what is being complected.
- When someone proposes adding a configuration option, flag, or extension point.
