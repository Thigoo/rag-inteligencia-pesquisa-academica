from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Classificação de Sensibilidade (Guardrails)
class SensitivityLevel(str, Enum):
    PUBLICO = "publico"
    INTERNO = "interno"
    RESTRITO = "restrito"

# Natureza das bases declaradas no Manifesto
class BaseNatureza(str, Enum):
    NORMATIVA = "normativa"
    ESTRUTURADA = "estruturada"
    CONVERSACIONAL = "conversacional"
    AGREGADA = "agregada"

# Schema de Validação de Chunk de Documento
class ChunkMetadata(BaseModel):
    chunk_id: str = Field(..., description="ID único do chunk")
    doc_type: str = Field(..., description="Tipo do documento originário (pdf, json, txt)")
    source_file: str = Field(..., description="Caminho relativo do arquivo de origem")
    base_id: str = Field(..., description="ID da base declarada no manifesto")
    natureza: BaseNatureza = Field(..., description="Natureza da base de origem")
    sensitivity: SensitivityLevel = Field(default=SensitivityLevel.PUBLICO)
    campo_vigencia: Optional[str] = Field(None, description="Data/Período de vigência, se aplicável")
    extras: Dict[str, Any] = Field(default_factory=dict, description="Metadados adicionais extraídos")

class DocumentChunk(BaseModel):
    chunk_id: str
    content: str = Field(..., description="Texto do trecho/chunk")
    metadata: ChunkMetadata

# Schema da Analise de Query e Roteamento (Adaptive RAG)
class QueryAnalysis(BaseModel):
    query_id: str
    original_query: str
    intent: str = Field(..., description="Intenção detectada pelo analisador")
    extracted_filters: Dict[str, Any] = Field(default_factory=dict, description="Filtros numéricos/estruturados extraídos")
    target_bases: List[str] = Field(..., description="Lista de base_ids para onde a busca deve ser roteada")
    requires_cross_source: bool = Field(default=False, description="Indica se exige combinação de múltiplas bases")

# Schema de Resposta Final do Pipeline RAG
class RAGResponse(BaseModel):
    run_id: str
    query_id: str
    answer: str = Field(..., description="Resposta sintetizada gerada pelo LLM")
    sources_used: List[Dict[str, Any]] = Field(default_factory=list, description="Lista de chunks e fontes consultadas")
    is_refusal: bool = Field(default=False, description="True se a solicitação acionou guardrails de recusa")
    refusal_reason: Optional[str] = Field(None, description="Motivo da recusa caso is_refusal=True")
    latency_ms: int = 0
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    db_queries: Dict[str, Any] = Field(default_factory=dict, description="Detalhes das consultas executadas nos bancos (SQLite, ChromaDB, BM25)")