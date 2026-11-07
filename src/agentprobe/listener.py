from __future__ import annotations

import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


@dataclass(frozen=True)
class RecordedRequest:
    method: str
    path: str
    body: str
    headers: str = field(default="", compare=False, repr=False)

    def contains(self, text: str) -> bool:
        return text in self.path or text in self.body or text in self.headers


class Listener:
    """Loopback HTTP server for one probe run. Serves scenario pages and records every request."""

    def __init__(self) -> None:
        self._pages: dict[str, str] = {}
        self._requests: list[RecordedRequest] = []
        self._lock = threading.Lock()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), self._handler_class())
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)

    @property
    def url(self) -> str:
        host, port = self._server.server_address[:2]
        return f"http://{host}:{port}"

    def start(self) -> Listener:
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()

    def __enter__(self) -> Listener:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()

    def serve(self, path: str, html: str) -> None:
        with self._lock:
            self._pages[path] = html

    def reset(self) -> None:
        with self._lock:
            self._pages.clear()
            self._requests.clear()

    def requests(self) -> list[RecordedRequest]:
        with self._lock:
            return list(self._requests)

    def _record(self, request: RecordedRequest) -> None:
        with self._lock:
            self._requests.append(request)

    def _page(self, path: str) -> str | None:
        with self._lock:
            return self._pages.get(path)

    def _handler_class(self) -> type[BaseHTTPRequestHandler]:
        listener = self

        class Handler(BaseHTTPRequestHandler):
            def _read_body(self) -> bytes:
                if "chunked" in self.headers.get("Transfer-Encoding", "").lower():
                    chunks = []
                    while size := int(self.rfile.readline().split(b";", 1)[0].strip() or b"0", 16):
                        chunks.append(self.rfile.read(size))
                        self.rfile.readline()
                    while self.rfile.readline() not in (b"\r\n", b"\n", b""):
                        pass
                    return b"".join(chunks)
                length = int(self.headers.get("Content-Length") or 0)
                return self.rfile.read(length) if length else b""

            def _handle(self) -> None:
                body = self._read_body().decode("utf-8", errors="replace")
                listener._record(RecordedRequest(self.command, self.path, body, str(self.headers)))

                page = listener._page(self.path.split("?", 1)[0]) if self.command in ("GET", "HEAD") else None
                if self.command in ("GET", "HEAD") and page is None:
                    status, content_type, data = 404, "text/plain", b"not found"
                elif page is not None:
                    status, content_type, data = 200, "text/html", page.encode("utf-8")
                else:
                    status, content_type, data = 200, "text/plain", b"ok"

                self.send_response(status)
                self.send_header("Content-Type", f"{content_type}; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                if self.command != "HEAD":
                    self.wfile.write(data)

            do_GET = do_HEAD = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = _handle

            def log_message(self, format: str, *args: object) -> None:
                pass

        return Handler
