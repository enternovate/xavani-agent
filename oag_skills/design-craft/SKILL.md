---
name: design-craft
description: "Design at a high level — layout, type, colour, hierarchy, motion, accessibility — in the user's learned taste, never generic."
version: 1.0.0
platforms: [linux, macos, windows]
metadata:
  xavani:
    tags: [design, ui, web, poster, deck, brand, typography, layout, creative]
    related_skills: []
---

# Design Craft: High-Level Visual Design

Use this whenever you create something visual — a website, landing page, app UI,
poster, ad creative, slide deck, or brand system. It distils the craft so output
is **excellent and distinctive**, in the user's learned taste — **never generic**.

The deterministic helpers live in `xavani_learner` (no token cost):
- `design.design_brief(brief, medium)` → the learned style direction + principles
  for the medium. Read it first; design *in that direction*.
- `design_review.design_review(spec)` → critique your own design before shipping.
- `style_profile` / `taste` → which exemplary direction fits this brief.

## The craft (apply every time)

1. **Hierarchy & focal point** — one clear primary idea/action per view. Guide the
   eye with size, weight, colour, and position. Not a wall of equal blocks.
2. **Typography** — a confident type scale (3–5 steps); one display + one text
   family; comfortable measure (60–75ch); real hierarchy. Big where it matters.
3. **Colour** — restrained palette (1–2 brand + neutrals) with one accent. Always
   meet **WCAG AA** contrast (≥4.5:1 body text).
4. **Space & rhythm** — a consistent spacing system (8pt). Whitespace is
   structure, not leftover. Group related, separate unrelated (proximity).
5. **Composition** — balance, alignment, repetition; intentional asymmetry beats
   safe centring.
6. **Motion** — purposeful (reveals, micro-interactions, feedback); never
   decoration; respect reduced-motion.
7. **Accessibility** — contrast, focus states, semantic structure, ≥44px targets,
   alt text.

## Per medium
- **web / landing** — strong above-the-fold focal point, generous whitespace, one
  primary CTA, purposeful scroll motion.
- **poster / ad** — ONE focal point, oversized display type, high figure/ground
  contrast, dramatic negative space; legible at a glance.
- **deck** — one idea per slide, one visual per slide, no bullet walls.
- **ui** — consistent tokens, obvious primary action, semantic states, data legible.
- **brand** — a coherent, ownable, consistent system.

## Process
1. Get the **direction**: `design_brief(brief, medium)` (learned taste + principles).
2. Design **originally** in that direction — do not copy any reference.
3. **Review**: run `design_review` (or self-check the craft list). Fix low-craft.
4. **Avoid the generic**: no default-framework looks, hero+3-cards clichés, stock
   photos, lorem ipsum, clashing fonts, low-contrast gray, tiny type.

The goal: distinctive, considered, accessible work that looks like *the user's*
taste — at the level of the best examples they've taught the agent.
