#!/usr/bin/env python3

# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""
security_scan — heuristic security scanner for local files and directories.

Concept adapted from oh-my-pi's security_scan tool. Walks a target path
(skipping VCS/vendor/cache directories and binary files) and applies regex
heuristics for common vulnerability patterns: hardcoded secrets, eval/exec,
unsafe deserialization, shell=True subprocesses, SQL string construction,
disabled TLS verification, Flask debug mode, and weak hashing.

When the ``bandit`` package happens to be importable, it is additionally
consulted in-process (no subprocess) for .py files; any failure falls back
silently to heuristics alone.

Detected secrets are ALWAYS masked in reported excerpts — only a short
prefix/suffix survives, the middle is replaced with ``***``.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import bandit as _bandit  # type: ignore[import-not-found]

    _BANDIT_AVAILABLE = True
except Exception:  # pragma: no cover - depends on environment
    _bandit = None  # type: ignore[assignment]
    _BANDIT_AVAILABLE = False

SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
}

MAX_FILE_BYTES = 512 * 1024
DEFAULT_MAX_FILES = 200
MAX_EXCERPT_CHARS = 80
_BINARY_SNIFF_BYTES = 8192

_SEVERITY_ORDER = {"HIGH": 0, "MED": 1, "LOW": 2}
_SUMMARY_KEYS = ("HIGH", "MED", "LOW")

_AWS_KEY_RE = re.compile(r"\b(?P<secret>(?:AKIA|ASIA)[0-9A-Z]{16})\b")
_GITHUB_TOKEN_RE = re.compile(r"\b(?P<secret>gh[pousr]_[A-Za-z0-9]{16,})\b")
_OPENAI_STYLE_RE = re.compile(
    r"\b(?P<secret>sk-(?:proj-)?[A-Za-z0-9_\-]{16,})"
)
_SLACK_TOKEN_RE = re.compile(r"\b(?P<secret>xox[baprs]-[A-Za-z0-9\-]{10,})\b")
_GENERIC_ASSIGN_RE = re.compile(
    r"(?i)\b(?:api[_-]?key|apikey|secret|token|passwd|password)\s*[=:]\s*"
    r"[\"']?(?P<secret>[A-Za-z0-9_\-+/=]{8,})"
)

_PLACEHOLDER_MARKERS = (
    "example",
    "changeme",
    "change_me",
    "placeholder",
    "xxxx",
    "****",
    "<",
    "${",
    "%s",
    "{}",
    "your-",
    "your_",
    "dummy",
    "sample",
)


class _Rule:
    __slots__ = ("rule_id", "severity", "description", "pattern", "accept")

    def __init__(
        self,
        rule_id: str,
        severity: str,
        description: str,
        pattern: "re.Pattern[str]",
        accept: Optional[Callable[[re.Match[str]], bool]] = None,
    ) -> None:
        self.rule_id = rule_id
        self.severity = severity
        self.description = description
        self.pattern = pattern
        self.accept = accept


def _yaml_without_loader(match: re.Match[str]) -> bool:
    return "loader" not in match.group(1).lower()


_generic_value_not_placeholder = (
    lambda match: not _is_placeholder(match.group("secret"))
)


_RULES: Tuple[_Rule, ...] = (
    _Rule(
        "hardcoded_secret",
        "HIGH",
        "Possible hardcoded credential",
        _GENERIC_ASSIGN_RE,
        _generic_value_not_placeholder,
    ),
    _Rule(
        "hardcoded_secret",
        "HIGH",
        "AWS access key ID in source",
        _AWS_KEY_RE,
    ),
    _Rule(
        "hardcoded_secret",
        "HIGH",
        "GitHub personal access token in source",
        _GITHUB_TOKEN_RE,
    ),
    _Rule(
        "hardcoded_secret",
        "HIGH",
        "OpenAI-style API key in source",
        _OPENAI_STYLE_RE,
    ),
    _Rule(
        "hardcoded_secret",
        "HIGH",
        "Slack token in source",
        _SLACK_TOKEN_RE,
    ),
    _Rule(
        "dangerous_eval_exec",
        "HIGH",
        "Use of eval()/exec() on dynamic input",
        re.compile(r"\b(?:eval|exec)\s*\("),
    ),
    _Rule(
        "subprocess_shell_true",
        "HIGH",
        "Subprocess invoked with shell=True",
        re.compile(r"\bshell\s*=\s*True\b"),
    ),
    _Rule(
        "yaml_load_no_loader",
        "HIGH",
        "yaml.load() without an explicit safe Loader",
        re.compile(r"\byaml\.loads?\s*\(([^()]*)\)"),
        _yaml_without_loader,
    ),
    _Rule(
        "tls_verify_disabled",
        "HIGH",
        "TLS certificate verification disabled (verify=False)",
        re.compile(r"\bverify\s*=\s*False\b"),
    ),
    _Rule(
        "pickle_load",
        "MED",
        "Unsafe pickle deserialization",
        re.compile(r"\bpickle\.loads?\s*\("),
    ),
    _Rule(
        "sql_string_build",
        "MED",
        "SQL query built via f-string interpolation",
        re.compile(
            r"f[\"']\s*(?:SELECT\b|INSERT\b|UPDATE\b|DELETE\b)", re.IGNORECASE
        ),
    ),
    _Rule(
        "flask_debug_true",
        "MED",
        "Flask dev server running with debug=True",
        re.compile(r"\bapp\.run\s*\([^)]*\bdebug\s*=\s*True"),
    ),
    _Rule(
        "weak_hash",
        "LOW",
        "Weak hash algorithm (MD5/SHA-1), unsuitable for passwords",
        re.compile(r"\bhashlib\.(?:md5|sha1)\s*\("),
    ),
)

_SECRET_SPAN_PATTERNS: Tuple[Tuple[str, "re.Pattern[str]"], ...] = (
    ("aws_key", _AWS_KEY_RE),
    ("github_token", _GITHUB_TOKEN_RE),
    ("openai_style_key", _OPENAI_STYLE_RE),
    ("slack_token", _SLACK_TOKEN_RE),
    ("generic_assignment", _GENERIC_ASSIGN_RE),
)


def _is_placeholder(value: str) -> bool:
    lowered = value.lower()
    return any(marker in lowered for marker in _PLACEHOLDER_MARKERS)


def _mask_value(value: str) -> str:
    if len(value) <= 8:
        return "***"
    return value[:4] + "***" + value[-2:]


def _secret_spans(line: str) -> List[Tuple[int, int]]:
    spans: List[Tuple[int, int]] = []
    for _, pattern in _SECRET_SPAN_PATTERNS:
        for match in pattern.finditer(line):
            group = match.group("secret") if "secret" in match.groupdict() else None
            if group is None:
                continue
            if pattern is _GENERIC_ASSIGN_RE and _is_placeholder(group):
                continue
            spans.append(match.span("secret"))
    if not spans:
        return []
    spans.sort()
    merged: List[List[int]] = [list(spans[0])]
    for start, end in spans[1:]:
        if start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [(span[0], span[1]) for span in merged]


def _masked_excerpt(raw_line: str) -> str:
    spans = _secret_spans(raw_line)
    if spans:
        pieces: List[str] = []
        cursor = 0
        for start, end in spans:
            pieces.append(raw_line[cursor:start])
            pieces.append(_mask_value(raw_line[start:end]))
            cursor = end
        pieces.append(raw_line[cursor:])
        line = "".join(pieces)
    else:
        line = raw_line
    return line.strip()[:MAX_EXCERPT_CHARS]


_BANDIT_SEVERITY_MAP = {1: "LOW", 2: "MED", 3: "HIGH"}


def _run_bandit_on_file(file_path: Path) -> List[Dict[str, Any]]:
    if not _BANDIT_AVAILABLE or file_path.suffix != ".py":
        return []
    try:
        from bandit.core import config as bandit_config
        from bandit.core import manager as bandit_manager

        conf = bandit_config.BanditConfig()
        mgr = bandit_manager.BanditManager(conf, "file")
        mgr.discover_files([str(file_path)], True)
        mgr.run_tests()
        issues = mgr.get_issue_list()
    except Exception:
        return []

    results: List[Dict[str, Any]] = []
    for issue in issues:
        try:
            code = getattr(issue, "code", "") or ""
            first_line = code.strip().splitlines()[0][:MAX_EXCERPT_CHARS] if code else ""
            results.append(
                {
                    "rule_id": f"bandit:{getattr(issue, 'test_id', 'unknown')}",
                    "severity": _BANDIT_SEVERITY_MAP.get(
                        int(getattr(issue, "severity", 1)), "LOW"
                    ),
                    "file": str(file_path),
                    "line_number": int(getattr(issue, "lineno", 0) or 0),
                    "excerpt": _masked_excerpt(first_line),
                }
            )
        except Exception:
            continue
    return results


def _looks_binary(file_path: Path) -> bool:
    try:
        with open(file_path, "rb") as fh:
            chunk = fh.read(_BINARY_SNIFF_BYTES)
    except OSError:
        return True
    return b"\x00" in chunk


def _collect_files(root: Path, limit: int) -> List[Path]:
    collected: List[Path] = []
    stack: List[Path] = [root]
    while stack and len(collected) < limit:
        current = stack.pop()
        if current.is_file():
            collected.append(current)
            continue
        if not current.is_dir():
            continue
        try:
            children = sorted(current.iterdir(), key=lambda p: p.name)
        except OSError:
            continue
        pending_dirs: List[Path] = []
        for child in children:
            if child.is_symlink():
                continue
            if child.is_dir():
                if child.name not in SKIP_DIRS:
                    pending_dirs.append(child)
            elif child.is_file():
                if len(collected) < limit:
                    collected.append(child)
        stack.extend(reversed(pending_dirs))
    return collected[:limit]


def _scan_file(file_path: Path) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            for line_number, raw_line in enumerate(fh, start=1):
                for rule in _RULES:
                    for match in rule.pattern.finditer(raw_line):
                        if rule.accept is not None and not rule.accept(match):
                            continue
                        findings.append(
                            {
                                "rule_id": rule.rule_id,
                                "severity": rule.severity,
                                "file": str(file_path),
                                "line_number": line_number,
                                "excerpt": _masked_excerpt(raw_line),
                            }
                        )
                        break
    except OSError:
        return []

    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for finding in findings:
        key = (finding["rule_id"], finding["line_number"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(finding)

    unique.extend(_run_bandit_on_file(file_path))
    return unique


def _empty_result(scan_path: str) -> Dict[str, Any]:
    return {
        "success": True,
        "path": scan_path,
        "files_scanned": 0,
        "findings": [],
        "summary": {"HIGH": 0, "MED": 0, "LOW": 0},
    }


def _summarize(findings: List[Dict[str, Any]]) -> Dict[str, int]:
    summary = {key: 0 for key in _SUMMARY_KEYS}
    for finding in findings:
        summary[finding["severity"]] = summary.get(finding["severity"], 0) + 1
    return summary


def _scan(root: Path, max_files: int) -> Dict[str, Any]:
    if max_files < 1:
        max_files = 1
    candidates = _collect_files(root, max_files * 4)
    findings: List[Dict[str, Any]] = []
    files_scanned = 0
    for candidate in candidates:
        if files_scanned >= max_files:
            break
        if not _is_scanable_text_file(candidate):
            continue
        files_scanned += 1
        findings.extend(_scan_file(candidate))

    findings.sort(
        key=lambda f: (
            f["file"],
            f["line_number"],
            _SEVERITY_ORDER.get(f["severity"], 99),
            f["rule_id"],
        )
    )
    return {
        "success": True,
        "path": str(root),
        "files_scanned": files_scanned,
        "findings": findings,
        "summary": _summarize(findings),
    }


def _is_scanable_text_file(file_path: Path) -> bool:
    try:
        if file_path.stat().st_size > MAX_FILE_BYTES:
            return False
    except OSError:
        return False
    return not _looks_binary(file_path)


def security_scan(
    path: str, max_files: int = DEFAULT_MAX_FILES, scan_depth: str = "heuristic"
) -> Dict[str, Any]:
    """Scan a file or directory tree with heuristic security rules."""
    del scan_depth
    try:
        target = Path(str(path)).expanduser()
        if not target.exists():
            return {
                "success": False,
                "path": str(path),
                "error": f"path not found: {target}",
                "files_scanned": 0,
                "findings": [],
                "summary": {"HIGH": 0, "MED": 0, "LOW": 0},
            }
        return _scan(target.resolve(), int(max_files))
    except Exception as exc:
        return {
            "success": False,
            "path": str(path),
            "error": f"{type(exc).__name__}: {exc}",
            "files_scanned": 0,
            "findings": [],
            "summary": {"HIGH": 0, "MED": 0, "LOW": 0},
        }


_SECURITY_SCAN_SCHEMA = {
    "name": "security_scan",
    "description": (
        "Heuristic security scan of a file or directory tree. Detects "
        "hardcoded secrets (always masked in output), eval/exec, unsafe "
        "deserialization, shell=True subprocesses, SQL string building, "
        "disabled TLS verification, Flask debug mode, and weak hashes."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File or directory to scan.",
            },
            "max_files": {
                "type": "integer",
                "description": (
                    "Maximum number of files to scan (default 200). "
                    "Files are visited in deterministic order."
                ),
            },
            "scan_depth": {
                "type": "string",
                "enum": ["heuristic"],
                "description": "Scan mode; only heuristic analysis is supported.",
            },
        },
        "required": ["path"],
    },
}


def _handle_security_scan(args: Dict[str, Any], **_: Any) -> str:
    return json.dumps(
        security_scan(
            path=args.get("path", ""),
            max_files=int(args.get("max_files", DEFAULT_MAX_FILES)),
            scan_depth=str(args.get("scan_depth", "heuristic")),
        ),
        indent=2,
        default=str,
    )


from tools.registry import registry  # noqa: E402

registry.register(
    name="security_scan",
    toolset="debugging",
    schema=_SECURITY_SCAN_SCHEMA,
    handler=_handle_security_scan,
    description=(
        "Heuristic security scan of a file or directory: hardcoded secrets "
        "(masked), eval/exec, shell=True, unsafe yaml/pickle, SQL injection "
        "strings, verify=False, Flask debug, weak hashes."
    ),
    emoji="\U0001f6e1",
)
