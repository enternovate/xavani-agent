from xavani_cli.pty_session import PtySession, PtySessionRegistry, RingBuffer


def test_import_succeeds():
    assert RingBuffer is not None
    assert PtySession is not None
    assert PtySessionRegistry is not None


def test_ring_buffer_keeps_only_most_recent_bytes():
    buf = RingBuffer(4)
    buf.append(b"abcdef")
    assert buf.snapshot() == b"cdef"
    assert buf.truncated is True
