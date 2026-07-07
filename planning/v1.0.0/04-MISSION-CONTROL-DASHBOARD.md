<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Spec for major ④ — the Mission Control dashboard. -->

# ④ Mission Control — the Enternovate Dashboard — `web/` + `xavani_cli/web_server.py`

## Purpose

`xavani dashboard` serves the `web/` React/Vite app via `xavani_cli/web_server.py`. The user wants it
**audited fully, every core thing changed, all words and texts written, and rebranded to the dark blue
of Enternovate**, using one of the design examples they taught the agent. It must also **surface the
three new engines** (Quantum, Oracle, Companion) so the agent's "mind" is visible.

## Step 1 — Audit (before any redesign)

- Inventory every route/page in `web/src/` (`App.tsx`, `components/`, `pages/`, plugins) and every
  endpoint in `xavani_cli/web_server.py`. Record what works, what's broken, what's placeholder.
- **Copy completeness:** find every empty/raw/untranslated label, tooltip, empty-state, and error
  string; ensure **all words and texts are written** (the user's explicit ask). Add the strings to the
  i18n catalogue used by the existing `LanguageSwitcher`.
- **Branding scrub (R1):** remove visible "Nous" branding/wordmarks from the UI chrome. (The
  `@nous-research/ui` npm package stays as an upstream library dependency — that's allowed.)
- Accessibility baseline: WCAG AA contrast, focus states, ≥44px targets, semantic landmarks.

## Step 2 — Rebrand to Enternovate deep-navy

Apply the **`principle-dark-elegance`** profile from `xavani_learner/style_library/` (one of the
user's taught examples) + the craft in `skills/design/SKILL.md`. The current default is "Xavani Teal"
(`#041c1c`) defined as LENS_0 in `web/src/index.css`; add an **`enternovate`** theme in
`web/src/themes/` and make it the **default**, keeping the switcher and the other themes.

### Palette (curated; canonical source — see `BRAND.md`)

| token | value | role |
|---|---|---|
| `--background-base` | `#0A1730` | deep navy canvas |
| surface / elevated | `#0F2147` | panels, cards |
| border / surface-2 | `#1B305C` | dividers, outlines |
| `--foreground-base` | `#E8EEF9` | primary text (cool near-white) |
| muted | `#93A4C4` | secondary text |
| **accent (primary)** | `#4D8DFF` | electric blue — CTAs, links, focus |
| quantum glow | `#22D3EE` | cyan — the decision waveform only |
| success / warning / danger | `#34D399` / `#FBBF24` / `#F87171` | states |
| `--warm-glow` → cool-glow | `rgba(77,141,255,0.30)` | Backdrop |

- **Typography:** replace the bundled display fonts with a clean premium pair (one display + one text);
  a confident 3–5 step type scale; comfortable measure; real hierarchy (per the design skill).
- **Motion:** purposeful reveals + micro-interactions; respect `prefers-reduced-motion`.

## Step 3 — New surfaces

Each is a page/card fed by a **read-only JSON endpoint** added to `xavani_cli/web_server.py`
(sourced from the operator state store, observability metrics, cron jobs, wisdom verdicts, quantum state):

| Page | Shows | Endpoint (read-only) |
|---|---|---|
| **Quantum Decision** | the superposed options, amplitudes, interference, and the collapse — a live "decision waveform" | `/api/quantum/last` |
| **Oracle** | wisdom verdicts, active downfall warnings, ascent suggestions, corpus browser | `/api/wisdom/verdict`, `/api/wisdom/corpus` |
| **Daily Counsel** | morning brief, the 8pm error log, tomorrow's tasks, hourly progress | `/api/advisor/brief`, `/api/advisor/errorlog` |
| **Operator / 24-7** | daemon health/heartbeat, cycle history, the tiered approve/reject queue | `/api/operator/health`, `/api/operator/proposals` |
| **Model Router** | which model each task-class resolves to + which providers are active | `/api/router/resolved` |
| **Cost & Savings** | per-tool/model spend + R10 avoided-cost | `/api/cost/summary` |

The approve/reject queue satisfies the deferred v0.7.0 **M7 U93/U94** (operator monitor + approval UI).

## Step 4 — Verify

- `cd web && npm run build` exits 0; `xavani dashboard` serves with the Enternovate theme as default.
- Drive it with the `webapp-testing` / playwright skill: navigate each page, screenshot, assert no
  empty labels, confirm WCAG-AA contrast on the navy palette.
- `grep -rniE '\b(nous|hermes)\b' web/src` → no visible-branding hits (npm dep import lines excepted).

## Definition of done

Audit notes captured · Enternovate theme default + switchable · all six surfaces render real data ·
every label written + translated · WCAG AA · build green · screenshots attached to the PR · R1 clean.
