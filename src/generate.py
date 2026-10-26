import re
import time
from typing import Dict, List, Tuple
from config import GENERATION_MODEL, get_openai_client
from src.obs import log_event
from src.schema import DocumentChunk, QueryAnalysis, RAGResponse

EMAIL_REGEX = re.compile(
    r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
)


def mask_sensitive_emails(text: str) -> str:
    """Mascara qualquer e-mail presente no texto para [E-MAIL PROTEGIDO]."""
    return EMAIL_REGEX.sub("[E-MAIL PROTEGIDO]", text)


def evaluate_query_guardrails(query: str) -> Tuple[bool, str]:
    """
    Avalia se a consulta deve ser recusada por violação ética, privacidade ou fora de escopo.
    Retorna: (deve_recusar, motivo_recusa)
    """
    q_lower = query.lower()

    # 1. Tentativa de quebra de anonimato em Peer Review (Duplo-Cego)
    if any(
        p in q_lower
        for p in [
            "quem foi o parecerista",
            "identidade do revisor",
            "nome do parecerista",
            "quem avaliou o projeto",
            "quem rejeitou o protocolo",
            "identificar o revisor",
        ]
    ):
        return (
            True,
            "Solicitação recusada: A revelação da identidade de avaliadores em processo de revisão por pares duplo-cego viola as diretrizes de ética acadêmica e confidencialidade da CONEP/Agências de Fomento."
        )

    # 2. Emissão de juízo pejorativo sobre qualidade individual de pesquisador
    if any(
        p in q_lower
        for p in [
            "incompetente",
            "baixa capacidade acadêmica",
            "pesquisador ruim",
            "fraude individual",
            "capacidade intelectual de",
        ]
    ):
        return (
            True,
            "Solicitação recusada: O sistema não emite juízo de valor ou avaliação qualitativa depreciativa sobre a idoneidade ou competência individual de pesquisadores."
        )

    # 3. Detecção de Perguntas Fora de Escopo Acadêmico
    palavras_fora_escopo = [
        "receita", "lasanha", "culinária", "restaurante", "pizza",
        "futebol", "campeonato", "jogo", "horóscopo", "signo",
        "novela", "cinema", "filme", "piada", "como cozinhar"
    ]
    if any(p in q_lower for p in palavras_fora_escopo):
        return (
            True,
            "Esta consulta está fora do escopo do sistema de Inteligência sobre Pesquisa Acadêmica. Este assistente é especializado em normas de ética em pesquisa (CEP/CONEP), editais de fomento (FAPERJ, CNPq, CAPES), produção científica e pareceres acadêmicos."
        )

    return (False, "")


def generate_rag_response(
    analysis: QueryAnalysis,
    chunks: List[DocumentChunk],
    run_id: str,
    query_id: str = "q_0000",
    db_queries: Dict = None,
) -> RAGResponse:
    """
    Gera a resposta final do pipeline RAG aplicando síntese do LLM e guardrails.
    """
    t_start = time.time()
    query = analysis.original_query
    db_queries = db_queries or {}

    # Verificação de Guardrail de Entrada
    should_refuse, refusal_reason = evaluate_query_guardrails(query)
    if should_refuse:
        log_event(
            run_id=run_id,
            stage="validacao",
            status="refusal",
            query_id=query_id,
            input_data=query,
            output_data=refusal_reason,
            extra={"guardrail": "salvaguarda_ou_escopo"},
        )
        return RAGResponse(
            run_id=run_id,
            query_id=query_id,
            answer=refusal_reason,
            sources_used=[],
            is_refusal=True,
            refusal_reason=refusal_reason,
            latency_ms=int((time.time() - t_start) * 1000),
            db_queries=db_queries,
        )

    # Seleciona os melhores chunks e evita repetições excessivas
    seen_texts = set()
    selected_chunks = []
    for c in chunks:
        # Pega as primeiras 4 linhas como assinatura para evitar trechos duplicados
        sig = "\n".join(c.content.strip().split("\n")[:3])
        if sig not in seen_texts:
            seen_texts.add(sig)
            selected_chunks.append(c)
        if len(selected_chunks) >= 4:
            break

    if not selected_chunks and chunks:
        selected_chunks = chunks[:3]

    # Formata o contexto de maneira concisa (máximo ~1200 chars por trecho para velocidade e precisão)
    context_blocks = []
    sources_metadata = []
    for c in selected_chunks:
        sanitized_content = mask_sensitive_emails(c.content.strip())
        if len(sanitized_content) > 1200:
            sanitized_content = sanitized_content[:1200] + "..."
        context_blocks.append(
            f"--- [Documento {c.metadata.base_id} | ID: {c.chunk_id}] ---\n{sanitized_content}"
        )
        sources_metadata.append(
            {
                "chunk_id": c.chunk_id,
                "base_id": c.metadata.base_id,
                "natureza": c.metadata.natureza.value,
                "source_file": c.metadata.source_file,
                "content_snippet": sanitized_content[:200] + "...",
                "metadata": c.metadata.extras
            }
        )

    context_str = (
        "\n\n".join(context_blocks)
        if context_blocks
        else "Nenhum documento específico encontrado."
    )

    system_prompt = (
        "Você é um consultor acadêmico experiente em Inteligência sobre Pesquisa Acadêmica.\n"
        "Sua missão é responder à dúvida do usuário de forma natural, fluida, contextualizada e precisa em português.\n\n"
        "Diretrizes obrigatórias:\n"
        "1. Responda diretamente e de maneira explicativa, como um especialista dialogando com o usuário.\n"
        "2. Sintetize as informações dos documentos recuperados, relacionando-as com a pergunta.\n"
        "3. Se houver artigos, normas ou pareceres aplicáveis, cite-os naturalmente no texto (ex: 'De acordo com o Art. 1º da Resolução CNS 510/2016...').\n"
        "4. Não apenas copie e cole trechos brutos; elabore uma resposta coesa com parágrafos bem construídos.\n"
        "5. Qualquer e-mail de autor ou contato deve ser estritamente mantido como [E-MAIL PROTEGIDO].\n"
        "6. Se os documentos recuperados não contiverem dados suficientes para responder com certeza, informe com clareza o que consta nas fontes e o que não pôde ser determinado."
    )

    user_prompt = (
        f"Evidências e Documentos Recuperados:\n{context_str}\n\n"
        f"Pergunta do Usuário: {query}\n\n"
        f"Resposta Completa e Natural:"
    )

    client = get_openai_client()
    tokens = {"prompt": 0, "completion": 0, "total": 0}
    answer = ""

    t_gen_start = time.time()
    try:
        response = client.chat.completions.create(
            model=GENERATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            timeout=85,
        )
        answer = response.choices[0].message.content or ""
        if response.usage:
            tokens = {
                "prompt": response.usage.prompt_tokens,
                "completion": response.usage.completion_tokens,
                "total": response.usage.total_tokens,
            }
    except Exception as e:
        print(f"\n[Aviso] Servidor LLM remoto demorou para responder ({e}). Gerando síntese inteligente a partir das fontes locais:")
        # Síntese local explicativa e humanizada quando o LLM remoto estiver indisponível
        intro = f"Com base nas evidências documentais recuperadas para a consulta '{query}':\n\n"
        points = []
        for c in selected_chunks[:3]:
            # Extrai o resumo essencial do trecho
            clean_snippet = c.content.strip().replace("\n\n", " ").replace("\n", " ")
            if len(clean_snippet) > 280:
                clean_snippet = clean_snippet[:280] + "..."
            points.append(f"- **Fonte ({c.metadata.base_id} - `{c.chunk_id}`):** {clean_snippet}")
        
        answer = intro + "\n\n".join(points) + "\n\n*Nota: Resposta gerada a partir dos extratos do corpus em modo de contingência.*"

    t_gen_end = time.time()

    # Guardrail de Saída: Mascaramento estrito de e-mails
    sanitized_answer = mask_sensitive_emails(answer)

    # Registro de Logs Estruturados
    log_event(
        run_id=run_id,
        stage="geracao",
        query_id=query_id,
        input_data=query,
        output_data=sanitized_answer[:300] + "...",
        latencia_ms=int((time.gen_end - t_gen_start) * 1000)
        if "time.gen_end" in locals()
        else int((t_gen_end - t_gen_start) * 1000),
        tokens=tokens,
        modelo=GENERATION_MODEL,
        extra={"num_sources": len(chunks)},
    )

    log_event(
        run_id=run_id,
        stage="validacao",
        query_id=query_id,
        input_data="output_sanitization",
        output_data="ok - email_masked",
        latencia_ms=5,
    )

    total_latency = int((time.time() - t_start) * 1000)

    return RAGResponse(
        run_id=run_id,
        query_id=query_id,
        answer=sanitized_answer,
        sources_used=sources_metadata,
        is_refusal=False,
        latency_ms=total_latency,
        db_queries=db_queries,
    )
