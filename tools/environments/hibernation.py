# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Hibernation adapter for long-running sandbox environments.

Adds hibernate/resume lifecycle to environment adapters. Hibernation
saves the sandbox state and pauses it to save cost; resume restores it.

Works with Modal snapshots and can be extended to other providers.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


class HibernationMixin:
    """Mixin that adds hibernate/resume to environment adapters."""

    def hibernate(self) -> Dict[str, Any]:
        """Hibernate the sandbox — save state and pause.

        Returns a hibernation ticket with:
          * snapshot_id — identifier for resume
          * hibernated_at — timestamp
          * provider — which environment provider
        """
        snapshot_id = self._create_snapshot()
        hibernated_at = time.time()

        # Try to pause the underlying resource
        try:
            self._pause_resource()
        except Exception as exc:
            logger.warning("Could not pause resource (snapshot still valid): %s", exc)

        ticket = {
            "snapshot_id": snapshot_id,
            "hibernated_at": hibernated_at,
            "provider": self.__class__.__name__,
            "task_id": getattr(self, "task_id", None),
        }

        # Persist the ticket
        self._save_hibernation_ticket(ticket)
        return ticket

    def resume(self, ticket: Dict[str, Any]) -> bool:
        """Resume from a hibernation ticket.

        Returns True if resume succeeded, False otherwise.
        """
        snapshot_id = ticket.get("snapshot_id")
        if not snapshot_id:
            logger.error("No snapshot_id in hibernation ticket")
            return False

        try:
            self._restore_snapshot(snapshot_id)
            self._resume_resource()
            return True
        except Exception as exc:
            logger.error("Resume failed: %s", exc)
            return False

    def _create_snapshot(self) -> str:
        """Create a snapshot of the current state. Override in subclass."""
        raise NotImplementedError

    def _restore_snapshot(self, snapshot_id: str) -> None:
        """Restore from a snapshot. Override in subclass."""
        raise NotImplementedError

    def _pause_resource(self) -> None:
        """Pause the underlying compute resource. Override in subclass."""
        pass

    def _resume_resource(self) -> None:
        """Resume the underlying compute resource. Override in subclass."""
        pass

    def _save_hibernation_ticket(self, ticket: Dict[str, Any]) -> None:
        """Persist a hibernation ticket. Override in subclass."""
        from xavani_constants import get_xavani_home
        store = get_xavani_home() / "hibernation_tickets.json"
        tickets = {}
        if store.exists():
            try:
                tickets = json.loads(store.read_text(encoding="utf-8"))
            except Exception:
                tickets = {}
        task_id = ticket.get("task_id", "unknown")
        tickets[task_id] = ticket
        store.write_text(json.dumps(tickets, indent=2) + "\n", encoding="utf-8")

    def load_hibernation_ticket(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Load a hibernation ticket by task_id."""
        from xavani_constants import get_xavani_home
        store = get_xavani_home() / "hibernation_tickets.json"
        if not store.exists():
            return None
        try:
            tickets = json.loads(store.read_text(encoding="utf-8"))
            return tickets.get(task_id)
        except Exception:
            return None
