# Copyright (c) 2025-2026 Enternovate.
# MIT License -- See LICENSE file for full terms.
# Built by Enternovate -- Open source. Private. Local.

"""F04: plugin marketplace tests."""

import hashlib
import io
import tarfile

import pytest

from tools.marketplace import Marketplace, PluginIndexEntry, _sha256, _verify_checksum


def _tar_bytes() -> bytes:
    """A small tar.gz containing one file."""
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        data = b"plugin-code"
        info = tarfile.TarInfo("plugin.py")
        info.size = len(data)
        tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _index(entries):
    return json_dumps({"plugins": entries})


def json_dumps(data):
    import json

    return json.dumps(data)


@pytest.fixture
def mkt(tmp_path):
    return Marketplace(install_dir=tmp_path / "plugins")


# ── checksums ──────────────────────────────────────────────────────


def test_sha256_known_value():
    assert _sha256(b"abc") == hashlib.sha256(b"abc").hexdigest()


def test_verify_checksum_match():
    data = b"payload"
    assert _verify_checksum(data, _sha256(data)) is True


def test_verify_checksum_mismatch():
    assert _verify_checksum(b"payload", _sha256(b"other")) is False


def test_verify_checksum_empty_expected():
    assert _verify_checksum(b"x", "") is False


# ── index parsing ──────────────────────────────────────────────────


def test_parse_index(mkt):
    archive = _tar_bytes()
    entry = {
        "name": "disk-cleanup",
        "version": "1.0.0",
        "description": "Clean disk",
        "url": "https://example.com/disk.tar.gz",
        "sha256": _sha256(archive),
    }
    index = mkt.parse_index(_index([entry]))
    assert len(index) == 1
    assert index[0].name == "disk-cleanup"
    assert index[0].sha256 == _sha256(archive)


def test_parse_index_bad_json(mkt):
    with pytest.raises(Exception):
        mkt.parse_index("not json")


# ── install ────────────────────────────────────────────────────────


def test_install_success(mkt):
    archive = _tar_bytes()
    index = [
        PluginIndexEntry(
            name="cleaner",
            version="1.0.0",
            description="x",
            url="https://example.com/cleaner.tar.gz",
            sha256=_sha256(archive),
        )
    ]
    result = mkt.install("cleaner", index, fetcher=lambda url: archive)
    assert result["ok"] is True
    assert result["name"] == "cleaner"
    assert (mkt.install_dir / "cleaner" / "plugin.py").exists()
    assert mkt.installed() == ["cleaner"]


def test_install_unknown_plugin(mkt):
    archive = _tar_bytes()
    result = mkt.install("ghost", [], fetcher=lambda url: archive)
    assert result["ok"] is False
    assert "not in index" in result["error"]


def test_install_checksum_mismatch_rejects(mkt):
    archive = _tar_bytes()
    index = [
        PluginIndexEntry(
            name="evil",
            version="1.0.0",
            description="x",
            url="https://example.com/evil.tar.gz",
            sha256="0" * 64,
        )
    ]
    result = mkt.install("evil", index, fetcher=lambda url: archive)
    assert result["ok"] is False
    assert "checksum mismatch" in result["error"]
    # Nothing was extracted.
    assert mkt.installed() == []


def test_install_bad_archive(mkt):
    index = [
        PluginIndexEntry(
            name="bad",
            version="1.0.0",
            description="x",
            url="https://example.com/bad.tar.gz",
            sha256=_sha256(b"not-an-archive"),
        )
    ]
    result = mkt.install("bad", index, fetcher=lambda url: b"not-an-archive")
    assert result["ok"] is False
    assert "extract failed" in result["error"]


def test_fetch_index_uses_fetcher(mkt):
    archive = _tar_bytes()
    entry = {
        "name": "cleaner",
        "version": "1.0.0",
        "description": "x",
        "url": "https://example.com/c.tar.gz",
        "sha256": _sha256(archive),
    }
    index = mkt.fetch_index("https://index.example.com", fetcher=lambda url: json_dumps({"plugins": [entry]}).encode())
    assert index[0].name == "cleaner"


def test_installed_empty(mkt):
    assert mkt.installed() == []
