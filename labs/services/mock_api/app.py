"""
Course mock API.

Serves a small JSON reference feed over real HTTP so the ingestion lab exercises
genuine network code: status codes, timeouts, retries and JSON parsing.

It runs in the course compose stack, so it needs no internet access, no account
and no API key, and it behaves identically for every delegate.

The important feature is that it can be told to FAIL. You cannot teach retry
logic against an endpoint that always works, so this one misbehaves on demand.

Endpoints
    GET /health
        Always 200. Used by the orchestrator to check the service is up.

    GET /holidays
        200 with the public holiday feed.
        Query parameters:
            fail_times=N   fail the next N requests with 503, then succeed.
                           The counter is per client and resets once exhausted.
            delay=S        wait S seconds before responding, to trigger timeouts.
            malformed=1    return a 200 carrying invalid JSON, which is the
                           failure mode a status check alone will not catch.

    GET /holidays/reset
        Clears any pending failure counters.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs
import json
import os
import time

DATA_PATH = os.getenv("HOLIDAYS_PATH", "/data/public_holidays.json")
PORT = int(os.getenv("MOCK_API_PORT", "8000"))

# Remaining forced failures, keyed by client address.
_failures = {}


def _load_feed():
    with open(DATA_PATH, "r", encoding="utf-8") as handle:
        return json.load(handle)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # Keep container logs readable during the lab.
        print("mock_api %s" % (fmt % args), flush=True)

    def _send(self, code, payload, raw=False):
        body = payload if raw else json.dumps(payload, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        client = self.client_address[0]

        if parsed.path == "/health":
            self._send(200, {"status": "ok"})
            return

        if parsed.path == "/holidays/reset":
            _failures.pop(client, None)
            self._send(200, {"status": "reset"})
            return

        if parsed.path != "/holidays":
            self._send(404, {"error": "not found", "path": parsed.path})
            return

        # Optional slow response, so a timeout can be demonstrated.
        delay = float(params.get("delay", [0])[0])
        if delay > 0:
            time.sleep(delay)

        # Forced failures, so a retry can be demonstrated.
        requested = int(params.get("fail_times", [0])[0])
        if requested > 0 and client not in _failures:
            _failures[client] = requested
        if _failures.get(client, 0) > 0:
            # Leave the exhausted counter in place at zero. Removing it would let
            # the next request re-arm the budget and the endpoint would never
            # recover, which defeats the point of demonstrating a retry.
            _failures[client] -= 1
            self._send(
                503,
                {"error": "service unavailable", "detail": "upstream is warming up"},
            )
            return

        # A 200 carrying broken JSON, which is the failure a status check misses.
        if params.get("malformed", ["0"])[0] == "1":
            self._send(200, b'{"holidays": [ {"date": "2025-01-01",', raw=True)
            return

        self._send(200, _load_feed())


if __name__ == "__main__":
    print("mock_api listening on port %d, serving %s" % (PORT, DATA_PATH), flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
