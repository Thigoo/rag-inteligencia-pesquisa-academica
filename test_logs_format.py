from src.obs import log_event, generate_run_id

# Simulação de pipeline completo para validação do formato de log JSONL
run_id = generate_run_id()
query_id = "q_0042"

# 1. query_analysis
log_event(
    run_id=run_id,
    stage="query_analysis",
    status="ok",
    query_id=query_id,
    input_data="Quais trabalhos de saúde digital tiveram financiamento externo?",
    output_data="Intenção: cross_source; Filtros: {linha: saude digital}",
    latencia_ms=12,
    extra={"filtros": {"linha": "saude digital"}}
)

# 2. roteamento
log_event(
    run_id=run_id,
    stage="roteamento",
    status="ok",
    query_id=query_id,
    input_data="Quais trabalhos de saúde digital tiveram financiamento externo?",
    output_data="Bases: ['producao_estruturada', 'metricas_agregada']",
    latencia_ms=5,
    extra={"target_bases": ["producao_estruturada", "metricas_agregada"]}
)

# 3. retrieval_denso
log_event(
    run_id=run_id,
    stage="retrieval_denso",
    status="ok",
    query_id=query_id,
    input_data="saúde digital financiamento externo",
    output_data="12 chunks recuperados",
    latencia_ms=150,
    extra={"k": 12, "modelo_embedding": "xagi/qwen3-embedding:0.6b-q4_k_m"}
)

# 4. retrieval_bm25
log_event(
    run_id=run_id,
    stage="retrieval_bm25",
    status="ok",
    query_id=query_id,
    input_data="saúde digital financiamento externo",
    output_data="10 chunks recuperados",
    latencia_ms=8,
    extra={"k": 10}
)

# 5. fusao_rrf
log_event(
    run_id=run_id,
    stage="fusao_rrf",
    status="ok",
    query_id=query_id,
    input_data="Denso (12) + BM25 (10)",
    output_data="6 chunks selecionados via RRF (k=60)",
    latencia_ms=3,
    extra={"top_ids": ["est_work_01", "norm_faperj_02"]}
)

# 6. geracao
log_event(
    run_id=run_id,
    stage="geracao",
    status="ok",
    query_id=query_id,
    input_data="Prompt contextual com 6 fontes",
    output_data="Resposta sintetizada com citações",
    latencia_ms=850,
    tokens={"prompt": 450, "completion": 120, "total": 570},
    modelo="qcwind/qwen3-8b-instruct-Q4-K-M",
    extra={"temperature": 0.2}
)

# 7. validacao
log_event(
    run_id=run_id,
    stage="validacao",
    status="ok",
    query_id=query_id,
    input_data="output_sanitization",
    output_data="ok - e-mails mascarados para [E-MAIL PROTEGIDO]",
    latencia_ms=4
)

# 8. feedback
log_event(
    run_id=run_id,
    stage="feedback",
    status="ok",
    query_id=query_id,
    input_data="pipeline_completed",
    output_data="Latência total: 1032ms",
    latencia_ms=1032
)

print(f"[OK] Logs gravados para o run_id: {run_id}")
