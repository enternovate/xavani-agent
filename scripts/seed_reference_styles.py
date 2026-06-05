# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Seed the shipped reference style library (v0.7.0 operator L2/L5).

Distils the user's reference sites + the eleken "best website design examples"
principles into attributed :class:`StyleProfile`s and writes them as YAML into
``xavani_learner/style_library/`` so they ship as a base with xavani-agent.

This is the ``learn`` mechanism with the agent as the extractor: we capture each
site's **design DNA** (direction/principles), **attribute** the source, and copy
**no** markup or assets. Re-run to regenerate. Provenance / reproducible.
"""

from __future__ import annotations

from xavani_learner.style_learn import save_profile
from xavani_learner.style_profile import StyleProfile, packaged_library_dir

_DIR = packaged_library_dir()

_PROFILES: list[StyleProfile] = [
    StyleProfile(
        name="ref-apple-siri",
        title="Apple · Siri",
        inspiration="inspired by https://www.apple.com/siri/ (principles only; no assets copied)",
        tags=["minimal", "clarity", "premium", "product", "whitespace", "gradient", "scroll", "calm", "apple"],
        layout="centered product hero, one idea per viewport, scroll-reveal sections",
        typography="huge confident SF-style headings, tight hierarchy, sparse body",
        color="light canvas with a luminous multi-stop gradient as the signature accent",
        motion="fluid gradient/orb morphing, gentle scroll-tied reveals; smooth and premium",
        whitespace="vast; the product floats in space",
        imagery="photoreal device renders, glowing abstract gradients",
        feel=["calm", "premium", "precise", "magical"],
        avoid=["clutter", "stock photos", "dense text", "generic 3-card rows"],
    ),
    StyleProfile(
        name="ref-deriv",
        title="Deriv · Trading App",
        inspiration="inspired by https://app.deriv.com/ (principles only)",
        tags=["fintech", "trading", "dashboard", "data", "dense", "functional", "app", "charts"],
        layout="multi-panel trading workspace, persistent chart, scannable tables, clear primary CTAs",
        typography="compact legible UI sans, tabular figures for numbers",
        color="dark/neutral base with semantic gain/loss accents",
        motion="instant feedback, live tickers; flourish-free",
        whitespace="economical; information density with clear grouping",
        imagery="candlestick/line charts and data viz over photography",
        feel=["functional", "fast", "trustworthy", "pro"],
        avoid=["marketing fluff in-app", "huge empty hero", "decorative animation"],
    ),
    StyleProfile(
        name="ref-abetkaua",
        title="Abetka · Ukrainian Alphabet",
        inspiration="inspired by https://abetkaua.com/en/ (principles only)",
        tags=["illustration", "cultural", "playful", "editorial", "interactive", "vivid", "story", "educational"],
        layout="letter-by-letter interactive narrative, full-bleed illustrated scenes",
        typography="expressive display + a clean readable body for context",
        color="rich, warm, culturally-rooted palette; confident contrasts",
        motion="characterful hover/scroll animation tied to each illustration",
        whitespace="balanced around bold illustration",
        imagery="bespoke hand illustration as the hero; no stock",
        feel=["warm", "characterful", "meaningful", "crafted"],
        avoid=["generic grids", "stock imagery", "flat corporate minimalism"],
    ),
    StyleProfile(
        name="ref-b-egg",
        title="b-egg · Brand",
        inspiration="inspired by https://www.b-egg.farm/ (principles only)",
        tags=["playful", "brand", "colorful", "d2c", "friendly", "illustration", "vivid", "fun"],
        layout="characterful product-brand sections, organic shapes, lively rhythm",
        typography="expressive display paired with a friendly humanist body",
        color="vivid, appetising palette; bold confident combinations",
        motion="bouncy, delightful micro-interactions",
        whitespace="balanced with bold colour blocks",
        imagery="custom illustration, texture, characterful product shots",
        feel=["playful", "warm", "energetic", "human"],
        avoid=["corporate sterility", "grey-on-grey", "stocky minimalism"],
    ),
    StyleProfile(
        name="ref-mona-sans",
        title="Mona Sans · Type Specimen",
        inspiration="inspired by https://github.com/mona-sans (principles only)",
        tags=["typography", "type", "specimen", "variable-fonts", "monochrome", "bold", "minimal"],
        layout="type fills the canvas; interactive weight/width specimen controls",
        typography="the product IS the type — massive variable-font play",
        color="monochrome; the letters carry the design",
        motion="axis animation (weight/width), hover variation",
        whitespace="stark; glyphs breathe alone",
        imagery="none — pure type",
        feel=["bold", "precise", "expressive"],
        avoid=["busy backgrounds", "competing imagery", "decorative chrome"],
    ),
    StyleProfile(
        name="ref-ellipsus",
        title="Ellipsus · Writing",
        inspiration="inspired by https://ellipsus.com/ (principles only)",
        tags=["editorial", "writing", "calm", "literary", "soft", "reading", "minimal", "considered"],
        layout="reading-first, generous columns, gentle section rhythm",
        typography="refined serif/sans pairing, real typographic care",
        color="soft paper neutrals with a calm accent",
        motion="restrained; quiet text reveals",
        whitespace="generous margins, unhurried pacing",
        imagery="subtle, supportive; never loud",
        feel=["calm", "literary", "considered", "human"],
        avoid=["loud gradients", "dense dashboards", "gimmicky motion"],
    ),
    StyleProfile(
        name="ref-mode",
        title="Mode · Analytics",
        inspiration="inspired by https://mode.com/ (principles only)",
        tags=["data", "analytics", "saas", "clean", "professional", "dashboard", "b2b", "clarity"],
        layout="clear marketing hierarchy up top, confident product/data screenshots",
        typography="clean modern sans, strong hierarchy, legible at density",
        color="professional palette, restrained accent, plenty of light",
        motion="subtle, credible; supports comprehension",
        whitespace="comfortable; structured",
        imagery="real product UI + crisp data viz",
        feel=["clear", "professional", "credible", "modern"],
        avoid=["decorative fluff", "low-contrast text", "stock business photos"],
    ),
    StyleProfile(
        name="ref-lusion",
        title="Lusion · Immersive Studio",
        inspiration="inspired by https://lusion.co/ (principles only)",
        tags=["immersive", "webgl", "3d", "motion", "cinematic", "experimental", "agency", "award"],
        layout="full-bleed 3D scenes, scroll-choreographed, unexpected composition",
        typography="oversized display, dramatic scale contrast over motion",
        color="rich dark canvas with vivid, luminous accents",
        motion="signature WebGL/canvas physics + parallax; motion IS the brand",
        whitespace="negative space framing immersive scenes",
        imagery="bespoke 3D and shader work; nothing templated",
        feel=["immersive", "bold", "memorable", "crafted"],
        avoid=["static templates", "stock sliders", "safe centered layouts"],
    ),
    StyleProfile(
        name="ref-message-to-ukraine",
        title="The Message to Ukraine · Obys",
        inspiration="inspired by https://themessagetoukraine.obys.agency/ (principles only)",
        tags=["immersive", "editorial", "cause", "dramatic", "motion", "typography", "story", "award"],
        layout="cinematic editorial scenes, scroll-driven narrative, dramatic full-bleed type",
        typography="huge emotive display type as a storytelling device",
        color="high-contrast, restrained palette with charged accents",
        motion="bold scroll choreography, transitions that carry meaning",
        whitespace="dramatic pauses between beats",
        imagery="documentary-grade photography, full-bleed",
        feel=["emotive", "cinematic", "purposeful", "crafted"],
        avoid=["generic card grids", "safe centered hero", "decorative-only motion"],
    ),
    StyleProfile(
        name="ref-diko",
        title="Diko · Brand Experimental",
        inspiration="inspired by https://www.diko.co/ (principles only)",
        tags=["experimental", "brand", "bold", "playful", "high-contrast", "characterful", "unconventional"],
        layout="confident asymmetry, bold blocks, intentional tension",
        typography="characterful grotesk/display, oversized and brave",
        color="bold, high-contrast brand palette",
        motion="snappy, characterful interactions",
        whitespace="used for impact, not safety",
        imagery="distinctive brand art direction; no stock",
        feel=["bold", "characterful", "modern", "memorable"],
        avoid=["predictable SaaS template", "muted grey minimalism", "centered everything"],
    ),
    StyleProfile(
        name="ref-ventriloc",
        title="Ventriloc · Studio",
        inspiration="inspired by https://ventriloc.ca/en/ (principles only)",
        tags=["agency", "editorial", "motion", "portfolio", "crafted", "bold", "typography"],
        layout="editorial grid meets motion; strong case-study storytelling",
        typography="expressive display + disciplined body; confident hierarchy",
        color="refined palette with a punchy accent",
        motion="smooth, crafted transitions and hovers",
        whitespace="generous and intentional",
        imagery="high-craft project visuals, full-bleed",
        feel=["crafted", "confident", "modern", "polished"],
        avoid=["template portfolios", "generic card grids", "stock photography"],
    ),
    # --- principles distilled from the eleken "best website design examples" collection ---
    StyleProfile(
        name="principle-bold-typography",
        title="Principle · Bold Typography",
        inspiration="distilled from the eleken 'best website design examples' collection",
        tags=["typography", "bold", "headline", "editorial", "impact", "minimal"],
        layout="type-led layouts, oversized headlines as the primary visual",
        typography="huge, confident, characterful headlines; tight pairing with body",
        color="restrained so type leads",
        motion="text reveals, weight shifts",
        whitespace="generous around big type",
        imagery="secondary to type",
        feel=["bold", "confident", "modern"],
        avoid=["thin generic sans everywhere", "tiny timid headings"],
    ),
    StyleProfile(
        name="principle-whitespace-luxury",
        title="Principle · Whitespace as Luxury",
        inspiration="distilled from the eleken 'best website design examples' collection",
        tags=["whitespace", "minimal", "premium", "calm", "clarity", "luxury"],
        layout="few elements per view, strong focal point, breathing room everywhere",
        typography="refined, restrained, high hierarchy",
        color="light, quiet, one accent",
        motion="subtle, unhurried",
        whitespace="the design IS the whitespace",
        imagery="few, high-quality",
        feel=["calm", "premium", "considered"],
        avoid=["clutter", "wall-to-wall content", "default framework spacing"],
    ),
    StyleProfile(
        name="principle-micro-interaction-delight",
        title="Principle · Micro-interaction Delight",
        inspiration="distilled from the eleken 'best website design examples' collection",
        tags=["micro-interaction", "motion", "delight", "playful", "feedback", "polish"],
        layout="ordinary layouts elevated by considered interaction",
        typography="clear, supportive",
        color="brand-led with lively accents",
        motion="purposeful hover/click/scroll micro-interactions that delight and inform",
        whitespace="balanced",
        imagery="supports interaction",
        feel=["delightful", "polished", "responsive"],
        avoid=["janky motion", "decoration-only animation", "no feedback states"],
    ),
    StyleProfile(
        name="principle-dark-elegance",
        title="Principle · Dark Elegance",
        inspiration="distilled from the eleken 'best website design examples' collection",
        tags=["dark", "elegant", "premium", "contrast", "moody", "modern"],
        layout="confident dark canvas, glowing focal points, strong hierarchy",
        typography="crisp, high-contrast on dark; refined",
        color="deep dark base with luminous, restrained accents",
        motion="smooth, premium reveals",
        whitespace="dark space as breathing room",
        imagery="high-contrast, cinematic",
        feel=["elegant", "premium", "moody", "modern"],
        avoid=["muddy low-contrast dark", "neon overload", "pure-black flat boxes"],
    ),
]


def main() -> None:
    _DIR.mkdir(parents=True, exist_ok=True)
    for profile in _PROFILES:
        path = save_profile(profile, save_dir=_DIR)
        print(f"wrote {path.name}")
    print(f"\n{len(_PROFILES)} reference profiles written to {_DIR}")


if __name__ == "__main__":
    main()
