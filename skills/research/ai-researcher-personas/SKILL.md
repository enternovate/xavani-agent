---
name: ai-researcher-personas
description: Invoke AI researcher coding philosophies (Karpathy, Chollet, LeCun, Swyx, Willison, Hightower, Vaswani, Jim Fan) to guide code quality, architecture decisions, and engineering practices. Use when the task would benefit from a specific researcher's perspective on simplicity, systems design, or AI methodology.
license: MIT
---

# AI Researcher Personas

Xavani includes 8 researcher-derived personas that inject domain-expert coding philosophies into subagent sessions. These are available via the `persona` parameter in `delegate_task` or `xavani --agents <name>`.

## Available Personas

| Persona | Researcher | Core Philosophy |
|---------|-----------|----------------|
| `karpathy-researcher` | Andrej Karpathy | Think first, simplicity, surgical changes, goal-driven loops |
| `chollet-researcher` | Francois Chollet | Deep abstraction, generalization, developer experience |
| `lecun-researcher` | Yann LeCun | Self-supervised learning, hierarchical design, open science |
| `swyx-researcher` | Swyx (Shawn Wang) | AI engineering, eval-driven development, compound systems |
| `willison-researcher` | Simon Willison | Data-first, simplicity in tools, ethical AI, open source |
| `hightower-researcher` | Kelsey Hightower | Infrastructure simplicity, operability, zero-drama deployments |
| `vaswani-researcher` | Ashish Vaswani | Transformer architecture, scalable design, efficient computation |
| `jim-fan-researcher` | Jim Fan (NVIDIA) | Embodied AI, simulation-first, GPU-native agent design |

## Sources

- Karpathy principles derived from: https://github.com/multica-ai/andrej-karpathy-skills
- Chollet: Keras design philosophy, ARC challenge papers
- LeCun: Self-supervised learning publications, Meta AI blog
- Swyx: Latent.Space newsletter, AI Engineer Summit talks
- Willison: simonwillison.net blog, Datasette/Django design patterns
- Hightower: Kubernetes philosophy, KubeCon talks, "Kubernetes The Hard Way"
- Vaswani: "Attention Is All You Need" paper, scalable architecture principles
- Jim Fan: NVIDIA research on embodied agents, Eureka, Voyager projects

## Usage

```
xavani --agents karpathy-researcher
```

Or via delegation:
```python
delegate_task(
    goal="Refactor the authentication module for clarity",
    persona="karpathy-researcher",
)
```
