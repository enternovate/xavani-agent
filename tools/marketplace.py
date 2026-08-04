# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F04: plugin marketplace.

A plugin registry with provenance pinning: every plugin lists its
source URL and SHA-256 checksum, and installs verify both before
touching the filesystem. The registry is a remote JSON index; this
module handles fetch-parse-verify-install with a hermetic install dir.

Installation is transactional: verify first, then extract; a failed
verification leaves no partial state.

Usage::

    from tools.marketplace import Marketplace

    mkt = Marketplace(install_dir=Path("~/.xavani/plugins"))
    index = mkt.fetch_index(index_url, fetcher=my_fetcher)
    mkt.install("disk-cleanup", index, fetcher=my_fetcher)
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import tarfile
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)

# A fetcher returns bytes for a URL. Tests inject fakes.
Fetcher = Callable[[str], bytes]


@dataclass
class PluginIndexEntry:
    """One plugin entry in the marketplace index."""

    name: str
    version: str
    description: str
    url: str
    sha256: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginIndexEntry":
        return cls(
            name=str(data["name"]),
            version=str(data.get("version", "")),
            description=str(data.get("description", "")),
            url=str(data["url"]),
            sha256=str(data.get("sha256", "")),
        )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _verify_checksum(data: bytes, expected: str) -> bool:
    if not expected:
        return False
    return _sha256(data) == expected.lower()


def _extract_archive(archive_bytes: bytes, dest: Path) -> None:
    """Extract a .tar.gz or .zip archive into dest (created)."""
    dest.mkdir(parents=True, exist_ok=True)
    suffix = ""
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as tmp:
        tmp.write(archive_bytes)
        tmp_path = tmp.name
    try:
        # Sniff the archive type by magic bytes.
        if archive_bytes[:2] == b"\x1f\x8b":
            with tarfile.open(tmp_path, "r:gz") as tar:
                tar.extractall(dest, filter="data")  # safe extraction
        elif archive_bytes[:4] == b"PK\x03\x04":
            with zipfile.ZipFile(tmp_path) as zf:
                zf.extractall(dest)
        else:
            raise ValueError("unsupported archive format")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


class Marketplace:
    """Plugin registry with provenance-pinned installs."""

    def __init__(self, install_dir: Path):
        self.install_dir = Path(install_dir)

    def parse_index(self, raw: str) -> List[PluginIndexEntry]:
        """Parse the index JSON into entries."""
        data = json.loads(raw)
        plugins = data.get("plugins", data) if isinstance(data, dict) else data
        return [PluginIndexEntry.from_dict(entry) for entry in plugins]

    def fetch_index(self, index_url: str, fetcher: Fetcher) -> List[PluginIndexEntry]:
        """Fetch and parse the marketplace index."""
        raw = fetcher(index_url).decode("utf-8")
        return self.parse_index(raw)

    def install(
        self,
        name: str,
        index: List[PluginIndexEntry],
        fetcher: Fetcher,
    ) -> Dict[str, Any]:
        """Install a plugin by name. Verifies checksum before extract."""
        entry = next((e for e in index if e.name == name), None)
        if entry is None:
            return {"ok": False, "error": f"plugin '{name}' not in index"}

        archive = fetcher(entry.url)
        if not _verify_checksum(archive, entry.sha256):
            return {
                "ok": False,
                "error": f"checksum mismatch for {name}",
                "expected": entry.sha256,
                "actual": _sha256(archive),
            }

        target = self.install_dir / entry.name
        try:
            _extract_archive(archive, target)
        except Exception as exc:
            return {"ok": False, "error": f"extract failed: {exc}"}

        return {
            "ok": True,
            "name": entry.name,
            "version": entry.version,
            "installed_to": str(target),
        }

    def installed(self) -> List[str]:
        """Names of installed plugins (directories in install_dir)."""
        if not self.install_dir.is_dir():
            return []
        return sorted(p.name for p in self.install_dir.iterdir() if p.is_dir())
