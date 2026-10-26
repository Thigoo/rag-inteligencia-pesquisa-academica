import sys
from src.pipeline import AcademicRAGPipeline

# Garante compatibilidade de encoding UTF-8 no Windows (evita erro com emojis e acentos)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def safe_print(text: str = ""):
    """Imprime texto de forma segura em qualquer terminal Windows."""
    try:
        print(text)
    except UnicodeEncodeError:
        print(text.encode("ascii", "replace").decode("ascii"))


def main():
    safe_print("=" * 70)
    safe_print("  Inteligência sobre Pesquisa Acadêmica · Adaptive RAG")
    safe_print("  Residência TIC em Trilhas · PUC-Rio / ECOA (Cenário 3)")
    safe_print("=" * 70)
    safe_print("Digite sua pergunta ou 'sair' para encerrar.\n")

    safe_print("[*] Carregando índices locais...")
    pipeline = AcademicRAGPipeline()
    safe_print("[OK] Pipeline pronto para receber perguntas!\n")

    while True:
        try:
            query = input("\n[Pergunta] > ").strip()
            if not query:
                continue
            if query.lower() in ["sair", "exit", "quit"]:
                safe_print("[*] Encerrando sessão. Até logo!")
                break

            safe_print("[*] Processando pergunta através do pipeline Adaptive RAG...")
            response = pipeline.run(query)

            safe_print("\n" + "-" * 70)
            safe_print("  RESPOSTA GERADA")
            safe_print("-" * 70)
            safe_print(response.answer)

            if response.is_refusal:
                safe_print(f"\n[!] AVISO DE ÉTICA/GUARDRAILS: {response.refusal_reason}")

            if response.sources_used:
                safe_print("\n" + "-" * 70)
                safe_print(f"  FONTES CONSULTADAS ({len(response.sources_used)})")
                safe_print("-" * 70)
                for s in response.sources_used:
                    safe_print(f"  • Base: {s['base_id']} | Natureza: {s['natureza']} | Chunk: {s['chunk_id']}")

            safe_print(f"\n[Latência Total: {response.latency_ms} ms]")

        except KeyboardInterrupt:
            safe_print("\n[*] Sessão interrompida.")
            break
        except Exception as e:
            safe_print(f"[Erro] Falha ao processar a pergunta: {e}")


if __name__ == "__main__":
    main()
