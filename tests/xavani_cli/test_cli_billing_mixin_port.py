import inspect


def test_cli_billing_mixin_imports():
    import xavani_cli.cli_billing_mixin as mod

    assert mod is not None


def test_cli_billing_mixin_is_class():
    from xavani_cli.cli_billing_mixin import CLIBillingMixin

    assert inspect.isclass(CLIBillingMixin)


def test_usage_bar_lines_empty_for_no_usage():
    from xavani_cli.cli_billing_mixin import CLIBillingMixin

    assert CLIBillingMixin._usage_bar_lines(object(), None, None) == []
