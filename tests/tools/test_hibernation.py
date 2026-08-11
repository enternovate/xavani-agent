# Copyright (c) 2025-2026 Enternovate.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Tests for tools/environments/hibernation.py — hibernate/resume lifecycle."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tools.environments.hibernation import HibernationMixin

pytestmark = pytest.mark.integration


class FakeEnvironment(HibernationMixin):
    """A fake environment backend for testing."""

    def __init__(self):
        self.task_id = "test-task-123"
        self.snapshot_created = False
        self.snapshot_restored = False
        self.resource_paused = False
        self.resource_resumed = False

    def _create_snapshot(self):
        self.snapshot_created = True
        return "snap-abc123"

    def _restore_snapshot(self, snapshot_id):
        self.snapshot_restored = True

    def _pause_resource(self):
        self.resource_paused = True

    def _resume_resource(self):
        self.resource_resumed = True


@pytest.fixture(autouse=True)
def _patch_home(tmp_path):
    """Patch xavani_constants.get_xavani_home to return tmp_path."""
    with patch("xavani_constants.get_xavani_home", return_value=tmp_path):
        yield tmp_path


class TestHibernationMixin:
    """Test the hibernate/resume lifecycle."""

    def test_hibernate_creates_snapshot(self):
        """Hibernate creates a snapshot and pauses the resource."""
        env = FakeEnvironment()
        ticket = env.hibernate()
        assert env.snapshot_created is True
        assert env.resource_paused is True
        assert ticket["snapshot_id"] == "snap-abc123"
        assert ticket["task_id"] == "test-task-123"
        assert "hibernated_at" in ticket

    def test_resume_restores_snapshot(self):
        """Resume restores the snapshot and resumes the resource."""
        env = FakeEnvironment()
        ticket = env.hibernate()
        # Reset flags
        env.snapshot_restored = False
        env.resource_resumed = False
        ok = env.resume(ticket)
        assert ok is True
        assert env.snapshot_restored is True
        assert env.resource_resumed is True

    def test_resume_without_ticket_fails(self):
        """Resume with empty ticket returns False."""
        env = FakeEnvironment()
        ok = env.resume({})
        assert ok is False

    def test_hibernate_saves_ticket(self, tmp_path):
        """Hibernate persists the ticket to disk."""
        env = FakeEnvironment()
        env.hibernate()
        ticket_path = tmp_path / "hibernation_tickets.json"
        assert ticket_path.exists()
        data = json.loads(ticket_path.read_text())
        assert "test-task-123" in data

    def test_load_hibernation_ticket(self):
        """Can load a saved ticket by task_id."""
        env = FakeEnvironment()
        env.hibernate()
        loaded = env.load_hibernation_ticket("test-task-123")
        assert loaded is not None
        assert loaded["snapshot_id"] == "snap-abc123"

    def test_load_nonexistent_ticket(self):
        """Returns None for unknown task_id."""
        env = FakeEnvironment()
        loaded = env.load_hibernation_ticket("nonexistent")
        assert loaded is None

    def test_subclass_must_implement(self):
        """Base HibernationMixin raises NotImplementedError for snapshot methods."""
        mixin = HibernationMixin()
        with pytest.raises(NotImplementedError):
            mixin._create_snapshot()
