# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Port-guard tests for xavani_state_common plus repair helpers."""


def test_state_common_imports():
    import xavani_state_common

    assert xavani_state_common is not None


def test_state_common_exposes_main_entry():
    import xavani_state_common

    assert xavani_state_common.SCHEMA_VERSION == 30
    assert isinstance(xavani_state_common.SCHEMA_SQL, str)
    assert callable(xavani_state_common.escape_like)


def test_state_common_pure_helper_static_inputs():
    import xavani_state_common

    assert xavani_state_common.escape_like("100%_match\\path") == "100\\%\\_match\\\\path"


def test_describe_skill_invocation_renders_slash_invocation():
    from agent import skill_commands as sc

    content = (
        sc._SKILL_INVOCATION_PREFIX
        + '"work" skill '
        + sc._SINGLE_SKILL_MARKER
        + " body "
        + sc._SINGLE_SKILL_INSTRUCTION
        + "fix the title leak"
    )
    assert sc.describe_skill_invocation(content) == "/work \u2014 fix the title leak"


def test_describe_skill_invocation_plain_text_returns_none():
    from agent import skill_commands as sc

    assert sc.describe_skill_invocation("hello, how are you?") is None


def test_db_opens_cleanly_reports_missing_path(tmp_path):
    from xavani_state import _db_opens_cleanly

    reason = _db_opens_cleanly(tmp_path / "missing.db")
    assert isinstance(reason, str) and reason
