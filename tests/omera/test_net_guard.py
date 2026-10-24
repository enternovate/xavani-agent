import pytest

from xavani_omera.net_guard import UnsafeUrl, assert_safe_url


@pytest.mark.parametrize("url", [
    "file:///etc/passwd",
    "ftp://example.com/x",
    "http://localhost/",
    "http://127.0.0.1:8080/",
    "http://169.254.169.254/latest/meta-data/",
    "http://10.0.0.5/",
    "http://192.168.1.1/",
    "http://[::1]/",
    "http://user:pass@example.com/",
    "http://metadata.google.internal/",
])
def test_blocks_unsafe_targets(url):
    with pytest.raises(UnsafeUrl):
        assert_safe_url(url)


def test_allows_a_public_https_url():
    assert assert_safe_url("https://example.com/page") == "https://example.com/page"
