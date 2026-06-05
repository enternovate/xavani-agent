# Xavani Learning & Taste Layer

Xavani **learns you** — your design taste, your preferences, how you like things —
*once*, then defaults to it so you don't have to re-explain. It stays creative; it
just knows the direction, and it actively avoids generic, template-y looks.

## What it learns

| Kind | How | Where |
|---|---|---|
| **Design taste** | curated `StyleProfile`s distilled from exemplary sites (inspiration-attributed, never copied) + anything you teach it | `style_profile.py` + `~/.xavani/learner/style_library/*.yaml` |
| **Preferences** | stated prefs + liked references, explicit or passively captured | `preferences.py` → operator state |
| **Communication style** | tone, humor, depth, favorite builds (passive) | `user_profile.py` (Phase 7) |

The seed library ships with directions distilled from the references you gave —
clarity/precision, immersive motion, fintech density, playful brand, editorial,
type specimen, scroll narrative, brutalist/experimental — **plus `claude-craft`**,
distilled from Claude's pptx / canvas / frontend design principles (clarity,
hierarchy, restraint, accessible contrast).

## Teach it (on demand)

```bash
xavani learn url https://lusion.co        # distil a design direction from a site
xavani learn file ./brand/guide.md         # learn from a local reference
xavani learn pref "I prefer dark, editorial layouts with big type"
xavani learn list                          # what it knows
xavani learn show clarity-precision        # a direction's details
```

`learn` distils **principles** and **attributes** the source — it never copies
markup or assets. Learned once, a profile is saved as YAML and reused forever.

## How it defaults to your taste

When the agent builds something, it calls `taste.taste_context(brief)`:
1. `select_styles` deterministically picks the best-matching direction for the brief
   (zero LLM — R10);
2. it injects that direction + your preferences + the **anti-generic guardrail**
   (`anti_generic.flag_generic`) into the generation prompt;
3. the agent designs **originally** in that direction.

So: **learn once → apply deterministically → original output in your style.** The
model is only ever used to *generate* (and, optionally, to distil a richer profile
when you teach it) — never to choose, rank, or guard. The build workstream (M4)
wires `taste_context` into website generation.

## Design principle

Profiles are *direction*, not handcuffs. They encode the craft of exceptional
design (and what to avoid) so the agent's defaults are excellent — then it adapts
to **you** as it learns more.

---
Built by [Enternovate](https://enternovate.com) — Open source. Private. Local.
