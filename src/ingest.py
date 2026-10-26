import json
from pathlib import Path
from typing import List
from src.schema import DocumentChunk, ChunkMetadata, BaseNatureza, SensitivityLevel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "v1"
CHUNKS_FILE = DATA_DIR / "chunks_v1.json"


def chunk_text_by_paragraphs(text: str, chunk_size: int = 400, overlap: int = 50) -> List[str]:
    """Divide texto por quebras de parÃ¡grafos/artigos mantendo overlap."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_len = len(p)
        if current_len + p_len > chunk_size and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [current_chunk[-1]] if overlap > 0 else []
            current_len = len(current_chunk[0]) if current_chunk else 0

        current_chunk.append(p)
        current_len += p_len

    if current_chunk:
        chunks.append("\n\n".join(current_chunk))

    return chunks if chunks else [text]


import pypdf

def ingest_editais_normativo() -> List[DocumentChunk]:
    """Processa documentos normativos e editais (TXT e PDF)."""
    chunks = []
    base_dir = RAW_DIR / "editais_normativo"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.*"):
        if file_path.suffix.lower() == ".pdf":
            try:
                reader = pypdf.PdfReader(file_path)
                pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
                content = "\n\n".join(pages_text)
            except Exception as e:
                print(f"[!] Erro ao ler PDF {file_path.name}: {e}")
                continue
        else:
            content = file_path.read_text(encoding="utf-8", errors="ignore")

        if not content.strip():
            continue

        sub_chunks = chunk_text_by_paragraphs(content, chunk_size=600, overlap=100)

        for idx, text in enumerate(sub_chunks):
            chunk_id = f"norm_{file_path.stem}_{idx:03d}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type=file_path.suffix.replace(".", "") or "txt",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="editais_normativo",
                natureza=BaseNatureza.NORMATIVA,
                sensitivity=SensitivityLevel.PUBLICO,
                campo_vigencia="2016-presente",
                extras={
                    "filename": file_path.name,
                    "orgao": "CNS/CONEP" if "cns" in file_path.name.lower() else "FAPERJ",
                    "chunk_index": idx
                }
            )
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=text, metadata=metadata))

    return chunks


def _parse_faperj_beneficiarios(data: dict, file_path, chunks: list):
    """Parser para arquivos de beneficiários FAPERJ com publicações cruzadas."""
    beneficiarios = data.get("beneficiarios_com_publicacoes", [])
    edital = data.get("edital", "")
    for idx, pesq in enumerate(beneficiarios):
        if not isinstance(pesq, dict):
            continue
        nome = pesq.get("pesquisador", "")
        inst = pesq.get("instituicao", "")
        projeto = pesq.get("projeto_financiado", "")
        categoria = pesq.get("categoria_edital", "")
        valor = pesq.get("valor_concedido", 0)
        cumprimento = pesq.get("cumprimento_meta_publicacoes", "")
        pubs = pesq.get("publicacoes_com_financiamento_declarado", [])

        pubs_text = []
        for pub in pubs:
            pubs_text.append(
                f"  - {pub.get('titulo', '')} ({pub.get('revista', '')}, {pub.get('ano', '')}), "
                f"{pub.get('citacoes', 0)} citações, financiamento FAPERJ declarado: {pub.get('agradecimento_faperj', False)}. "
                f"Agradecimento: '{pub.get('texto_agradecimento', '')}'"
            )

        content = (
            f"Edital: {edital}\n"
            f"Pesquisador Beneficiário: {nome}\n"
            f"Instituição: {inst}\n"
            f"Projeto Financiado: {projeto}\n"
            f"Categoria: {categoria} | Valor Concedido: R$ {valor:,.2f}\n"
            f"Cumprimento da meta de publicações: {cumprimento}\n"
            f"Publicações com menção de financiamento FAPERJ:\n" + "\n".join(pubs_text)
        )
        chunk_id = f"est_faperj_{file_path.stem}_{idx:02d}"
        metadata = ChunkMetadata(
            chunk_id=chunk_id,
            doc_type="json",
            source_file=str(file_path.relative_to(DATA_DIR)),
            base_id="producao_estruturada",
            natureza=BaseNatureza.ESTRUTURADA,
            sensitivity=SensitivityLevel.PUBLICO,
            campo_vigencia="2022-2024",
            extras={"pesquisador": nome, "edital": edital, "categoria": categoria, "has_funding": True, "origem": "sintetico"}
        )
        chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))


def ingest_producao_estruturada() -> List[DocumentChunk]:
    """Processa metadados estruturados de artigos do OpenAlex e corpus sintético."""
    chunks = []
    base_dir = RAW_DIR / "producao_estruturada"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Erro ao ler JSON {file_path.name}: {e}")
            continue

        # Formato especial: beneficiários FAPERJ
        if isinstance(data, dict) and "beneficiarios_com_publicacoes" in data:
            _parse_faperj_beneficiarios(data, file_path, chunks)
            continue

        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        elif isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = [data]
        else:
            results = []

        origem = "sintetico" if "sintetico" in file_path.name else "openalex"

        for idx, item in enumerate(results):
            if not isinstance(item, dict):
                continue
            work_id = str(item.get("id", f"work_{file_path.stem}_{idx}")).split("/")[-1]
            title = item.get("title") or "Sem título"
            pub_year = item.get("publication_year")
            cited_by = item.get("cited_by_count", 0)
            doi = item.get("doi", "")

            authors_list = []
            institutions_list = []

            for authorship in item.get("authorships", []):
                if isinstance(authorship, dict):
                    author_name = authorship.get("author", {}).get("display_name")
                    if author_name:
                        authors_list.append(author_name)

                    for inst in authorship.get("institutions", []):
                        if isinstance(inst, dict):
                            inst_name = inst.get("display_name")
                            if inst_name and inst_name not in institutions_list:
                                institutions_list.append(inst_name)

            grants_list = []
            for grant in item.get("grants", []):
                if isinstance(grant, dict):
                    funder = grant.get("funder_display_name")
                    award = grant.get("award_id")
                    if funder:
                        grants_list.append(f"{funder} (Auxílio: {award})" if award else funder)

            if not grants_list:
                for funder in item.get("funders", []):
                    if isinstance(funder, dict):
                        funder_name = funder.get("display_name")
                        if funder_name:
                            grants_list.append(funder_name)

            abstract_idx = item.get("abstract_inverted_index")
            abstract_text = ""
            if abstract_idx and isinstance(abstract_idx, dict):
                word_pos = []
                for word, positions in abstract_idx.items():
                    if isinstance(positions, list):
                        for pos in positions:
                            word_pos.append((pos, word))
                word_pos.sort()
                abstract_text = " ".join(w for _, w in word_pos)

            content = (
                f"Título: {title}\n"
                f"Ano de Publicação: {pub_year}\n"
                f"Autores: {', '.join(authors_list[:5])}\n"
                f"Instituições: {', '.join(institutions_list[:3])}\n"
                f"Financiamento/Grants: "
                f"{', '.join(grants_list) if grants_list else 'Não declarado'}\n"
                f"Total de Citações: {cited_by}\n"
                f"DOI: {doi}\n"
                f"Resumo: {abstract_text[:600]}"
            )

            chunk_id = f"est_{work_id}_{idx:03d}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type="json",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="producao_estruturada",
                natureza=BaseNatureza.ESTRUTURADA,
                sensitivity=SensitivityLevel.PUBLICO,
                campo_vigencia=str(pub_year) if pub_year else None,
                extras={
                    "work_id": work_id,
                    "title": title,
                    "year": pub_year,
                    "cited_by_count": cited_by,
                    "authors": authors_list[:5],
                    "institutions": institutions_list[:3],
                    "has_funding": bool(grants_list),
                    "origem": origem,
                }
            )
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))  # BUG FIX
    return chunks


def ingest_pareceres_conversacional() -> List[DocumentChunk]:
    """Processa pareceres e registros de revisão por pares."""
    chunks = []
    base_dir = RAW_DIR / "pareceres_conversacional"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                pareceres = json.load(f)
        except Exception as e:
            print(f"[!] Erro ao ler JSON {file_path.name}: {e}")
            continue

        if not isinstance(pareceres, list):
            pareceres = [pareceres]

        for idx, p in enumerate(pareceres):
            if not isinstance(p, dict):
                continue
            proto_id = p.get("protocolo_id", f"proto_{file_path.stem}_{idx}")
            titulo = p.get("titulo_projeto", "")
            decisao = p.get("decisao", "")
            data_p = p.get("data_parecer", "")
            rodada = p.get("rodada", "")
            texto = p.get("parecer_texto", "")
            interno = p.get("comentario_interno_revisor", "")

            content = (
                f"Protocolo: {proto_id}\n"
                f"Projeto: {titulo}\n"
                f"Área: {p.get('area', '')}\n"
                f"Data: {data_p} ({rodada})\n"
                f"Decisão Editorial: {decisao}\n"
                f"Parecer Técnico: {texto}\n"
                f"Observação Interna: {interno}"
            )

            chunk_id = f"conv_{proto_id.replace('-', '_')}_{idx:02d}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type="json",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="pareceres_conversacional",
                natureza=BaseNatureza.CONVERSACIONAL,
                sensitivity=SensitivityLevel.INTERNO,
                campo_vigencia=data_p,
                extras={
                    "protocolo_id": proto_id,
                    "decisao": decisao,
                    "status_anonimato": p.get("status_anonimato", "duplo_cego"),
                    "rodada": rodada
                }
            )
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))

    return chunks


def _parse_citacoes_institucionais(data: dict, file_path, chunks: list):
    """Parser para arquivos de métricas de citação institucional."""
    periodo = data.get("periodo_referencia", "")
    instituicao = data.get("instituicao", "")
    resumo = data.get("resumo_indicadores_institucionais_2023", {})

    # Chunk 1: Resumo geral
    if resumo:
        content = (
            f"Indicadores Institucionais de Pesquisa - {instituicao} ({periodo})\n"
            f"Total de artigos indexados: {resumo.get('total_artigos_indexados', 0):,}\n"
            f"Artigos em revistas A1/A2: {resumo.get('total_artigos_a1_a2', 0):,}\n"
            f"Total de citações (OpenAlex): {resumo.get('citacoes_totais_openalex', 0):,}\n"
            f"H-index institucional: {resumo.get('h_index_institucional', 0)}\n"
            f"Coautorias internacionais: {resumo.get('coautorias_internacionais_percentual', 0)}%\n"
            f"Áreas mais produtivas: {', '.join(resumo.get('areas_mais_produtivas', []))}\n"
            f"Principais financiadores: {', '.join(resumo.get('financiadores_principais', []))}"
        )
        chunk_id = f"agr_inst_resumo_{file_path.stem}"
        metadata = ChunkMetadata(
            chunk_id=chunk_id, doc_type="json",
            source_file=str(file_path.relative_to(DATA_DIR)),
            base_id="metricas_agregada", natureza=BaseNatureza.AGREGADA,
            sensitivity=SensitivityLevel.PUBLICO, campo_vigencia=str(periodo),
            extras={"tipo": "resumo_institucional", "periodo": periodo}
        )
        chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))

    # Chunk 2+: Top artigos individuais
    for idx, artigo in enumerate(data.get("top_artigos_citacoes_2023", [])):
        autores = artigo.get("autores", [])
        financiamento = artigo.get("financiamento_declarado", "Não declarado")
        content = (
            f"[Rank #{artigo.get('rank', idx+1)} em Citações - {periodo}] {artigo.get('titulo', '')}\n"
            f"Autores: {', '.join(autores)}\n"
            f"Instituição: {artigo.get('instituicao_principal', '')}\n"
            f"Revista: {artigo.get('revista', '')} (Qualis CAPES: {artigo.get('qualis_capes', '')})\n"
            f"Citações no OpenAlex: {artigo.get('citacoes_openalex', 0):,}\n"
            f"Citações no Google Scholar: {artigo.get('citacoes_google_scholar', 0):,}\n"
            f"Financiamento declarado: {financiamento}\n"
            f"Agradecimentos: {artigo.get('agradecimentos', '')}\n"
            f"DOI: {artigo.get('doi', '')}"
        )
        chunk_id = f"agr_top_art_{file_path.stem}_{idx:02d}"
        metadata = ChunkMetadata(
            chunk_id=chunk_id, doc_type="json",
            source_file=str(file_path.relative_to(DATA_DIR)),
            base_id="metricas_agregada", natureza=BaseNatureza.AGREGADA,
            sensitivity=SensitivityLevel.PUBLICO, campo_vigencia=str(periodo),
            extras={"rank": artigo.get('rank'), "citacoes": artigo.get('citacoes_openalex', 0),
                    "revista": artigo.get('revista', ''), "tipo": "top_artigo"}
        )
        chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))


def _parse_artigos_etica_ia(data: dict, file_path, chunks: list):
    """Parser para arquivos de artigos de ética em IA com aprovação CEP."""
    periodo = data.get("periodo", "")
    total = data.get("total_encontrado", 0)
    stats = data.get("estatisticas_gerais_2023", {})

    # Chunk de estatísticas
    content_stat = (
        f"Panorama: Artigos sobre Ética em IA publicados no Brasil em {periodo}\n"
        f"Total encontrado: {total} artigos\n"
        f"Com menção de aprovação CEP no resumo: {stats.get('artigos_com_mencao_cep_no_resumo', 0)}\n"
        f"Dispensados de CEP (Resolução CNS 510/2016): {stats.get('artigos_dispensados_cep_resolucao_510', 0)}\n"
        f"Média de citações: {stats.get('media_citacoes', 0)}\n"
        f"Periódicos mais frequentes: {', '.join(stats.get('periódicos_mais_frequentes', []))}"
    )
    chunk_id = f"agr_etica_ia_stat_{file_path.stem}"
    meta = ChunkMetadata(
        chunk_id=chunk_id, doc_type="json",
        source_file=str(file_path.relative_to(DATA_DIR)),
        base_id="metricas_agregada", natureza=BaseNatureza.AGREGADA,
        sensitivity=SensitivityLevel.PUBLICO, campo_vigencia=periodo,
        extras={"tipo": "estatistica_etica_ia"}
    )
    chunks.append(DocumentChunk(chunk_id=chunk_id, content=content_stat, metadata=meta))

    for idx, artigo in enumerate(data.get("artigos", [])):
        autores = artigo.get("autores", [])
        content = (
            f"Artigo sobre Ética em IA ({periodo}): {artigo.get('titulo', '')}\n"
            f"Autores: {', '.join(autores)}\n"
            f"Instituições: {', '.join(artigo.get('instituicoes', []))}\n"
            f"Revista: {artigo.get('revista', '')} | Ano: {artigo.get('ano_publicacao', '')}\n"
            f"Citações: {artigo.get('citacoes', 0)} | DOI: {artigo.get('doi', '')}\n"
            f"Menção de aprovação CEP no resumo: {'Sim' if artigo.get('mencao_aprovacao_cep_no_resumo') else 'Não'}\n"
            f"Protocolo CEP: {artigo.get('protocolo_cep', 'N/A')}\n"
            f"Registrado na Plataforma Brasil: {'Sim' if artigo.get('plataforma_brasil') else 'Não'}\n"
            f"Financiamento: {', '.join(artigo.get('financiamento', []))}\n"
            f"Resumo: {artigo.get('resumo', '')[:500]}"
        )
        chunk_id = f"agr_etica_ia_{file_path.stem}_{idx:02d}"
        meta = ChunkMetadata(
            chunk_id=chunk_id, doc_type="json",
            source_file=str(file_path.relative_to(DATA_DIR)),
            base_id="metricas_agregada", natureza=BaseNatureza.AGREGADA,
            sensitivity=SensitivityLevel.PUBLICO, campo_vigencia=str(artigo.get('ano_publicacao', periodo)),
            extras={"mencao_cep": artigo.get('mencao_aprovacao_cep_no_resumo', False),
                    "protocolo_cep": artigo.get('protocolo_cep', ''), "tipo": "artigo_etica_ia"}
        )
        chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=meta))


def ingest_metricas_agregada() -> List[DocumentChunk]:
    """Processa tópicos e indicadores bibliométricos do OpenAlex."""
    chunks = []
    base_dir = RAW_DIR / "metricas_agregada"
    if not base_dir.exists():
        return chunks

    for file_path in base_dir.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"[!] Erro ao ler JSON {file_path.name}: {e}")
            continue

        # Formato especial: citações institucionais
        if isinstance(data, dict) and "top_artigos_citacoes_2023" in data:
            _parse_citacoes_institucionais(data, file_path, chunks)
            continue

        # Formato especial: artigos de ética em IA
        if isinstance(data, dict) and "artigos" in data and "total_encontrado" in data:
            _parse_artigos_etica_ia(data, file_path, chunks)
            continue

        if isinstance(data, dict) and "results" in data:
            results = data["results"]
        elif isinstance(data, list):
            results = data
        elif isinstance(data, dict):
            results = [data]
        else:
            results = []

        for idx, topic in enumerate(results):
            if not isinstance(topic, dict):
                continue
            topic_id = str(topic.get("id", f"topic_{file_path.stem}_{idx}")).split("/")[-1]
            name = topic.get("display_name", "Tópico")
            works_count = topic.get("works_count", 0)
            cited_count = topic.get("cited_by_count", 0)
            subfield = topic.get("subfield", {}).get("display_name", "") if isinstance(topic.get("subfield"), dict) else ""
            field_name = topic.get("field", {}).get("display_name", "") if isinstance(topic.get("field"), dict) else ""
            domain = topic.get("domain", {}).get("display_name", "") if isinstance(topic.get("domain"), dict) else ""

            if works_count > 0:
                impact = f"{(cited_count/works_count):.2f}"
            else:
                impact = "0"

            content = (
                f"Tópico de Pesquisa: {name}\n"
                f"Grande Área: {domain} -> {field_name} -> {subfield}\n"
                f"Total de Obras Indexadas: {works_count:,}\n"
                f"Total de Citações Acumuladas: {cited_count:,}\n"
                f"Impacto Médio de Citações por Obra: {impact}"
            )

            chunk_id = f"agr_{topic_id}_{idx:03d}"
            metadata = ChunkMetadata(
                chunk_id=chunk_id,
                doc_type="json",
                source_file=str(file_path.relative_to(DATA_DIR)),
                base_id="metricas_agregada",
                natureza=BaseNatureza.AGREGADA,
                sensitivity=SensitivityLevel.PUBLICO,
                campo_vigencia="2024",
                extras={
                    "topic_id": topic_id,
                    "works_count": works_count,
                    "cited_by_count": cited_count,
                    "subfield": subfield,
                    "field": field_name,
                    "domain": domain
                }
            )
            chunks.append(DocumentChunk(chunk_id=chunk_id, content=content, metadata=metadata))  # BUG FIX
    return chunks


def run_ingest() -> List[DocumentChunk]:
    """Executa a ingestÃ£o completa de todas as bases e salva em data/chunks_v1.json."""
    all_chunks: List[DocumentChunk] = []
    
    all_chunks.extend(ingest_editais_normativo())
    all_chunks.extend(ingest_producao_estruturada())
    all_chunks.extend(ingest_pareceres_conversacional())
    all_chunks.extend(ingest_metricas_agregada())

    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    serialized = [c.model_dump() for c in all_chunks]
    
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        json.dump(serialized, f, ensure_ascii=False, indent=2)

    print(f"[OK] IngestÃ£o concluÃ­da! Total de {len(all_chunks)} chunks gerados e salvos em {CHUNKS_FILE.relative_to(BASE_DIR)}")
    return all_chunks


if __name__ == "__main__":
    run_ingest()



