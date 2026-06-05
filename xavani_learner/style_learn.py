# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Learn intake: distil a StyleProfile from a reference (v0.7.0 operator L5/L6).

``xavani learn <url|file|text>`` flows through here. Distillation is **learn once,
reuse deterministically** (R10): the model is an *injected* ``extract`` callable
(the CLI wires the real LLM; tests/offline use a heuristic keyword distiller), and
network is an *injected* ``fetch``. The result is saved as a YAML
:class:`StyleProfile` in the library so ``select_styles`` can reuse it forever.

Copyright-safe (L12): we distil *principles* and **attribute** the source — never
copy verbatim markup or assets.
"""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import Any, Callable

import yaml

from xavani_learner.style_profile import StyleProfile, default_library_dir

_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you", "are", "but",
    "not", "have", "has", "was", "were", "will", "can", "all", "our", "their", "they",
    "more", "most", "some", "into", "over", "https", "http", "www", "com", "page",
    "site", "website", "design", "designs", "designed", "content", "section", "sections",
    # common web chrome / boilerplate — not design signal
    "browser", "javascript", "support", "does", "enable", "enabled", "cookies", "cookie",
    "accept", "menu", "skip", "loading", "please", "toggle", "navigation", "close", "open",
    "click", "scroll", "home", "contact", "about", "privacy", "terms", "copyright",
    "reserved", "rights", "here", "learn", "read", "view", "using", "use",
}


def _slug(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s or "learned"


def _slug_from_url(url: str) -> str:
    core = re.sub(r"^https?://", "", url.lower())
    core = core.split("?")[0].rstrip("/")
    return _slug(core)[:48] or "learned"


def _keywords(text: str, k: int = 12) -> list[str]:
    words = re.findall(r"[a-z]{4,}", text.lower())
    freq = Counter(w for w in words if w not in _STOPWORDS)
    return [w for w, _ in freq.most_common(k)]


def distill_profile(
    text: str,
    name: str,
    *,
    extract: Callable[[str], dict] | None = None,
    inspiration: str | None = None,
) -> StyleProfile:
    """Turn reference ``text`` into a :class:`StyleProfile`.

    With an injected ``extract`` (LLM) it uses the returned field dict; otherwise it
    falls back to a deterministic keyword distillation.
    """
    if extract is not None:
        data = dict(extract(text) or {})
        data.setdefault("name", name)
        data.setdefault("inspiration", inspiration or f"learned from {name}")
        return StyleProfile.from_dict(data)
    return StyleProfile(
        name=name,
        title=name.replace("-", " ").title(),
        inspiration=inspiration or f"learned from {name} (principles only)",
        tags=_keywords(text),
        avoid=["generic templates", "default framework chrome"],
        notes="distilled heuristically; refine with an LLM extractor for richer detail",
    )


def save_profile(profile: StyleProfile, save_dir: str | Path | None = None) -> Path:
    """Persist a profile as YAML in the style library; return its path."""
    d = Path(save_dir) if save_dir is not None else default_library_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{profile.name}.yaml"
    path.write_text(yaml.safe_dump(profile.to_dict(), sort_keys=False, allow_unicode=True), encoding="utf-8")
    return path


def learn_text(
    text: str,
    name: str,
    *,
    extract: Callable[[str], dict] | None = None,
    save_dir: str | Path | None = None,
    inspiration: str | None = None,
) -> StyleProfile:
    """Distil + save a profile from raw text."""
    profile = distill_profile(text, name, extract=extract, inspiration=inspiration)
    save_profile(profile, save_dir)
    return profile


def learn_file(
    path: str | Path,
    *,
    extract: Callable[[str], dict] | None = None,
    save_dir: str | Path | None = None,
) -> StyleProfile:
    """Distil + save a profile from a local file."""
    p = Path(path)
    text = p.read_text(encoding="utf-8", errors="ignore")
    return learn_text(
        text, _slug(p.stem), extract=extract, save_dir=save_dir,
        inspiration=f"learned from file {p.name} (principles only)",
    )


def learn_url(
    url: str,
    *,
    fetch: Callable[[str], str],
    extract: Callable[[str], dict] | None = None,
    save_dir: str | Path | None = None,
) -> StyleProfile:
    """Distil + save a profile from a URL using an injected ``fetch``."""
    text = fetch(url)
    return learn_text(
        text, _slug_from_url(url), extract=extract, save_dir=save_dir,
        inspiration=f"inspired by {url} (principles only — no assets or markup copied)",
    )
