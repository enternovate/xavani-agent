from __future__ import annotations


def test_security_audit_startup_import_succeeds():
    import xavani_cli.security_audit_startup as security_audit_startup

    assert security_audit_startup is not None


def test_security_audit_startup_exposes_main_entry():
    import xavani_cli.security_audit_startup as security_audit_startup

    assert callable(security_audit_startup.run_security_audit)


def test_line_input_is_callable():
    from xavani_cli.cli_output import line_input

    assert callable(line_input)
