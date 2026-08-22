# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.

from xavani_cli import director


class TestDirectorMode:
    def test_default_off(self):
        assert director.is_enabled() is False

    def test_enable_disable_roundtrip(self):
        token = director._director_on.set(False)
        try:
            director.enable()
            assert director.is_enabled() is True
            director.disable()
            assert director.is_enabled() is False
        finally:
            director._director_on.reset(token)

    def test_filter_passthrough_when_disabled(self):
        toolsets = ["terminal", "web"]
        assert director.director_filter_toolsets(toolsets) == toolsets

    def test_filter_intersects_when_enabled(self):
        token = director._director_on.set(True)
        try:
            filtered = director.director_filter_toolsets(
                ["terminal", "file", "web", "search", "delegation"]
            )
            assert sorted(filtered) == ["search", "web"]
        finally:
            director._director_on.reset(token)
