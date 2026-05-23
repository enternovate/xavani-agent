# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""No-op stub kept after the Nous Portal provider was removed.

Existing call sites (auxiliary client, conversation loop, web tools) still
import ``nous_portal_tags`` to attach product-attribution tags on outgoing
requests. Now that Xavani no longer ships a Nous Portal integration, the
helper returns an empty list and the callers tack on nothing — keeping the
import contract stable while emitting no extra metadata.
"""

from __future__ import annotations


def nous_portal_tags() -> list[str]:
    return []
