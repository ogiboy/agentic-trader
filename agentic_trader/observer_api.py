import json
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from secrets import compare_digest
from urllib.parse import urlsplit

from agentic_trader.security import is_loopback_host


PayloadResolver = Callable[[str], tuple[int, dict[str, object]]]


def _extract_bearer_token(value: str | None) -> str | None:
    if value is None:
        return None
    prefix = "Bearer "
    if not value.startswith(prefix):
        return None
    token = value[len(prefix) :].strip()
    return token or None


def create_observer_server(
    *,
    host: str,
    port: int,
    resolver: PayloadResolver,
    allow_nonlocal: bool = False,
    token: str | None = None,
) -> ThreadingHTTPServer:
    if not allow_nonlocal and not is_loopback_host(host):
        raise ValueError(
            "Observer API is local-only by default. Bind to 127.0.0.1/localhost "
            "or pass --allow-nonlocal with AGENTIC_TRADER_OBSERVER_API_TOKEN set."
        )
    normalized_token = token.strip() if token else None
    if allow_nonlocal and not is_loopback_host(host) and not normalized_token:
        raise ValueError(
            "Non-local observer API binds require AGENTIC_TRADER_OBSERVER_API_TOKEN."
        )

    class ObserverHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            if not self._is_authorized():
                self._write_json(401, {"error": "unauthorized"})
                return
            status_code, payload = resolver(urlsplit(self.path).path)
            self._write_json(status_code, payload)

        def _is_authorized(self) -> bool:
            if not normalized_token:
                return True
            provided = (
                self.headers.get("X-Agentic-Trader-Observer-Token")
                or _extract_bearer_token(self.headers.get("Authorization"))
                or ""
            )
            return compare_digest(provided, normalized_token)

        def _write_json(self, status_code: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Frame-Options", "DENY")
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
    allow_nonlocal: bool = False,
    token: str | None = None,
) -> None:
    server = create_observer_server(
        host=host,
        port=port,
        resolver=resolver,
        allow_nonlocal=allow_nonlocal,
        token=token,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
