# Copyright (c) 2025-2026 Enternovate.
# MIT License — See LICENSE file for full terms.
# Built by Enternovate — Open source. Private. Local.

"""Tests for tools/computer_use_tool.py — computer-use guard and actions."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest

from tools.computer_use_tool import (
    _check_computer_use_available,
    _handle_computer_use,
    COMPUTER_USE_SCHEMA,
)


class TestComputerUseGuard:
    """Test the availability check."""

    def test_unavailable_without_env(self):
        """Returns False when XAVANI_COMPUTER_USE is not set."""
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("XAVANI_COMPUTER_USE", None)
            assert _check_computer_use_available() is False

    def test_unavailable_with_env_false(self):
        """Returns False when XAVANI_COMPUTER_USE=false."""
        with patch.dict(os.environ, {"XAVANI_COMPUTER_USE": "false"}):
            assert _check_computer_use_available() is False

    def test_available_with_env_true(self):
        """Returns True when env is set and MCP tools exist."""
        mock_mcp = MagicMock()
        mock_mcp.get_mcp_tools.return_value = [{"name": "computer_screenshot"}]
        with patch.dict(os.environ, {"XAVANI_COMPUTER_USE": "1"}), \
             patch.dict("sys.modules", {"tools.mcp_tool": mock_mcp}):
            assert _check_computer_use_available() is True

    def test_unavailable_when_mcp_missing(self):
        """Returns False when MCP tools don't include computer tools."""
        mock_mcp = MagicMock()
        mock_mcp.get_mcp_tools.return_value = []
        with patch.dict(os.environ, {"XAVANI_COMPUTER_USE": "1"}), \
             patch.dict("sys.modules", {"tools.mcp_tool": mock_mcp}):
            assert _check_computer_use_available() is False


class TestComputerUseHandler:
    """Test the tool handler."""

    def test_unknown_action(self):
        """Returns error for unknown action."""
        output = _handle_computer_use({"action": "invalid"})
        data = json.loads(output)
        assert "error" in data

    def test_screenshot_calls_backend(self):
        """Screenshot action calls the MCP backend."""
        mock_mcp = MagicMock()
        mock_mcp.call_mcp_tool.return_value = "screenshot_data"
        with patch.dict("sys.modules", {"tools.mcp_tool": mock_mcp}):
            output = _handle_computer_use({"action": "screenshot"})
            data = json.loads(output)
            assert data["ok"] is True

    def test_click_calls_backend(self):
        """Click action calls the MCP backend with coordinates."""
        mock_mcp = MagicMock()
        mock_mcp.call_mcp_tool.return_value = "clicked"
        with patch.dict("sys.modules", {"tools.mcp_tool": mock_mcp}):
            output = _handle_computer_use({"action": "click", "x": 100, "y": 200})
            data = json.loads(output)
            assert data["ok"] is True

    def test_type_calls_backend(self):
        """Type action calls the MCP backend with text."""
        mock_mcp = MagicMock()
        mock_mcp.call_mcp_tool.return_value = "typed"
        with patch.dict("sys.modules", {"tools.mcp_tool": mock_mcp}):
            output = _handle_computer_use({"action": "type", "text": "hello"})
            data = json.loads(output)
            assert data["ok"] is True


class TestComputerUseSchema:
    """Test schema structure."""

    def test_schema_name(self):
        assert COMPUTER_USE_SCHEMA["name"] == "computer_use"

    def test_schema_has_action(self):
        assert "action" in COMPUTER_USE_SCHEMA["parameters"]["properties"]
        assert "action" in COMPUTER_USE_SCHEMA["parameters"]["required"]

    def test_registered_in_registry(self):
        """Tool is registered in the registry."""
        from tools.registry import registry
        entry = registry.get_entry("computer_use")
        assert entry is not None
        assert entry.toolset == "computer_use"
