import json
import os
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


PORT = int(os.getenv("PORT", "8080"))
TEMPLATE = Path(__file__).with_name("index.html").read_text(encoding="utf-8")


class RequestHandler(BaseHTTPRequestHandler):
    def send_content(self, status, content_type, body):
        encoded = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_GET(self):
        if self.path == "/health":
            self.send_content(200, "application/json", json.dumps({"status": "healthy"}))
            return

        if self.path != "/":
            self.send_content(404, "text/plain", "Not found")
            return

        replacements = {
            "{{HOSTNAME}}": socket.gethostname(),
            "{{PLATFORM}}": os.getenv("PLATFORM", "Local container"),
            "{{APP_VERSION}}": os.getenv("APP_VERSION", "v1"),
            "{{AWS_REGION}}": os.getenv("AWS_REGION", "not set"),
        }
        page = TEMPLATE
        for marker, value in replacements.items():
            page = page.replace(marker, value)

        self.send_content(200, "text/html; charset=utf-8", page)

    def log_message(self, message_format, *args):
        print(
            json.dumps(
                {
                    "client": self.client_address[0],
                    "request": message_format % args,
                    "platform": os.getenv("PLATFORM", "Local container"),
                }
            ),
            flush=True,
        )


if __name__ == "__main__":
    print(f"CloudAdhar demo listening on port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), RequestHandler).serve_forever()
