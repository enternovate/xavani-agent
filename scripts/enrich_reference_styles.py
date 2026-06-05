# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Enrich shipped reference profiles with live-observed signals (v0.7.0 operator L5).

Fetches each reference site and merges *observed* signals (title, description,
headings, salient keywords) into the existing hand-distilled
:class:`StyleProfile` — deepening it without losing the curated craft fields and
without copying markup or assets (only short, factual metadata in ``notes``).

Graceful: a site that blocks bots or times out keeps its curated profile.
Run: ``PYTHONPATH=. python3 scripts/enrich_reference_styles.py``
"""

from __future__ import annotations

import re
import urllib.request

import yaml

from xavani_learner.style_learn import _keywords, save_profile
from xavani_learner.style_profile import StyleProfile, packaged_library_dir

SITES = {
    "ref-apple-siri": "https://www.apple.com/siri/",
    "ref-deriv": "https://app.deriv.com/",
    "ref-abetkaua": "https://abetkaua.com/en/",
    "ref-b-egg": "https://www.b-egg.farm/",
    "ref-mona-sans": "https://github.com/mona-sans",
    "ref-ellipsus": "https://ellipsus.com/",
    "ref-mode": "https://mode.com/",
    "ref-lusion": "https://lusion.co/",
    "ref-message-to-ukraine": "https://themessagetoukraine.obys.agency/",
    "ref-diko": "https://www.diko.co/",
    "ref-ventriloc": "https://ventriloc.ca/en/",
}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s or "")).strip()


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (xavani-learn/0.7)"})
    with urllib.request.urlopen(req, timeout=15) as resp:  # noqa: S310
        return resp.read().decode("utf-8", "ignore")


def _signals(html: str) -> dict:
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    desc = re.search(
        r'<meta[^>]+name=["\']description["\'][^>]+content=["\'](.*?)["\']', html, re.S | re.I
    )
    heads = re.findall(r"<h[12][^>]*>(.*?)</h[12]>", html, re.S | re.I)
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return {
        "title": _clean(title.group(1)) if title else "",
        "desc": _clean(desc.group(1)) if desc else "",
        "headings": [_clean(h) for h in heads[:4] if _clean(h)],
        "keywords": _keywords(text, 8),
    }


def enrich(name: str, url: str) -> str:
    path = packaged_library_dir() / f"{name}.yaml"
    profile = StyleProfile.from_dict(yaml.safe_load(path.read_text(encoding="utf-8")))
    try:
        sig = _signals(_fetch(url))
    except Exception as exc:  # blocked / timeout / parse — keep curated profile
        return f"  {name}: fetch failed ({type(exc).__name__}) — kept curated"
    extra = [k for k in sig["keywords"] if k not in profile.tags][:6]
    profile.tags = list(dict.fromkeys(profile.tags + extra))
    observed = sig["title"]
    if sig["desc"]:
        observed += f" — {sig['desc']}"
    profile.notes = f"observed via live fetch: {observed}".strip()[:240]
    save_profile(profile, save_dir=packaged_library_dir())
    return f"  {name}: +{len(extra)} tags · '{sig['title'][:48]}'"


def main() -> None:
    print("Enriching reference profiles from live fetches:")
    for name, url in SITES.items():
        print(enrich(name, url))


if __name__ == "__main__":
    main()
