import json
import time
from pathlib import Path

from src.schema import RAGResponse, QueryAnalysis, DocumentChunk
from src.obs import generate_run_id, log_event
from src.router import analyze_and_route
from src.retrieve import retrieve_chunks
from src.generate import generate_rag_response
from src.index import VectorIndex


BASE_DIR = Path(__file__).resolve().parent.parent
CHUNKS_FILE = BASE_DIR / "data" / "chunks_v1.json"
HISTORY_FILE = BASE_DIR / "data" / "history.jsonl"


class AcademicRAGPipeline:
    def __init__(self):
        self.index = VectorIndex()
        self._initialize_index()
        self._ensure_databases()

    def _initialize_index(self):
        """Carrega ou constroi o indice BM25 com cache em disco."""
        if not self.index.load_local():
            if CHUNKS_FILE.exists():
                with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chunks = [DocumentChunk(**item) for item in data]
                self.index.build_index(chunks)
            else:
                print(
                    "[!] chunks_v1.json nao encontrado. "
                    "Execute `python -m src.ingest` primeiro."
                )

    def _ensure_databases(self):
        """Garante que SQLite e ChromaDB existem e estao populados."""
        from src.db_sql import build_sql_db, DB_PATH
        from src.db_chroma import build_chroma_index, get_stats

        # SQLite: cria se nao existe
        if not DB_PATH.exists():
            print("[Pipeline] Construindo SQLite pela primeira vez...")
            build_sql_db(force=True)

        # ChromaDB: cria se vazio
        stats = get_stats()
        if sum(stats.values()) == 0:
            print("[Pipeline] Construindo ChromaDB pela primeira vez...")
            if CHUNKS_FILE.exists():
                with open(CHUNKS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    chunks = [DocumentChunk(**item) for item in data]
                build_chroma_index(chunks, force=True)
            else:
                print("[!] Sem chunks para indexar no ChromaDB.")

    def _persist_history(
        self,
        run_id: str,
        query_id: str,
        query: str,
        response: RAGResponse,
    ):
        """Persiste o histórico das interações do pipeline."""
        HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        search_history_file = BASE_DIR / "data" / "search_history.jsonl"

        record = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "run_id": run_id,
            "query_id": query_id,
            "query": query,
            "answer": response.answer,
            "is_refusal": response.is_refusal,
            "refusal_reason": response.refusal_reason,
            "latency_ms": response.latency_ms,
            "sources_used": response.sources_used,
            "db_queries": response.db_queries or {},
        }

        # Salva tanto no history.jsonl quanto no search_history.jsonl
        for target_file in [HISTORY_FILE, search_history_file]:
            with open(target_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def run(self, query: str, query_id: str = "q_0001") -> RAGResponse:
        """Executa o pipeline completo de 9 estágios do Adaptive RAG."""
        run_id = generate_run_id()
        t_start = time.time()

        # 1. Análise da Query
        log_event(
            run_id=run_id,
            stage="query_analysis",
            query_id=query_id,
            input_data=query,
            output_data="Análise concluída",
            latencia_ms=2
        )

        # 2. Roteamento Adaptativo
        analysis = analyze_and_route(
            query,
            run_id=run_id,
            query_id=query_id
        )

        # 3. Recuperacao Hibrida (ChromaDB + BM25 + SQL + RRF + Reranker)
        retrieved_chunks, db_queries = retrieve_chunks(
            analysis,
            self.index,
            run_id=run_id,
            top_k=6,
            return_queries_info=True
        )

        # 4. Geração e Validação de Guardrails
        response = generate_rag_response(
            analysis,
            retrieved_chunks,
            run_id=run_id,
            query_id=query_id,
            db_queries=db_queries
        )

        # 5. Persistência do histórico
        self._persist_history(
            run_id=run_id,
            query_id=query_id,
            query=query,
            response=response
        )

        # 6. Estágio de Feedback / Conclusão
        log_event(
            run_id=run_id,
            stage="feedback",
            query_id=query_id,
            input_data="pipeline_completed",
            output_data=(
                f"Latência total: {response.latency_ms}ms | "
                f"Refusal: {response.is_refusal}"
            ),
            latencia_ms=int((time.time() - t_start) * 1000),
            extra={
                "sources_count": len(response.sources_used),
                "history_persisted": True
            }
        )

        return response



if __name__ == "__main__":
    pipeline = AcademicRAGPipeline()
    sample_q = (
        "Quais artigos publicados tiveram financiamento declarado "
        "e qual foi o edital?"
    )

    print(f"\n[*] Executando pergunta de teste: {sample_q}")

    res = pipeline.run(sample_q)

    print("\n--- RESPOSTA ---")
    print(res.answer)

    print(f"\n--- FONTES ({len(res.sources_used)}) ---")
    for s in res.sources_used:
        print(f"- Base: {s['base_id']} | ID: {s['chunk_id']}")
