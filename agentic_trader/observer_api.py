import json
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


PayloadResolver = Callable[[str], tuple[int, dict[str, object]]]


def create_observer_server(
    *,
    host: str,
    port: int,
    resolver: PayloadResolver,
) -> ThreadingHTTPServer:
    class ObserverHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            status_code, payload = resolver(self.path)
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:  # noqa: A003
            return

    return ThreadingHTTPServer((host, port), ObserverHandler)


def serve_observer_api(
    *,
    host: str,
    port: int,
    resolver: PayloadResolver,
) -> None:
    server = create_observer_server(host=host, port=port, resolver=resolver)
    try:
        server.serve_forever()
    finally:
        server.server_close()
