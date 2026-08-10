# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Central registry for all xavani-agent tools.

Each tool file calls ``registry.register()`` at module level to declare its
schema, handler, toolset membership, and availability check.  ``model_tools.py``
queries the registry instead of maintaining its own parallel data structures.

Import chain (circular-import safe):
    tools/registry.py  (no imports from model_tools or tool files)
           ^
    tools/*.py  (import from tools.registry at module level)
           ^
    model_tools.py  (imports tools.registry + all tool modules)
           ^
    run_agent.py, cli.py, batch_runner.py, etc.

Tool-argument schema validation (backlog D78 / S3-2)
=====================================================
``dispatch()`` validates a call's args against the tool's registered schema
BEFORE invoking the handler: unknown parameters (strict schemas), missing
required fields, and primitive type mismatches are rejected with a
``tool_error``-style string. Complex nested types and enums are intentionally
not validated in this pass, and ``None`` values are never type-checked.

The validation plan is precomputed at ``register()`` time so the hot path
stays cheap: plain dict lookups and isinstance checks only, no jsonschema
import at call time.

Opt-out list (``_SCHEMA_VALIDATION_OPT_OUTS``) — tools whose schema cannot
describe their accepted arguments and therefore skip validation entirely:
  * tool_call  — the meta-tool's ``arguments`` payload is arbitrary by design;
                 only the outer {name, arguments} envelope is schematized.
Tools with an empty/None schema bypass validation automatically (no plan is
built). A per-tool opt-out also exists: pass ``schema_validation=False`` to
``register()`` (e.g. tools whose schemas are built dynamically at runtime).
"""

import ast
import importlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)
try:
    from xavani_cli.safe_logging import SafeLogFilter
    SafeLogFilter.install()
except Exception:
    pass


def _is_registry_register_call(node: ast.AST) -> bool:
    """Return True when *node* is a ``registry.register(...)`` call expression."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    return (
        isinstance(func, ast.Attribute)
        and func.attr == "register"
        and isinstance(func.value, ast.Name)
        and func.value.id == "registry"
    )


def _module_registers_tools(module_path: Path) -> bool:
    """Return True when the module contains a top-level ``registry.register(...)`` call.

    Only inspects module-body statements so that helper modules which happen
    to call ``registry.register()`` inside a function are not picked up.
    """
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(module_path))
    except (OSError, SyntaxError):
        return False

    return any(_is_registry_register_call(stmt) for stmt in tree.body)


# ---------------------------------------------------------------------------
# Tool-argument schema validation (backlog D78 / S3-2)
#
# Validation runs in dispatch() before the handler is invoked. The plan is
# precomputed at register() time so the hot path is pure dict lookups +
# isinstance checks — no jsonschema import at call time. See the module
# docstring for the opt-out policy.
# ---------------------------------------------------------------------------

_SCHEMA_VALIDATION_OPT_OUTS = frozenset({"tool_call"})

_PRIMITIVE_TYPES = frozenset({"string", "boolean", "integer", "number"})


def _type_ok(expected: str, value: Any) -> bool:
    """Return True when *value* matches the JSON-schema primitive *expected*."""
    if expected == "string":
        return isinstance(value, str)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return True


def _build_validation_plan(schema: Optional[dict]) -> Optional[dict]:
    """Precompute a fast arg-validation plan from an OpenAI-style tool schema.

    Returns None (validation skipped) for empty/None schemas and schemas with
    nothing checkable. Only primitive property types are planned; array/object
    and multi-type (e.g. ``["string", "null"]``) properties are not checked.
    """
    if not isinstance(schema, dict):
        return None
    try:
        params = schema.get("parameters")
        if not isinstance(params, dict):
            return None
        properties = params.get("properties")
        if not isinstance(properties, dict):
            properties = {}
        typed: Dict[str, str] = {}
        for prop_name, prop_schema in properties.items():
            if not isinstance(prop_schema, dict):
                continue
            prop_type = prop_schema.get("type")
            if isinstance(prop_type, str) and prop_type in _PRIMITIVE_TYPES:
                typed[prop_name] = prop_type
        required = params.get("required")
        required_set = (
            frozenset(required) if isinstance(required, (list, tuple, set)) else frozenset()
        )
        strict = params.get("additionalProperties") is False
        if not typed and not required_set and not strict:
            return None
        return {
            "typed": typed,
            "known": frozenset(properties) | required_set,
            "required": required_set,
            "strict": strict,
        }
    except Exception:
        return None


def _validate_args(name: str, args: Any, plan: dict) -> Optional[str]:
    """Return an error message for the first violation, or None when valid."""
    if not isinstance(args, dict):
        return f"Arguments for tool '{name}' must be a JSON object"
    if plan["strict"]:
        unknown = [k for k in args if k not in plan["known"]]
        if unknown:
            return (
                f"Unknown parameter(s) for tool '{name}': "
                + ", ".join(sorted(unknown))
            )
    missing = [k for k in plan["required"] if k not in args]
    if missing:
        return (
            f"Missing required parameter(s) for tool '{name}': "
            + ", ".join(sorted(missing))
        )
    for key, expected in plan["typed"].items():
        value = args.get(key)
        if value is None:
            continue
        if not _type_ok(expected, value):
            return (
                f"Parameter '{key}' for tool '{name}' must be a {expected} "
                f"(got {type(value).__name__})"
            )
    return None


# ---------------------------------------------------------------------------
# Tool-discovery fingerprint cache
#
# discover_builtin_tools() pays two costs per call: a directory scan with an
# AST parse of every tools/*.py (the capability check) and the module imports
# themselves. The scan is pure waste when tools/ is unchanged between runs,
# so we fingerprint tools/*.py (mtime+size) and persist the resulting module
# list at <xavani home>/cache/tool_discovery.json. A matching fingerprint
# skips the scan; the imports still run, but sys.modules makes repeat imports
# free. A process-level memo makes the second call in the same process return
# instantly. Any cache read/write error falls back silently to a full scan —
# discovery must never break.
# ---------------------------------------------------------------------------

_discovery_memo: Optional[tuple] = None  # (tools_path_str, fingerprint, modules)
_discovery_cache_hits = 0
_discovery_memo_lock = threading.Lock()


def _discovery_fingerprint(tools_path: Path) -> list:
    """Return a sorted ``[(name, mtime_ns, size)]`` fingerprint of tools/*.py."""
    entries = []
    for path in sorted(tools_path.glob("*.py")):
        try:
            st = path.stat()
        except OSError:
            continue
        entries.append([path.name, st.st_mtime_ns, st.st_size])
    return entries


def _discovery_cache_path() -> Optional[Path]:
    """Return the cache file path under the Xavani home, or None on failure."""
    try:
        from xavani_constants import get_xavani_home
        return get_xavani_home() / "cache" / "tool_discovery.json"
    except Exception:
        return None


def _discovery_cache_read() -> Optional[dict]:
    """Return the cached payload, or None when unreadable/invalid."""
    path = _discovery_cache_path()
    if path is None:
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return None
    # A valid-JSON but non-dict payload (interrupted write, external clobber)
    # must degrade to None like any other invalid cache state.
    return payload if isinstance(payload, dict) else None


def _discovery_cache_write(fingerprint: list, modules: list) -> None:
    """Persist the fingerprint + module list. Never raises."""
    path = _discovery_cache_path()
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"fingerprint": fingerprint, "modules": modules}, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass


def _import_tool_modules(module_names: List[str]) -> List[str]:
    """Import each module name, returning the names that imported cleanly."""
    imported: List[str] = []
    for mod_name in module_names:
        try:
            importlib.import_module(mod_name)
            imported.append(mod_name)
        except Exception as e:
            logger.warning("Could not import tool module %s: %s", mod_name, e)
    return imported


def discover_builtin_tools(tools_dir: Optional[Path] = None) -> List[str]:
    """Import built-in self-registering tool modules and return their module names.

    The directory scan + AST capability check is skipped when the on-disk
    fingerprint cache (``<xavani home>/cache/tool_discovery.json``) matches
    the current ``tools/*.py`` fingerprint, and a process-level memo makes
    repeat calls in the same process return instantly. Both layers are
    transparent: any cache read/write failure degrades silently to a full
    scan, so discovery itself never breaks.
    """
    tools_path = Path(tools_dir) if tools_dir is not None else Path(__file__).resolve().parent
    fingerprint = _discovery_fingerprint(tools_path)

    global _discovery_cache_hits, _discovery_memo
    with _discovery_memo_lock:
        if (
            _discovery_memo is not None
            and _discovery_memo[0] == str(tools_path)
            and _discovery_memo[1] == fingerprint
        ):
            _discovery_cache_hits += 1
            return list(_discovery_memo[2])

    # The on-disk cache is only consulted for the default tools dir; explicit
    # tools_dir callers (tests, embedders) always get a fresh scan + import.
    if tools_dir is None:
        cached = _discovery_cache_read()
        if cached is not None and cached.get("fingerprint") == fingerprint:
            modules = cached.get("modules")
            if isinstance(modules, list):
                imported = _import_tool_modules(modules)
                with _discovery_memo_lock:
                    _discovery_memo = (str(tools_path), fingerprint, imported)
                    _discovery_cache_hits += 1
                return imported

    module_names = [
        f"tools.{path.stem}"
        for path in sorted(tools_path.glob("*.py"))
        if path.name not in {"__init__.py", "registry.py", "mcp_tool.py"}
        and _module_registers_tools(path)
    ]
    imported = _import_tool_modules(module_names)
    with _discovery_memo_lock:
        _discovery_memo = (str(tools_path), fingerprint, imported)
    if tools_dir is None:
        _discovery_cache_write(fingerprint, imported)
    return imported


class ToolEntry:
    """Metadata for a single registered tool."""

    __slots__ = (
        "name", "toolset", "schema", "handler", "check_fn", "health_fn",
        "requires_env", "is_async", "description", "emoji",
        "max_result_size_chars", "dynamic_schema_overrides",
        "schema_validation", "validation_plan",
    )

    def __init__(self, name, toolset, schema, handler, check_fn, health_fn,
                 requires_env, is_async, description, emoji,
                 max_result_size_chars=None, dynamic_schema_overrides=None,
                 schema_validation=True):
        self.name = name
        self.toolset = toolset
        self.schema = schema
        self.handler = handler
        self.check_fn = check_fn
        self.health_fn = health_fn
        self.requires_env = requires_env
        self.is_async = is_async
        self.description = description
        self.emoji = emoji
        self.max_result_size_chars = max_result_size_chars
        # Optional zero-arg callable returning a dict of schema overrides
        # applied at get_definitions() time. Use for fields that depend on
        # runtime config (e.g. delegate_task's description must reflect the
        # user's current delegation.max_concurrent_children / max_spawn_depth
        # so the model isn't told the wrong limits). The callable is invoked
        # on every get_definitions() call; results are merged shallow on top
        # of the base schema before the {"type": "function", ...} wrap.
        self.dynamic_schema_overrides = dynamic_schema_overrides
        self.schema_validation = (
            schema_validation and name not in _SCHEMA_VALIDATION_OPT_OUTS
        )
        self.validation_plan = (
            _build_validation_plan(self.schema) if self.schema_validation else None
        )


# ---------------------------------------------------------------------------
# check_fn TTL cache
#
# check_fn callables like tools/terminal_tool.check_terminal_requirements
# probe external state (Docker daemon, Modal SDK install, playwright binary
# availability). For a long-lived CLI or gateway process, calling them on
# every get_definitions() is pure waste — external state changes on human
# timescales. Cache results for ~30 s so env-var flips via ``xavani tools``
# or live credential file changes propagate within a turn or two without
# requiring any explicit invalidation.
# ---------------------------------------------------------------------------

_CHECK_FN_TTL_SECONDS = 30.0
_check_fn_cache: Dict[Callable, tuple[float, bool]] = {}
_check_fn_cache_lock = threading.Lock()


def _check_fn_cached(fn: Callable) -> bool:
    """Return bool(fn()), TTL-cached across calls. Swallows exceptions as False."""
    now = time.monotonic()
    with _check_fn_cache_lock:
        cached = _check_fn_cache.get(fn)
        if cached is not None:
            ts, value = cached
            if now - ts < _CHECK_FN_TTL_SECONDS:
                return value
    try:
        value = bool(fn())
    except Exception:
        value = False
    with _check_fn_cache_lock:
        _check_fn_cache[fn] = (now, value)
    return value


def invalidate_check_fn_cache() -> None:
    """Drop all cached ``check_fn`` results. Call after config changes that
    affect tool availability (e.g. ``xavani tools enable``)."""
    with _check_fn_cache_lock:
        _check_fn_cache.clear()


class ToolRegistry:
    """Singleton registry that collects tool schemas + handlers from tool files."""

    def __init__(self):
        self._tools: Dict[str, ToolEntry] = {}
        self._toolset_checks: Dict[str, Callable] = {}
        self._toolset_aliases: Dict[str, str] = {}
        # MCP dynamic refresh can mutate the registry while other threads are
        # reading tool metadata, so keep mutations serialized and readers on
        # stable snapshots.
        self._lock = threading.RLock()
        # Monotonically-increasing generation counter. Bumped on every
        # mutation (register / deregister / register_toolset_alias / MCP
        # refresh). External callers (e.g. get_tool_definitions) can memoize
        # against it: a cache entry keyed on the generation is valid for as
        # long as the generation hasn't changed.
        self._generation: int = 0

    def _snapshot_state(self) -> tuple[List[ToolEntry], Dict[str, Callable]]:
        """Return a coherent snapshot of registry entries and toolset checks."""
        with self._lock:
            return list(self._tools.values()), dict(self._toolset_checks)

    def _snapshot_entries(self) -> List[ToolEntry]:
        """Return a stable snapshot of registered tool entries."""
        return self._snapshot_state()[0]

    def _snapshot_toolset_checks(self) -> Dict[str, Callable]:
        """Return a stable snapshot of toolset availability checks."""
        return self._snapshot_state()[1]

    def _evaluate_toolset_check(self, toolset: str, check: Callable | None) -> bool:
        """Run a toolset check, treating missing or failing checks as unavailable/available."""
        if not check:
            return True
        try:
            return bool(check())
        except Exception:
            logger.debug("Toolset %s check raised; marking unavailable", toolset)
            return False

    def get_entry(self, name: str) -> Optional[ToolEntry]:
        """Return a registered tool entry by name, or None."""
        with self._lock:
            return self._tools.get(name)

    def get_tool_health(self, name: str) -> Optional[Dict[str, Any]]:
        """Run a tool's health_fn (E08). Returns None when no health_fn.

        The health_fn contract: zero-arg callable returning a dict with
        at least ``ok`` (bool) and optionally ``detail`` (str). Exceptions
        are reported as not-ok, never raised.
        """
        entry = self.get_entry(name)
        if entry is None or entry.health_fn is None:
            return None
        try:
            result = entry.health_fn()
            if isinstance(result, dict):
                result.setdefault("ok", False)
                result.setdefault("detail", "")
                return result
            return {"ok": bool(result), "detail": ""}
        except Exception as exc:
            return {"ok": False, "detail": f"{type(exc).__name__}: {exc}"}

    def get_all_tool_health(self) -> Dict[str, Dict[str, Any]]:
        """Run health_fn for every tool that has one (E08)."""
        result: Dict[str, Dict[str, Any]] = {}
        for entry in self._snapshot_entries():
            if entry.health_fn is not None:
                health = self.get_tool_health(entry.name)
                if health is not None:
                    result[entry.name] = health
        return result

    def get_registered_toolset_names(self) -> List[str]:
        """Return sorted unique toolset names present in the registry."""
        return sorted({entry.toolset for entry in self._snapshot_entries()})

    def get_tool_names_for_toolset(self, toolset: str) -> List[str]:
        """Return sorted tool names registered under a given toolset."""
        return sorted(
            entry.name for entry in self._snapshot_entries()
            if entry.toolset == toolset
        )

    def register_toolset_alias(self, alias: str, toolset: str) -> None:
        """Register an explicit alias for a canonical toolset name."""
        with self._lock:
            existing = self._toolset_aliases.get(alias)
            if existing and existing != toolset:
                logger.warning(
                    "Toolset alias collision: '%s' (%s) overwritten by %s",
                    alias, existing, toolset,
                )
            self._toolset_aliases[alias] = toolset
            self._generation += 1

    def get_registered_toolset_aliases(self) -> Dict[str, str]:
        """Return a snapshot of ``{alias: canonical_toolset}`` mappings."""
        with self._lock:
            return dict(self._toolset_aliases)

    def get_toolset_alias_target(self, alias: str) -> Optional[str]:
        """Return the canonical toolset name for an alias, or None."""
        with self._lock:
            return self._toolset_aliases.get(alias)

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register(
        self,
        name: str,
        toolset: str,
        schema: dict,
        handler: Callable,
        check_fn: Callable = None,
        health_fn: Callable = None,
        requires_env: list = None,
        is_async: bool = False,
        description: str = "",
        emoji: str = "",
        max_result_size_chars: int | float | None = None,
        dynamic_schema_overrides: Callable = None,
        schema_validation: bool = True,
        override: bool = False,
    ):
        """Register a tool.  Called at module-import time by each tool file.

        ``override=True`` is an explicit opt-in for plugins that intend to
        replace an existing built-in tool implementation (e.g. swap the
        default browser tool for a headed-Chrome CDP backend). Without it,
        registrations that would shadow an existing tool from a different
        toolset are rejected to prevent accidental overwrites.

        ``schema_validation=False`` opts this tool out of dispatch-time
        argument validation (see the module docstring for the opt-out policy
        and the name-based opt-out list).
        """
        with self._lock:
            existing = self._tools.get(name)
            if existing and existing.toolset != toolset:
                # Allow MCP-to-MCP overwrites (legitimate: server refresh,
                # or two MCP servers with overlapping tool names).
                both_mcp = (
                    existing.toolset.startswith("mcp-")
                    and toolset.startswith("mcp-")
                )
                if both_mcp:
                    logger.debug(
                        "Tool '%s': MCP toolset '%s' overwriting MCP toolset '%s'",
                        name, toolset, existing.toolset,
                    )
                elif override:
                    # Explicit plugin opt-in: replace the existing tool.
                    # Logged at INFO so the override is auditable in agent.log.
                    logger.info(
                        "Tool '%s': toolset '%s' overriding existing toolset '%s' "
                        "(override=True opt-in)",
                        name, toolset, existing.toolset,
                    )
                else:
                    # Reject shadowing — prevent plugins/MCP from overwriting
                    # built-in tools or vice versa.
                    logger.error(
                        "Tool registration REJECTED: '%s' (toolset '%s') would "
                        "shadow existing tool from toolset '%s'. Pass "
                        "override=True to register() if the replacement is "
                        "intentional, or deregister the existing tool first.",
                        name, toolset, existing.toolset,
                    )
                    return
            self._tools[name] = ToolEntry(
                name=name,
                toolset=toolset,
                schema=schema,
                handler=handler,
                check_fn=check_fn,
                health_fn=health_fn,
                requires_env=requires_env or [],
                is_async=is_async,
                description=description or schema.get("description", ""),
                emoji=emoji,
                max_result_size_chars=max_result_size_chars,
                dynamic_schema_overrides=dynamic_schema_overrides,
                schema_validation=schema_validation,
            )
            if check_fn and toolset not in self._toolset_checks:
                self._toolset_checks[toolset] = check_fn
            self._generation += 1

    def deregister(self, name: str) -> None:
        """Remove a tool from the registry.

        Also cleans up the toolset check if no other tools remain in the
        same toolset.  Used by MCP dynamic tool discovery to nuke-and-repave
        when a server sends ``notifications/tools/list_changed``.
        """
        with self._lock:
            entry = self._tools.pop(name, None)
            if entry is None:
                return
            # Drop the toolset check and aliases if this was the last tool in
            # that toolset.
            toolset_still_exists = any(
                e.toolset == entry.toolset for e in self._tools.values()
            )
            if not toolset_still_exists:
                self._toolset_checks.pop(entry.toolset, None)
                self._toolset_aliases = {
                    alias: target
                    for alias, target in self._toolset_aliases.items()
                    if target != entry.toolset
                }
            self._generation += 1
        logger.debug("Deregistered tool: %s", name)

    # ------------------------------------------------------------------
    # Schema retrieval
    # ------------------------------------------------------------------

    def get_definitions(self, tool_names: Set[str], quiet: bool = False) -> List[dict]:
        """Return OpenAI-format tool schemas for the requested tool names.

        Only tools whose ``check_fn()`` returns True (or have no check_fn)
        are included. ``check_fn()`` results are cached for ~30 s via
        :func:`_check_fn_cached` to amortize repeat probes (check_terminal_
        requirements probes modal/docker, browser checks probe playwright,
        etc.); TTL chosen so env-var changes (``xavani tools enable foo``)
        still take effect in near-real-time without forcing a full cache
        flush on every call.
        """
        result = []
        # Per-call cache on top of the 30 s TTL — handles repeat probes of the
        # same check_fn within one definitions pass without re-reading the
        # TTL clock.
        check_results: Dict[Callable, bool] = {}
        entries_by_name = {entry.name: entry for entry in self._snapshot_entries()}
        for name in sorted(tool_names):
            entry = entries_by_name.get(name)
            if not entry:
                continue
            if entry.check_fn:
                if entry.check_fn not in check_results:
                    check_results[entry.check_fn] = _check_fn_cached(entry.check_fn)
                if not check_results[entry.check_fn]:
                    if not quiet:
                        logger.debug("Tool %s unavailable (check failed)", name)
                    continue
            # Ensure schema always has a "name" field — use entry.name as fallback
            schema_with_name = {**entry.schema, "name": entry.name}
            # Apply runtime-dynamic overrides (e.g. delegate_task description
            # depends on current delegation.max_concurrent_children /
            # max_spawn_depth). Caller side (model_tools.get_tool_definitions)
            # already keys its memo on config.yaml mtime + size, so changes
            # to delegation.* in config invalidate the cache automatically.
            if entry.dynamic_schema_overrides is not None:
                try:
                    overrides = entry.dynamic_schema_overrides()
                    if isinstance(overrides, dict):
                        schema_with_name.update(overrides)
                except Exception as exc:
                    logger.warning(
                        "dynamic_schema_overrides for tool %s raised %s; "
                        "using static schema",
                        name, exc,
                    )
            result.append({"type": "function", "function": schema_with_name})
        return result

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    def dispatch(self, name: str, args: dict, **kwargs) -> str:
        """Execute a tool handler by name.

        * Async handlers are bridged automatically via ``_run_async()``.
        * All exceptions are caught and returned as ``{"error": "..."}``
          for consistent error format.
        * Args are validated against the tool's registered schema before the
          handler runs; violations return a ``tool_error``-style string and
          never reach the handler (see module docstring, backlog D78 / S3-2).
        """
        entry = self.get_entry(name)
        if not entry:
            return json.dumps({"error": f"Unknown tool: {name}"})
        plan = entry.validation_plan
        if plan is not None:
            violation = _validate_args(name, args, plan)
            if violation is not None:
                return tool_error(violation)
        try:
            if entry.is_async:
                from model_tools import _run_async
                return _run_async(entry.handler(args, **kwargs))
            return entry.handler(args, **kwargs)
        except Exception as e:
            logger.exception("Tool %s dispatch error: %s", name, e)
            # Route through the sanitizer so framing tokens / CDATA / fences
            # in exception strings don't reach the model as structural noise.
            # See model_tools._sanitize_tool_error for rationale.
            raw = f"Tool execution failed: {type(e).__name__}: {e}"
            try:
                from model_tools import _sanitize_tool_error
                sanitized = _sanitize_tool_error(raw)
            except Exception:
                sanitized = raw  # defensive: never let the sanitizer block error propagation
            return json.dumps({"error": sanitized})

    # ------------------------------------------------------------------
    # Query helpers  (replace redundant dicts in model_tools.py)
    # ------------------------------------------------------------------

    def get_max_result_size(self, name: str, default: int | float | None = None) -> int | float:
        """Return per-tool max result size, or *default* (or global default)."""
        entry = self.get_entry(name)
        if entry and entry.max_result_size_chars is not None:
            return entry.max_result_size_chars
        if default is not None:
            return default
        from tools.budget_config import DEFAULT_RESULT_SIZE_CHARS
        return DEFAULT_RESULT_SIZE_CHARS

    def get_all_tool_names(self) -> List[str]:
        """Return sorted list of all registered tool names."""
        return sorted(entry.name for entry in self._snapshot_entries())

    def get_schema(self, name: str) -> Optional[dict]:
        """Return a tool's raw schema dict, bypassing check_fn filtering.

        Useful for token estimation and introspection where availability
        doesn't matter — only the schema content does.
        """
        entry = self.get_entry(name)
        return entry.schema if entry else None

    def get_toolset_for_tool(self, name: str) -> Optional[str]:
        """Return the toolset a tool belongs to, or None."""
        entry = self.get_entry(name)
        return entry.toolset if entry else None

    def get_emoji(self, name: str, default: str = "⚡") -> str:
        """Return the emoji for a tool, or *default* if unset."""
        entry = self.get_entry(name)
        return (entry.emoji if entry and entry.emoji else default)

    def get_tool_to_toolset_map(self) -> Dict[str, str]:
        """Return ``{tool_name: toolset_name}`` for every registered tool."""
        return {entry.name: entry.toolset for entry in self._snapshot_entries()}

    def is_toolset_available(self, toolset: str) -> bool:
        """Check if a toolset's requirements are met.

        Returns False (rather than crashing) when the check function raises
        an unexpected exception (e.g. network error, missing import, bad config).
        """
        with self._lock:
            check = self._toolset_checks.get(toolset)
        return self._evaluate_toolset_check(toolset, check)

    def check_toolset_requirements(self) -> Dict[str, bool]:
        """Return ``{toolset: available_bool}`` for every toolset."""
        entries, toolset_checks = self._snapshot_state()
        toolsets = sorted({entry.toolset for entry in entries})
        return {
            toolset: self._evaluate_toolset_check(toolset, toolset_checks.get(toolset))
            for toolset in toolsets
        }

    def get_available_toolsets(self) -> Dict[str, dict]:
        """Return toolset metadata for UI display."""
        toolsets: Dict[str, dict] = {}
        entries, toolset_checks = self._snapshot_state()
        for entry in entries:
            ts = entry.toolset
            if ts not in toolsets:
                toolsets[ts] = {
                    "available": self._evaluate_toolset_check(
                        ts, toolset_checks.get(ts)
                    ),
                    "tools": [],
                    "description": "",
                    "requirements": [],
                }
            toolsets[ts]["tools"].append(entry.name)
            if entry.requires_env:
                for env in entry.requires_env:
                    if env not in toolsets[ts]["requirements"]:
                        toolsets[ts]["requirements"].append(env)
        return toolsets

    def get_toolset_requirements(self) -> Dict[str, dict]:
        """Build a TOOLSET_REQUIREMENTS-compatible dict for backward compat."""
        result: Dict[str, dict] = {}
        entries, toolset_checks = self._snapshot_state()
        for entry in entries:
            ts = entry.toolset
            if ts not in result:
                result[ts] = {
                    "name": ts,
                    "env_vars": [],
                    "check_fn": toolset_checks.get(ts),
                    "setup_url": None,
                    "tools": [],
                }
            if entry.name not in result[ts]["tools"]:
                result[ts]["tools"].append(entry.name)
            for env in entry.requires_env:
                if env not in result[ts]["env_vars"]:
                    result[ts]["env_vars"].append(env)
        return result

    def check_tool_availability(self, quiet: bool = False):
        """Return (available_toolsets, unavailable_info) like the old function."""
        available = []
        unavailable = []
        seen = set()
        entries, toolset_checks = self._snapshot_state()
        for entry in entries:
            ts = entry.toolset
            if ts in seen:
                continue
            seen.add(ts)
            if self._evaluate_toolset_check(ts, toolset_checks.get(ts)):
                available.append(ts)
            else:
                unavailable.append({
                    "name": ts,
                    "env_vars": entry.requires_env,
                    "tools": [e.name for e in entries if e.toolset == ts],
                })
        return available, unavailable


# Module-level singleton
registry = ToolRegistry()


# ---------------------------------------------------------------------------
# Helpers for tool response serialization
# ---------------------------------------------------------------------------
# Every tool handler must return a JSON string.  These helpers eliminate the
# boilerplate ``json.dumps({"error": msg}, ensure_ascii=False)`` that appears
# hundreds of times across tool files.
#
# Usage:
#   from tools.registry import registry, tool_error, tool_result
#
#   return tool_error("something went wrong")
#   return tool_error("not found", code=404)
#   return tool_result(success=True, data=payload)
#   return tool_result(items)            # pass a dict directly


def tool_error(message, **extra) -> str:
    """Return a JSON error string for tool handlers.

    >>> tool_error("file not found")
    '{"error": "file not found"}'
    >>> tool_error("bad input", success=False)
    '{"error": "bad input", "success": false}'
    """
    result = {"error": str(message)}
    if extra:
        result.update(extra)
    return json.dumps(result, ensure_ascii=False)


def tool_result(data=None, **kwargs) -> str:
    """Return a JSON result string for tool handlers.

    Accepts a dict positional arg *or* keyword arguments (not both):

    >>> tool_result(success=True, count=42)
    '{"success": true, "count": 42}'
    >>> tool_result({"key": "value"})
    '{"key": "value"}'
    """
    if data is not None:
        return json.dumps(data, ensure_ascii=False)
    return json.dumps(kwargs, ensure_ascii=False)
