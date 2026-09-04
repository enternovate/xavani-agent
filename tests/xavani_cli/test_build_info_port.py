from __future__ import annotations


def test_build_info_import_succeeds():
    import xavani_cli.build_info as build_info

    assert callable(build_info.get_build_sha)


def test_build_sha_file_name():
    from xavani_cli.build_info import _BUILD_SHA_FILE

    assert _BUILD_SHA_FILE.name == ".xavani_build_sha"


def test_get_build_sha_short_returns_none_or_short_string():
    from xavani_cli.build_info import get_build_sha

    result = get_build_sha(short=8)
    assert result is None or (isinstance(result, str) and len(result) >= 8)
