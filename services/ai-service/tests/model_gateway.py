"""CI-only synthetic OpenAI-compatible gateway; never a real model."""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from app.extraction import rules
from app.models import Evidence


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"UP")

    def do_POST(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        evidence = [Evidence.model_validate(line) for line in json.loads(payload["messages"][1]["content"])]
        result = rules(evidence)
        content = {"structuredResume": result.structuredResume.model_dump(), "requirements": [item.model_dump() for item in result.requirements]}
        body = json.dumps({"choices": [{"message": {"content": json.dumps(content)}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
