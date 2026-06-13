# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Wisdom patterns — the ascent/downfall corpus + deterministic matcher (v1.0.0 ②).

A :class:`WisdomPattern` is one distilled lesson: *what someone did, the small
observable signal, and the lesson* — for both **ascent** (how the great rose) and
**downfall** (what made them fall after doing well). Patterns are
**inspiration-attributed**: we store the lesson and a source attribution, never
copyrighted text.

The seed library below is curated (Solomon, Bezos, Buffett, plus failure
archetypes). Users/agents add more as YAML under the packaged ``corpus/`` dir or
``<xavani-home>/wisdom/corpus/`` — merged in by :func:`load_corpus`.

:func:`match` ranks patterns against a piece of text by token/signal/keyword
overlap — **pure Python, zero model calls** (R10), mirroring
``xavani_learner.style_profile.select_styles``.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

# Common English stopwords stripped before matching, so corpus prose (full
# sentences in ``the_signal``) and ordinary query text don't produce spurious
# overlaps on words like "the"/"and"/"we". Keeps :func:`match` meaningful.
_STOP: frozenset[str] = frozenset(
    {
        "a", "an", "the", "and", "or", "but", "for", "to", "of", "in", "on", "at",
        "by", "we", "you", "our", "us", "it", "is", "are", "be", "was", "were",
        "that", "this", "these", "those", "with", "as", "from", "into", "onto",
        "your", "their", "they", "i", "me", "my", "so", "do", "not", "no", "can",
        "will", "would", "should", "let", "lets", "s", "t", "re", "ll", "ve", "if",
        "then", "than", "out", "up", "down", "over", "all", "any", "each", "more",
        "most", "some", "such", "own", "too", "very", "just", "now", "here", "there",
    }
)


@dataclass
class WisdomPattern:
    """One distilled lesson of ascent or downfall (attributed, never a copy)."""

    id: str
    kind: str = "downfall"  # "ascent" | "downfall"
    figure: str = ""
    domain: str = ""  # leadership | finance | product | ethics | ops
    era: str = ""  # free text, e.g. "c. 970-931 BC" (not a parsed date)
    what_they_did: str = ""
    the_signal: list[str] = field(default_factory=list)
    the_lesson: str = ""
    signals: list[str] = field(default_factory=list)  # detector signal tags
    keywords: list[str] = field(default_factory=list)  # detector keyword hints
    sources: list[str] = field(default_factory=list)  # attribution only

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WisdomPattern":
        fields = set(cls.__dataclass_fields__)
        return cls(**{k: v for k, v in d.items() if k in fields})

    def search_terms(self) -> set[str]:
        """Lowercased tokens used for deterministic matching."""
        text = " ".join(
            [
                self.id,
                self.figure,
                self.domain,
                " ".join(self.the_signal),
                " ".join(self.signals),
                " ".join(self.keywords),
            ]
        )
        return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _STOP}


# --- Curated seed library (inspiration-attributed; not copies) ---------------
_SEED: list[WisdomPattern] = [
    # ----- Ascent: how the great rose -----
    WisdomPattern(
        id="solomon-ascent-wisdom",
        kind="ascent",
        figure="King Solomon",
        domain="leadership",
        era="c. 970-931 BC",
        what_they_did="Asked for wisdom over riches; judged justly; built trade alliances and prosperity.",
        the_signal=["optimize for judgment, not vanity", "ask for the right thing", "fair dealing builds trust"],
        the_lesson="Sound judgment compounds; reputation for fairness opens doors money cannot.",
        signals=["judgment", "fairness", "long_term"],
        keywords=["wisdom", "judgment", "justice", "trust", "alliance"],
        sources=["Kings", "Chronicles"],
    ),
    WisdomPattern(
        id="bezos-ascent-day1",
        kind="ascent",
        figure="Jeff Bezos",
        domain="product",
        era="1994-present",
        what_they_did="Customer obsession, long time horizons, 'Day 1' mindset, regret-minimization.",
        the_signal=["work backwards from the customer", "optimize lifetime not quarter", "stay Day 1"],
        the_lesson="Customer-obsessed, long-horizon bets beat competitor-obsessed short-term optimization.",
        signals=["customer_obsession", "long_term", "experiment"],
        keywords=["customer", "long term", "invent", "patient", "regret"],
        sources=["Amazon shareholder letters"],
    ),
    WisdomPattern(
        id="buffett-ascent-moat",
        kind="ascent",
        figure="Warren Buffett",
        domain="finance",
        era="1956-present",
        what_they_did="Circle of competence, margin of safety, durable moats, patience, reputation.",
        the_signal=["stay in your circle of competence", "demand a margin of safety", "let it compound"],
        the_lesson="Avoiding ruin and compounding patiently beats chasing every opportunity.",
        signals=["margin_of_safety", "competence", "patience", "long_term"],
        keywords=["moat", "margin of safety", "compound", "patient", "competence", "reputation"],
        sources=["Berkshire Hathaway letters"],
    ),
    # ----- Downfall: what made them fall after doing well -----
    WisdomPattern(
        id="solomon-downfall-overreach",
        kind="downfall",
        figure="King Solomon",
        domain="leadership",
        era="c. 970-931 BC",
        what_they_did=(
            "At the peak — wealth and wisdom — turned to heavy forced labour, crushing taxation, "
            "and foreign cults; drifted from the principles that earned the rise."
        ),
        the_signal=[
            "success funding ever-larger commitments (overextension)",
            "burden shifted onto the base that made you",
            "drifting from the principles that earned the rise",
        ],
        the_lesson="Peak success is when overreach and principle-drift are most dangerous; the bill comes due later (the kingdom split under Rehoboam, after his death).",
        signals=["overextension", "base_burden", "principle_drift", "succession_gap"],
        keywords=["expand", "scale fast", "raise more", "defer cost", "ignore base", "tax", "heavier"],
        sources=["Kings", "Chronicles"],
    ),
    WisdomPattern(
        id="kodak-downfall-disruption-denial",
        kind="downfall",
        figure="Kodak",
        domain="product",
        era="1990s-2012",
        what_they_did="Invented the digital camera, then protected the film cash-cow instead of cannibalizing it.",
        the_signal=["protecting the cash cow against the future", "denying a disruption you can see"],
        the_lesson="The thing paying the bills today blinds you to the thing that ends you tomorrow.",
        signals=["disruption_denial", "incumbent_inertia", "principle_drift"],
        keywords=["protect", "cash cow", "legacy", "cannibalize", "ignore", "later"],
        sources=["Kodak bankruptcy case studies"],
    ),
    WisdomPattern(
        id="lehman-downfall-leverage",
        kind="downfall",
        figure="Lehman Brothers / LTCM",
        domain="finance",
        era="1998 / 2008",
        what_they_did="Stacked enormous leverage on models that assumed the tails wouldn't arrive.",
        the_signal=["winning streak funding bigger leverage", "no margin of safety for the tail"],
        the_lesson="Leverage turns a survivable mistake into ruin; survival first, returns second.",
        signals=["leverage", "tail_blindness", "no_margin_of_safety"],
        keywords=["leverage", "borrow", "debt", "take on debt", "leverage up", "all in", "bet big", "guarantee", "cannot lose"],
        sources=["financial-crisis post-mortems"],
    ),
    WisdomPattern(
        id="enron-downfall-fraud",
        kind="downfall",
        figure="Enron / Theranos",
        domain="ethics",
        era="2001 / 2018",
        what_they_did="Manufactured the metrics; hid reality behind theatre until it collapsed at once.",
        the_signal=["the number must look good at any cost", "hide the bad news", "metric theatre"],
        the_lesson="Lying to the scoreboard guarantees a sudden, total collapse; truth early is cheap.",
        signals=["fraud", "metric_theatre", "hidden_reality", "ethics_redflag"],
        keywords=["hide", "fake", "inflate", "cover up", "mislead", "at any cost"],
        sources=["Enron / Theranos case studies"],
    ),
    WisdomPattern(
        id="wework-downfall-founder-excess",
        kind="downfall",
        figure="WeWork",
        domain="leadership",
        era="2019",
        what_they_did="Story-driven over-expansion, weak governance, founder excess, no path to profit.",
        the_signal=["narrative outrunning the numbers", "no check on the founder", "growth before unit economics"],
        the_lesson="When the story outruns the economics and no one can say 'no', the correction is brutal.",
        signals=["overextension", "governance_gap", "narrative_over_numbers", "succession_gap"],
        keywords=["blitzscale", "story", "vision", "grow at all costs", "no governance"],
        sources=["WeWork S-1 / collapse coverage"],
    ),
    WisdomPattern(
        id="icarus-downfall-hubris",
        kind="downfall",
        figure="Icarus (archetype)",
        domain="leadership",
        era="myth",
        what_they_did="Given working wings, ignored the warning and flew too high; the wax melted.",
        the_signal=["ignoring the explicit warning", "early success breeding invincibility"],
        the_lesson="Hubris after early success is the classic killer; respect the constraints that got you airborne.",
        signals=["hubris", "ignore_warning", "overconfidence"],
        keywords=["nothing can stop", "this time is different", "ignore the risk", "too cautious"],
        sources=["Greek myth (archetype)"],
    ),
]


def _xavani_home() -> Path:
    try:
        from xavani_constants import get_xavani_home

        return get_xavani_home()
    except Exception:  # pragma: no cover - fallback only
        import os

        return Path(os.path.expanduser("~/.xavani"))


def packaged_corpus_dir() -> Path:
    """Shipped corpus directory (package data): ``xavani_wisdom/corpus/``."""
    return Path(__file__).resolve().parent / "corpus"


def default_corpus_dir() -> Path:
    """User-added corpus: ``<xavani-home>/wisdom/corpus``."""
    return _xavani_home() / "wisdom" / "corpus"


def _load_yaml_dir(directory: Path, patterns: list[WisdomPattern], seen: set[str]) -> None:
    if not directory.exists():
        return
    # Recurse so corpus/ascent/*.yaml and corpus/downfall/*.yaml both load.
    for path in sorted(directory.rglob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except (yaml.YAMLError, OSError):
            continue
        if isinstance(data, dict) and data.get("id") and data["id"] not in seen:
            patterns.append(WisdomPattern.from_dict(data))
            seen.add(data["id"])


def load_corpus(extra_dir: str | Path | None = None) -> list[WisdomPattern]:
    """Return the in-code seed + shipped corpus + user-added patterns (deduped by id)."""
    patterns = list(_SEED)
    seen = {p.id for p in patterns}
    _load_yaml_dir(packaged_corpus_dir(), patterns, seen)
    user_dir = Path(extra_dir) if extra_dir is not None else default_corpus_dir()
    _load_yaml_dir(user_dir, patterns, seen)
    return patterns


def _tokens(text: str) -> set[str]:
    return {t for t in re.split(r"[^a-z0-9]+", text.lower()) if t and t not in _STOP}


def match(
    text: str,
    patterns: list[WisdomPattern] | None = None,
    *,
    kind: str | None = None,
) -> list[tuple[WisdomPattern, int]]:
    """Rank patterns for ``text`` by term/keyword overlap (score desc, then id).

    Deterministic and zero-LLM. ``kind`` filters to "ascent" or "downfall".
    Multi-word keyword phrases (e.g. "cash cow") are matched as substrings so a
    phrase counts even when its tokens are split.
    """
    if patterns is None:
        patterns = load_corpus()
    if kind is not None:
        patterns = [p for p in patterns if p.kind == kind]
    toks = _tokens(text)
    low = text.lower()
    scored: list[tuple[WisdomPattern, int]] = []
    for p in patterns:
        score = len(toks & p.search_terms())
        # Multi-word keyword phrases (e.g. "all in", "cash cow", "at any cost") are
        # deliberate, high-signal tells — worth 2, so one concise phrase clears the
        # downfall threshold while single incidental words still need a second hit.
        score += sum(2 for kw in p.keywords if " " in kw and kw.lower() in low)
        scored.append((p, score))
    scored.sort(key=lambda ps: (-ps[1], ps[0].id))
    return scored
