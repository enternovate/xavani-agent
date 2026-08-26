# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Project scaffolders for ``xavani new``."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path
from typing import Sequence

_TEMPLATE_ROOT = Path(__file__).with_name("templates") / "scaffold"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9._-]*$")


class ScaffoldError(ValueError):
    """Raised when a scaffold request cannot be safely completed."""


def _validate_name(name: str) -> str:
    if not name or not _NAME_RE.fullmatch(name) or ".." in name:
        raise ScaffoldError(
            "name must be lowercase and contain only letters, numbers, dots, "
            "underscores, and hyphens"
        )
    return name


def _validate_optional_name(value: str | None, label: str) -> str | None:
    if value is None:
        return None
    if not value or not _NAME_RE.fullmatch(value) or ".." in value:
        raise ScaffoldError(f"{label} must be lowercase and filesystem-safe")
    return value


def _root_path(root: str | Path | None) -> Path:
    return Path.cwd() if root is None else Path(root)


def _yaml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _python_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _title(name: str) -> str:
    return name.replace("-", " ").replace("_", " ").replace(".", " ").title()


def _read_template(kind: str, filename: str) -> str:
    try:
        return (_TEMPLATE_ROOT / kind / filename).read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise ScaffoldError(f"scaffold template is missing: {kind}/{filename}") from exc


def _ensure_available(target: Path, force: bool) -> None:
    if target.exists() or target.is_symlink():
        if not force:
            raise ScaffoldError(
                f"{target} already exists — pass --force to overwrite"
            )
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_skill(
    name: str,
    *,
    root: str | Path | None = None,
    category: str | None = None,
    description: str | None = None,
    condition: str | None = None,
    force: bool = False,
) -> Path:
    """Create a skill under ``skills[/category]/name/SKILL.md``."""
    name = _validate_name(name)
    category = _validate_optional_name(category, "category")
    target_dir = _root_path(root) / "skills"
    if category:
        target_dir /= category
    skill_dir = target_dir / name
    _ensure_available(skill_dir, force)
    target = skill_dir / "SKILL.md"

    title = _title(name)
    categories_yaml = f"\n  - {category}" if category else " []"
    content = _read_template("skill", "SKILL.md.tmpl").replace(
        "${name}", name
    ).replace(
        "${description_yaml}",
        _yaml_string(description or f"Guidance for {title.lower()} tasks."),
    ).replace(
        "${categories_yaml}", categories_yaml
    ).replace(
        "${condition_yaml}",
        _yaml_string(condition or f"When a task requires {title.lower()} support."),
    ).replace(
        "${title}", title
    ).replace(
        "${title_lc}", title.lower()
    )
    _write_file(target, content)
    return target


def create_plugin(
    name: str,
    *,
    root: str | Path | None = None,
    description: str | None = None,
    author: str = "Enternovate",
    force: bool = False,
) -> Path:
    """Create a plugin package under ``plugins/name``."""
    name = _validate_name(name)
    target = _root_path(root) / "plugins" / name
    _ensure_available(target, force)
    values = {
        "name": name,
        "description_yaml": _yaml_string(
            description or f"Xavani plugin for {name.replace('-', ' ')}."
        ),
        "author_yaml": _yaml_string(author),
    }
    _write_file(
        target / "plugin.yaml",
        _read_template("plugin", "plugin.yaml.tmpl").replace(
            "${name}", values["name"]
        ).replace(
            "${description_yaml}", values["description_yaml"]
        ).replace(
            "${author_yaml}", values["author_yaml"]
        ),
    )
    _write_file(
        target / "__init__.py",
        _read_template("plugin", "__init__.py.tmpl").replace("${name}", name),
    )
    return target


def _normalise_env_vars(env_var: str | Sequence[str] | None, name: str) -> tuple[str, ...]:
    if env_var is None:
        default = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").upper()
        return (f"{default}_API_KEY",)
    values = (env_var,) if isinstance(env_var, str) else tuple(env_var)
    if not values or any(not value or not re.fullmatch(r"[A-Z][A-Z0-9_]*", value) for value in values):
        raise ScaffoldError("env-var values must be uppercase environment variable names")
    return values


def _tuple_expr(values: Sequence[str]) -> str:
    if not values:
        return "()"
    rendered = ",".join(_python_string(value) for value in values)
    return f"({rendered},)"


def create_provider(
    name: str,
    *,
    root: str | Path | None = None,
    display_name: str | None = None,
    env_var: str | Sequence[str] | None = None,
    base_url: str = "",
    aliases: Sequence[str] | None = None,
    description: str | None = None,
    author: str = "Enternovate",
    force: bool = False,
) -> Path:
    """Create a model-provider plugin under ``plugins/model-providers/name``."""
    name = _validate_name(name)
    aliases = tuple(aliases or ())
    if any(not alias or not _NAME_RE.fullmatch(alias) or ".." in alias for alias in aliases):
        raise ScaffoldError("aliases must be lowercase and filesystem-safe")
    env_vars = _normalise_env_vars(env_var, name)
    target = _root_path(root) / "plugins" / "model-providers" / name
    _ensure_available(target, force)
    human_name = display_name or _title(name)
    provider_description = description or f"{human_name} model provider."
    values = {
        "name_expr": _python_string(name),
        "aliases_expr": _tuple_expr(aliases),
        "display_name_text": human_name,
        "display_name_expr": _python_string(human_name),
        "description_expr": _python_string(provider_description),
        "env_vars_expr": _tuple_expr(env_vars),
        "base_url_expr": _python_string(base_url),
        "description_yaml": _yaml_string(provider_description),
        "author_yaml": _yaml_string(author),
    }
    source = _read_template("provider", "__init__.py.tmpl")
    for key, value in values.items():
        source = source.replace(f"${{{key}}}", value)
    manifest = _read_template("provider", "plugin.yaml.tmpl")
    manifest_values = {
        "name": name,
        "description_yaml": values["description_yaml"],
        "author_yaml": values["author_yaml"],
    }
    for key, value in manifest_values.items():
        manifest = manifest.replace(f"${{{key}}}", value)
    _write_file(target / "__init__.py", source)
    _write_file(target / "plugin.yaml", manifest)
    return target


def cmd_new(args: argparse.Namespace) -> int:
    """Dispatch an ``xavani new`` scaffold request."""
    try:
        common = {
            "root": getattr(args, "root", None),
            "force": getattr(args, "force", False),
        }
        if args.new_type == "skill":
            result = create_skill(
                args.name,
                category=getattr(args, "category", None),
                description=getattr(args, "description", None),
                condition=getattr(args, "condition", None),
                **common,
            )
        elif args.new_type == "plugin":
            result = create_plugin(
                args.name,
                description=getattr(args, "description", None),
                author=getattr(args, "author", "Enternovate"),
                **common,
            )
        elif args.new_type == "provider":
            result = create_provider(
                args.name,
                display_name=getattr(args, "display_name", None),
                env_var=getattr(args, "env_var", None),
                base_url=getattr(args, "base_url", ""),
                aliases=getattr(args, "aliases", None),
                description=getattr(args, "description", None),
                author=getattr(args, "author", "Enternovate"),
                **common,
            )
        else:
            raise ScaffoldError(f"unknown scaffold type: {args.new_type}")
    except ScaffoldError as exc:
        print(f"xavani new: {exc}", file=sys.stderr)
        raise SystemExit(2) from exc
    print(result)
    return 0


def register_cli(parent: argparse.ArgumentParser) -> None:
    """Register ``skill``, ``plugin``, and ``provider`` under a ``new`` parser."""
    subparsers = parent.add_subparsers(dest="new_type", required=True)

    skill = subparsers.add_parser("skill", help="Create a skill scaffold")
    skill.add_argument("name")
    skill.add_argument("--category", default=None)
    skill.add_argument("--description", default=None)
    skill.add_argument("--condition", default=None)
    skill.add_argument("--root", type=Path, default=None)
    skill.add_argument("--force", action="store_true")
    skill.set_defaults(func=cmd_new)

    plugin = subparsers.add_parser("plugin", help="Create a plugin scaffold")
    plugin.add_argument("name")
    plugin.add_argument("--description", default=None)
    plugin.add_argument("--author", default="Enternovate")
    plugin.add_argument("--root", type=Path, default=None)
    plugin.add_argument("--force", action="store_true")
    plugin.set_defaults(func=cmd_new)

    provider = subparsers.add_parser("provider", help="Create a model-provider scaffold")
    provider.add_argument("name")
    provider.add_argument("--display-name", default=None)
    provider.add_argument("--env-var", action="append", default=None)
    provider.add_argument("--base-url", default="")
    provider.add_argument("--alias", dest="aliases", action="append", default=None)
    provider.add_argument("--description", default=None)
    provider.add_argument("--author", default="Enternovate")
    provider.add_argument("--root", type=Path, default=None)
    provider.add_argument("--force", action="store_true")
    provider.set_defaults(func=cmd_new)
