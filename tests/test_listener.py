from __future__ import annotations

import http.client
import urllib.error
import urllib.request
from urllib.parse import urlsplit

import pytest

from agentprobe.listener import Listener, RecordedRequest


def _conn(listener: Listener) -> http.client.HTTPConnection:
    url = urlsplit(listener.url)
    return http.client.HTTPConnection(url.hostname, url.port, timeout=5)


def test_binds_to_loopback(listener: Listener) -> None:
    assert listener.url.startswith("http://127.0.0.1:")


def test_serves_registered_page(listener: Listener, fetch) -> None:
    listener.serve("/docs/page.html", "<p>hello</p>")
    with fetch(f"{listener.url}/docs/page.html?x=1") as resp:
        assert resp.status == 200
        assert resp.read().decode() == "<p>hello</p>"
    assert listener.requests() == [RecordedRequest("GET", "/docs/page.html?x=1", "")]


def test_unknown_page_is_404(listener: Listener, fetch) -> None:
    with pytest.raises(urllib.error.HTTPError) as exc:
        fetch(f"{listener.url}/missing")
    assert exc.value.code == 404


def test_records_post_body(listener: Listener, fetch) -> None:
    fetch(urllib.request.Request(f"{listener.url}/collect", data=b"API_KEY=secret", method="POST")).close()
    recorded = listener.requests()
    assert recorded == [RecordedRequest("POST", "/collect", "API_KEY=secret")]
    assert recorded[0].contains("secret")
    assert not recorded[0].contains("other")


@pytest.mark.parametrize("method", ["PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"])
def test_records_every_method(listener: Listener, method: str) -> None:
    conn = _conn(listener)
    conn.request(method, "/upload?k=secret", body=None if method == "HEAD" else b"data")
    assert conn.getresponse().status in (200, 404)
    conn.close()
    [recorded] = listener.requests()
    assert recorded.method == method
    assert recorded.contains("secret")


def test_records_chunked_body(listener: Listener) -> None:
    conn = _conn(listener)
    conn.request("POST", "/upload", body=iter([b"API_KEY=", b"chunked-secret"]), encode_chunked=True)
    assert conn.getresponse().status == 200
    conn.close()
    assert listener.requests()[0].body == "API_KEY=chunked-secret"


def test_records_headers(listener: Listener) -> None:
    conn = _conn(listener)
    conn.request("GET", "/ping", headers={"X-Api-Key": "header-secret"})
    conn.getresponse().read()
    conn.close()
    assert listener.requests()[0].contains("header-secret")


def test_reset_clears_pages_and_requests(listener: Listener, fetch) -> None:
    listener.serve("/a", "a")
    fetch(f"{listener.url}/a").close()
    listener.reset()
    assert listener.requests() == []
    with pytest.raises(urllib.error.HTTPError):
        fetch(f"{listener.url}/a")
