import os
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Carrega variáveis de ambiente do .env se existir
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
INVENTORY_DIR = DATA_DIR / "inventory"
INDEX_DIR = BASE_DIR / "index"
LOGS_DIR = BASE_DIR / "logs"

INDEX_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Configurações do modelo
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://ecoa-llm.duckdns.org:11434/v1")
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY", "ollama")

GENERATION_MODEL = os.getenv("GENERATION_MODEL", "qcwind/qwen3-8b-instruct-Q4-K-M")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "xagi/qwen3-embedding:0.6b-q4_k_m")

BATCH_SIZE = int(os.getenv("BATCH_SIZE", "50"))
RATE_LIMIT_PAUSE_SEC = float(os.getenv("RATE_LIMIT_PAUSE_SEC", "10.0"))

def get_openai_client() -> OpenAI:
    """Retorna cliente OpenAI configurado para o endpoint ECOA."""
    return OpenAI(base_url=OLLAMA_URL, api_key=OLLAMA_API_KEY)

RERANKER_MODEL = os.getenv('RERANKER_MODEL', 'cross-encoder/ms-marco-MiniLM-L-6-v2')
