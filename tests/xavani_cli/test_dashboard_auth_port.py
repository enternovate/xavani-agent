import importlib

MODULES = [
    "audit",
    "base",
    "cookies",
    "login_page",
    "middleware",
    "native_flow",
    "prefix",
    "public_paths",
    "registry",
    "routes",
    "token_auth",
    "ws_tickets",
]


def test_dashboard_auth_package_imports():
    mod = importlib.import_module("xavani_cli.dashboard_auth")
    assert mod is not None


def test_dashboard_auth_modules_import():
    for name in MODULES:
        mod = importlib.import_module(f"xavani_cli.dashboard_auth.{name}")
        assert mod is not None


def test_dashboard_auth_modules_expose_public_names():
    pkg = importlib.import_module("xavani_cli.dashboard_auth")
    assert [n for n in dir(pkg) if not n.startswith("_")]
    for name in MODULES:
        mod = importlib.import_module(f"xavani_cli.dashboard_auth.{name}")
        assert [n for n in dir(mod) if not n.startswith("_")], name
