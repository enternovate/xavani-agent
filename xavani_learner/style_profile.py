# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Design style profiles + deterministic selector (v0.7.0 operator L1–L3).

A :class:`StyleProfile` is the agent's *learned design direction* — distilled
**design DNA** (layout, typography, colour, motion, whitespace, the "feel"), plus
an ``avoid`` list that keeps output away from generic/template-y looks. Profiles
set direction; they never replace the agent's creativity, and they are
**inspiration-attributed, never copies** (L12): no verbatim assets or markup, only
the principles a great designer would internalise.

The seed library below is curated from exemplary sites the user referenced
(clarity/precision, immersive motion, fintech density, playful brand, editorial,
type specimen, scroll-narrative, brutalist-experimental). Users teach more via
``xavani learn`` (saved as YAML and merged in).

``select_styles`` ranks profiles for a brief by keyword/tag overlap — **pure
Python, zero model calls** (R10): learn once, then choose deterministically.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml


@dataclass
class StyleProfile:
    """A reusable, inspiration-attributed design direction."""

    name: str
    title: str = ""
    inspiration: str = ""           # attribution — the vibe, never a copy
    tags: list[str] = field(default_factory=list)
    layout: str = ""
    typography: str = ""
    color: str = ""
    motion: str = ""
    whitespace: str = ""
    imagery: str = ""
    feel: list[str] = field(default_factory=list)
    avoid: list[str] = field(default_factory=list)
    notes: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "StyleProfile":
        fields = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in fields})

    def search_terms(self) -> set[str]:
        """Lowercased tokens used for deterministic selection."""
        text = " ".join([self.name, self.title, " ".join(self.tags), " ".join(self.feel)])
        return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t}


# --- Curated seed library (inspiration-attributed; not copies) ---------------
_SEED: list[StyleProfile] = [
    StyleProfile(
        name="clarity-precision",
        title="Clarity & Precision",
        inspiration="the calm restraint and product-first clarity of Apple-style pages",
        tags=["minimal", "clarity", "whitespace", "saas", "product", "calm", "precise", "clean"],
        layout="generous whitespace, strong centered product hero, few elements per view",
        typography="large confident headings, tight hierarchy, one refined sans family",
        color="near-monochrome with one restrained accent",
        motion="subtle, purposeful reveals on scroll; nothing decorative",
        whitespace="abundant; breathing room is the design",
        imagery="high-fidelity product shots, no stock photos",
        feel=["calm", "precise", "premium", "trustworthy"],
        avoid=["clutter", "stock photos", "generic 3-card rows", "default framework spacing"],
    ),
    StyleProfile(
        name="immersive-motion",
        title="Immersive Motion",
        inspiration="the cinematic, experimental motion of award-winning agency/portfolio sites",
        tags=["immersive", "motion", "webgl", "cinematic", "experimental", "bold", "agency", "portfolio"],
        layout="full-bleed scenes, scroll-driven choreography, unexpected composition",
        typography="oversized display type, dramatic scale contrast",
        color="rich, high-contrast, often dark with vivid accents",
        motion="signature: physics, parallax, WebGL/canvas; motion IS the brand",
        whitespace="intentional negative space framing motion",
        imagery="bespoke 3D/animation, no templates",
        feel=["immersive", "bold", "memorable", "crafted"],
        avoid=["static templates", "stock sliders", "safe centered layouts"],
    ),
    StyleProfile(
        name="fintech-density",
        title="Functional Density",
        inspiration="the information-dense, hierarchy-clear feel of pro fintech/data dashboards",
        tags=["fintech", "data", "dashboard", "dense", "functional", "trading", "finance", "app"],
        layout="dense but ordered grids, clear primary actions, scannable tables/charts",
        typography="compact, legible, numeric-friendly; tabular figures",
        color="neutral base, semantic status colours (gain/loss)",
        motion="minimal; instant feedback over flourish",
        whitespace="economical, every pixel earns its place",
        imagery="charts and data viz over photography",
        feel=["functional", "trustworthy", "fast", "serious"],
        avoid=["decorative fluff", "huge hero with no data", "marketing fluff in-app"],
    ),
    StyleProfile(
        name="playful-brand",
        title="Playful Brand",
        inspiration="the vivid, characterful warmth of friendly D2C/brand sites",
        tags=["playful", "colorful", "brand", "friendly", "illustration", "vivid", "fun", "warm"],
        layout="characterful sections, organic shapes, lively asymmetry",
        typography="expressive display type paired with a friendly body",
        color="vivid, confident palette; bold combinations",
        motion="bouncy, delightful micro-interactions",
        whitespace="balanced with bold color blocks",
        imagery="custom illustration, characters, texture",
        feel=["playful", "warm", "energetic", "human"],
        avoid=["corporate sterility", "grey-on-grey", "stocky minimalism"],
    ),
    StyleProfile(
        name="editorial",
        title="Editorial",
        inspiration="typography-led, reading-first editorial and cause-driven sites",
        tags=["editorial", "typography", "reading", "magazine", "asymmetric", "content", "longform", "story"],
        layout="asymmetric editorial grid, strong baseline rhythm, pull quotes",
        typography="serif/sans pairing, expressive headlines, real typographic care",
        color="paper-like neutrals with one ink accent",
        motion="restrained; text reveals, not gimmicks",
        whitespace="generous margins, column discipline",
        imagery="photo-essay quality, full-bleed plates",
        feel=["literary", "considered", "human", "timeless"],
        avoid=["generic card grids", "centered marketing blocks", "thin generic sans everywhere"],
    ),
    StyleProfile(
        name="type-specimen",
        title="Type Specimen",
        inspiration="type-as-hero specimen pages (e.g. open-source variable-font showcases)",
        tags=["typography", "type", "specimen", "monochrome", "variable-fonts", "minimal", "bold"],
        layout="type fills the canvas; interactive specimen controls",
        typography="the product IS the type; massive variable-font play",
        color="monochrome, the letters do the talking",
        motion="weight/width axis animation, hover variation",
        whitespace="stark; the type breathes alone",
        imagery="none — glyphs only",
        feel=["bold", "precise", "expressive"],
        avoid=["busy backgrounds", "competing imagery", "decorative chrome"],
    ),
    StyleProfile(
        name="product-story",
        title="Scroll Narrative",
        inspiration="scroll-driven product storytelling that reveals a feature step by step",
        tags=["scroll", "narrative", "story", "product", "sticky", "marketing", "launch", "feature"],
        layout="sticky scenes, pinned visuals, sequential reveals",
        typography="clear section headlines guiding the story",
        color="brand-led, shifting per chapter",
        motion="scroll-tied transitions, sticky pinning, step reveals",
        whitespace="deliberate pauses between beats",
        imagery="device/feature mockups animated in sequence",
        feel=["guided", "polished", "convincing"],
        avoid=["wall-of-text", "everything-above-the-fold", "static feature lists"],
    ),
    StyleProfile(
        name="brutalist-experimental",
        title="Brutalist / Experimental",
        inspiration="raw, high-contrast, unconventional 'ugly-beautiful' experimental design",
        tags=["brutalist", "raw", "high-contrast", "experimental", "unconventional", "bold", "edgy"],
        layout="broken grids, overlap, intentional tension",
        typography="monospace/grotesk, oversized, raw",
        color="stark high contrast, occasional jarring accent",
        motion="abrupt, glitchy, deliberate",
        whitespace="uneven by design",
        imagery="raw scans, noise, unpolished texture",
        feel=["edgy", "memorable", "anti-corporate"],
        avoid=["safe centered hero", "rounded-soft everything", "predictable SaaS template"],
    ),
    StyleProfile(
        name="claude-craft",
        title="Claude Design Craft",
        inspiration="design principles distilled from Claude's pptx / canvas-design / frontend-design "
        "skills: clarity, strong hierarchy, restraint, accessible contrast",
        tags=["presentation", "slides", "pptx", "deck", "clarity", "hierarchy", "accessible",
              "polished", "ui", "report", "document", "dashboard"],
        layout="content-first; one idea per slide/section; disciplined grid and alignment; clear focal point",
        typography="confident type scale, limited families, real hierarchy (display/heading/body), generous line-height",
        color="restrained, intentional palette with sufficient (accessible) contrast",
        motion="purposeful and minimal; supports comprehension, never decoration",
        whitespace="generous and deliberate; whitespace as structure",
        imagery="meaningful diagrams/charts over decoration; one consistent icon/illustration system",
        feel=["clear", "polished", "intentional", "credible"],
        avoid=["dense bullet walls", "clashing fonts", "low-contrast text", "clip-art", "default template chrome"],
    ),
]


def _xavani_home() -> Path:
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home()
    except Exception:
        import os

        return Path(os.path.expanduser("~/.xavani"))


def default_library_dir() -> Path:
    """Where user-learned profiles live: ``<xavani-home>/learner/style_library``."""
    return _xavani_home() / "learner" / "style_library"


def packaged_library_dir() -> Path:
    """Shipped reference profiles distilled from exemplary sites (package data)."""
    return Path(__file__).resolve().parent / "style_library"


def _load_yaml_profiles(directory: Path, profiles: list[StyleProfile], seen: set[str]) -> None:
    if not directory.exists():
        return
    for path in sorted(directory.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError:
            continue
        if isinstance(data, dict) and data.get("name") and data["name"] not in seen:
            profiles.append(StyleProfile.from_dict(data))
            seen.add(data["name"])


def load_style_library(extra_dir: str | Path | None = None) -> list[StyleProfile]:
    """Return the in-code seed + shipped reference profiles + user-learned profiles."""
    profiles = list(_SEED)
    seen = {p.name for p in profiles}
    _load_yaml_profiles(packaged_library_dir(), profiles, seen)
    user_dir = Path(extra_dir) if extra_dir is not None else default_library_dir()
    _load_yaml_profiles(user_dir, profiles, seen)
    return profiles


def select_styles(brief: str, profiles: list[StyleProfile]) -> list[tuple[StyleProfile, int]]:
    """Rank profiles for ``brief`` by term overlap (score desc, then name). Deterministic."""
    tokens = {t for t in re.split(r"[^a-z0-9]+", brief.lower()) if t}
    scored = [(p, len(tokens & p.search_terms())) for p in profiles]
    scored.sort(key=lambda ps: (-ps[1], ps[0].name))
    return scored


def best_style(brief: str, profiles: list[StyleProfile]) -> StyleProfile | None:
    """The single best-matching profile for ``brief``, or ``None`` if the library is empty."""
    ranked = select_styles(brief, profiles)
    return ranked[0][0] if ranked else None
