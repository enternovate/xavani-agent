# Sovereign Indigo — Xavani Agent Briefing Publication

A four-plate **explainer** set that describes what Xavani Agent IS — its layers, its
capabilities, its access surfaces, and the patient sequence by which it turns a
question into work. Sister publication to [`design/social-media/`](../social-media/) :
same palette, same fonts, same serial / corner / header system, so the two read as one
continuous volume.

## Plates

| File | Format | Dimensions | What it briefs |
|------|--------|------------|----------------|
| `01_anatomy.png` | Portrait | 1080 × 1350 | **The layered stack.** Six bands — Surfaces, Agent, Skills, Memory, Gateway, Providers — read top-down like a geological cross-section. The Agent band is accented with an ember spine because it's the heart of the system. |
| `02_capabilities.png` | Portrait | 1080 × 1350 | **The capability matrix.** A 4 × 6 grid of 24 capability cards. Three (Gateway, Sandbox, Offline) carry the ember accent — the differentiators. |
| `03_surfaces.png` | Square | 1080 × 1080 | **Six ways to reach it.** Terminal, Dashboard, Gateway, ACP, Platforms, Python API — radiating from a single ember-cored agent. Every surface talks to the same memory, the same skills. |
| `04_flow.png` | Portrait | 1080 × 1350 | **The patient sequence.** Seven checkpoints down a vertical spine — Arrival → Authorization → Context → Planning → Dispatch → Provider → Persistence. Planning carries the ember accent because that's where the agent earns its keep. |

## What the publication briefs people on

A reader who scans all four plates in order leaves knowing:

1. **The architecture is honest** — six discrete layers, each named and each owned by
   the operator. No black boxes. No surprise round-trips.
2. **The toolbox is bundled** — 24 capabilities ship in one install, none gated behind
   a paywall or an add-on store.
3. **The agent is reachable everywhere** — six first-class surfaces, and a seventh if
   you count importing the Python module directly.
4. **The work is reproducible** — every request walks the same seven-step pipeline,
   and every step is logged.

## Palette

| Token | Hex | Use |
|-------|-----|-----|
| `INK` | `#0C1226` | Primary text, hero forms, bold band fill |
| `INK_DEEP` | `#080C1A` | Title text |
| `INK_MID` | `#3C4660` | Secondary body text |
| `CREAM` | `#F4EBDC` | Paper |
| `CREAM_SOFT` | `#EBE0CE` | Grain noise |
| `EMBER` | `#E46D2F` | The single accent — used like saffron |
| `SILVER_DIM` | `#6E7480` | Annotations, archival labels |
| `SILVER_PALE` | `#D2C8B8` | Cell borders, hairlines |

## Fonts

All from the Anthropic Canvas Design font set (no licensing required for redistribution):

- **Gloock-Regular** — serif display titles
- **InstrumentSerif-Regular / Italic** — block titles + italic subtitles
- **Boldonse-Regular** — slab-face layer / step names
- **GeistMono-Regular / Bold** — annotations, doctrine, header system
- **IBMPlexMono-Regular** — foot doctrine lines

## Re-generating

```bash
cd design/brief
python3 render.py
```

Requires Pillow (`python3 -m pip install pillow`). No network calls; deterministic
byte-identical output across runs.
