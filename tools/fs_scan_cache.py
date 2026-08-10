# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""Pure-Python filesystem scan cache for the file tools.

Memoizes directory-tree listings behind a short TTL (1.0s default) so
consecutive file searches within an agent turn don't rescan the same
tree. Semantics are a port of omp's pi-walker FS scan cache: keyed by
(canonical root, options tuple), write invalidation via ``invalidate()``,
bounded LRU-style capacity, thread-safe, zero dependencies.

Design notes
------------
* ``walk(root, options_key=None)`` returns a sorted list of relative
  path strings (POSIX separators) covering the directory tree, honoring
  common ignore rules by default (``.git``, ``node_modules``,
  ``__pycache__``, ``.venv``, and hidden files/dirs).
* The cache key is ``(os.path.realpath(root), options_tuple)`` so
  equivalent paths (``foo`` vs ``foo/./`` vs ``foo/../foo``) share one
  entry. Options are normalized to a hashable tuple of pairs.
* ``invalidate(path)`` drops every entry whose root is equal to, an
  ancestor of, or a descendant of ``path`` — a write anywhere inside a
  cached tree invalidates it, and a write to an ancestor invalidates all
  subtrees beneath it.
* TTL is read from ``XAVANI_FS_CACHE_TTL_MS`` (milliseconds) per call,
  defaulting to 1000 ms. A single lock guards the cache dict.
"""

import os
import threading
import time

__all__ = ["walk", "invalidate", "hits"]

MAX_ENTRIES = 16
DEFAULT_TTL_MS = 1000
DEFAULT_IGNORE_DIRS = (".git", "node_modules", "__pycache__", ".venv")

_lock = threading.Lock()
# key -> (last_access_monotonic, expires_monotonic, entries_tuple)
_cache = {}

# Module-level cache-hit counter (tests assert on this).
hits = 0


def _ttl_seconds():
    """TTL in seconds from XAVANI_FS_CACHE_TTL_MS, falling back to 1.0s."""
    try:
        return float(os.environ.get("XAVANI_FS_CACHE_TTL_MS", DEFAULT_TTL_MS)) / 1000.0
    except (TypeError, ValueError):
        return DEFAULT_TTL_MS / 1000.0


def _normalize_options(options_key):
    """Canonicalize options_key into a hashable, deterministic tuple.

    Accepts:
    * ``None`` -- defaults (ignore hidden + common junk dirs, include dirs).
    * a dict -- ``ignore_hidden`` (bool, default True), ``ignore_dirs``
      (iterable of extra directory names — a plain string is treated as
      ONE name, not a set of characters — additive over the defaults),
      ``include_dirs`` (bool, default True).
    * a frozenset/set/tuple/list of names -- additive ignore dirs.
    """
    ignore_hidden = True
    include_dirs = True
    if options_key is None:
        ignore_dirs = DEFAULT_IGNORE_DIRS
    elif isinstance(options_key, dict):
        ignore_hidden = bool(options_key.get("ignore_hidden", True))
        include_dirs = bool(options_key.get("include_dirs", True))
        extra = options_key.get("ignore_dirs", ())
        if isinstance(extra, str):
            extra = [extra]  # lenient: one dir name, never a set of chars
        ignore_dirs = tuple(sorted(set(DEFAULT_IGNORE_DIRS) | set(extra)))
    elif isinstance(options_key, (frozenset, set, tuple, list)):
        ignore_dirs = tuple(sorted(set(DEFAULT_IGNORE_DIRS) | set(options_key)))
    else:
        raise TypeError(
            "options_key must be None, a dict, or an iterable of dir names; "
            f"got {type(options_key).__name__}"
        )
    return (
        ("ignore_hidden", ignore_hidden),
        ("ignore_dirs", frozenset(ignore_dirs)),
        ("include_dirs", include_dirs),
    )


def _scan(root, opts):
    """Fresh directory-tree listing of ``root`` honoring ``opts``."""
    ignore_hidden = dict(opts)["ignore_hidden"]
    ignore_dirs = dict(opts)["ignore_dirs"]
    include_dirs = dict(opts)["include_dirs"]
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [
            d for d in dirnames
            if not (ignore_hidden and d.startswith("."))
            and d not in ignore_dirs
        ]
        rel = os.path.relpath(dirpath, root)
        rel = "" if rel == "." else rel.replace(os.sep, "/")
        if include_dirs and rel:
            out.append(rel)
        for name in sorted(filenames):
            if ignore_hidden and name.startswith("."):
                continue
            out.append(name if not rel else f"{rel}/{name}")
    out.sort()
    return out


def _evict_locked(now):
    """Drop expired entries, then LRU-evict until at most MAX_ENTRIES."""
    while len(_cache) > MAX_ENTRIES:
        expired = [k for k, (_, exp, _) in _cache.items() if exp <= now]
        if expired:
            for k in expired:
                del _cache[k]
            continue
        victim = min(_cache, key=lambda k: _cache[k][0])  # least recently used
        del _cache[victim]


def walk(root, options_key=None):
    """Return a sorted list of relative paths under ``root`` (cached)."""
    global hits
    opts = _normalize_options(options_key)
    canon = os.path.realpath(str(root))
    key = (canon, opts)
    ttl = _ttl_seconds()
    now = time.monotonic()

    with _lock:
        entry = _cache.get(key)
        if entry is not None and entry[1] > now:
            hits += 1
            _cache[key] = (now, entry[1], entry[2])  # refresh LRU stamp
            return list(entry[2])
        if entry is not None:
            del _cache[key]  # stale entry

    entries = tuple(_scan(canon, opts))
    now = time.monotonic()
    with _lock:
        _cache[key] = (now, now + ttl, entries)
        _evict_locked(now)
    return list(entries)


def invalidate(path):
    """Drop cache entries whose root is equal to, contains, or is
    contained by ``path`` (canonical comparison)."""
    canon = os.path.realpath(str(path))
    with _lock:
        doomed = []
        for key in _cache:
            root = key[0]
            if root == canon:
                doomed.append(key)
            elif root.startswith(canon + os.sep):  # entry root inside path
                doomed.append(key)
            elif canon.startswith(root + os.sep):  # path inside entry root
                doomed.append(key)
        for key in doomed:
            del _cache[key]
