import http.server
import json
import socketserver
import sys
import threading
from pathlib import Path
from urllib.parse import urlparse

# Garante compatibilidade UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.pipeline import AcademicRAGPipeline

PORT = 8000
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"

print("[*] Inicializando pipeline Adaptive RAG para a interface Web...")
pipeline = AcademicRAGPipeline()
print("[OK] Pipeline carregado e pronto!")


class RAGHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(STATIC_DIR), **kwargs)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/query":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length).decode("utf-8")

            try:
                data = json.loads(post_data)
                query = data.get("query", "").strip()
                query_id = data.get("query_id", "web_q_01")

                if not query:
                    self._send_json({"error": "A pergunta não pode estar vazia."}, status=400)
                    return

                # Executa o pipeline
                response = pipeline.run(query=query, query_id=query_id)

                result = {
                    "run_id": response.run_id,
                    "query_id": response.query_id,
                    "answer": response.answer,
                    "sources": response.sources_used,
                    "is_refusal": response.is_refusal,
                    "refusal_reason": response.refusal_reason,
                    "latency_ms": response.latency_ms,
                    "generated_at": response.generated_at
                }

                self._send_json(result)

            except Exception as e:
                self._send_json({"error": f"Falha no processamento: {str(e)}"}, status=500)
        else:
            self.send_error(404, "Endpoint não encontrado")

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            status_data = {
                "status": "online",
                "total_chunks": len(pipeline.index.chunks),
                "scenario": "Cenário 3 · Inteligência sobre Pesquisa Acadêmica",
                "bases": ["editais_normativo", "producao_estruturada", "pareceres_conversacional", "metricas_agregada"]
            }
            self._send_json(status_data)
        else:
            # Serve os arquivos estáticos (index.html, style.css, app.js)
            super().do_GET()

    def _send_json(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), RAGHandler) as httpd:
        print("\n" + "=" * 70)
        print("  [OK] INTERFACE WEB DO ADAPTIVE RAG ATIVA!")
        print(f"  [+] Acesse no seu navegador: http://localhost:{PORT}")
        print("=" * 70 + "\n")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[*] Servidor web encerrado.")


if __name__ == "__main__":
    run_server()
