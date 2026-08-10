"""Per-session snapshot tag store for hashline (ported from omp's snapshots.ts).

A hashline section header ``[PATH#TAG]`` carries a TAG that is a content
fingerprint of the *whole file* at read time.  This module binds those tags
to the exact normalized content that minted them so a follow-up edit anchored
at any line can validate against the live file, and recovery can resolve a
stale tag back to the full text the model actually saw.

Design (mirrors ``InMemorySnapshotStore`` in omp):

* Tags are 4 uppercase hex chars from ``blake2b(digest_size=2)`` (stdlib — no
  xxhash dependency) of the *normalized* text.  Normalization is CRLF->LF,
  per-line trailing ``[ \\t]`` stripped, final trailing newlines stripped, so
  byte-identical reads and display-trimmed reads mint the same tag.
* :class:`SnapshotStore` is a bounded LRU: at most ``max_paths`` (30) paths,
  each holding a short ring of ``max_versions`` (4) full-file versions,
  oldest dropped first.  Recording byte-identical content again refreshes
  recency and reuses the existing version (read fusion); recording new
  content unshifts a fresh version onto the front.
* Two distinct texts that collide on the short 4-hex tag are retained as
  separate versions — the tag is only a fast index, never the identity
  (dedup is by full-text equality, see omp issue #4075).

Session scoping: an agent session creates one :class:`SnapshotStore` and
holds it on the agent/session object; :data:`default_store` is the
module-level singleton for CLI/tool use outside a session.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Iterable, Optional, Tuple

__all__ = ["Snapshot", "SnapshotStore", "compute_tag", "default_store"]

#: Default maximum distinct paths tracked at once (LRU eviction).
DEFAULT_MAX_PATHS = 30
#: Default maximum full-file versions retained per path (oldest dropped first).
DEFAULT_MAX_VERSIONS_PER_PATH = 4


def normalize_content(content: str) -> str:
    """Canonical form for hashing: LF endings, no per-line trailing space/tab.

    CRLF (and lone CR) become LF; each line is stripped of trailing spaces and
    tabs (so display-trimmed lines do not invalidate a tag); trailing newlines
    are stripped so ``text`` and ``text + "\\n"`` share a tag.
    """
    text = content.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip(" \t") for line in text.split("\n")]
    normalized = "\n".join(lines)
    # Strip exactly one trailing newline: a single final ``\\n`` is the
    # canonical file terminator and must not invalidate a tag, but additional
    # blank lines are real content (matching omp's hash normalization).
    if normalized.endswith("\n"):
        normalized = normalized[:-1]
    return normalized


def compute_tag(content: str) -> str:
    """Content-derived 4-uppercase-hex snapshot tag for ``content``.

    Deterministic across equivalent normalizations (see
    :func:`normalize_content`): CRLF vs LF, trailing whitespace, and a final
    newline all hash identically.  Any real content change yields a different
    tag (16-bit digest; collisions are possible but astronomically rare for
    edit-sized differences and never treated as identity — the store dedups by
    full-text equality).
    """
    normalized = normalize_content(content).encode("utf-8")
    return hashlib.blake2b(normalized, digest_size=2).hexdigest().upper()


@dataclass(frozen=True)
class Snapshot:
    """One full-file version observed at a point in time.

    ``content`` is the full file as UTF-8 bytes, ``tag`` its content tag,
    ``visible_ranges`` the 1-indexed ``(start, end)`` line ranges a producer
    (read/search) displayed under this tag, and ``recorded_at`` the wall-clock
    time it was recorded.
    """

    path: str
    content: bytes
    tag: str
    visible_ranges: Tuple[Tuple[int, int], ...] = ()
    recorded_at: float = field(default_factory=time.time)


class SnapshotStore:
    """Bounded per-session store of full-file snapshot versions.

    ``path -> [versions]`` ordered by recency of *path* access (LRU across
    paths) with each path's versions ordered newest-first and capped at
    ``max_versions``.  ``get``/``record`` refresh path recency.
    """

    def __init__(
        self,
        max_paths: int = DEFAULT_MAX_PATHS,
        max_versions: int = DEFAULT_MAX_VERSIONS_PER_PATH,
    ) -> None:
        self._max_paths = max_paths
        self._max_versions = max_versions
        self._versions: "OrderedDict[str, list[Snapshot]]" = OrderedDict()

    # -- queries -----------------------------------------------------------

    def get(self, path: str) -> Optional[Snapshot]:
        """Most-recently recorded version for ``path``, or ``None``.

        Refreshes LRU recency for ``path``.
        """
        history = self._versions.get(path)
        if history:
            self._versions.move_to_end(path)  # refresh LRU recency
            return history[0]
        return None

    def head(self, path: str) -> Optional[Snapshot]:
        """Alias of :meth:`get` (omp's ``head``)."""
        return self.get(path)

    def by_hash(self, path: str, tag: str) -> Optional[Snapshot]:
        """Recorded version for ``path`` whose tag equals ``tag``, or ``None``."""
        history = self._versions.get(path)
        if not history:
            return None
        for version in history:
            if version.tag == tag:
                return version
        return None

    def by_content(self, path: str, content: str) -> Optional[Snapshot]:
        """Recorded version for ``path`` whose text equals ``content``, or ``None``."""
        history = self._versions.get(path)
        if not history:
            return None
        want = content.encode("utf-8")
        for version in history:
            if version.content == want:
                return version
        return None

    def verify(self, path: str, tag: str) -> bool:
        """True iff the current (head) stored tag for ``path`` matches ``tag``."""
        entry = self.get(path)
        return entry is not None and entry.tag == tag

    def tag_of(self, path: str, content: str) -> str:
        """Compute the tag for ``content`` without storing anything.

        ``path`` is accepted for signature symmetry with :meth:`record`.
        """
        return compute_tag(content)

    # -- writes ------------------------------------------------------------

    def record(
        self,
        path: str,
        content: str,
        ranges: Optional[Iterable[Tuple[int, int]]] = None,
    ) -> str:
        """Record the full text of ``path`` and return its content tag.

        Byte-identical content reuses the existing version (refreshing recency
        and unioning ``ranges`` into its visible lines); new content unshifts
        a fresh version, dropping the oldest if the per-path history is full.
        Paths beyond ``max_paths`` evict the least-recently-used path.
        """
        tag = compute_tag(content)
        payload = content.encode("utf-8")
        new_ranges = tuple(ranges) if ranges is not None else ()

        history = self._versions.get(path)
        if history is not None:
            for i, version in enumerate(history):
                if version.tag == tag and version.content == payload:
                    # Same content state observed again: refresh recency,
                    # promote to head, union any newly-displayed ranges.
                    merged = tuple(sorted(set(version.visible_ranges) | set(new_ranges)))
                    refreshed = Snapshot(
                        path,
                        payload,
                        tag,
                        merged,
                        time.time(),
                    )
                    history.pop(i)
                    history.insert(0, refreshed)
                    self._versions.move_to_end(path)
                    return tag
        else:
            history = []

        history.insert(0, Snapshot(path, payload, tag, new_ranges))
        del history[self._max_versions :]
        self._versions[path] = history
        self._versions.move_to_end(path)
        while len(self._versions) > self._max_paths:
            self._versions.popitem(last=False)
        return tag

    def invalidate(self, path: str) -> None:
        """Drop the version history for ``path``."""
        self._versions.pop(path, None)

    def clear(self) -> None:
        """Drop every version history."""
        self._versions.clear()

    def __len__(self) -> int:
        return len(self._versions)

    def __contains__(self, path: str) -> bool:
        return path in self._versions


#: Module-level default store for CLI/tool use outside an agent session.
default_store = SnapshotStore()
