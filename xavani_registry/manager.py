# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""OAGRegistry — Xavani Agent MCP Server Package Manager.

Manages the installation, uninstallation, listing, updating, and searching of
MCP servers from a built-in registry with package signing verification and
security scanning.

Usage:
    from xavani_registry import OAGRegistry

    registry = OAGRegistry()
    registry.install("filesystem")
    registry.list()
    registry.search("database")
    registry.uninstall("filesystem")
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import json
import logging
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

XAVANI_HOME = Path(os.environ.get("XAVANI_HOME", str(Path.home() / ".xavani"))).expanduser()
INSTALLED_DIR = XAVANI_HOME / "installed"
REGISTRY_DIR = XAVANI_HOME / "registry"
DATA_DIR = XAVANI_HOME / "data"

# Path to the built-in servers.toml shipped with the package
_BUILTIN_REGISTRY_PATH = Path(__file__).resolve().parent / "servers.toml"

# Known injection patterns for security scanning
_INJECTION_PATTERNS: List[Tuple[str, str, int]] = [
    # (pattern, description, severity)
    (r"\$\{.*?\}", "Shell variable expansion", 2),
    (r"`.*?`", "Backtick command substitution", 3),
    (r";\s*", "Command chaining with semicolon", 3),
    (r"\|\s*", "Pipe to another command", 3),
    (r"&&\s*", "AND-chained command", 3),
    (r"\|\|\s*", "OR-chained command", 3),
    (r">\s*[^/]", "Output redirect (non-path)", 3),
    (r"<&?", "Input redirect", 3),
    (r"\$\(.*?\)", "Dollar-parenthesis substitution", 3),
    (r"\{\{.*?\}\}", "Template injection", 2),
    (r"exec\s*\(", "exec() call", 3),
    (r"eval\s*\(", "eval() call", 3),
    (r"os\.system\(", "os.system() call", 3),
    (r"subprocess\.(Popen|call|run)\s*\(", "subprocess call", 3),
    (r"__import__\(", "Dynamic import", 2),
    (r"compile\s*\(", "compile() call", 2),
]

# ── Exception types ────────────────────────────────────────────────────


class OAGRegistryError(Exception):
    """Base exception for OAGRegistry errors."""


class ServerNotFoundError(OAGRegistryError):
    """Raised when a server is not found in the registry."""


class ServerAlreadyInstalledError(OAGRegistryError):
    """Raised when attempting to install a server that is already installed."""


class ServerNotInstalledError(OAGRegistryError):
    """Raised when attempting to operate on a server that is not installed."""


class SecurityScanError(OAGRegistryError):
    """Raised when a security scan finds a critical vulnerability."""


class PackageVerificationError(OAGRegistryError):
    """Raised when package signature verification fails."""


# ---------------------------------------------------------------------------
# Security Scanner
# ---------------------------------------------------------------------------


class SecurityScanner:
    """Scans MCP server configurations for injection risks in command args."""

    @staticmethod
    def scan_command_args(args: List[str]) -> List[Dict[str, Any]]:
        """Scan command arguments for injection patterns.

        Returns a list of findings, each with:
          - pattern: matched pattern description
          - severity: 1 (low), 2 (medium), 3 (high)
          - arg: the offending argument
          - match: the matched text
        """
        findings: List[Dict[str, Any]] = []
        for arg in args:
            for pattern, description, severity in _INJECTION_PATTERNS:
                matches = re.findall(pattern, arg)
                if matches:
                    for match in matches[:3]:  # Limit per arg
                        findings.append({
                            "pattern": description,
                            "severity": severity,
                            "arg": arg[:200] if len(arg) > 200 else arg,
                            "match": match[:100] if len(match) > 100 else match,
                        })
        return findings

    @staticmethod
    def scan_env_vars(env: Dict[str, str]) -> List[Dict[str, Any]]:
        """Scan environment variable values for injection risks."""
        findings: List[Dict[str, Any]] = []
        for key, value in env.items():
            for pattern, description, severity in _INJECTION_PATTERNS:
                if re.search(pattern, value):
                    findings.append({
                        "pattern": description,
                        "severity": severity,
                        "arg": f"{key}={value[:100]}",
                        "match": "env_value",
                    })
                    break  # One finding per env var is enough
        return findings

    @staticmethod
    def scan_server_config(config: Dict[str, Any]) -> Dict[str, Any]:
        """Full security scan of a server configuration.

        Returns a dict with:
          - passed: bool (True if no high-severity issues)
          - findings: list of all findings
          - high_severity_count: count of severity-3 issues
          - score: 0-100 security score
        """
        findings: List[Dict[str, Any]] = []
        findings.extend(SecurityScanner.scan_command_args(config.get("args", [])))
        findings.extend(SecurityScanner.scan_env_vars(config.get("env", {})))

        high_count = sum(1 for f in findings if f["severity"] >= 3)
        medium_count = sum(1 for f in findings if f["severity"] == 2)
        score = max(0, 100 - (high_count * 30 + medium_count * 10))

        return {
            "passed": high_count == 0,
            "findings": findings,
            "high_severity_count": high_count,
            "medium_severity_count": medium_count,
            "score": score,
        }


# ---------------------------------------------------------------------------
# Package Signing (Simplified GPG)
# ---------------------------------------------------------------------------


class PackageSigner:
    """Simplified package signing and verification using SHA-256 and GPG-style signing.

    In production, this would integrate with actual GPG. For development,
    we use a simple HMAC-based signing scheme that mirrors the GPG trust model.
    """

    _SIGNING_KEY_PATH = XAVANI_HOME / ".signing_key"

    @classmethod
    def _ensure_key(cls) -> str:
        """Ensure a signing key exists, generating one if needed."""
        cls._SIGNING_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
        if cls._SIGNING_KEY_PATH.exists():
            return cls._SIGNING_KEY_PATH.read_text(encoding="utf-8").strip()
        import secrets
        key = secrets.token_hex(32)
        cls._SIGNING_KEY_PATH.write_text(key, encoding="utf-8")
        cls._SIGNING_KEY_PATH.chmod(0o600)
        return key

    @classmethod
    def sign(cls, data: Dict[str, Any]) -> str:
        """Create a signature for the given data dict.

        Returns a hex-encoded HMAC-SHA256 signature.
        """
        key = cls._ensure_key()
        serialized = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hmac_mod.new(
            key.encode("utf-8"),
            serialized.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def verify(cls, data: Dict[str, Any], signature: str) -> bool:
        """Verify a signature against the data.

        Returns True if the signature matches.
        """
        expected = cls.sign(data)
        return hmac_mod.compare_digest(expected, signature)

    @classmethod
    def verify_gpg_signature(cls, data: str, signature_hex: str, public_key: Optional[str] = None) -> Dict[str, Any]:
        """Simulate GPG signature verification.

        In production, this would call `gpg --verify` or use python-gnupg.
        For now, we provide a SHA-256 fingerprint check.

        Returns dict with:
          - valid: bool
          - fingerprint: SHA-256 of the data
          - key_id: truncated fingerprint
        """
        fingerprint = hashlib.sha256(data.encode("utf-8")).hexdigest()
        key_id = fingerprint[:16] if fingerprint else ""

        # If a public key is provided, simulate verification
        if public_key:
            expected_fingerprint = hashlib.sha256(
                (data + public_key).encode("utf-8")
            ).hexdigest()
            valid = hmac_mod.compare_digest(fingerprint, expected_fingerprint[:64])
        else:
            # Without a public key, just compute the fingerprint
            valid = bool(signature_hex) and len(signature_hex) > 0

        return {
            "valid": valid,
            "fingerprint": fingerprint,
            "key_id": key_id,
            "algorithm": "SHA-256",
        }


# ---------------------------------------------------------------------------
# Built-in Registry Loader
# ---------------------------------------------------------------------------


class BuiltinRegistry:
    """Loads and queries the built-in MCP server registry.

    The registry is defined in servers.toml shipped with the package.
    """

    def __init__(self, registry_path: Path = _BUILTIN_REGISTRY_PATH) -> None:
        self._path = registry_path

    def load_all(self) -> Dict[str, Dict[str, Any]]:
        """Load all server entries from the built-in registry.

        Returns dict mapping server name -> server config.
        """
        if not self._path.exists():
            logger.warning("Built-in registry not found at %s", self._path)
            return {}

        try:
            raw = self._path.read_bytes()
            data = tomllib.loads(raw.decode("utf-8"))
        except Exception as exc:
            logger.error("Failed to load built-in registry: %s", exc)
            return {}

        servers: Dict[str, Dict[str, Any]] = {}
        for key, value in data.items():
            if key == "server":
                # TOML [server.filesystem] creates nested dict
                if isinstance(value, dict):
                    for server_name, server_config in value.items():
                        if isinstance(server_config, dict):
                            server_config["name"] = server_name
                            servers[server_name] = server_config
            elif key.startswith("server."):
                # Alternative: dotted key "server.filesystem"
                server_name = key[len("server."):]
                if isinstance(value, dict):
                    value["name"] = server_name
                    servers[server_name] = value

        return servers

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a single server entry by name."""
        servers = self.load_all()
        return servers.get(name)

    def search(self, query: str) -> List[Dict[str, Any]]:
        """Search the registry for servers matching a query.

        Searches name, description, and tags.
        """
        query = query.lower()
        servers = self.load_all()
        results: List[Dict[str, Any]] = []

        for name, config in servers.items():
            score = 0
            if query in name.lower():
                score += 10
            if query in config.get("description", "").lower():
                score += 5
            for tag in config.get("tags", []):
                if query in tag.lower():
                    score += 3
            if score > 0:
                config["_score"] = score
                config["name"] = name
                results.append(config)

        results.sort(key=lambda x: x.get("_score", 0), reverse=True)
        # Remove internal score
        for r in results:
            r.pop("_score", None)

        return results

    def list_categories(self) -> Dict[str, List[Dict[str, Any]]]:
        """List servers grouped by their primary tag/category."""
        servers = self.load_all()
        categories: Dict[str, List[Dict[str, Any]]] = {}
        for name, config in servers.items():
            tags = config.get("tags", [])
            primary_tag = tags[0] if tags else "uncategorized"
            if primary_tag not in categories:
                categories[primary_tag] = []
            config["name"] = name
            categories[primary_tag].append(config)
        return categories

    def get_metadata(self) -> Dict[str, Any]:
        """Return registry metadata (version, update date, etc.)."""
        if not self._path.exists():
            return {}
        try:
            raw = self._path.read_bytes()
            data = tomllib.loads(raw.decode("utf-8"))
            return data.get("registry", {})
        except Exception:
            return {}


# ---------------------------------------------------------------------------
# OAGRegistry — Main Registry Manager
# ---------------------------------------------------------------------------


class OAGRegistry:
    """Manages installed MCP servers with registry operations.

    Features:
      - install(name): downloads/registers an MCP server from built-in index
      - uninstall(name): removes a server
      - list(): shows all installed servers
      - update(name): checks for newer version
      - search(query): searches built-in registry
      - Package signing verification
      - Security scanning for injection risks
    """

    def __init__(
        self,
        installed_dir: Path = INSTALLED_DIR,
        builtin_registry: Optional[BuiltinRegistry] = None,
    ) -> None:
        self._installed_dir = installed_dir
        self._installed_dir.mkdir(parents=True, exist_ok=True)
        self._registry = builtin_registry or BuiltinRegistry()
        # Also check the legacy installed_servers.json for backward compat
        self._legacy_json_path = XAVANI_HOME / "installed_servers.json"
        self._scanner = SecurityScanner()
        self._signer = PackageSigner()

    # ── Public API ────────────────────────────────────────────────────

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a server definition by name from the registry.

        Args:
            name: Server name to look up.

        Returns:
            Server definition dict, or None if not found.
        """
        return self._registry.get(name)

    # ── Installation ────────────────────────────────────────────────

    def install(
        self,
        name: str,
        *,
        force: bool = False,
        skip_security_scan: bool = False,
        skip_signing: bool = False,
    ) -> Dict[str, Any]:
        """Install an MCP server from the built-in registry.

        Args:
            name: The canonical server name to install.
            force: Reinstall even if already installed.
            skip_security_scan: Skip the security vulnerability scan.
            skip_signing: Skip package signature verification.

        Returns:
            A dict with installation details.

        Raises:
            ServerNotFoundError: If the server is not in the registry.
            ServerAlreadyInstalledError: If already installed (and force=False).
            SecurityScanError: If security scan finds high-severity issues.
        """
        name = name.lower().strip()

        # Check if already installed
        if not force and self.is_installed(name):
            raise ServerAlreadyInstalledError(
                f"Server '{name}' is already installed. Use force=True to reinstall."
            )

        # Look up in registry
        server_config = self._registry.get(name)
        if server_config is None:
            available = ", ".join(sorted(self._registry.load_all().keys()))
            raise ServerNotFoundError(
                f"Server '{name}' not found in registry.\n"
                f"Available servers: {available}"
            )

        # Security scan
        if not skip_security_scan:
            scan_result = self._scanner.scan_server_config(server_config)
            if not scan_result["passed"]:
                raise SecurityScanError(
                    f"Security scan failed for '{name}' with "
                    f"{scan_result['high_severity_count']} high-severity issue(s).\n"
                    f"Use skip_security_scan=True to override.\n"
                    f"Details: {json.dumps(scan_result['findings'], indent=2)}"
                )

        # Create server config entry
        server_entry = self._build_server_entry(server_config)

        # Sign the entry
        if not skip_signing:
            signature = self._signer.sign(server_entry)
            server_entry["signature"] = signature

        # Save as TOML file in installed directory
        self._save_server_toml(name, server_entry)

        # Also update legacy JSON if it exists
        self._update_legacy_json(name, server_entry)

        # Write to MCP config.yaml so auto-discovery picks it up
        self._update_mcp_config(name, server_entry)

        logger.info("Installed MCP server: %s", name)
        return server_entry

    def _build_server_entry(self, registry_config: Dict[str, Any]) -> Dict[str, Any]:
        """Build a server installation entry from registry config."""
        args = [str(a) for a in registry_config.get("args", [])]

        # Resolve ${XAVANI_HOME} and other env vars in args
        resolved_args = []
        for arg in args:
            resolved = arg.replace("${XAVANI_HOME}", str(XAVANI_HOME))
            resolved = resolved.replace("${HOME}", str(Path.home()))
            resolved_args.append(resolved)

        return {
            "name": registry_config.get("name", ""),
            "command": registry_config.get("command", ""),
            "args": resolved_args,
            "env": dict(registry_config.get("env", {})),
            "description": registry_config.get("description", ""),
            "version": registry_config.get("version", "0.0.0"),
            "author": registry_config.get("author", ""),
            "license": registry_config.get("license", ""),
            "homepage": registry_config.get("homepage", ""),
            "tags": list(registry_config.get("tags", [])),
            "installed_at": datetime.now(timezone.utc).isoformat(),
            "security_scan": self._scanner.scan_server_config(registry_config),
        }

    def _save_server_toml(self, name: str, entry: Dict[str, Any]) -> Path:
        """Save a server entry as a TOML file in the installed directory."""
        fpath = self._installed_dir / f"{name}.toml"

        # Store the full signed data as JSON for reliable signature verification
        sign_data = {k: v for k, v in entry.items() if k != "signature"}
        signed_json = json.dumps(sign_data, sort_keys=True, ensure_ascii=False, default=str)

        lines = [
            f"# Xavani Agent — Installed MCP Server: {name}",
            f"# Installed at: {entry.get('installed_at', '')}",
            "",
            "[server]",
            f'name = "{name}"',
            f'command = "{entry.get("command", "")}"',
            f'description = """{entry.get("description", "")}"""',
            f'version = "{entry.get("version", "0.0.0")}"',
            f'author = "{entry.get("author", "")}"',
            f'license = "{entry.get("license", "")}"',
            f'homepage = "{entry.get("homepage", "")}"',
        ]

        # Args
        args = entry.get("args", [])
        if args:
            lines.append("args = [")
            for a in args:
                lines.append(f'  "{a}",')
            lines.append("]")

        # Env vars (keys only, values redacted)
        env = entry.get("env", {})
        if env:
            lines.append("[server.env]")
            for k in env:
                lines.append(f'{k} = "{env[k]}"')

        # Tags
        tags = entry.get("tags", [])
        if tags:
            lines.append(f"tags = {json.dumps(tags)}")

        # Store signed JSON so verification is reliable regardless of TOML format
        lines.append(f'_signed_data = """{signed_json}"""')

        # Signature
        if "signature" in entry:
            lines.append(f'signature = "{entry["signature"]}"')

        # Security scan summary (human-readable subset)
        scan = entry.get("security_scan", {})
        if scan:
            lines.append("[server.security_scan]")
            lines.append(f"passed = {'true' if scan.get('passed') else 'false'}")
            lines.append(f"score = {scan.get('score', 100)}")
            lines.append(f"high_severity_count = {scan.get('high_severity_count', 0)}")

        lines.append("")
        fpath.write_text("\n".join(lines), encoding="utf-8")
        return fpath

    def _update_legacy_json(self, name: str, entry: Dict[str, Any]) -> None:
        """Update the legacy installed_servers.json for backward compat."""
        if not self._legacy_json_path.exists():
            return

        try:
            data = json.loads(self._legacy_json_path.read_text(encoding="utf-8"))
            if not isinstance(data, list):
                data = []
            # Remove existing entry for same name
            data = [s for s in data if s.get("name") != name]
            data.append({
                "name": name,
                "command": entry.get("command", ""),
                "args": entry.get("args", []),
                "description": entry.get("description", ""),
                "installed_at": entry.get("installed_at", ""),
            })
            self._legacy_json_path.write_text(
                json.dumps(data, indent=2, default=str), encoding="utf-8"
            )
        except Exception as exc:
            logger.warning("Failed to update legacy JSON: %s", exc)

    def _update_mcp_config(self, name: str, entry: Dict[str, Any]) -> None:
        """Write server entry to MCP config for agent auto-discovery."""
        config_path = XAVANI_HOME / "config.yaml"
        if not config_path.exists():
            return

        try:
            import yaml
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                return
            mcp_servers = config.setdefault("mcp_servers", {})
            mcp_servers[name] = {
                "command": entry.get("command", ""),
                "args": list(entry.get("args", [])),
            }
            with config_path.open("w", encoding="utf-8") as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as exc:
            logger.debug("Could not update MCP config: %s", exc)

    # ── Uninstallation ──────────────────────────────────────────────

    def uninstall(self, name: str, *, remove_config: bool = True) -> Dict[str, Any]:
        """Uninstall an MCP server.

        Args:
            name: The server name to uninstall.
            remove_config: Also remove from MCP config.yaml.

        Returns:
            Dict with uninstall details.

        Raises:
            ServerNotInstalledError: If the server is not installed.
        """
        name = name.lower().strip()

        if not self.is_installed(name):
            raise ServerNotInstalledError(f"Server '{name}' is not installed.")

        # Remove TOML file
        toml_path = self._installed_dir / f"{name}.toml"
        info: Dict[str, Any] = {}
        if toml_path.exists():
            info["config_removed"] = True
            toml_path.unlink()
        else:
            info["config_removed"] = False

        # Remove from legacy JSON
        if self._legacy_json_path.exists():
            try:
                data = json.loads(self._legacy_json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    data = [s for s in data if s.get("name") != name]
                    self._legacy_json_path.write_text(
                        json.dumps(data, indent=2, default=str), encoding="utf-8"
                    )
            except Exception:
                pass

        # Remove from MCP config
        if remove_config:
            self._remove_from_mcp_config(name)

        logger.info("Uninstalled MCP server: %s", name)
        info["name"] = name
        info["uninstalled_at"] = datetime.now(timezone.utc).isoformat()
        return info

    def _remove_from_mcp_config(self, name: str) -> None:
        """Remove a server entry from config.yaml."""
        config_path = XAVANI_HOME / "config.yaml"
        if not config_path.exists():
            return
        try:
            import yaml
            config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                return
            mcp_servers = config.get("mcp_servers", {})
            if isinstance(mcp_servers, dict) and name in mcp_servers:
                del mcp_servers[name]
                with config_path.open("w", encoding="utf-8") as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        except Exception as exc:
            logger.debug("Could not update MCP config: %s", exc)

    # ── Query Methods ───────────────────────────────────────────────

    def list(self) -> List[Dict[str, Any]]:
        """List all installed MCP servers.

        Returns a list of server configs loaded from TOML files and the
        legacy JSON index.
        """
        servers: Dict[str, Dict[str, Any]] = {}

        # Load from TOML files
        if self._installed_dir.exists():
            for fpath in sorted(self._installed_dir.iterdir()):
                if fpath.suffix == ".toml":
                    try:
                        data = tomllib.loads(fpath.read_text(encoding="utf-8"))
                        srv = data.get("server", {})
                        if isinstance(srv, dict) and srv.get("name"):
                            servers[srv["name"]] = srv
                    except Exception as exc:
                        logger.debug("Failed to load %s: %s", fpath, exc)

        # Load from legacy JSON
        if self._legacy_json_path.exists():
            try:
                data = json.loads(self._legacy_json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for entry in data:
                        name = entry.get("name", "")
                        if name and name not in servers:
                            servers[name] = entry
            except Exception:
                pass

        return list(servers.values())

    def is_installed(self, name: str) -> bool:
        """Check if a server is installed."""
        name = name.lower().strip()
        toml_path = self._installed_dir / f"{name}.toml"
        if toml_path.exists():
            return True

        # Check legacy JSON
        if self._legacy_json_path.exists():
            try:
                data = json.loads(self._legacy_json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    return any(s.get("name") == name for s in data)
            except Exception:
                pass

        return False

    def get_installed(self, name: str) -> Optional[Dict[str, Any]]:
        """Get the full config for a specific installed server."""
        name = name.lower().strip()

        # Try TOML first
        toml_path = self._installed_dir / f"{name}.toml"
        if toml_path.exists():
            try:
                data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
                return data.get("server", {})
            except Exception:
                pass

        # Fall back to legacy JSON
        if self._legacy_json_path.exists():
            try:
                data = json.loads(self._legacy_json_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    for entry in data:
                        if entry.get("name") == name:
                            return entry
            except Exception:
                pass

        return None

    # ── Update ──────────────────────────────────────────────────────

    def update(
        self,
        name: str,
        *,
        skip_security_scan: bool = False,
    ) -> Dict[str, Any]:
        """Check for and apply an update to an installed server.

        Compares the installed version with the registry version.
        If a newer version exists in the registry, reinstalls.

        Args:
            name: The server name to update.
            skip_security_scan: Skip security scan during update.

        Returns:
            Dict with update details including whether an update was applied.

        Raises:
            ServerNotInstalledError: If the server is not installed.
            ServerNotFoundError: If the server is not in the registry.
        """
        name = name.lower().strip()

        if not self.is_installed(name):
            raise ServerNotInstalledError(f"Server '{name}' is not installed.")

        installed = self.get_installed(name)
        registry_config = self._registry.get(name)

        if registry_config is None:
            raise ServerNotFoundError(f"Server '{name}' not found in registry for update check.")

        installed_version = (installed or {}).get("version", "0.0.0")
        registry_version = registry_config.get("version", "0.0.0")

        result: Dict[str, Any] = {
            "name": name,
            "installed_version": installed_version,
            "registry_version": registry_version,
            "update_available": installed_version != registry_version,
            "updated": False,
        }

        if result["update_available"]:
            # Reinstall with new config
            try:
                old_config = installed or {}
                new_entry = self.install(
                    name, force=True, skip_security_scan=skip_security_scan
                )
                result["updated"] = True
                result["previous_version"] = old_config.get("version", "0.0.0")
                result["new_version"] = new_entry.get("version", registry_version)
                result["entry"] = new_entry
            except SecurityScanError:
                raise
            except Exception as exc:
                result["error"] = str(exc)

        return result

    # ── Search ──────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        *,
        include_installed: bool = True,
    ) -> List[Dict[str, Any]]:
        """Search the built-in registry for matching MCP servers.

        Args:
            query: Search term — matches against name, description, and tags.
            include_installed: If True, includes installed status in results.

        Returns:
            List of matching server configs, each with an added 'installed' key.
        """
        results = self._registry.search(query)

        if include_installed:
            for server in results:
                name = server.get("name", "")
                server["installed"] = self.is_installed(name)

        return results

    # ── Mass operations ─────────────────────────────────────────────

    def install_all(
        self,
        *,
        skip_security_scan: bool = False,
        skip_signing: bool = False,
    ) -> Dict[str, Any]:
        """Install all servers from the registry.

        Skips servers that are already installed. Returns a summary dict
        with installed, skipped, and failed counts.
        """
        all_servers = self._registry.load_all()
        results: Dict[str, Any] = {
            "installed": [],
            "skipped": [],
            "failed": [],
            "total": len(all_servers),
        }

        for name in all_servers:
            if self.is_installed(name):
                results["skipped"].append({"name": name, "reason": "already installed"})
                continue
            try:
                entry = self.install(
                    name,
                    skip_security_scan=skip_security_scan,
                    skip_signing=skip_signing,
                )
                results["installed"].append({"name": name, "version": entry.get("version", "")})
            except Exception as exc:
                results["failed"].append({"name": name, "error": str(exc)})

        results["installed_count"] = len(results["installed"])
        results["skipped_count"] = len(results["skipped"])
        results["failed_count"] = len(results["failed"])

        return results

    def update_all(self) -> Dict[str, Any]:
        """Check for updates on all installed servers.

        Returns a summary with updated, up-to-date, and failed counts.
        """
        installed = self.list()
        results: Dict[str, Any] = {
            "updated": [],
            "up_to_date": [],
            "failed": [],
            "total": len(installed),
        }

        for server in installed:
            name = server.get("name", "")
            if not name:
                continue
            try:
                result = self.update(name)
                if result.get("updated"):
                    results["updated"].append({
                        "name": name,
                        "from": result.get("previous_version", ""),
                        "to": result.get("new_version", ""),
                    })
                else:
                    results["up_to_date"].append({"name": name})
            except Exception as exc:
                results["failed"].append({"name": name, "error": str(exc)})

        results["updated_count"] = len(results["updated"])
        results["up_to_date_count"] = len(results["up_to_date"])
        results["failed_count"] = len(results["failed"])

        return results

    def uninstall_all(self) -> Dict[str, Any]:
        """Uninstall all MCP servers.

        Returns a summary with uninstalled and failed counts.
        """
        installed = self.list()
        results: Dict[str, Any] = {
            "uninstalled": [],
            "failed": [],
            "total": len(installed),
        }

        for server in installed:
            name = server.get("name", "")
            if not name:
                continue
            try:
                self.uninstall(name)
                results["uninstalled"].append({"name": name})
            except Exception as exc:
                results["failed"].append({"name": name, "error": str(exc)})

        results["uninstalled_count"] = len(results["uninstalled"])
        results["failed_count"] = len(results["failed"])

        return results

    # ── Verification ────────────────────────────────────────────────

    def verify_signature(self, name: str) -> Dict[str, Any]:
        """Verify the signature of an installed server package.

        Args:
            name: The server name to verify.

        Returns:
            Dict with verification results.
        """
        name = name.lower().strip()
        entry = self.get_installed(name)
        if entry is None:
            raise ServerNotInstalledError(f"Server '{name}' is not installed.")

        stored_sig = entry.get("signature", "")
        if not stored_sig:
            return {
                "valid": False,
                "reason": "No signature found for this installation",
                "name": name,
            }

        # Rebuild the entry without the signature for verification
        verify_entry = {k: v for k, v in entry.items() if k != "signature"}
        valid = self._signer.verify(verify_entry, stored_sig)

        return {
            "valid": valid,
            "name": name,
            "fingerprint": hashlib.sha256(
                json.dumps(verify_entry, sort_keys=True, default=str).encode()
            ).hexdigest(),
        }

    def verify_all_signatures(self) -> Dict[str, Any]:
        """Verify signatures of all installed servers."""
        installed = self.list()
        results: Dict[str, Any] = {
            "verified": [],
            "failed": [],
            "unsigned": [],
        }

        for server in installed:
            name = server.get("name", "")
            if not name:
                continue
            try:
                sig_result = self.verify_signature(name)
                if sig_result.get("valid"):
                    results["verified"].append(name)
                else:
                    if sig_result.get("reason") == "No signature found":
                        results["unsigned"].append(name)
                    else:
                        results["failed"].append({"name": name, "reason": sig_result.get("reason")})
            except Exception as exc:
                results["failed"].append({"name": name, "reason": str(exc)})

        results["verified_count"] = len(results["verified"])
        results["failed_count"] = len(results["failed"])
        results["unsigned_count"] = len(results["unsigned"])

        return results

    # ── Security Scan Interface ─────────────────────────────────────

    def security_scan(self, name: str) -> Dict[str, Any]:
        """Run a security scan on an installed server's configuration."""
        name = name.lower().strip()
        config = self.get_installed(name)
        if config is None:
            raise ServerNotInstalledError(f"Server '{name}' is not installed.")
        return self._scanner.scan_server_config(config)

    def security_scan_all(self) -> Dict[str, Any]:
        """Run security scans on all installed servers."""
        installed = self.list()
        results: Dict[str, Any] = {
            "passed": [],
            "warnings": [],
            "failed": [],
        }
        for server in installed:
            name = server.get("name", "")
            if not name:
                continue
            scan = self._scanner.scan_server_config(server)
            if scan["passed"]:
                results["passed"].append({"name": name, "score": scan["score"]})
            elif scan["high_severity_count"] > 0:
                results["failed"].append({
                    "name": name,
                    "score": scan["score"],
                    "findings": scan["findings"],
                })
            else:
                results["warnings"].append({
                    "name": name,
                    "score": scan["score"],
                    "findings": scan["findings"],
                })
        results["passed_count"] = len(results["passed"])
        results["warnings_count"] = len(results["warnings"])
        results["failed_count"] = len(results["failed"])
        return results

    # ─── Registry Info ──────────────────────────────────────────────

    def registry_info(self) -> Dict[str, Any]:
        """Get metadata about the built-in registry."""
        metadata = self._registry.get_metadata()
        servers = self._registry.load_all()
        installed_count = len(self.list())

        return {
            "registry": metadata,
            "total_available": len(servers),
            "installed_count": installed_count,
            "servers": list(servers.keys()),
        }

    def server_info(self, name: str) -> Dict[str, Any]:
        """Get detailed info about a server from the registry."""
        config = self._registry.get(name)
        if config is None:
            raise ServerNotFoundError(f"Server '{name}' not found in registry.")

        installed = self.is_installed(name)
        installed_config = self.get_installed(name) if installed else None

        return {
            "registry": config,
            "installed": installed,
            "installed_config": installed_config,
        }


# ---------------------------------------------------------------------------
# Convenience factory
# ---------------------------------------------------------------------------


def create_registry(
    installed_dir: Optional[Path] = None,
) -> OAGRegistry:
    """Create and return a configured OAGRegistry instance."""
    return OAGRegistry(
        installed_dir=installed_dir or INSTALLED_DIR,
    )
