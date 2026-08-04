"""Tests for bounded error-body reads (agent/bounded_response.py)."""

import io

import pytest

from agent.bounded_response import (
    DEFAULT_ERROR_BODY_MAX_BYTES,
    read_streaming_error_body,
    read_urllib_error_body,
)


class _FakeChunkedResponse:
    """Minimal httpx.Response stand-in: iter_bytes + close + status_code."""

    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._pos = 0
        self.closed = False
        self.status_code = 500

    def iter_bytes(self):
        while self._pos < len(self._chunks):
            yield self._chunks[self._pos]
            self._pos += 1

    def close(self):
        self.closed = True


class _StallResponse:
    """Response whose body stream blocks forever (simulates stalled socket)."""

    def __init__(self, first_chunk=b""):
        self._first = first_chunk
        self.closed = False
        self.status_code = 500
        self._yielded_first = False

    def iter_bytes(self):
        if self._first:
            yield self._first
        import time
        time.sleep(3600)  # stall mid-chunk

    def close(self):
        self.closed = True


class TestReadStreamingErrorBody:
    def test_returns_full_body(self):
        resp = _FakeChunkedResponse([b"hello ", b"world"])
        assert read_streaming_error_body(resp) == "hello world"

    def test_truncates_oversized_body(self):
        resp = _FakeChunkedResponse([b"x" * 1000])
        text = read_streaming_error_body(resp, max_bytes=100)
        assert len(text) == 100

    def test_handles_multibyte_utf8(self):
        resp = _FakeChunkedResponse(["héllo".encode("utf-8")])
        assert read_streaming_error_body(resp) == "héllo"

    def test_invalid_utf8_replaced(self):
        resp = _FakeChunkedResponse([b"\xff\xfe broken"])
        text = read_streaming_error_body(resp)
        assert "broken" in text

    def test_empty_body_returns_empty_string(self):
        resp = _FakeChunkedResponse([])
        assert read_streaming_error_body(resp) == ""

    def test_hard_timeout_on_stalled_body(self):
        resp = _StallResponse(first_chunk=b"partial")
        text = read_streaming_error_body(resp, timeout_s=0.2)
        assert text == "partial"
        assert resp.closed is True

    def test_never_raises_on_transport_error(self):
        class Boom:
            def iter_bytes(self):
                raise RuntimeError("socket blew up")

            def close(self):
                pass

        assert read_streaming_error_body(Boom()) == ""

    def test_byte_cap_respects_chunk_boundary(self):
        resp = _FakeChunkedResponse([b"abcdef"])
        text = read_streaming_error_body(resp, max_bytes=3)
        assert text == "abc"


class TestReadUrllibErrorBody:
    def test_reads_bounded(self):
        exc = io.BytesIO(b"error detail here")
        assert read_urllib_error_body(exc) == "error detail here"

    def test_truncates(self):
        exc = io.BytesIO(b"x" * 1000)
        assert len(read_urllib_error_body(exc, max_bytes=64)) == 64

    def test_returns_empty_for_non_readable(self):
        assert read_urllib_error_body(Exception("nope")) == ""

    def test_never_raises_on_read_failure(self):
        class Bad:
            def read(self, n):
                raise OSError("boom")

        assert read_urllib_error_body(Bad()) == ""
