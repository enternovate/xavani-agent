"""Best-effort accessors for the single-writer stream fence (A02).

The fence itself lives on ``AIAgent`` (``_claim_stream_writer`` /
``_stream_writer_superseded`` in ``run_agent.py``), but the streaming code
paths that use it live in other modules (``agent/chat_completion_helpers.py``).
Calling the fence directly as ``agent._claim_stream_writer()`` from those
modules makes them hard-depend on the method being present on whatever
object is passed in as ``agent``.

That coupling is a latent crash: a partially-updated checkout, a hot-reloaded
gateway, a duck-typed agent, or a test double without the method turns an
*additive* safety net into a fatal ``AttributeError`` that aborts the whole
turn.

The fence is only ever allowed to drop a *provably* superseded stream —
never the sole legitimate writer. So when the guard is unavailable (or
raises), the correct degradation is "no fence": keep streaming. These
helpers make the claim/check best-effort to guarantee that.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def claim_stream_writer(agent: Any) -> int:
    """Claim the delta sink for the calling stream attempt, best-effort.

    Returns the agent's monotonic writer token when the fence is available,
    or ``0`` when the agent doesn't expose it (or the claim raised). A ``0``
    token pairs with :func:`stream_writer_is_current` always returning
    ``True``, so a guard-less agent is simply never fenced.
    """
    claim = getattr(agent, "_claim_stream_writer", None)
    if callable(claim):
        try:
            claimed = claim()
            if isinstance(claimed, int):
                return claimed
            return 0
        except Exception:
            logger.debug(
                "stream single-writer: claim failed; proceeding unfenced",
                exc_info=True,
            )
    return 0


def stream_writer_is_current(agent: Any, token: int) -> bool:
    """True when ``token`` is still the active writer, best-effort.

    A falsy token (claim no-oped) or an agent without the fence means we
    cannot prove supersession, so the stream is treated as current and never
    fenced.
    """
    if not token:
        return True
    check = getattr(agent, "_stream_writer_is_current", None)
    if callable(check):
        try:
            return bool(check(token))
        except Exception:
            logger.debug(
                "stream single-writer: current-check failed; proceeding unfenced",
                exc_info=True,
            )
    return True


def stream_writer_superseded(agent: Any) -> bool:
    """True when the calling thread is a stale writer whose deltas must drop.

    A thread that never claimed is not a writer and is never reported as
    superseded.
    """
    check = getattr(agent, "_stream_writer_superseded", None)
    if callable(check):
        try:
            return bool(check())
        except Exception:
            logger.debug(
                "stream single-writer: superseded-check failed; proceeding unfenced",
                exc_info=True,
            )
    return False


__all__ = [
    "claim_stream_writer",
    "stream_writer_is_current",
    "stream_writer_superseded",
]
