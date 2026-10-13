"""Loopback-only synthetic demo. Actor labels are not authentication."""
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from pathlib import Path
import secrets
import uuid
import webbrowser
from .engine import Ledger
from .model import ReviewError, canonical
from .runner import execute

ROOT = Path(__file__).resolve().parents[1]

class Demo:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)
        self.token = secrets.token_urlsafe(32)
        self.reset(False)

    def reset(self, incomplete=False):
        self.path = self.folder / ("synthetic_" + uuid.uuid4().hex + ".sqlite")
        corpus = json.loads((ROOT / "fixtures/inputs.json").read_text())
        case_id = "missing_edges" if incomplete else "relevant_time"
        case = next(c for c in corpus["cases"] if c["id"] == case_id)
        ledger = Ledger(self.path)
        try:
            for action in case["setup"]:
                execute(ledger, action)
        finally:
            ledger.close()

    def state(self):
        ledger = Ledger(self.path)
        try:
            state = ledger.state()
            state["session_file"] = self.path.name
            return state
        finally:
            ledger.close()

    def action(self, op):
        if op in {"reset", "missing_links"}:
            self.reset(op == "missing_links")
            return self.state()
        ledger = Ledger(self.path)
        try:
            if op in {"correct", "metadata"}:
                bus = ledger.observation("obs_bus")
                row = ledger.db.execute("SELECT content FROM versions WHERE id=?", (bus["source_version_id"],)).fetchone()
                content = json.loads(row[0])
                number = len(ledger.state()["captures"]) + 1
                if op == "correct":
                    content["event_time"] = "2026-10-01T15:40:00+08:00"
                else:
                    content["editor_note"] = "Edited metadata " + str(number)
                execute(ledger, {"op": "capture", "capture_id": "capture_ui_" + str(number),
                        "source_key": "source_bus", "content": content, "retrieved_at": ledger._now()})
            elif op == "review":
                requests = [r for r in ledger.state()["review_requests"] if r["status"] == "awaiting_human_review"]
                if not requests:
                    raise ReviewError("Apply a correction first; there is no open request to review.")
                request = requests[-1]
                suffix = len(ledger.state()["human_reviews"]) + 2
                refs = [{"node_id": ledger.observation(k)["id"], "fields": ["event_time"]}
                        for k in ("obs_school", "obs_bus")]
                ledger.review(request["id"], "review_ui_" + str(suffix), "decision_ui_" + str(suffix),
                              "defer", "Demo human: corrected timing removes the stated exclusion basis. Identity remains unverified; seek corroboration.",
                              refs, "reviewer_demo")
            else:
                raise ReviewError("Unknown demo action.")
            state = ledger.state()
            state["session_file"] = self.path.name
            return state
        finally:
            ledger.close()

def make_server(folder, port=8765):
    demo = Demo(folder)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, data, status=200, content_type="application/json; charset=utf-8", attachment=False):
            body = data if isinstance(data, bytes) else canonical(data).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
            if attachment:
                self.send_header("Content-Disposition", 'attachment; filename="synthetic-review-trace.json"')
            self.end_headers()
            self.wfile.write(body)

        def allowed_host(self):
            return self.headers.get("Host") == f"127.0.0.1:{self.server.server_port}"

        def do_GET(self):
            if not self.allowed_host():
                return self.send({"error": "Use the loopback URL printed by the demo."}, 403)
            if self.path == "/":
                html = (ROOT / "web/index.html").read_text().replace("__DEMO_TOKEN__", demo.token)
                return self.send(html.encode("utf-8"), content_type="text/html; charset=utf-8")
            if self.path in {"/state", "/export"}:
                return self.send(demo.state(), attachment=self.path == "/export")
            return self.send({"error": "Not found."}, 404)

        def do_POST(self):
            origin = f"http://127.0.0.1:{self.server.server_port}"
            if not self.allowed_host() or self.headers.get("Origin") != origin or self.headers.get("X-Demo-Token") != demo.token:
                return self.send({"error": "Only this local demo page may request a change."}, 403)
            if self.path != "/action":
                return self.send({"error": "Not found."}, 404)
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if size < 1 or size > 1024 or self.headers.get_content_type() != "application/json":
                    raise ReviewError("Invalid demo request.")
                value = json.loads(self.rfile.read(size))
                if not isinstance(value, dict) or set(value) != {"op"}:
                    raise ReviewError("Request requires one demo operation.")
                return self.send(demo.action(value["op"]))
            except (ValueError, TypeError, KeyError) as exc:
                return self.send({"error": str(exc)}, 400)
    server = HTTPServer(("127.0.0.1", port), Handler)
    server.demo = demo
    return server

def serve_demo(folder, port, open_browser=True):
    server = make_server(folder, port)
    url = f"http://127.0.0.1:{server.server_port}/"
    print("Synthetic local demonstration: " + url, flush=True)
    print("Stop with Ctrl+C. Session ledgers are preserved in " + str(Path(folder).resolve()), flush=True)
    if open_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
