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
        responses = self.path.endswith('/responses')
        messages = payload['input'] if responses else payload['messages']
        evidence = [Evidence.model_validate(line) for line in json.loads(messages[1]["content"])]
        result = rules(evidence)
        content = {"structuredResume": result.structuredResume.model_dump(), "requirements": [item.model_dump() for item in result.requirements]}
        text = json.dumps(content, ensure_ascii=False)
        if payload.get('stream'):
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Connection', 'close')
            self.end_headers()
            for start in range(0, len(text), 64):
                delta = text[start:start+64]
                item = {'type': 'response.output_text.delta', 'delta': delta} if responses else {'choices': [{'index': 0, 'delta': {'content': delta}}]}
                self.wfile.write(('data: '+json.dumps(item, ensure_ascii=False)+'\n\n').encode())
                self.wfile.flush()
            if responses:
                terminal = {'type': 'response.completed', 'response': {'status': 'completed', 'output_text': text}}
                self.wfile.write(('data: '+json.dumps(terminal, ensure_ascii=False)+'\n\n').encode())
            else:
                self.wfile.write(b'data: {"choices":[{"delta":{},"finish_reason":"stop"}]}\n\ndata: [DONE]\n\n')
            self.wfile.flush()
            self.close_connection = True
            return
        body = json.dumps({'output_text': text} if responses else {"choices": [{"message": {"content": text}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8099), Handler).serve_forever()
