# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.


"""Tool-discovery fingerprint cache (tools/registry.py).

The second in-process ``discover_builtin_tools()`` call must hit the
process-level memo and increment ``registry._discovery_cache_hits``.
Discovery must never break on any on-disk cache state, including a
valid-JSON payload that is not a dict.
"""

import pytest


def test_discovery_cache_reused_when_tools_unchanged():
    from tools import registry

    # Reset module state so the assertion below measures THIS test's calls,
    # not hits accumulated by earlier tests in the same process.
    registry._discovery_memo = None
    registry._discovery_cache_hits = 0

    names1 = registry.discover_builtin_tools()
    hits_after_first = registry._discovery_cache_hits
    names2 = registry.discover_builtin_tools()

    assert registry._discovery_cache_hits == hits_after_first + 1
    assert names1 == names2
    assert len(names1) > 0


@pytest.mark.parametrize("payload", ["[1, 2, 3]", '"x"'])
def test_discovery_survives_non_dict_cache_payload(payload):
    from tools import registry

    # Reset module state so the on-disk cache is actually consulted.
    registry._discovery_memo = None
    registry._discovery_cache_hits = 0
    cache_path = registry._discovery_cache_path()
    assert cache_path is not None
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(payload, encoding="utf-8")

    names = registry.discover_builtin_tools()

    assert isinstance(names, list)
    assert len(names) > 0
