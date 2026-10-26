import functools
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Diretório base de logs
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

def generate_run_id() -> str:
    """Gera um identificador único de 8 caracteres para amarração das etapas."""
    return str(uuid.uuid4())[:8]

def get_log_filepath() -> Path:
    """Retorna o caminho do arquivo de log com data atual no formato pipeline-AAAA-MM-DD.jsonl."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return LOGS_DIR / f"pipeline-{today}.jsonl"

def log_event(
    run_id: str,
    stage: str,
    status: str = "ok",
    query_id: str = "q_0000",
    input_data: str = "",
    output_data: str = "",
    latencia_ms: int = 0,
    tokens: dict = None,
    modelo: str = None,
    extra: dict = None
):
    """
    Grava uma linha de log estruturada no formato JSONL.
    Estágios padronizados: query_analysis, roteamento, retrieval_denso, 
    retrieval_bm25, fusao_rrf, rerank, geracao, validacao, feedback.
    """
    if tokens is None:
        tokens = {"prompt": 0, "completion": 0, "total": 0}
    if extra is None:
        extra = {}

    log_entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "query_id": query_id,
        "stage": stage,
        "status": status,
        "latencia_ms": latencia_ms,
        "input": str(input_data),
        "output": str(output_data),
        "tokens": tokens,
        "modelo": modelo,
        "extra": extra
    }

    log_file = get_log_filepath()
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def trace_stage(stage_name: str, query_id: str = "q_0000"):
    """
    Decorator para capturar latência, entrada/saída e tokens de chamadas de função.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            run_id = kwargs.get("run_id", generate_run_id())
            status = "ok"
            output = None
            tokens = {"prompt": 0, "completion": 0, "total": 0}
            modelo = None

            try:
                result = func(*args, **kwargs)
                output = result

                # Tenta capturar o uso de tokens se a resposta for um objeto compatível com OpenAI
                if hasattr(result, "usage") and result.usage:
                    tokens = {
                        "prompt": getattr(result.usage, "prompt_tokens", 0),
                        "completion": getattr(result.usage, "completion_tokens", 0),
                        "total": getattr(result.usage, "total_tokens", 0)
                    }
                if hasattr(result, "model"):
                    modelo = getattr(result, "model")

                return result
            except Exception as e:
                status = "error"
                output = str(e)
                raise e
            finally:
                latencia_ms = int((time.time() - start_time) * 1000)
                input_data = str(args[0]) if args else str(kwargs)
                
                log_event(
                    run_id=run_id,
                    stage=stage_name,
                    status=status,
                    query_id=query_id,
                    input_data=input_data,
                    output_data=output,
                    latencia_ms=latencia_ms,
                    tokens=tokens,
                    modelo=modelo
                )

        return wrapper
    return decorator