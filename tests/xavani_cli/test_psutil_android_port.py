from xavani_cli.psutil_android import (
    PsutilAndroidInstallError,
    _normalize_member_parts,
    prepare_patched_psutil_sdist,
)


def test_import_succeeds():
    assert PsutilAndroidInstallError is not None
    assert prepare_patched_psutil_sdist is not None


def test_normalize_member_parts_splits_posix_path():
    assert _normalize_member_parts("a/b/c") == ("a", "b", "c")
