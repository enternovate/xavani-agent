<!-- LOCAL, UNTRACKED, DO-NOT-PUSH. Enternovate dashboard design system (canonical color source). -->

# Enternovate — Dashboard Design System (deep-navy)

The canonical brand/design spec for the `xavani dashboard` redesign (major ④). Built in the
`principle-dark-elegance` direction (a profile the user taught the agent) per `skills/design/SKILL.md`.
Curated by the agent (the user delegated the exact palette); tunable later.

## 1. Color tokens

| Token | Hex / value | Role | Notes |
|---|---|---|---|
| `--background-base` | `#0A1730` | app canvas | deep Enternovate navy |
| `--surface` | `#0F2147` | panels, cards | one step up from canvas |
| `--surface-2` / `--border` | `#1B305C` | dividers, outlines, inputs | |
| `--foreground-base` | `#E8EEF9` | primary text | cool near-white |
| `--muted` | `#93A4C4` | secondary text, captions | ≥4.5:1 on canvas |
| `--accent` | `#4D8DFF` | primary — CTAs, links, focus ring | electric blue |
| `--accent-strong` | `#2F6FE0` | hover/pressed accent | |
| `--quantum` | `#22D3EE` | the decision waveform ONLY | cyan; used sparingly |
| `--success` | `#34D399` | healthy / done | |
| `--warning` | `#FBBF24` | attention / downfall warning | |
| `--danger` | `#F87171` | error / blocked / Tier-3 | |
| `--glow` | `rgba(77,141,255,0.30)` | Backdrop glow (replaces warm amber) | |

**Contrast (must hold, WCAG AA):** `#E8EEF9` on `#0A1730` ≈ 15:1 (AAA); `#93A4C4` on `#0A1730`
≈ 6.6:1 (AA); `#4D8DFF` on `#0A1730` ≈ 5.0:1 (AA for UI + large text — use `#E8EEF9` for body, the
accent for emphasis/links/controls). Re-verify any new pairing before shipping.

## 2. Typography

- **Display:** one confident geometric/grotesk for headings (replace the bundled novelty faces).
- **Text:** one highly-legible humanist sans for body/UI.
- **Mono:** keep JetBrains Mono for the embedded terminal/code.
- **Scale (3–5 steps):** e.g. 12 / 14 / 16 / 20 / 28 / 40 px; line-height 1.5 body, 1.15 display;
  measure 60–75ch for prose. Real hierarchy — big where it matters.

## 3. Space, radius, motion

- **8pt spacing system** (`--spacing` multiplier already exists in `index.css`).
- **Radius:** `--radius: 0.5rem` cards, `0.75rem` modals, full for pills/avatars.
- **Elevation:** navy surfaces + a soft cool glow, never harsh black drop-shadows ("dark elegance":
  glowing focal points, no pure-black flat boxes).
- **Motion:** purposeful reveals (120–240ms), micro-interactions on controls, the quantum waveform
  animates its collapse; everything respects `prefers-reduced-motion`.

## 4. Component conventions

- One clear primary action per view (the accent). Secondary actions are ghost/outline.
- Status uses the semantic colors + a written label (never color alone — accessibility).
- Cards: `--surface` bg, `--border` 1px, generous padding, a clear title + one focal metric.
- Charts (Observable Plot / existing libs): navy bg, `--accent` series, `--quantum` for the waveform,
  `--muted` gridlines; always a written axis label + legend.

## 5. Copy / voice

- **Every label, empty-state, tooltip, and error is written** (the user's explicit requirement) and
  added to the i18n catalogue (works with the existing `LanguageSwitcher`).
- Voice: precise, calm, confident — Enternovate ("Open source. Private. Local."). No filler, no lorem.
- Empty states explain what will appear and how to make it appear (e.g. "No decisions yet — run
  `xavani operator cycle` and the waveform will appear here.").

## 6. Implementation notes

- Add `web/src/themes/enternovate.*` and register it in the theme list; set it **default** (replaces
  the Xavani-Teal LENS_0 defaults in `web/src/index.css`). Keep the switcher + existing themes.
- The DS is `@nous-research/ui` (upstream npm library — allowed to remain a dependency); we **theme**
  it via the existing token-rewrite mechanism (`ThemeProvider` writes inline CSS vars). Do not fork the
  package; override tokens.
- Scrub any visible "Nous" wordmark/branding from the chrome (R1) — replace with Enternovate.
