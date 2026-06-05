# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""CLI dispatch for `xavani learn` (v0.7.0 operator L10).

Lets the user *teach* Xavani on demand — "learn this site", "learn from this
file", "I prefer X" — and inspect what it has learned. Heavy logic lives in
``style_learn`` / ``preferences`` / ``style_profile``; this stays import-light.

``learn url`` fetches with a small stdlib fetcher and distils **principles**
(attributed, no assets copied). An LLM extractor can be wired in for richer
profiles; the deterministic heuristic is the always-available default.
"""

from __future__ import annotations

import re
from typing import Any


def cmd_learn(args: Any) -> None:
    """Dispatch a ``xavani learn <subcommand>`` invocation."""
    command = getattr(args, "learn_command", None)
    handler = {
        "url": _learn_url,
        "file": _learn_file,
        "pref": _learn_pref,
        "preference": _learn_pref,
        "list": _learn_list,
        "show": _learn_show,
    }.get(command)
    if handler is None:
        _usage()
    else:
        handler(args)


def _fetch_url(url: str) -> str:
    import urllib.request

    req = urllib.request.Request(url, headers={"User-Agent": "xavani-learn/0.7"})
    with urllib.request.urlopen(req, timeout=20) as resp:  # noqa: S310 (user-initiated)
        raw = resp.read().decode("utf-8", "ignore")
    raw = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", raw, flags=re.S | re.I)
    text = re.sub(r"<[^>]+>", " ", raw)
    return re.sub(r"\s+", " ", text)[:20000]


def _learn_url(args: Any) -> None:
    from xavani_learner.style_learn import learn_url

    url = getattr(args, "target", None)
    if not url:
        print("Usage: xavani learn url <url>")
        return
    try:
        profile = learn_url(url, fetch=_fetch_url)
    except Exception as exc:  # network/parse issues shouldn't crash the CLI
        print(f"✗ could not learn {url}: {exc}")
        return
    print(f"✓ Learned '{profile.name}' from {url}")
    print(f"  tags: {', '.join(profile.tags[:10])}")
    print("  (inspiration-attributed; principles only — no assets copied)")


def _learn_file(args: Any) -> None:
    from pathlib import Path

    from xavani_learner.style_learn import learn_file

    target = getattr(args, "target", None)
    if not target or not Path(target).exists():
        print(f"No such file: {target}")
        return
    profile = learn_file(target)
    print(f"✓ Learned '{profile.name}' from {Path(target).name}")
    print(f"  tags: {', '.join(profile.tags[:10])}")


def _learn_pref(args: Any) -> None:
    from xavani_learner.preferences import PreferenceStore
    from xavani_operator.state import OperatorState

    text = getattr(args, "target", None)
    if not text:
        print('Usage: xavani learn pref "I prefer ..."')
        return
    PreferenceStore(OperatorState()).record(text)
    print(f"✓ Noted preference: {text}")


def _learn_list(args: Any) -> None:
    from xavani_learner.preferences import PreferenceStore
    from xavani_learner.style_profile import load_style_library
    from xavani_operator.state import OperatorState

    print("Learned style profiles:")
    for p in load_style_library():
        print(f"  {p.name} — {p.title}")
    prefs = PreferenceStore(OperatorState()).recall()
    if prefs:
        print("Preferences:")
        for text in prefs:
            print(f"  • {text}")


def _learn_show(args: Any) -> None:
    from xavani_learner.style_profile import load_style_library

    name = getattr(args, "target", None)
    profile = next((p for p in load_style_library() if p.name == name), None)
    if profile is None:
        print(f"No profile '{name}'. Try `xavani learn list`.")
        return
    print(f"{profile.title} ({profile.name})")
    print(f"  inspiration: {profile.inspiration}")
    print(f"  tags: {', '.join(profile.tags)}")
    for label in ("layout", "typography", "color", "motion", "whitespace", "imagery"):
        value = getattr(profile, label)
        if value:
            print(f"  {label}: {value}")
    if profile.feel:
        print(f"  feel: {', '.join(profile.feel)}")
    if profile.avoid:
        print(f"  avoid: {', '.join(profile.avoid)}")


def _usage() -> None:
    print("xavani learn — teach Xavani your taste & preferences")
    print('  url <url>       learn a design direction from a website')
    print('  file <path>     learn from a local reference')
    print('  pref "<text>"   record a preference')
    print("  list            list learned profiles + preferences")
    print("  show <name>     show a profile's details")
