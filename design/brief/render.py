#!/usr/bin/env python3
"""Sovereign Indigo — Xavani Agent briefing publication.

A four-plate explainer set that describes what Xavani Agent IS — its
layers, its capabilities, its surfaces, and the patient sequence by
which it turns a question into work. Sister publication to the
``design/social-media/`` campaign: same palette, same fonts, same
serial / corner / header system, so the two read as one volume.

Run with ``python3 render.py``.
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
INK_MID = (60, 70, 96)
CREAM = (244, 235, 220)
CREAM_SOFT = (235, 224, 206)
EMBER = (228, 109, 47)
EMBER_DIM = (170, 80, 32)
SILVER = (164, 168, 178)
SILVER_DIM = (110, 116, 128)
SILVER_PALE = (210, 200, 184)


def font(name: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONTS / name), size)


# ----------------------------------------------------------------------
# Drawing primitives
# ----------------------------------------------------------------------


def tw(draw, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    return b[2] - b[0]


def th(draw, text, f):
    b = draw.textbbox((0, 0), text, font=f)
    return b[3] - b[1]


def circle(d, cx, cy, r, outline=INK, width=1, fill=None):
    bbox = (cx - r, cy - r, cx + r, cy + r)
    if fill is not None:
        d.ellipse(bbox, fill=fill, outline=outline, width=width)
    else:
        d.ellipse(bbox, outline=outline, width=width)


def diamond(d, cx, cy, size, fill=INK):
    pts = [(cx, cy - size), (cx + size, cy), (cx, cy + size), (cx - size, cy)]
    d.polygon(pts, fill=fill)


def serial(d, W, H, color=SILVER_DIM):
    f = font("GeistMono-Regular.ttf", 13)
    txt = "XAVANI  ·  BRIEFING  ·  SOVEREIGN INDIGO  ·  MMXXVI"
    d.text(((W - tw(d, txt, f)) / 2, H - 50), txt, font=f, fill=color)


def corner_marks(d, W, H, m=56, color=INK):
    arm = 18
    for cx, cy in [(m, m), (W - m, m), (m, H - m), (W - m, H - m)]:
        d.line([(cx - arm, cy), (cx + arm, cy)], fill=color, width=1)
        d.line([(cx, cy - arm), (cx, cy + arm)], fill=color, width=1)


def top_meta(d, W, label, plate, color=INK):
    f = font("GeistMono-Regular.ttf", 13)
    d.text((96, 84), label.upper(), font=f, fill=color)
    p = plate.upper()
    d.text((W - 96 - tw(d, p, f), 84), p, font=f, fill=color)


def paper_grain(d, W, H, seed):
    rng = random.Random(seed)
    for _ in range(2400):
        x = rng.randint(0, W - 1)
        y = rng.randint(0, H - 1)
        d.point((x, y), fill=CREAM_SOFT if rng.random() < 0.5 else (228, 218, 200))


# ----------------------------------------------------------------------
# Plate I — Anatomy (the layered stack)
# ----------------------------------------------------------------------


def render_plate_anatomy() -> Path:
    """Portrait 1080×1350. The cross-section: six layers stacked."""
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=41)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE I  ·  ANATOMY", "01 / 04")

    title_f = font("Gloock-Regular.ttf", 84)
    title = "Anatomy"
    title_y = 180
    d.text(((W - tw(d, title, title_f)) / 2, title_y), title, font=title_f, fill=INK_DEEP)
    title_bot = d.textbbox(((W - tw(d, title, title_f)) / 2, title_y), title, font=title_f)[3]

    sub_f = font("InstrumentSerif-Italic.ttf", 30)
    sub = "the layers of a sovereign agent"
    sub_y = title_bot + 24
    d.text(((W - tw(d, sub, sub_f)) / 2, sub_y), sub, font=sub_f, fill=INK_SOFT)
    sub_bot = d.textbbox(((W - tw(d, sub, sub_f)) / 2, sub_y), sub, font=sub_f)[3]

    layers = [
        ("01", "SURFACES",  "xavani CLI · dashboard · MCP gateway · ACP · platforms"),
        ("02", "AGENT",     "conversation loop · planning · dispatch · failover"),
        ("03", "SKILLS",    "169 bundled · MCP tools · file · web · shell · browser"),
        ("04", "MEMORY",    "sessions · episodic · procedural · per-profile"),
        ("05", "GATEWAY",   "MCP proxy on :8080 · policy · audit · rate limit"),
        ("06", "PROVIDERS", "openai · anthropic · gemini · ollama · openrouter · xai · …"),
    ]

    stack_top = sub_bot + 64
    stack_h = 660
    band_h = stack_h // len(layers)
    stack_left = 130
    stack_right = W - 130

    d.rectangle(
        (stack_left, stack_top, stack_right, stack_top + band_h * len(layers)),
        outline=INK,
        width=1,
    )

    for y in range(stack_top, stack_top + band_h * len(layers), 12):
        d.line([(stack_left - 8, y), (stack_left - 2, y)], fill=SILVER_PALE, width=1)
        d.line([(stack_right + 2, y), (stack_right + 8, y)], fill=SILVER_PALE, width=1)

    num_f = font("GeistMono-Regular.ttf", 14)
    name_f = font("Boldonse-Regular.ttf", 38)
    body_f = font("GeistMono-Regular.ttf", 13)

    for i, (num, name, body) in enumerate(layers):
        band_top = stack_top + i * band_h
        band_bot = band_top + band_h

        if i % 2 == 0:
            d.rectangle((stack_left, band_top, stack_right, band_bot), fill=INK)
            text_color = CREAM
            num_color = SILVER_PALE
            body_color = SILVER_PALE
        else:
            text_color = INK_DEEP
            num_color = SILVER_DIM
            body_color = INK_MID

        if name == "AGENT":
            d.rectangle((stack_left, band_top, stack_left + 5, band_bot), fill=EMBER)

        d.text((stack_left + 22, band_top + (band_h - 18) / 2 - 2), num, font=num_f, fill=num_color)

        name_x = stack_left + 70
        name_h = th(d, name, name_f)
        d.text((name_x, band_top + (band_h - name_h) / 2 - 4), name, font=name_f, fill=text_color)

        body_w = tw(d, body, body_f)
        d.text(
            (stack_right - 22 - body_w, band_top + (band_h - 14) / 2 - 1),
            body,
            font=body_f,
            fill=body_color,
        )

        if i > 0:
            d.line([(stack_left, band_top), (stack_right, band_top)], fill=INK, width=1)

    foot_f = font("IBMPlexMono-Regular.ttf", 14)
    foot = "EVERY LAYER OWNED  ·  EVERY LAYER OPTIONAL  ·  EVERY LAYER YOURS"
    fw = tw(d, foot, foot_f)
    d.text(((W - fw) / 2, H - 140), foot, font=foot_f, fill=INK)
    d.line([(W / 2 - 80, H - 108), (W / 2 + 80, H - 108)], fill=EMBER, width=2)

    serial(d, W, H)
    out = HERE / "01_anatomy.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Plate II — Capabilities (the matrix grid of cards)
# ----------------------------------------------------------------------


def render_plate_capabilities() -> Path:
    """Portrait 1080×1350. A 4×6 grid of capability cards."""
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=53)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE II  ·  CAPABILITIES", "02 / 04")

    title_f = font("Gloock-Regular.ttf", 84)
    title = "Capabilities"
    title_y = 180
    d.text(((W - tw(d, title, title_f)) / 2, title_y), title, font=title_f, fill=INK_DEEP)
    title_bot = d.textbbox(((W - tw(d, title, title_f)) / 2, title_y), title, font=title_f)[3]

    sub_f = font("InstrumentSerif-Italic.ttf", 30)
    sub = "what it does, without asking permission"
    sub_y = title_bot + 24
    d.text(((W - tw(d, sub, sub_f)) / 2, sub_y), sub, font=sub_f, fill=INK_SOFT)
    sub_bot = d.textbbox(((W - tw(d, sub, sub_f)) / 2, sub_y), sub, font=sub_f)[3]

    caps = [
        ("dot",     "CHAT",        "interactive REPL", False),
        ("ring",    "GATEWAY",     "MCP proxy on :8080", True),
        ("diamond", "DASHBOARD",   "web UI on :9119", False),
        ("bar",     "SKILLS",      "169 bundled", False),

        ("ring",    "PLUGINS",     "extensible at runtime", False),
        ("dot",     "MEMORY",      "persistent across sessions", False),
        ("diamond", "CRON",        "scheduled tasks", False),
        ("bar",     "KANBAN",      "built-in board", False),

        ("ring",    "VOICE",       "TTS + STT", False),
        ("dot",     "BROWSER",     "browser-use / firecrawl", False),
        ("diamond", "IMAGE",       "generation + edit", False),
        ("bar",     "SANDBOX",     "isolated execution", True),

        ("dot",     "MULTI-MODEL", "automatic failover", False),
        ("ring",    "MCP-NATIVE",  "the tool bus", False),
        ("diamond", "ACP",         "IDE editor adapter", False),
        ("bar",     "POLICY",      "guardrails + audit", False),

        ("ring",    "PORTABLE",    "mac / linux / windows", False),
        ("dot",     "OFFLINE",     "works without a network", True),
        ("diamond", "SCRIPTABLE",  "Fire-style CLI", False),
        ("bar",     "HOOKS",       "pre/post lifecycle", False),

        ("dot",     "PLATFORMS",   "telegram · discord · slack", False),
        ("ring",    "PROFILES",    "per-context configuration", False),
        ("diamond", "UPDATE",      "self-managed releases", False),
        ("bar",     "OPEN SOURCE", "MIT · forever", False),
    ]

    cols = 4
    rows = 6
    grid_top = sub_bot + 56
    grid_bottom = H - 180
    grid_left = 96
    grid_right = W - 96
    cell_w = (grid_right - grid_left) / cols
    cell_h = (grid_bottom - grid_top) / rows

    d.rectangle((grid_left, grid_top, grid_right, grid_bottom), outline=INK, width=1)

    name_f = font("GeistMono-Bold.ttf", 16)
    desc_f = font("GeistMono-Regular.ttf", 11)

    for idx, (glyph, name, desc, accent) in enumerate(caps):
        r = idx // cols
        c = idx % cols
        x0 = grid_left + c * cell_w
        y0 = grid_top + r * cell_h
        x1 = x0 + cell_w
        y1 = y0 + cell_h

        d.rectangle((x0, y0, x1, y1), outline=SILVER_PALE, width=1)

        gcx = x0 + cell_w / 2
        gcy = y0 + 38
        glyph_color = EMBER if accent else INK

        if glyph == "dot":
            circle(d, gcx, gcy, 9, fill=glyph_color, outline=glyph_color)
        elif glyph == "ring":
            circle(d, gcx, gcy, 11, outline=glyph_color, width=2)
        elif glyph == "diamond":
            diamond(d, gcx, gcy, 11, fill=glyph_color)
        elif glyph == "bar":
            d.rectangle((gcx - 3, gcy - 12, gcx + 3, gcy + 12), fill=glyph_color)

        nw = tw(d, name, name_f)
        d.text((gcx - nw / 2, gcy + 22), name, font=name_f, fill=INK_DEEP)

        dw = tw(d, desc, desc_f)
        d.text((gcx - dw / 2, gcy + 50), desc, font=desc_f, fill=INK_MID)

        idx_label = f"{idx+1:02d}"
        idx_f = font("GeistMono-Regular.ttf", 10)
        d.text((x1 - 22, y0 + 8), idx_label, font=idx_f, fill=SILVER_DIM)

    foot_f = font("IBMPlexMono-Regular.ttf", 14)
    foot = "TWENTY-FOUR INSTRUMENTS BUNDLED  ·  ONE INSTALL  ·  ZERO TELEMETRY"
    fw = tw(d, foot, foot_f)
    d.text(((W - fw) / 2, H - 140), foot, font=foot_f, fill=INK)
    d.line([(W / 2 - 80, H - 108), (W / 2 + 80, H - 108)], fill=EMBER, width=2)

    serial(d, W, H)
    out = HERE / "02_capabilities.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Plate III — Surfaces (the radial fan of access points)
# ----------------------------------------------------------------------


def render_plate_surfaces() -> Path:
    """Square 1080×1080. Six surfaces radiating from the core."""
    W, H = 1080, 1080
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=67)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE III  ·  SURFACES", "03 / 04")

    title_f = font("InstrumentSerif-Regular.ttf", 58)
    d.text((96, 168), "Six ways", font=title_f, fill=INK_DEEP)
    d.text((96, 230), "to reach it.", font=title_f, fill=INK_DEEP)

    sub_f = font("GeistMono-Regular.ttf", 13)
    d.multiline_text(
        (96, 312),
        "EVERY SURFACE TALKS TO THE SAME AGENT,\nTHE SAME MEMORY, THE SAME SKILLS.",
        font=sub_f,
        fill=SILVER_DIM,
        spacing=4,
    )

    # Constellation geometry — shrunk and lifted so the bottom petal label
    # sits well clear of the doctrine zone, and the core caption can be
    # placed above the core (out of the south hairline's path).
    cx, cy = W / 2, 640
    core_r = 56
    petal_r = 178
    label_r = 232

    surfaces = [
        ("TERMINAL",    "$ xavani"),
        ("DASHBOARD",   "localhost:9119"),
        ("GATEWAY",     "localhost:8080"),
        ("ACP",         "stdio · IDEs"),
        ("PLATFORMS",   "tg · dc · sl · mx"),
        ("PYTHON API",  "import xavani"),
    ]
    angles = [-math.pi / 2 + i * (2 * math.pi / len(surfaces)) for i in range(len(surfaces))]

    # outer label ring, then an inner guide ring just outside the petals
    circle(d, cx, cy, label_r + 38, outline=INK, width=1)
    circle(d, cx, cy, petal_r + 10, outline=SILVER_PALE, width=1)

    # hairlines from core to each petal, EXCEPT the one going south through
    # the core caption — leave a small gap at the core end so the caption
    # isn't bisected by a line.
    for ang in angles:
        sx = cx + petal_r * math.cos(ang)
        sy = cy + petal_r * math.sin(ang)
        # start the line OUTSIDE the core (not from cx,cy) so the core
        # composition reads cleanly
        x0 = cx + (core_r + 4) * math.cos(ang)
        y0 = cy + (core_r + 4) * math.sin(ang)
        d.line([(x0, y0), (sx, sy)], fill=INK, width=1)

    petal_name_f = font("GeistMono-Bold.ttf", 14)
    petal_meta_f = font("GeistMono-Regular.ttf", 11)

    for ang, (name, meta) in zip(angles, surfaces):
        sx = cx + petal_r * math.cos(ang)
        sy = cy + petal_r * math.sin(ang)
        diamond(d, sx, sy, 11, fill=INK)
        circle(d, sx, sy, 4, fill=EMBER, outline=EMBER)

        ltx = cx + label_r * math.cos(ang)
        lty = cy + label_r * math.sin(ang)

        nw = tw(d, name, petal_name_f)
        mw = tw(d, meta, petal_meta_f)
        nh = th(d, name, petal_name_f)

        d.text((ltx - nw / 2, lty - nh - 4), name, font=petal_name_f, fill=INK)
        d.text((ltx - mw / 2, lty + 4), meta, font=petal_meta_f, fill=INK_MID)

    # the core — drawn AFTER the hairlines so it sits cleanly on top.
    # No caption: the subtitle ("every surface talks to the same agent")
    # and the bottom doctrine ("the work is the same work") already carry
    # the meaning. The iconic indigo + ember disc is enough.
    circle(d, cx, cy, core_r, fill=INK_DEEP, outline=INK_DEEP)
    circle(d, cx, cy, core_r - 12, outline=CREAM, width=1)
    circle(d, cx, cy, 12, fill=EMBER, outline=EMBER)

    # archival annotation off to the left of the constellation, with a
    # short leader line — small reverence rather than a label crashing
    # into the south hairline.
    annot_f = font("GeistMono-Regular.ttf", 11)
    annot = "AGENT · CORE"
    annot_w = tw(d, annot, annot_f)
    annot_y = cy
    annot_x_right = cx - label_r - 48  # text right-edge sits left of outer ring
    annot_x_left = annot_x_right - annot_w
    # leader: short hairline from annotation back toward the outer ring
    d.line(
        [(annot_x_right + 6, annot_y + 5), (annot_x_right + 28, annot_y + 5)],
        fill=SILVER_DIM,
        width=1,
    )
    d.text((annot_x_left, annot_y - 4), annot, font=annot_f, fill=SILVER_DIM)

    foot_f = font("IBMPlexMono-Regular.ttf", 14)
    foot = "PICK YOUR ENTRY  ·  THE WORK IS THE SAME WORK"
    fw = tw(d, foot, foot_f)
    d.text(((W - fw) / 2, H - 130), foot, font=foot_f, fill=INK)
    d.line([(W / 2 - 80, H - 98), (W / 2 + 80, H - 98)], fill=EMBER, width=2)

    serial(d, W, H)
    out = HERE / "03_surfaces.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Plate IV — Flow (the patient sequence)
# ----------------------------------------------------------------------


def render_plate_flow() -> Path:
    """Portrait 1080×1350. Vertical timeline of a request's journey."""
    W, H = 1080, 1350
    img = Image.new("RGB", (W, H), CREAM)
    d = ImageDraw.Draw(img)
    paper_grain(d, W, H, seed=79)

    corner_marks(d, W, H)
    top_meta(d, W, "PLATE IV  ·  FLOW", "04 / 04")

    title_f = font("Gloock-Regular.ttf", 74)
    d.text((96, 178), "How a question", font=title_f, fill=INK_DEEP)
    d.text((96, 270), "becomes work.", font=title_f, fill=INK_DEEP)

    sub_f = font("InstrumentSerif-Italic.ttf", 28)
    d.text((96, 366), "the patient sequence", font=sub_f, fill=INK_SOFT)

    steps = [
        ("01", "ARRIVAL",       "input lands on a surface — REPL, dashboard,",
                                "gateway, ACP, platform, API"),
        ("02", "AUTHORIZATION", "policy check + profile selection — every",
                                "request runs inside a known context"),
        ("03", "CONTEXT",       "memory, skills, SOUL.md and the research-",
                                "guideline pack are assembled"),
        ("04", "PLANNING",      "the agent decomposes the request into a",
                                "sequence of tool calls"),
        ("05", "DISPATCH",      "tool calls run — MCP, local shell, file",
                                "ops, web, browser, image, voice"),
        ("06", "PROVIDER",      "the model is invoked; if it fails, the",
                                "fallback chain takes over silently"),
        ("07", "PERSISTENCE",   "response is composed, logged, persisted;",
                                "memory updated for next turn"),
    ]

    spine_x = 178
    spine_top = 470
    spine_bot = H - 200
    d.line([(spine_x, spine_top), (spine_x, spine_bot)], fill=INK, width=1)

    n = len(steps)
    step_gap = (spine_bot - spine_top) / (n - 1)

    num_f = font("GeistMono-Bold.ttf", 12)
    name_f = font("Boldonse-Regular.ttf", 30)
    desc_f = font("GeistMono-Regular.ttf", 14)

    for i, (num, name, line1, line2) in enumerate(steps):
        y = spine_top + i * step_gap

        accent = (name == "PLANNING")
        outer_color = EMBER if accent else INK
        circle(d, spine_x, y, 18, outline=outer_color, width=2, fill=CREAM)
        circle(d, spine_x, y, 6, fill=outer_color, outline=outer_color)

        num_w = tw(d, num, num_f)
        d.text((spine_x - 38 - num_w, y - 7), num, font=num_f, fill=SILVER_DIM)

        name_x = spine_x + 42
        name_h = th(d, name, name_f)
        d.text((name_x, y - name_h / 2 - 3), name, font=name_f, fill=INK_DEEP)

        desc_x = spine_x + 42
        desc_y = y + name_h / 2 + 4
        d.text((desc_x, desc_y), line1, font=desc_f, fill=INK_MID)
        d.text((desc_x, desc_y + 22), line2, font=desc_f, fill=INK_MID)

    foot_f = font("IBMPlexMono-Regular.ttf", 14)
    foot = "SEVEN STEPS  ·  ONE PROCESS  ·  EVERY TURN AUDITED"
    fw = tw(d, foot, foot_f)
    d.text(((W - fw) / 2, H - 138), foot, font=foot_f, fill=INK)
    d.line([(W / 2 - 80, H - 106), (W / 2 + 80, H - 106)], fill=EMBER, width=2)

    serial(d, W, H)
    out = HERE / "04_flow.png"
    img.save(out, format="PNG", optimize=True)
    return out


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------


def main() -> None:
    os.makedirs(HERE, exist_ok=True)
    for renderer in (
        render_plate_anatomy,
        render_plate_capabilities,
        render_plate_surfaces,
        render_plate_flow,
    ):
        p = renderer()
        print(f"  rendered: {p}")


if __name__ == "__main__":
    main()
