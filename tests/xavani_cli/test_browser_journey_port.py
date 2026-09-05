"""Port checks for browser probe helpers plus the journey module."""

import socket


def _closed_loopback_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def test_find_free_debug_port_returns_int_above_preferred():
    from xavani_cli.browser_connect import find_free_debug_port

    port = find_free_debug_port(preferred=19377, attempts=5)
    assert isinstance(port, int)
    assert 19377 < port <= 19377 + 5


def test_is_browser_debug_ready_false_for_closed_port():
    from xavani_cli.browser_connect import is_browser_debug_ready

    assert is_browser_debug_ready(f"http://127.0.0.1:{_closed_loopback_port()}", timeout=0.2) is False


def test_journey_register_cli_imports_and_callable():
    from xavani_cli.journey import register_cli

    assert callable(register_cli)
