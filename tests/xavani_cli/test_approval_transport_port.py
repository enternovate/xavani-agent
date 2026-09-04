import inspect


def test_approval_transport_import_succeeds():
    import xavani_cli.approval_transport


def test_approval_decision_is_class():
    from xavani_cli.approval_transport import ApprovalDecision
    assert inspect.isclass(ApprovalDecision)


def test_invoke_approval_transport_is_callable():
    from xavani_cli.approval_transport import invoke_approval_transport
    assert callable(invoke_approval_transport)
