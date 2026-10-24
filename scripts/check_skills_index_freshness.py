#!/usr/bin/env python3
"""Compare the built skills index with the published index."""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Pages serves the deploy artifact, so it is the first source of truth.
# The public host is the second source, for when it mirrors the artifact.
PUBLISHED_URLS = (
    "https://enternovate.github.io/xavani-agent/api/skills-index.json",
    "https://enternovate.co.za/xavani-agent/api/skills-index.json",
)
LOCAL_PATH = Path("website/static/api/skills-index.json")
EXIT_STALE = 1
EXIT_MISSING = 2


def canonical_hash(payload: bytes) -> str:
    """Hash the index content without the build timestamp."""
    doc = json.loads(payload)
    doc.pop("generated_at", None)
    canonical = json.dumps(doc, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def read_published(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=20) as response:
        return response.read()


def published_hash() -> str | None:
    """Return the canonical hash of the first readable published index."""
    for url in PUBLISHED_URLS:
        try:
            return canonical_hash(read_published(url))
        except (urllib.error.URLError, OSError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            print(f"{url} unavailable ({exc})")
    return None


def main() -> int:
    """Return 0 when fresh or pending, 1 when stale, 2 when the local build is missing."""
    if not LOCAL_PATH.exists():
        print("local index missing — the build step did not run")
        return EXIT_MISSING
    local_hash = canonical_hash(LOCAL_PATH.read_bytes())
    remote_hash = published_hash()
    if remote_hash is None:
        print("no published index is readable — pending deployment")
        print("PENDING-DEPLOYMENT")
        return 0
    stale = local_hash != remote_hash
    print(f"local={local_hash[:12]} published={remote_hash[:12]} stale={stale}")
    print("STALE" if stale else "FRESH")
    return EXIT_STALE if stale else 0


if __name__ == "__main__":
    sys.exit(main())
