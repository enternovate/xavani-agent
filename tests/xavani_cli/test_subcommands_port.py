import importlib
import inspect
import pkgutil


def _module_names():
    import xavani_cli.subcommands as pkg
    return sorted(
        m.name for m in pkgutil.iter_modules(pkg.__path__) if not m.name.startswith("_")
    )


def test_subcommands_package_imports():
    mod = importlib.import_module("xavani_cli.subcommands")
    assert mod is not None


def test_subcommands_every_module_imports():
    for name in _module_names():
        mod = importlib.import_module(f"xavani_cli.subcommands.{name}")
        assert mod is not None


def test_subcommands_each_module_exposes_entry():
    for name in _module_names():
        mod = importlib.import_module(f"xavani_cli.subcommands.{name}")
        public_callables = [
            member
            for attr, member in vars(mod).items()
            if not attr.startswith("_") and callable(member)
        ]
        imported = [
            member
            for attr, member in vars(mod).items()
            if not attr.startswith("_")
            and inspect.isfunction(member)
            and member.__module__ != mod.__name__
        ]
        own = [m for m in public_callables if getattr(m, "__module__", None) == mod.__name__]
        assert public_callables, name
        assert own or imported or any(
            a in ("register", "register_subcommand", "register_commands", "command", "run", "main", "handle", "add_parser", "add_subparser")
            for a in dir(mod)
        ), name
