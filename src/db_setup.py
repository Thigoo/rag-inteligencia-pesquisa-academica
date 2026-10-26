"""
src/db_setup.py
===============
Script de setup unificado: constroi SQLite + ChromaDB a partir dos dados raw.

Uso:
    python -m src.db_setup              # build incremental (nao sobrescreve)
    python -m src.db_setup --force      # rebuild completo (apaga e recria)
    python -m src.db_setup --stats      # apenas exibe estatisticas dos bancos
"""

import argparse
import sys
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.ingest import run_ingest
from src.db_sql import build_sql_db, get_connection
from src.db_chroma import build_chroma_index, get_stats as chroma_stats


def print_stats() -> None:
    """Exibe estatisticas dos dois bancos de dados."""
    print("\n" + "=" * 55)
    print("  ESTATISTICAS DOS BANCOS DE DADOS")
    print("=" * 55)

    # SQLite
    print("\n[SQL] SQLite (dados estruturados/relacionais):")
    sql_path = BASE_DIR / "data" / "academic_rag.db"
    if sql_path.exists():
        conn = get_connection()
        tables = ["artigos", "metricas", "pareceres", "editais", "beneficiarios_fomento"]
        for table in tables:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                print(f"   {table:<30} {count:>5} registros")
            except Exception:
                print(f"   {table:<30} (erro)")
        conn.close()
        size_kb = sql_path.stat().st_size // 1024
        print(f"   {'Tamanho do arquivo':<30} {size_kb:>5} KB")
    else:
        print("   [AVISO] Banco nao encontrado (execute --force para criar)")

    # ChromaDB
    print("\n[Chroma] ChromaDB (busca semantica vetorial):")
    chroma_path = BASE_DIR / "data" / "chroma_db"
    if chroma_path.exists():
        stats = chroma_stats()
        total = sum(stats.values())
        for base_id, count in stats.items():
            print(f"   {base_id:<35} {count:>5} chunks")
        print(f"   {'TOTAL':<35} {total:>5} chunks")
    else:
        print("   [AVISO] ChromaDB nao encontrado (execute --force para criar)")

    print("\n" + "=" * 55)


def build_all(force: bool = False) -> None:
    """Constroi SQLite e ChromaDB a partir dos dados raw."""
    print("\n" + "=" * 55)
    print(f"  BUILD {'COMPLETO (force)' if force else 'INCREMENTAL'}")
    print("=" * 55)
    t_total = time.time()

    # 1. Ingestao dos dados raw -> chunks
    print("\n[1/3] Ingerindo dados raw...")
    t0 = time.time()
    chunks = run_ingest()
    print(f"      OK: {len(chunks)} chunks gerados em {time.time()-t0:.1f}s")

    # 2. SQLite
    print("\n[2/3] Construindo banco SQLite...")
    t0 = time.time()
    build_sql_db(force=force)
    print(f"      OK: SQLite pronto em {time.time()-t0:.1f}s")

    # 3. ChromaDB
    print("\n[3/3] Construindo indice ChromaDB...")
    t0 = time.time()
    total_chroma = build_chroma_index(chunks, force=force)
    print(f"      OK: ChromaDB pronto: {total_chroma} chunks em {time.time()-t0:.1f}s")

    print(f"\nSetup completo em {time.time()-t_total:.1f}s total")
    print_stats()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Setup dos bancos de dados RAG (SQLite + ChromaDB)"
    )
    parser.add_argument("--force", action="store_true",
                        help="Rebuild completo (apaga e recria ambos os bancos)")
    parser.add_argument("--stats", action="store_true",
                        help="Apenas exibe estatisticas dos bancos existentes")
    args = parser.parse_args()

    if args.stats:
        print_stats()
    else:
        build_all(force=args.force)
