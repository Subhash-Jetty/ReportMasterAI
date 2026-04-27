"""Lightweight preview server - serves static files + mock API for UI testing."""
import json, http.server, os

PORT = 8000
STATIC = os.path.join(os.path.dirname(__file__), "static")

MOCK_DOCS = {"total_documents": 2, "total_chunks": 47, "embedding_model": "all-MiniLM-L6-v2", "index_ready": True,
    "documents": [{"name": "lease_accounting_asc842.txt", "size_bytes": 18432, "chunk_count": 25, "indexed_at": "2026-04-26"},
                  {"name": "revenue_recognition_asc606.txt", "size_bytes": 12288, "chunk_count": 22, "indexed_at": "2026-04-26"}]}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/": self.serve_file("index.html")
        elif self.path == "/login": self.serve_file("login.html")
        elif self.path == "/register": self.serve_file("register.html")
        elif self.path.startswith("/static/"): self.serve_static()
        elif self.path == "/api/documents": self.json_response(MOCK_DOCS)
        elif self.path == "/api/health": self.json_response({"status": "healthy"})
        else: self.send_error(404)

    def do_POST(self):
        if self.path == "/api/query":
            length = int(self.headers.get('Content-Length', 0))
            body = json.loads(self.rfile.read(length)) if length else {}
            self.json_response({"answer": f"This is a **preview mode** response to: \"{body.get('question','')}\".\n\nThe full RAG pipeline requires PyTorch. Your UI is working correctly!",
                "sources": [{"document_name": "sample_doc.txt", "content": "Sample source content for preview.", "relevance_score": 0.92, "chunk_index": 0}],
                "query": body.get("question",""), "processing_time": 0.42, "model_used": "preview-mode"})
        else: self.send_error(404)

    def serve_file(self, name):
        path = os.path.join(STATIC, name)
        if os.path.exists(path):
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            with open(path, "rb") as f: self.wfile.write(f.read())
        else: self.send_error(404)

    def serve_static(self):
        rel = self.path[len("/static/"):]
        path = os.path.join(STATIC, rel)
        if os.path.exists(path):
            self.send_response(200)
            ct = "text/css" if rel.endswith(".css") else "application/javascript" if rel.endswith(".js") else "text/html"
            self.send_header("Content-Type", ct)
            self.end_headers()
            with open(path, "rb") as f: self.wfile.write(f.read())
        else: self.send_error(404)

    def json_response(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def log_message(self, fmt, *args): pass

print(f"Preview server at http://localhost:{PORT}")
http.server.HTTPServer(("", PORT), Handler).serve_forever()
