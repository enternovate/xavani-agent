# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Task 4: tool-discovery fingerprint cache.

The second in-process ``discover_builtin_tools()`` call must hit the
process-level memo and increment ``registry._discovery_cache_hits``.
"""


def test_discovery_cache_reused_when_tools_unchanged(tmp_path, monkeypatch):
    from tools import registry
    names1 = registry.discover_builtin_tools()
    names2 = registry.discover_builtin_tools()
    assert names1 == names2
    assert registry._discovery_cache_hits >= 1
