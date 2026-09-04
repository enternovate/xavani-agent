import logging

from xavani_cli.goals import _warn_dropped_write


def test_warn_dropped_write_importable():
    assert callable(_warn_dropped_write)


def test_warn_dropped_write_emits_one_warning(caplog):
    with caplog.at_level(logging.WARNING):
        _warn_dropped_write("GoalManager", "goal", "sess-123")
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
