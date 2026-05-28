#!/usr/bin/env python3
"""Sovereign Indigo — Xavani Agent social-media campaign.

Renders four single-page compositions to PNG, each a single piece of the
larger story: what Xavani is, what it refuses, what it carries, what it
makes possible. Run ``python3 render.py``.

LAYOUT DISCIPLINE
-----------------
Every page is partitioned into clearly bounded zones — header, title,
hero, doctrine, serial — with no element allowed to cross a zone
boundary. Margins are measured in units, never decorative. Each
helper enforces the boundary it owns.
"""
from __future__ import annotations

import math
import os
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# ----------------------------------------------------------------------
# Paths & palette
# ----------------------------------------------------------------------

HERE = Path(__file__).resolve().parent
FONTS = Path(
    "/Users/andilemushwana/.claude/plugins/cache/anthropic-agent-skills/"
    "claude-api/5128e1865d67/skills/canvas-design/canvas-fonts"
)

INK = (12, 18, 38)
INK_DEEP = (8, 12, 26)
INK_SOFT = (28, 38, 64)
CREAM = (244, 235, 220)
CREAM_SOFT = (235, 224, 206)
EMBER = (228, 109, 47)
EMBER_DIM = (170, 80, 32)
SILVER = (164, 168, 178)
SILVER_DIM = (110, 116, 128)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


# ----------------------------------------------------------------------
# Drawing primitives
# ----------------------------------------------------------------------


def tw(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> float:
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[2] - bbox[0]


def th(draw: ImageDraw.ImageDraw, text: str, f: ImageFont.FreeTypeFont) -> float:
    bbox = draw.textbbox((0, 0), text, font=f)
    return bbox[3] - bbox[1]


def circle(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r: float,
    outline=INK,
    width: int = 1,
    fill=None,
) -> None:
    bbox = (cx - r, cy - r, cx + r, cy + r)
    if fill is not None:
        draw.ellipse(bbox, fill=fill, outline=outline, width=width)
    else:
        draw.ellipse(bbox, outline=outline, width=width)


def diamond(draw: ImageDraw.ImageDraw, cx: float, cy: float, size: float, fill=INK) -> None:
    pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
    draw.polygon(pts, fill=fill)


def serial(draw: ImageDraw.ImageDraw, W: int, H: int, color=SILVER_DIM) -> None:
    f = font("GeistMono-Regular.ttf", 13)
    txt = "XAVANI  ·  SOVEREIGN INDIGO  ·  MMXXVI"
    draw.text(((W - tw(draw, txt, f)) / 2, H - 50), txt, font=f, fill=color)


def corner_marks(draw: ImageDraw.ImageDraw, W: int, H: int, m: int = 56, color=INK) -> None:
    arm = 18
    for cx, cy in [(m, m), (W - m, m), (m, H - m), (W - m, H - m)]:
        draw.line([(cx - arm, cy), (cx + arm, cy)], fill=color, width=1)
        draw.line([(cx, cy - arm), (cx, cy + arm)], fill=color, width=1)


def top_meta(draw: ImageDraw.ImageDraw, W: int, label: str, plate: str, color=INK) -> None:
    f = font("GeistMono-Regular.ttf", 13)
    y = 84
    draw.text((96, y), label.upper(), font=f, fill=color)
    plate = plate.upper()
    draw.text((W - 96 - tw(draw, plate, f), y), plate, font=f, fill=color)


def paper_grain(draw: ImageDraw.ImageDraw, W: int, H: int, seed: int) -> None:
    rng = random.Random(seed)
    for _ in range(2400):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, H - 1)
        draw.point((x, y), fill=CREAM_SOFT if rng.random() < 0.5 else (228, 218, 200))


def centered_text(
    draw: ImageDraw.ImageDraw,
    W: int,
    y: float,
    text: str,
    f: ImageFont.FreeTypeFont,
    color,
) -> float:
    """Draw text centred horizontally; return the next y after the line."""
    width = tw(draw, text, f)
    draw.text(((W - width) / 2, y), text, font=f, fill=color)
    # Use the font's ascent + descent for a tight, predictable line height.
    ascent, descent = f.getmetrics()
    return y + ascent + descent


# ----------------------------------------------------------------------
# Plate I — Manifesto / hero
# ----------------------------------------------------------------------


def render_plate_one() -> Path:
    """Portrait, 1080×1350. The signature poster."""
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=7)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE I  ·  MANIFESTO", "01 / 04")

    # ZONES (vertical) — derived from real textbbox, not eyeballed:
    # header   : 0   – 130
    # title    : measured below
    # subtitle : 40 px below title bbox bottom
    # hairline : 22 px below subtitle bbox bottom
    # hero     : 60 px below hairline
    # doctrine : 1210 – 1260
    # serial   : 1300 – 1350

    # ─── Title lockup ────────────────────────────────────────────────
    title_f = font("Boldonse-Regular.ttf", 150)
    title = "XAVANI"
    title_y_anchor = 200
    title_bbox = d.textbbox(((W - tw(d, title, title_f)) / 2, title_y_anchor), title, font=title_f)
    title_x = (W - tw(d, title, title_f)) / 2
    d.text((title_x, title_y_anchor), title, font=title_f, fill=INK_DEEP)
    title_bottom = title_bbox[3]  # real pixel bottom

    # ─── Subtitle — placed at a measured gap below the title ─────────
    sub_f = font("InstrumentSerif-Italic.ttf", 32)
    sub = "the agent that answers to you"
    sub_y = title_bottom + 36
    sub_x = (W - tw(d, sub, sub_f)) / 2
    sub_bbox = d.textbbox((sub_x, sub_y), sub, font=sub_f)
    d.text((sub_x, sub_y), sub, font=sub_f, fill=INK_SOFT)
    sub_bottom = sub_bbox[3]

    # a hairline beneath the subtitle — a printer's mark, separating the
    # nameplate from the hero composition
    rule_y = sub_bottom + 22
    rule_half = 70
    d.line(
        [(W / 2 - rule_half, rule_y), (W / 2 + rule_half, rule_y)],
        fill=INK,
        width=1,
    )

    # ─── Hero: the indigo disc + ember spark ─────────────────────────
    # disc top is placed 60px below the hairline so the title zone is
    # unambiguously separate from the hero zone.
    arch_r = 280
    arch_top = rule_y + 60
    arch_cx = W / 2
    arch_cy = arch_top + arch_r
    circle(d, arch_cx, arch_cy, arch_r, fill=INK, outline=INK)

    # internal ring — a quiet rhythm inside the form, only visible up close
    circle(d, arch_cx, arch_cy, arch_r - 24, outline=INK_SOFT, width=1)
    circle(d, arch_cx, arch_cy, arch_r - 60, outline=INK_SOFT, width=1)

    # vertical meridian inside the disc
    d.line(
        [(arch_cx, arch_cy - arch_r + 16), (arch_cx, arch_cy + arch_r - 16)],
        fill=INK_SOFT,
        width=1,
    )

    # ember pupil — the only warm element on the page
    circle(d, arch_cx, arch_cy, 14, fill=EMBER, outline=EMBER)
    # ember halo (thin ring)
    circle(d, arch_cx, arch_cy, 28, outline=EMBER_DIM, width=1)

    # cardinal annotations — placed OUTSIDE the disc, with breathing room
    fmono_sm = font("GeistMono-Regular.ttf", 12)
    for angle_deg, label in [
        (-90, "ZENITH"),
        (0, "EAST"),
        (90, "NADIR"),
        (180, "WEST"),
    ]:
        rad = math.radians(angle_deg)
        tx = arch_cx + (arch_r + 38) * math.cos(rad)
        ty = arch_cy + (arch_r + 38) * math.sin(rad)
        lw = tw(d, label, fmono_sm)
        lh = th(d, label, fmono_sm)
        d.text((tx - lw / 2, ty - lh / 2), label, font=fmono_sm, fill=SILVER_DIM)

    # ─── Doctrine ────────────────────────────────────────────────────
    fdoc = font("GeistMono-Regular.ttf", 22)
    doctrine = ["LOCAL.", "PRIVATE.", "OPEN."]
    gap = 92
    total = sum(tw(d, t, fdoc) for t in doctrine) + gap * (len(doctrine) - 1)
    cur_x = (W - total) / 2
    y_doc = 1210
    d.line(
        [(cur_x - 22, y_doc + 36), (cur_x + total + 22, y_doc + 36)],
        fill=INK,
        width=1,
    )
    for word in doctrine:
        d.text((cur_x, y_doc), word, font=fdoc, fill=INK)
        cur_x += tw(d, word, fdoc) + gap

    serial(d, W, H)
    out = HERE / "01_manifesto.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Plate II — Refusal (privacy / no telemetry)
# ----------------------------------------------------------------------


def render_plate_two() -> Path:
    """Square, 1080×1080. The vow of refusal."""
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), INK)
    d = ImageDraw.Draw(img)

    # cream "paper" inset — a tipped-in plate inside an indigo cover
    margin = 64
    inner = (margin, margin, W - margin, H - margin)
    d.rectangle(inner, fill=CREAM)
    d.rectangle(inner, outline=INK, width=2)

    top_meta(d, W, "PLATE II  ·  REFUSAL", "02 / 04")

    # ZONES (vertical, inside the cream inset):
    # title    : 150 – 350
    # hero     : 400 – 800  (circle + ring labels; ring radius 240)
    # doctrine : 870 – 940
    # serial   : H - 50 (outside the inset, on the indigo border)

    # ─── Title (in the cream zone) ───────────────────────────────────
    title_f = font("Gloock-Regular.ttf", 80)
    title = "Nothing leaves"
    centered_text(d, W, 168, title, title_f, INK_DEEP)

    title2_f = font("InstrumentSerif-Italic.ttf", 56)
    title2 = "your machine."
    centered_text(d, W, 268, title2, title2_f, INK_SOFT)

    # ─── Hero: ringed circle struck through with ember ───────────────
    cx, cy, r = W / 2, 600, 160
    circle(d, cx, cy, r, outline=INK, width=4)
    circle(d, cx, cy, r - 14, outline=INK_SOFT, width=1)

    # the diagonal slash — ember, hand-confident
    pad = 22
    a = (cx - r + pad, cy + r - pad)
    b = (cx + r - pad, cy - r + pad)
    d.line([a, b], fill=EMBER, width=8)

    # ring of micro-labels — things Xavani refuses
    refusals = [
        "TELEMETRY", "CLOUD-LOCK", "PHONE-HOME", "BACKDOORS",
        "SURVEILLANCE", "DARK PATTERNS", "VENDOR LOCK", "DATA HARVEST",
    ]
    fmark = font("GeistMono-Regular.ttf", 12)
    ring_r = r + 76  # well outside the circle
    for i, word in enumerate(refusals):
        ang = -math.pi / 2 + i * (2 * math.pi / len(refusals))
        lw = tw(d, word, fmark)
        lh = th(d, word, fmark)
        ltx = cx + ring_r * math.cos(ang)
        lty = cy + ring_r * math.sin(ang)
        d.text((ltx - lw / 2, lty - lh / 2), word, font=fmark, fill=SILVER_DIM)
        # short connector tick from circle edge toward label
        x1 = cx + (r + 14) * math.cos(ang)
        y1 = cy + (r + 14) * math.sin(ang)
        x2 = cx + (r + 30) * math.cos(ang)
        y2 = cy + (r + 30) * math.sin(ang)
        d.line([(x1, y1), (x2, y2)], fill=INK, width=1)

    # ─── Doctrine ────────────────────────────────────────────────────
    fnote = font("IBMPlexMono-Regular.ttf", 15)
    note = "ZERO TELEMETRY  ·  LOCAL EXECUTION  ·  OPEN SOURCE  ·  MIT LICENSE"
    nw = tw(d, note, fnote)
    d.text(((W - nw) / 2, 900), note, font=fnote, fill=INK)
    # ember footer underline
    d.line([(W / 2 - 70, 938), (W / 2 + 70, 938)], fill=EMBER, width=2)

    serial(d, W, H, color=SILVER)
    out = HERE / "02_refusal.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Plate III — Constellation (multi-provider gateway)
# ----------------------------------------------------------------------


def render_plate_three() -> Path:
    """Square, 1080×1080. Many providers, one gateway."""
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=13)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE III  ·  CONSTELLATION", "03 / 04")

    # ZONES (vertical):
    # title-block : 160 – 360 (left-aligned)
    # hero        : 400 – 880 (constellation centre at y=620, sat_r=180, label_r=220)
    # doctrine    : 920 – 980

    # ─── Title block ─────────────────────────────────────────────────
    title_f = font("InstrumentSerif-Regular.ttf", 58)
    d.text((96, 168), "One key.", font=title_f, fill=INK_DEEP)
    d.text((96, 232), "Every model.", font=title_f, fill=INK_DEEP)

    fmeta = font("GeistMono-Regular.ttf", 13)
    d.multiline_text(
        (96, 312),
        "A SINGLE GATEWAY FOR EVERY PROVIDER\nYOU ALREADY PAY FOR.",
        font=fmeta,
        fill=SILVER_DIM,
        spacing=4,
    )

    # ─── Hero: constellation ─────────────────────────────────────────
    cx, cy = W / 2, 640
    core_r = 48
    sat_r = 180       # node ring
    label_r = 232     # text ring (well outside satellite nodes)

    provider_names = [
        "OPENAI", "ANTHROPIC", "GEMINI", "OLLAMA",
        "OPENROUTER", "XAI", "MISTRAL", "GROQ",
    ]

    sat_positions: list[tuple[float, float]] = []
    for i in range(len(provider_names)):
        ang = -math.pi / 2 + i * (2 * math.pi / len(provider_names))
        sx = cx + sat_r * math.cos(ang)
        sy = cy + sat_r * math.sin(ang)
        sat_positions.append((sx, sy))
        d.line([(cx, cy), (sx, sy)], fill=INK, width=1)

    # circumscribing outer ring
    circle(d, cx, cy, label_r + 32, outline=INK, width=1)

    # satellite nodes
    fname = font("GeistMono-Regular.ttf", 11)
    for i, ((sx, sy), name) in enumerate(zip(sat_positions, provider_names)):
        circle(d, sx, sy, 18, fill=INK, outline=INK)
        circle(d, sx, sy, 6, fill=CREAM, outline=CREAM)
        # label position computed around `label_r` so labels sit on a clean ring
        ang = -math.pi / 2 + i * (2 * math.pi / len(provider_names))
        ltx = cx + label_r * math.cos(ang)
        lty = cy + label_r * math.sin(ang)
        lw = tw(d, name, fname)
        lh = th(d, name, fname)
        # offset label outward by half its own width along the angle
        ltx += (lw / 2 + 4) * math.cos(ang) * 0  # keep label centred on radius
        d.text((ltx - lw / 2, lty - lh / 2), name, font=fname, fill=INK)

    # the core — ember pupil
    circle(d, cx, cy, core_r, fill=INK_DEEP, outline=INK_DEEP)
    circle(d, cx, cy, core_r - 12, outline=CREAM, width=1)
    circle(d, cx, cy, 11, fill=EMBER, outline=EMBER)

    # core caption — placed where it cannot collide with satellites:
    # tucked into the WHITESPACE just above the title block? no, place it
    # directly below the constellation centre but well inside the disc-free
    # gap between core and satellites. The gap = sat_r - core_r - label_size,
    # which here is 180 - 48 - 20 = 112px — plenty of room.
    fcore = font("GeistMono-Bold.ttf", 13)
    cap = "XAVANI · CORE"
    capw = tw(d, cap, fcore)
    d.text((cx - capw / 2, cy + core_r + 14), cap, font=fcore, fill=INK)

    # ─── Doctrine ────────────────────────────────────────────────────
    # placed safely BELOW the outer ring (which ends at cy + label_r + 32 = 904)
    fbottom = font("GeistMono-Regular.ttf", 15)
    bottom = "25+ PROVIDERS  ·  MCP-NATIVE GATEWAY  ·  localhost:8080"
    bw = tw(d, bottom, fbottom)
    d.text(((W - bw) / 2, 956), bottom, font=fbottom, fill=INK)
    d.line([(W / 2 - 70, 990), (W / 2 + 70, 990)], fill=EMBER, width=2)

    serial(d, W, H)
    out = HERE / "03_constellation.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Plate IV — Codex (the skills library)
# ----------------------------------------------------------------------


def render_plate_four() -> Path:
    """Portrait, 1080×1350. The skills codex — meditative grid of marks."""
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=29)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE IV  ·  CODEX", "04 / 04")

    # ZONES (vertical):
    # title      : 170 – 360
    # codex grid : 420 – 1100 (13 cols × 13 rows = 169 cells; cell ≈ 52)
    # doctrine   : 1170 – 1240

    # ─── Title block ─────────────────────────────────────────────────
    title_f = font("Gloock-Regular.ttf", 90)
    centered_text(d, W, 188, "169 instruments.", title_f, INK_DEEP)
    sub_f = font("InstrumentSerif-Italic.ttf", 32)
    centered_text(d, W, 304, "all in the bench, all yours.", sub_f, INK_SOFT)

    # ─── Codex grid ──────────────────────────────────────────────────
    cols, rows = 13, 13
    cell = 50  # tuned so grid_top + 13*cell <= 1100
    grid_w = cols * cell
    grid_h = rows * cell
    grid_left = (W - grid_w) / 2
    grid_top = 430
    grid_right = grid_left + grid_w
    grid_bottom = grid_top + grid_h  # 430 + 650 = 1080 — fits cleanly

    # outer frame
    d.rectangle(
        (grid_left, grid_top, grid_right, grid_bottom),
        outline=INK,
        width=1,
    )

    # mark each cell with a small glyph; choice forms a pattern inspired by
    # Tsonga/Ndebele textile rhythms, abstracted to pure form
    ember_cells = {(6, 6), (3, 9), (9, 3), (1, 11), (11, 1), (5, 0), (0, 5), (12, 12)}
    for r in range(rows):
        for c in range(cols):
            x0 = grid_left + c * cell
            y0 = grid_top + r * cell
            ccx = x0 + cell / 2
            ccy = y0 + cell / 2
            d.rectangle(
                (x0, y0, x0 + cell, y0 + cell),
                outline=(220, 210, 192),
                width=1,
            )
            kind = (r + c) % 4
            glyph_color = EMBER if (c, r) in ember_cells else INK
            if kind == 0:
                circle(d, ccx, ccy, 7, fill=glyph_color, outline=glyph_color)
            elif kind == 1:
                circle(d, ccx, ccy, 8, outline=glyph_color, width=1)
            elif kind == 2:
                diamond(d, ccx, ccy, 8, fill=glyph_color)
            else:
                d.rectangle(
                    (ccx - 2, ccy - 8, ccx + 2, ccy + 8),
                    fill=glyph_color,
                )

    # left-margin row letters
    flbl = font("GeistMono-Regular.ttf", 10)
    letters = "ABCDEFGHIJKLM"
    for i, ch in enumerate(letters):
        d.text(
            (grid_left - 20, grid_top + i * cell + cell / 2 - 6),
            ch,
            font=flbl,
            fill=SILVER_DIM,
        )
    for i in range(cols):
        d.text(
            (grid_left + i * cell + cell / 2 - 6, grid_bottom + 6),
            str(i + 1).zfill(2),
            font=flbl,
            fill=SILVER_DIM,
        )

    # ─── Doctrine ────────────────────────────────────────────────────
    foot_f = font("IBMPlexMono-Regular.ttf", 15)
    foot = "SKILLS  ·  PLUGINS  ·  AGENTS  ·  GATEWAYS"
    fw = tw(d, foot, foot_f)
    y_foot = 1190
    d.text(((W - fw) / 2, y_foot), foot, font=foot_f, fill=INK)
    sub_foot = font("InstrumentSerif-Italic.ttf", 22)
    sub_t = "all bundled, none optional"
    centered_text(d, W, y_foot + 36, sub_t, sub_foot, INK_SOFT)
    d.line([(W / 2 - 80, 1280), (W / 2 + 80, 1280)], fill=EMBER, width=2)

    serial(d, W, H)
    out = HERE / "04_codex.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> None:
    os.makedirs(HERE, exist_ok=True)
    for renderer in (render_plate_one, render_plate_two, render_plate_three, render_plate_four):
        p = renderer()
        print(f"  rendered: {p}")


if __name__ == "__main__":
    main()
