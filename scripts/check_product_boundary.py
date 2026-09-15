# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""Task 24a — product and legal boundary scan (agent repository).

Code Pack Q defines two scan categories:

* ``product`` — default product links and default remote services.
* ``legal``   — required attribution and provenance surfaces.

This is a *scanner*, not a word-deletion tool. It reports prohibited default
behavior (upstream subscription/portal/telemetry endpoints, un-opted update
checks, undeclared default network targets) and verifies that the required
legal attribution is present. It never edits a file.

Why a curated surface list instead of a repo-wide walk: provider catalog
entries are user-selected endpoints, not product links (Code Pack Q). A
repo-wide host scan would flag hundreds of legitimate provider endpoints, so
the scan runs over a reviewed list of default product surfaces and over
declared default services.

Commands::

    python3 scripts/check_product_boundary.py           # human report
    python3 scripts/check_product_boundary.py --json    # machine-readable
    python3 scripts/check_product_boundary.py --root DIR

Exit code 0 only when every rule passes.

Scope note: this script covers the agent repository half of Task 24. The
desktop half (THIRD_PARTY_NOTICES.md, src/main.js, src/renderer/app.js,
scripts/build-macos.sh) is Task 24b.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Boundary allowlist — Code Pack Q
# ---------------------------------------------------------------------------

#: Code Pack Q's product surface allowlist, verbatim. ``owned_hosts`` is the
#: *product* allowlist; it is deliberately not a ban on user-selected model
#: providers (see ``PROVIDER_CATALOG_HOSTS``).
BOUNDARY_CONFIG: Dict[str, object] = {
    "product_names": ["Xavani", "Enternovate"],
    "owned_hosts": ["enternovate.com", "www.enternovate.com"],
    "release_repositories": ["enternovate/xavani-agent", "enternovate/xavani-desktop"],
    "legal_files": ["LICENSE", "THIRD_PARTY_NOTICES.md"],
    "default_remote_inference": False,
    "default_telemetry": False,
    "default_update_checks": False,
}

#: Apex domains of the upstream project. No *default* product request may
#: target one of these, at any subdomain (``portal.``, ``api.``, ...). Matching
#: by apex avoids inventing subdomain names.
UPSTREAM_APEX_DOMAINS = frozenset({"nousresearch.com"})

#: Hosts published by Enternovate outside the pack's product-domain allowlist.
#: ``enternovate.co.za`` is declared in ``acp_registry/agent.json`` and
#: ``xavani_constants.py`` as the publisher's product documentation host.
PUBLISHER_HOSTS = frozenset({"enternovate.co.za", "www.enternovate.co.za"})

#: Endpoints of user-selected model providers. Declared, and never treated as
#: an undeclared product host (Code Pack Q: "Scan default product links
#: separately from provider catalogs").
PROVIDER_CATALOG_HOSTS = frozenset(
    {
        "openrouter.ai",
        "ai-gateway.vercel.sh",
        "api.openai.com",
        "api.anthropic.com",
        "ollama.com",
        "ai.azure.com",
        "generativelanguage.googleapis.com",
        "mcp.notion.com",
        "honcho.dev",
        "app.honcho.dev",
    }
)

#: Non-provider functional hosts that a default product surface may reference:
#: the release repository, distribution registries, loopback, schema hosts.
DECLARED_FUNCTIONAL_HOSTS = frozenset(
    {
        "github.com",
        "raw.githubusercontent.com",
        "pypi.org",
        "files.pythonhosted.org",
        "json-schema.org",
        "localhost",
        "127.0.0.1",
        "0.0.0.0",
    }
)


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    """One boundary rule. ``category`` is ``product`` or ``legal``."""

    id: str
    category: str
    description: str


RULES: Tuple[Rule, ...] = (
    Rule("P1", "product", "No default product link targets an upstream subscription, portal, or telemetry host."),
    Rule("P2", "product", "Every default product link host is owned or declared."),
    Rule("P3", "product", "No default telemetry request — including one to an owned host."),
    Rule("P4", "product", "Remote inference is not enabled by default."),
    Rule("P5", "product", "An un-opted default update check targets an owned release repository or a declared registry."),
    Rule("P6", "product", "Declared default services match the source that implements them."),
    Rule("L1", "legal", "Required legal files exist and are non-empty."),
    Rule("L2", "legal", "Required attribution is retained in the legal files."),
    Rule("L3", "legal", "Every bundled third-party notice is declared in THIRD_PARTY_NOTICES.md."),
    Rule("A1", "product", "Every configured surface and probe path resolves on disk."),
)

RULES_BY_ID: Dict[str, Rule] = {rule.id: rule for rule in RULES}


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Finding:
    """A single rule violation."""

    rule: str
    category: str
    path: str
    detail: str
    line: Optional[int] = None

    def as_dict(self) -> Dict[str, object]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Surfaces
# ---------------------------------------------------------------------------

#: ``kind`` controls which rules apply:
#:   * ``runtime``          — shipped code/metadata that renders or issues a
#:                            default request. P1 + P2 apply.
#:   * ``docs``             — product documentation. P1 applies (a prohibited
#:                            host is prohibited anywhere), P2 does not: badge,
#:                            illustration and standards links are not default
#:                            product requests.
#:   * ``provider_catalog`` — user-selected provider endpoints. Link rules do
#:                            not apply (Code Pack Q).
#:   * ``legal``            — attribution surfaces. Link rules do not apply;
#:                            the L-rules require the attribution instead.
PRODUCT_SURFACES: Tuple[Tuple[str, str], ...] = (
    ("README.md", "docs"),
    ("AGENTS.md", "docs"),
    ("CONTRIBUTING.md", "docs"),
    ("CHANGELOG.md", "docs"),
    ("SECURITY.md", "docs"),
    ("pyproject.toml", "runtime"),
    ("acp_registry/agent.json", "runtime"),
    ("xavani.py", "runtime"),
    ("xavani_cli/banner.py", "runtime"),
    ("xavani_constants.py", "runtime"),
    ("scripts/release.py", "runtime"),
    ("cli-config.yaml.example", "provider_catalog"),
)


@dataclass(frozen=True)
class FileException:
    """A file-specific exception with a stated legal purpose.

    Code Pack Q forbids whitelisting a directory because it contains one legal
    notice; exceptions are per path, per rule, and must state why.
    """

    path: str
    rules: Tuple[str, ...]
    reason: str


FILE_EXCEPTIONS: Tuple[FileException, ...] = (
    FileException(
        path="LICENSE",
        rules=("P1", "P2"),
        reason=(
            "Legal attribution file: the MIT license of the derived-work ancestor must "
            "retain its upstream copyright holder and source URL. Attribution is not branding."
        ),
    ),
    FileException(
        path="THIRD_PARTY_NOTICES.md",
        rules=("P1", "P2"),
        reason=(
            "Legal attribution file: required to name upstream copyright holders and their "
            "licenses. Code Pack Q test: a legal notice naming an upstream holder passes."
        ),
    ),
)


def exceptions_for(path: str) -> Dict[str, str]:
    """Return ``{rule_id: reason}`` for a path."""
    out: Dict[str, str] = {}
    for exc in FILE_EXCEPTIONS:
        if exc.path == path:
            for rule_id in exc.rules:
                out[rule_id] = exc.reason
    return out


# ---------------------------------------------------------------------------
# Link classification
# ---------------------------------------------------------------------------

_URL_RE = re.compile(r"https?://[^\s\"'`<>\\)\]}]+")
_TRAILING = ".,;:!?'\""

OWNED = "owned"
PUBLISHER = "publisher"
PROVIDER = "provider"
DECLARED = "declared"
PROHIBITED = "prohibited"
UNDECLARED = "undeclared"


def extract_urls(text: str) -> List[Tuple[int, str]]:
    """Return ``(line_number, url)`` for every URL in ``text``."""
    found: List[Tuple[int, str]] = []
    for line_no, line in enumerate(text.splitlines(), 1):
        for match in _URL_RE.finditer(line):
            url = match.group(0).rstrip(_TRAILING)
            found.append((line_no, url))
    return found


def host_of(url: str) -> str:
    """Return the lowercase host of ``url`` (empty when unparseable)."""
    try:
        host = urlsplit(url).hostname
    except ValueError:
        return ""
    return (host or "").lower()


def is_prohibited_host(host: str) -> bool:
    """True when ``host`` is the upstream project at any subdomain."""
    host = (host or "").lower()
    return any(host == apex or host.endswith("." + apex) for apex in UPSTREAM_APEX_DOMAINS)


def classify_host(host: str) -> str:
    """Classify a link host against the boundary allowlist."""
    host = (host or "").lower()
    if not host:
        return UNDECLARED
    if is_prohibited_host(host):
        return PROHIBITED
    owned = {str(h).lower() for h in BOUNDARY_CONFIG["owned_hosts"]}  # type: ignore[union-attr]
    if host in owned:
        return OWNED
    if host in PUBLISHER_HOSTS:
        return PUBLISHER
    if host in PROVIDER_CATALOG_HOSTS:
        return PROVIDER
    if host in DECLARED_FUNCTIONAL_HOSTS:
        return DECLARED
    return UNDECLARED


def is_release_repository_target(target: str) -> bool:
    """True when ``target`` points at an owned release repository."""
    repositories = [str(r) for r in BOUNDARY_CONFIG["release_repositories"]]  # type: ignore[union-attr]
    return any(repo in target for repo in repositories)


# ---------------------------------------------------------------------------
# Product rule implementations
# ---------------------------------------------------------------------------


def scan_text(text: str, *, path: str = "<memory>", kind: str = "runtime") -> List[Finding]:
    """Scan a product surface's text for prohibited / undeclared default links."""
    if kind in {"legal", "provider_catalog"}:
        return []

    skip = exceptions_for(path)
    findings: List[Finding] = []
    for line_no, url in extract_urls(text):
        host = host_of(url)
        if is_prohibited_host(host):
            if "P1" in skip:
                continue
            findings.append(
                Finding(
                    rule="P1",
                    category="product",
                    path=path,
                    line=line_no,
                    detail=f"default product link targets upstream subscription/portal host: {url}",
                )
            )
            continue
        if kind != "runtime":
            continue
        if "P2" in skip:
            continue
        if classify_host(host) == UNDECLARED:
            findings.append(
                Finding(
                    rule="P2",
                    category="product",
                    path=path,
                    line=line_no,
                    detail=(
                        f"undeclared default host '{host}': declare it as owned, publisher, "
                        f"provider or functional before shipping it as a default link"
                    ),
                )
            )
    return findings


@dataclass(frozen=True)
class DefaultService:
    """A service the product may contact without the user asking for it."""

    name: str
    category: str  # telemetry | remote_inference | update_check
    target: str
    enabled_by_default: bool
    requires_user_action: bool = False
    evidence: str = ""


def check_default_service(service: DefaultService) -> List[Finding]:
    """Flag a prohibited default service.

    * telemetry — fails whenever it is on by default, whatever the host.
    * remote_inference — fails when on by default, unless the endpoint is a
      user-selected provider endpoint.
    * update_check — fails when un-opted and not aimed at the owned release
      repository or a declared registry.
    """
    if not service.enabled_by_default:
        return []

    host = host_of(service.target)
    if service.category == "telemetry":
        return [
            Finding(
                rule="P3",
                category="product",
                path=service.name,
                detail=(
                    "default telemetry request is prohibited; a request to an owned host "
                    "is still prohibited (Code Pack Q)"
                ),
            )
        ]

    if service.category == "remote_inference":
        if classify_host(host) in {PROHIBITED, OWNED, PUBLISHER, UNDECLARED}:
            return [
                Finding(
                    rule="P4",
                    category="product",
                    path=service.name,
                    detail=f"remote inference is enabled by default against {service.target!r}",
                )
            ]
        return []

    if service.category == "update_check":
        if service.requires_user_action:
            return []
        if is_release_repository_target(service.target):
            return []
        if classify_host(host) == DECLARED:
            return []
        return [
            Finding(
                rule="P5",
                category="product",
                path=service.name,
                detail=(
                    f"un-opted default update check targets {service.target!r}; it must be "
                    f"user-initiated or point at an owned release repository"
                ),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Default-service declarations and source probes
# ---------------------------------------------------------------------------

#: The default services this repository actually ships, as reviewed for Task
#: 24a. Every entry is verified against the source that implements it by
#: ``SOURCE_PROBES`` — a stale declaration is a P6 failure.
DEFAULT_SERVICES: Tuple[DefaultService, ...] = (
    DefaultService(
        name="startup-update-check",
        category="update_check",
        target="https://github.com/enternovate/xavani-agent.git",
        enabled_by_default=True,
        requires_user_action=False,
        evidence="xavani_cli/banner.py check_for_updates() compares the checkout against the owned release repository.",
    ),
    DefaultService(
        name="package-version-lookup",
        category="update_check",
        target="https://pypi.org/pypi/{package}/json",
        enabled_by_default=True,
        requires_user_action=False,
        evidence="xavani_cli/banner.py resolves the published version from the distribution registry.",
    ),
    DefaultService(
        name="telemetry",
        category="telemetry",
        target="",
        enabled_by_default=False,
        evidence='xavani.py forces XAVANI_DISABLE_TELEMETRY=1 and DO_NOT_TRACK=1 at import time.',
    ),
    DefaultService(
        name="managed-remote-inference",
        category="remote_inference",
        target="",
        enabled_by_default=False,
        evidence="tools/tool_backend_helpers.py managed_nous_tools_enabled() returns False without a signed-in subscription.",
    ),
)


@dataclass(frozen=True)
class SourceProbe:
    """Assert a documented fact about the source that backs a declaration."""

    id: str
    path: str
    pattern: str
    description: str
    expect: str = "present"  # present | absent
    rule: str = "P6"


SOURCE_PROBES: Tuple[SourceProbe, ...] = (
    SourceProbe(
        "telemetry-off",
        "xavani.py",
        r'os\.environ\["XAVANI_DISABLE_TELEMETRY"\]\s*=\s*"1"',
        "launcher forces XAVANI_DISABLE_TELEMETRY=1",
    ),
    SourceProbe(
        "do-not-track",
        "xavani.py",
        r'os\.environ\["DO_NOT_TRACK"\]\s*=\s*"1"',
        "launcher forces DO_NOT_TRACK=1",
    ),
    SourceProbe(
        "update-target-owned",
        "xavani_cli/banner.py",
        r"enternovate/xavani-agent\.git",
        "default update check targets the owned release repository",
    ),
    SourceProbe(
        "no-upstream-update-target",
        "xavani_cli/banner.py",
        r"nousresearch",
        "default update check names no upstream host",
        expect="absent",
    ),
    SourceProbe(
        "remote-inference-opt-in",
        "tools/tool_backend_helpers.py",
        r'if not status\.get\("logged_in"\)',
        "managed remote inference requires a signed-in subscription",
    ),
    SourceProbe(
        "notices-name-ancestor",
        "THIRD_PARTY_NOTICES.md",
        r"Nous Research",
        "the notices file retains the derived-work ancestor attribution",
    ),
)


# ---------------------------------------------------------------------------
# Legal rules
# ---------------------------------------------------------------------------

#: Attribution that must be retained in the shipped legal files.
REQUIRED_ATTRIBUTION: Tuple[Tuple[str, str, str], ...] = (
    ("LICENSE", r"^MIT License", "MIT license identifier"),
    ("LICENSE", r"Copyright \(c\) 2025 Nous Research", "derived-work copyright — Nous Research"),
    ("LICENSE", r"Copyright \(c\) 2025-2026 Enternovate", "derivative-work copyright — Enternovate"),
    ("THIRD_PARTY_NOTICES.md", r"Nous Research", "derived-work ancestor named"),
    ("THIRD_PARTY_NOTICES.md", r"MIT License", "ancestor license named"),
    ("THIRD_PARTY_NOTICES.md", r"Mario Zechner", "upstream ported-project copyright holder"),
    ("THIRD_PARTY_NOTICES.md", r"Can B.l.k", "upstream ported-project copyright holder"),
    ("THIRD_PARTY_NOTICES.md", r"Stencil Labs, Inc\.", "upstream ported-project copyright holder"),
)

#: Bundled third-party components whose notice file must exist on disk. The
#: declaredness check below is discovery-based, so a newly vendored component
#: cannot slip past it; this list guards against silent deletion of the known
#: ones. Mirrored trees list every copy.
REQUIRED_BUNDLED_NOTICES: Tuple[Tuple[str, str], ...] = (
    ("plugins/xavani-achievements/LICENSE", "xavani-achievements plugin"),
    ("skills/creative/humanizer/LICENSE", "humanizer skill"),
    ("oag_skills/creative/humanizer/LICENSE", "humanizer skill (mirror)"),
    ("skills/productivity/powerpoint/LICENSE.txt", "powerpoint skill"),
    ("oag_skills/productivity/powerpoint/LICENSE.txt", "powerpoint skill (mirror)"),
    ("skills/creative/pixel-art/ATTRIBUTION.md", "pixel-art skill"),
    ("oag_skills/creative/pixel-art/ATTRIBUTION.md", "pixel-art skill (mirror)"),
    ("oag_skills/ponytail/ATTRIBUTION.md", "ponytail skill"),
    ("optional-skills/cybersecurity/NOTICE", "cybersecurity skills"),
    ("optional-skills/cybersecurity/ATTRIBUTION.md", "cybersecurity skills attribution"),
)

#: Trees that can bundle third-party notice files. Discovery is dynamic so a
#: newly vendored component cannot slip past the L3 declaration check.
_NOTICE_TREES: Tuple[str, ...] = ("skills", "oag_skills", "optional-skills", "plugins")
_NOTICE_NAME_RE = re.compile(r"(?i)^(?:LICENSE|LICENCE|NOTICE|ATTRIBUTION|COPYING)(?:\..+)?$")


def discover_bundled_notices(root: Path = REPO_ROOT) -> List[str]:
    """Every notice-like file under the bundled trees, as repo-relative paths."""
    found: List[str] = []
    for tree in _NOTICE_TREES:
        base = root / tree
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and _NOTICE_NAME_RE.match(path.name):
                found.append(path.relative_to(root).as_posix())
    return found


def scan_legal(root: Path = REPO_ROOT) -> List[Finding]:
    """Verify the required legal files, attribution, and bundled notices."""
    findings: List[Finding] = []

    for name in BOUNDARY_CONFIG["legal_files"]:  # type: ignore[union-attr]
        path = root / str(name)
        if not path.is_file():
            findings.append(
                Finding("L1", "legal", str(name), "required legal file is missing")
            )
        elif not path.read_text(encoding="utf-8").strip():
            findings.append(
                Finding("L1", "legal", str(name), "required legal file is empty")
            )

    for name, pattern, description in REQUIRED_ATTRIBUTION:
        path = root / name
        if not path.is_file():
            continue  # already reported by L1
        text = path.read_text(encoding="utf-8")
        if not re.search(pattern, text, re.MULTILINE):
            findings.append(
                Finding("L2", "legal", name, f"required attribution missing: {description}")
            )

    notices_path = root / "THIRD_PARTY_NOTICES.md"
    notices = notices_path.read_text(encoding="utf-8") if notices_path.is_file() else ""
    for bundle_path, component in REQUIRED_BUNDLED_NOTICES:
        if not (root / bundle_path).is_file():
            findings.append(
                Finding("L3", "legal", bundle_path, f"bundled notice for {component} is missing on disk")
            )
    for bundle_path in discover_bundled_notices(root):
        if bundle_path not in notices:
            findings.append(
                Finding(
                    "L3",
                    "legal",
                    bundle_path,
                    "bundled notice file is not declared in THIRD_PARTY_NOTICES.md",
                )
            )
    return findings


# ---------------------------------------------------------------------------
# Repository scan
# ---------------------------------------------------------------------------


def scan_repo(root: Path = REPO_ROOT) -> List[Finding]:
    """Run every rule over ``root`` and return the findings."""
    findings: List[Finding] = []

    for rel_path, kind in PRODUCT_SURFACES:
        path = root / rel_path
        if not path.is_file():
            findings.append(Finding("A1", "product", rel_path, "configured product surface is missing"))
            continue
        findings.extend(
            scan_text(path.read_text(encoding="utf-8"), path=rel_path, kind=kind)
        )

    for service in DEFAULT_SERVICES:
        findings.extend(check_default_service(service))

    for probe in SOURCE_PROBES:
        path = root / probe.path
        if not path.is_file():
            findings.append(Finding("A1", "product", probe.path, f"probe {probe.id} path is missing"))
            continue
        text = path.read_text(encoding="utf-8")
        matched = re.search(probe.pattern, text) is not None
        if probe.expect == "present" and not matched:
            findings.append(
                Finding(
                    probe.rule,
                    "product",
                    probe.path,
                    f"stale declaration — source no longer shows: {probe.description}",
                )
            )
        if probe.expect == "absent" and matched:
            findings.append(
                Finding(
                    probe.rule,
                    "product",
                    probe.path,
                    f"prohibited evidence present in source: {probe.description}",
                )
            )

    findings.extend(scan_legal(root))
    return findings


def render_report(findings: Sequence[Finding], *, scanned: int) -> str:
    """Render a human-readable report."""
    lines = [
        "Xavani product and legal boundary scan (Task 24a, agent repository)",
        f"Product surfaces scanned: {scanned}",
    ]
    if not findings:
        lines.append("RESULT: PASS — no prohibited default behavior, attribution intact.")
        return "\n".join(lines)

    lines.append(f"RESULT: FAIL — {len(findings)} finding(s)")
    for finding in findings:
        location = finding.path
        if finding.line is not None:
            location = f"{finding.path}:{finding.line}"
        lines.append(f"  [{finding.rule}/{finding.category}] {location}: {finding.detail}")
    return "\n".join(lines)


def build_report(findings: Sequence[Finding], *, root: Path) -> Dict[str, Any]:
    """Machine-readable report."""
    return {
        "task": "24a",
        "scope": "agent",
        "root": str(root),
        "ok": not findings,
        "product_surfaces": [path for path, _ in PRODUCT_SURFACES],
        "rules": [asdict(rule) for rule in RULES],
        "findings": [finding.as_dict() for finding in findings],
        "counts": {
            "total": len(findings),
            "product": sum(1 for f in findings if f.category == "product"),
            "legal": sum(1 for f in findings if f.category == "legal"),
        },
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """CLI entry point. Exit code 0 only when every rule passes."""
    parser = argparse.ArgumentParser(
        description="Task 24a: Xavani product and legal boundary scan (agent repository)."
    )
    parser.add_argument("--root", default=str(REPO_ROOT), help="repository root to scan")
    parser.add_argument("--json", action="store_true", help="emit a JSON report")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    findings = scan_repo(root)

    if args.json:
        json.dump(build_report(findings, root=root), sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(render_report(findings, scanned=len(PRODUCT_SURFACES)))

    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
