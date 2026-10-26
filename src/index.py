import json
import os
import pickle
import time
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np
from rank_bm25 import BM25Okapi
from config import (
    BATCH_SIZE,
    EMBEDDING_MODEL,
    INDEX_DIR,
    RATE_LIMIT_PAUSE_SEC,
    get_openai_client,
)
from src.schema import DocumentChunk

CACHE_FILE = INDEX_DIR / "embeddings_cache.pkl"
BM25_FILE = INDEX_DIR / "bm25_index.pkl"
CHUNKS_INDEX_FILE = INDEX_DIR / "indexed_chunks.json"


def get_embedding_with_cache(
    texts: List[str], client, cache: Dict[str, List[float]]
) -> List[List[float]]:
    """Gera embeddings utilizando cache em disco para evitar chamadas redundantes."""
    embeddings = []
    texts_to_fetch = []
    indices_to_fetch = []

    for i, text in enumerate(texts):
        if text in cache:
            embeddings.append(cache[text])
        else:
            embeddings.append(None)
            texts_to_fetch.append(text)
            indices_to_fetch.append(i)

    if texts_to_fetch:
        print(
            f"[*] Gerando embeddings para {len(texts_to_fetch)} novos trechos em lotes de {BATCH_SIZE}..."
        )

        for batch_start in range(0, len(texts_to_fetch), BATCH_SIZE):
            batch_texts = texts_to_fetch[batch_start : batch_start + BATCH_SIZE]
            batch_indices = indices_to_fetch[batch_start : batch_start + BATCH_SIZE]

            success = False
            for attempt in range(2):
                try:
                    # Sanitiza textos vazios ou problemáticos
                    clean_batch = [t if t.strip() else " " for t in batch_texts]
                    response = client.embeddings.create(
                        model=EMBEDDING_MODEL, input=clean_batch, timeout=30
                    )

                    for orig_idx, emb_item in zip(batch_indices, response.data):
                        emb_vector = emb_item.embedding
                        cache[texts[orig_idx]] = emb_vector
                        embeddings[orig_idx] = emb_vector
                    success = True
                    break
                except Exception as e:
                    if attempt == 0:
                        time.sleep(2)
                    else:
                        print(f"[!] Aviso: Embeddings remotos ocupados ({e}). Usando fallback léxico BM25.")

            if not success:
                for orig_idx in batch_indices:
                    embeddings[orig_idx] = [0.0] * 1024

            # Pausa para respeitar o rate-limit do servidor compartilhado
            if batch_start + BATCH_SIZE < len(texts_to_fetch):
                time.sleep(RATE_LIMIT_PAUSE_SEC)

        # Salva o cache atualizado
        with open(CACHE_FILE, "wb") as f:
            pickle.dump(cache, f)

    return embeddings


class VectorIndex:
    def __init__(self):
        self.chunks: List[DocumentChunk] = []
        self.embeddings: np.ndarray = np.array([])
        self.bm25: BM25Okapi = None
        self.tokenized_corpus: List[List[str]] = []
        self.client = get_openai_client()
        self.cache: Dict[str, List[float]] = {}
        self._load_cache()

    def _load_cache(self):
        if CACHE_FILE.exists():
            with open(CACHE_FILE, "rb") as f:
                self.cache = pickle.load(f)

    def build_index(self, chunks: List[DocumentChunk]):
        """Constrói índice denso (vetorial) e esparso (BM25)."""
        self.chunks = chunks
        texts = [c.content for c in chunks]

        # 1. Embeddings Densos com Cache
        vectors = get_embedding_with_cache(texts, self.client, self.cache)
        self.embeddings = np.array(vectors, dtype=np.float32)

        # Normalização L2 para similaridade de cosseno via dot product
        norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.embeddings = self.embeddings / norms

        # 2. Índice BM25
        print("[*] Construindo índice BM25...")
        self.tokenized_corpus = [c.content.lower().split() for c in chunks]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

        self.save_local()
        print(f"[OK] Índices construídos e persistidos com {len(chunks)} chunks!")

    def save_local(self):
        """Persiste os índices em disco."""
        INDEX_DIR.mkdir(parents=True, exist_ok=True)

        with open(CACHE_FILE, "wb") as f:
            pickle.dump(self.cache, f)

        with open(BM25_FILE, "wb") as f:
            pickle.dump((self.bm25, self.tokenized_corpus), f)

        with open(CHUNKS_INDEX_FILE, "w", encoding="utf-8") as f:
            json.dump(
                [c.model_dump() for c in self.chunks], f, ensure_ascii=False
            )

        np.save(INDEX_DIR / "vectors.npy", self.embeddings)

    def load_local(self) -> bool:
        """Carrega os índices persistidos do disco."""
        if not (
            CHUNKS_INDEX_FILE.exists()
            and BM25_FILE.exists()
            and (INDEX_DIR / "vectors.npy").exists()
        ):
            return False

        with open(CHUNKS_INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.chunks = [DocumentChunk(**item) for item in data]

        with open(BM25_FILE, "rb") as f:
            self.bm25, self.tokenized_corpus = pickle.load(f)

        self.embeddings = np.load(INDEX_DIR / "vectors.npy")
        self._load_cache()
        return True

    def _matches_filters(
        self,
        chunk: DocumentChunk,
        filters: Dict[str, object] = None,
    ) -> bool:
        """Verifica se um chunk atende aos filtros estruturados."""
        if not filters:
            return True

        extras = chunk.metadata.extras or {}

        for key, expected in filters.items():
            if expected is None:
                continue

            if key == "ano":
                value = extras.get("year")
                if value is None:
                    value = extras.get("publication_year")

                if value is None:
                    return False

                try:
                    if int(value) != int(expected):
                        return False
                except (TypeError, ValueError):
                    return False
            else:
                value = extras.get(key)

                if value is None:
                    return False

                if isinstance(value, list):
                    if expected not in value:
                        return False
                elif str(value).lower() != str(expected).lower():
                    return False

        return True

    def search_dense(
        self,
        query: str,
        top_k: int = 10,
        base_filter: List[str] = None,
        structured_filters: Dict[str, object] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Busca densa por similaridade de cosseno com suporte a filtro de base."""
        if len(self.chunks) == 0:
            return []

        # Embedding da query (com cache)
        q_emb = get_embedding_with_cache([query], self.client, self.cache)[0]
        q_vec = np.array(q_emb, dtype=np.float32)
        norm = np.linalg.norm(q_vec)
        if norm > 0:
            q_vec = q_vec / norm

        scores = np.dot(self.embeddings, q_vec)

        ranked = []
        for idx in np.argsort(-scores):
            chunk = self.chunks[idx]
            if (
                base_filter
                and chunk.metadata.base_id not in base_filter
                and "all" not in base_filter
            ):
                continue
            ranked.append((chunk, float(scores[idx])))
            if len(ranked) >= top_k:
                break

        return ranked

    def search_bm25(
        self,
        query: str,
        top_k: int = 10,
        base_filter: List[str] = None,
        structured_filters: Dict[str, object] = None,
    ) -> List[Tuple[DocumentChunk, float]]:
        """Busca esparsa por BM25 com suporte a filtro de base."""
        if not self.bm25 or len(self.chunks) == 0:
            return []

        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)

        ranked = []
        for idx in np.argsort(-scores):
            if scores[idx] <= 0:
                continue
            chunk = self.chunks[idx]
            if (
                base_filter
                and chunk.metadata.base_id not in base_filter
                and "all" not in base_filter
            ):
                continue
            ranked.append((chunk, float(scores[idx])))
            if len(ranked) >= top_k:
                break

        return ranked
