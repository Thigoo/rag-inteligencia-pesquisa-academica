"""
src/db_chroma.py
================
Banco de dados vetorial ChromaDB para busca semântica (RAG).

Responsabilidade:
  - Armazena TODOS os chunks de texto de TODAS as bases como embeddings vetoriais.
  - Substitui o FAISS in-memory do src/index.py para a busca densa.
  - O BM25 do src/index.py ainda é usado como complemento léxico (fusão RRF).

Collections ChromaDB (uma por base RAG):
  - "editais_normativo"       → textos normativos (Resoluções, Editais)
  - "producao_estruturada"    → metadados e conteúdo de artigos científicos
  - "pareceres_conversacional"→ textos dos pareceres de revisão/fomento
  - "metricas_agregada"       → textos de tópicos, rankings e indicadores

Uso no pipeline:
  db_chroma.search(query, bases=["editais_normativo"], top_k=5)
  → retorna Lista[DocumentChunk] com score de similaridade coseno
"""

import json
import time
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import chromadb
from chromadb.config import Settings

from src.schema import DocumentChunk, ChunkMetadata, BaseNatureza, SensitivityLevel

BASE_DIR = Path(__file__).resolve().parent.parent
CHROMA_DIR = BASE_DIR / "data" / "chroma_db"

# Mapeamento base_id → natureza
BASE_NATUREZA_MAP = {
    "editais_normativo": BaseNatureza.NORMATIVA,
    "producao_estruturada": BaseNatureza.ESTRUTURADA,
    "pareceres_conversacional": BaseNatureza.CONVERSACIONAL,
    "metricas_agregada": BaseNatureza.AGREGADA,
}

SENSITIVITY_MAP = {
    "editais_normativo": SensitivityLevel.PUBLICO,
    "producao_estruturada": SensitivityLevel.PUBLICO,
    "pareceres_conversacional": SensitivityLevel.INTERNO,
    "metricas_agregada": SensitivityLevel.PUBLICO,
}

# Todas as collections gerenciadas
ALL_BASES = list(BASE_NATUREZA_MAP.keys())


# ---------------------------------------------------------------------------
# Inicialização do cliente ChromaDB
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def get_chroma_client() -> chromadb.PersistentClient:
    """Retorna (cached) o cliente ChromaDB persistente em disco."""
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False)
    )
    return client


def get_collection(base_id: str) -> chromadb.Collection:
    """Retorna ou cria uma collection ChromaDB para a base especificada."""
    client = get_chroma_client()
    # ChromaDB usa embeddings próprios (sentence-transformers local via onnx)
    # Usamos o embedding function padrão do ChromaDB (all-MiniLM-L6-v2)
    return client.get_or_create_collection(
        name=base_id,
        metadata={
            "hnsw:space": "cosine",
            "description": f"Base RAG: {base_id}"
        }
    )


# ---------------------------------------------------------------------------
# Inserção de chunks no ChromaDB
# ---------------------------------------------------------------------------

def upsert_chunks(chunks: List[DocumentChunk], batch_size: int = 100) -> int:
    """
    Insere ou atualiza chunks no ChromaDB, agrupados por base_id.
    Retorna o total de chunks inseridos.
    """
    # Agrupa por base_id
    by_base: Dict[str, List[DocumentChunk]] = {}
    for chunk in chunks:
        bid = chunk.metadata.base_id
        by_base.setdefault(bid, []).append(chunk)

    total = 0
    for base_id, base_chunks in by_base.items():
        collection = get_collection(base_id)
        print(f"[Chroma] Inserindo {len(base_chunks)} chunks em '{base_id}'...")

        for i in range(0, len(base_chunks), batch_size):
            batch = base_chunks[i:i + batch_size]
            ids = [c.chunk_id for c in batch]
            documents = [c.content for c in batch]
            metadatas = []
            for c in batch:
                meta_dict = {
                    "chunk_id": c.chunk_id,
                    "base_id": c.metadata.base_id,
                    "doc_type": c.metadata.doc_type,
                    "source_file": c.metadata.source_file,
                    "natureza": c.metadata.natureza.value,
                    "sensitivity": c.metadata.sensitivity.value,
                    "campo_vigencia": c.metadata.campo_vigencia or "",
                }
                # Achata extras simples (ChromaDB aceita só str/int/float/bool)
                for k, v in (c.metadata.extras or {}).items():
                    if isinstance(v, (str, int, float, bool)):
                        meta_dict[f"extra_{k}"] = v
                    elif isinstance(v, list):
                        meta_dict[f"extra_{k}"] = ", ".join(str(x) for x in v[:5])
                metadatas.append(meta_dict)

            try:
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
                total += len(batch)
            except Exception as e:
                print(f"[Chroma] Erro no batch {i//batch_size}: {e}")

        print(f"[Chroma] OK '{base_id}': {len(base_chunks)} chunks indexados")

    return total


# ---------------------------------------------------------------------------
# Consulta semântica
# ---------------------------------------------------------------------------

def search(
    query: str,
    bases: Optional[List[str]] = None,
    top_k: int = 6,
) -> List[Tuple[DocumentChunk, float]]:
    """
    Busca semântica vetorial no ChromaDB.

    Args:
        query:  Texto da pergunta do usuário.
        bases:  Lista de base_ids para buscar. Se None, busca em todas.
        top_k:  Número de resultados por base (ou total se bases=None).

    Returns:
        Lista de (DocumentChunk, score) ordenada por relevância (score 0–1, maior=melhor).
    """
    target_bases = bases if bases else ALL_BASES
    results: List[Tuple[DocumentChunk, float]] = []

    for base_id in target_bases:
        try:
            collection = get_collection(base_id)
            count = collection.count()
            if count == 0:
                continue

            query_result = collection.query(
                query_texts=[query],
                n_results=min(top_k, count),
                include=["documents", "metadatas", "distances"]
            )

            docs = query_result.get("documents", [[]])[0]
            metas = query_result.get("metadatas", [[]])[0]
            distances = query_result.get("distances", [[]])[0]

            for doc, meta, dist in zip(docs, metas, distances):
                # ChromaDB cosine distance: 0=idêntico, 2=oposto → convert to similarity
                similarity = 1.0 - (dist / 2.0)

                chunk_meta = ChunkMetadata(
                    chunk_id=meta.get("chunk_id", ""),
                    doc_type=meta.get("doc_type", "txt"),
                    source_file=meta.get("source_file", ""),
                    base_id=meta.get("base_id", base_id),
                    natureza=BASE_NATUREZA_MAP.get(base_id, BaseNatureza.NORMATIVA),
                    sensitivity=SENSITIVITY_MAP.get(base_id, SensitivityLevel.PUBLICO),
                    campo_vigencia=meta.get("campo_vigencia") or None,
                    extras={k.replace("extra_", ""): v
                            for k, v in meta.items() if k.startswith("extra_")}
                )
                chunk = DocumentChunk(
                    chunk_id=meta.get("chunk_id", ""),
                    content=doc,
                    metadata=chunk_meta
                )
                results.append((chunk, similarity))

        except Exception as e:
            print(f"[Chroma] Erro na busca em '{base_id}': {e}")

    # Ordena globalmente por similaridade
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k * len(target_bases)]


def search_cross_source(
    query: str,
    bases: List[str],
    top_k_per_base: int = 2,
) -> List[Tuple[DocumentChunk, float]]:
    """
    Busca cross-source: garante pelo menos top_k_per_base resultados de CADA base solicitada.
    Útil para perguntas Q08 que precisam cruzar editais + produção + métricas.
    """
    all_results: List[Tuple[DocumentChunk, float]] = []
    seen_ids = set()

    for base_id in bases:
        base_results = search(query, bases=[base_id], top_k=top_k_per_base)
        for chunk, score in base_results:
            if chunk.chunk_id not in seen_ids:
                all_results.append((chunk, score))
                seen_ids.add(chunk.chunk_id)

    all_results.sort(key=lambda x: x[1], reverse=True)
    return all_results


def get_stats() -> Dict[str, int]:
    """Retorna o número de documentos em cada collection ChromaDB."""
    stats = {}
    client = get_chroma_client()
    existing = {c.name for c in client.list_collections()}
    for base_id in ALL_BASES:
        if base_id in existing:
            stats[base_id] = get_collection(base_id).count()
        else:
            stats[base_id] = 0
    return stats


def reset_all() -> None:
    """Remove e recria todas as collections (usado no rebuild)."""
    client = get_chroma_client()
    for base_id in ALL_BASES:
        try:
            client.delete_collection(base_id)
            print(f"[Chroma] Collection '{base_id}' removida.")
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Construção do índice ChromaDB a partir dos chunks já ingeridos
# ---------------------------------------------------------------------------

def build_chroma_index(chunks: List[DocumentChunk], force: bool = False) -> int:
    """
    Constrói o índice ChromaDB a partir de uma lista de DocumentChunk.
    Se force=True, apaga e recria todas as collections.
    """
    if force:
        reset_all()

    # Verifica se já tem dados
    stats = get_stats()
    total_existing = sum(stats.values())
    if total_existing > 0 and not force:
        print(f"[Chroma] Índice já populado ({total_existing} docs). Use force=True para recriar.")
        return total_existing

    print(f"[Chroma] Construindo índice com {len(chunks)} chunks...")
    t0 = time.time()
    total = upsert_chunks(chunks)
    elapsed = time.time() - t0
    print(f"[Chroma] OK: {total} chunks indexados em {elapsed:.1f}s")
    return total


if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(BASE_DIR))

    from src.ingest import run_ingest
    chunks = run_ingest()
    build_chroma_index(chunks, force=True)

    print("\n[Stats ChromaDB]:")
    for base, count in get_stats().items():
        print(f"  {base}: {count} documentos")

    print("\n[Teste busca semântica]:")
    results = search("questionários anônimos aprovação CEP Resolução 510", bases=["editais_normativo"], top_k=3)
    for chunk, score in results:
        print(f"  score={score:.3f} | {chunk.chunk_id}: {chunk.content[:80]}...")
