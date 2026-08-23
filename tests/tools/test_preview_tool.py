#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

"""Tests for the preview control tool (Task 2.4)."""

import json
from unittest.mock import patch

from tools.preview_tool import preview_control


class TestValidation:
    def test_unknown_action_rejected(self):
        r = preview_control(action="zoom")
        assert r["ok"] is False and "Unknown action" in r["error"]

    def test_open_requires_url(self):
        with patch("tools.preview_tool._desktop_api", return_value="http://127.0.0.1:1"):
            r = preview_control(action="open")
        assert r["ok"] is False and "needs a url" in r["error"]

    def test_navigate_requires_url(self):
        with patch("tools.preview_tool._desktop_api", return_value="http://127.0.0.1:1"):
            r = preview_control(action="navigate")
        assert r["ok"] is False and "needs a url" in r["error"]

    def test_close_and_status_need_no_url(self):
        # These reach the transport layer (fail as unreachable), proving
        # validation did not demand a url.
        with patch("tools.preview_tool._desktop_api", return_value="http://127.0.0.1:1"):
            r = preview_control(action="close")
        assert "needs a url" not in r.get("error", "")


class TestEnvironmentGate:
    def test_outside_desktop_reports_clearly(self, monkeypatch):
        monkeypatch.delenv("XAVANI_DESKTOP_API", raising=False)
        r = preview_control(action="status")
        assert r["ok"] is False
        assert "desktop app" in r["error"]

    def test_inside_desktop_posts_command(self, monkeypatch):
        monkeypatch.setenv("XAVANI_DESKTOP_API", "http://127.0.0.1:9999")
        captured = {}

        def fake_post(url, payload):
            captured["url"] = url
            captured["payload"] = payload
            return {"ok": True}

        with patch("tools.preview_tool._post", side_effect=fake_post):
            r = preview_control(action="open", url="http://localhost:3000")

        assert r == {"ok": True}
        assert captured["url"] == "http://127.0.0.1:9999/desktop/api/preview/cmd"
        assert captured["payload"]["action"] == "open"
        assert captured["payload"]["url"] == "http://localhost:3000"

    def test_transport_error_becomes_error_dict(self, monkeypatch):
        monkeypatch.setenv("XAVANI_DESKTOP_API", "http://127.0.0.1:9999")

        def boom(url, payload):
            raise OSError("connection refused")

        with patch("tools.preview_tool._post", side_effect=boom):
            r = preview_control(action="status")
        assert r["ok"] is False and "unreachable" in r["error"]


class TestRegistryWiring:
    def test_tool_registered(self):
        from tools.registry import registry

        assert "preview_control" in registry.get_all_tool_names()

    def test_handler_returns_json(self):
        from tools.preview_tool import _handle_preview_control

        data = json.loads(
            _handle_preview_control({"action": "bogus"})
        )
        assert data["ok"] is False
