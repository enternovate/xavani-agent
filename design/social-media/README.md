# Sovereign Indigo — Xavani Agent Social-Media Campaign

A four-plate visual campaign built on the [**Sovereign Indigo**](PHILOSOPHY.md) design philosophy.

## Plates

| File | Format | Dimensions | Story |
|------|--------|------------|-------|
| `01_manifesto.png` | Portrait | 1080 × 1350 | The signature poster — `XAVANI`, *the agent that answers to you* — anchored by a deep indigo disc with a single ember spark. **Use:** Instagram feed, LinkedIn post, Twitter pinned tweet. |
| `02_refusal.png` | Square | 1080 × 1080 | *Nothing leaves your machine.* The vow of refusal: a ringed circle struck through with ember, encircled by the eight things Xavani won't do — telemetry, cloud-lock, phone-home, backdoors, surveillance, dark patterns, vendor lock, data harvest. **Use:** Instagram grid, Twitter card. |
| `03_constellation.png` | Square | 1080 × 1080 | *One key. Every model.* The constellation — Xavani at the centre, eight providers radiating outward: OpenAI, Anthropic, Gemini, Ollama, OpenRouter, xAI, Mistral, Groq. **Use:** Instagram grid, Mastodon post. |
| `04_codex.png` | Portrait | 1080 × 1350 | *169 instruments — all in the bench, all yours.* A meditative 13 × 13 codex of glyphs representing the bundled skills, plugins, agents and gateways. **Use:** Instagram feed, blog hero image. |

## Palette

| Token | Hex | Use |
|-------|-----|-----|
| INK | `#0C1226` | Primary text, hero forms |
| CREAM | `#F4EBDC` | Paper |
| EMBER | `#E46D2F` | Single accent — sparingly |
| SILVER DIM | `#6E7480` | Annotations |

## Fonts

All from the Anthropic Canvas Design font set (no licensing required for redistribution):
- **Boldonse-Regular** — display capitals (Plate I title)
- **Gloock-Regular** — serif display (Plate II / IV titles)
- **InstrumentSerif-Italic** — italic taglines
- **InstrumentSerif-Regular** — block titles (Plate III)
- **GeistMono-Regular / Bold** — annotations & doctrine
- **IBMPlexMono-Regular** — doctrine lines

## Re-generating

```bash
cd design/social-media
python3 render.py
```

Requires Pillow (`python3 -m pip install pillow`). No network calls; deterministic output.
