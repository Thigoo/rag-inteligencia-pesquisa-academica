try:
    import pytest
except ImportError:
    pytest = None

from src.schema import DocumentChunk, ChunkMetadata, BaseNatureza, SensitivityLevel

if pytest is not None:
    @pytest.fixture
    def sample_chunks():
        return [
            DocumentChunk(
                chunk_id="norm_res510_001",
                content="Resolução CNS 510/2016 Artigo 1: Não serão avaliadas pelo sistema CEP/CONEP pesquisas com dados de acesso público.",
                metadata=ChunkMetadata(
                    chunk_id="norm_res510_001",
                    doc_type="txt",
                    source_file="raw/v1/editais_normativo/resolucao_cns_510_2016.txt",
                    base_id="editais_normativo",
                    natureza=BaseNatureza.NORMATIVA,
                    sensitivity=SensitivityLevel.PUBLICO,
                    campo_vigencia="2016-presente"
                )
            ),
            DocumentChunk(
                chunk_id="est_work_001",
                content="Título: Deep Learning in Cardiology\nAno: 2023\nAutores: Silva et al.\nFinanciamento: FAPERJ",
                metadata=ChunkMetadata(
                    chunk_id="est_work_001",
                    doc_type="json",
                    source_file="raw/v1/producao_estruturada/data.json",
                    base_id="producao_estruturada",
                    natureza=BaseNatureza.ESTRUTURADA,
                    sensitivity=SensitivityLevel.PUBLICO,
                    campo_vigencia="2023"
                )
            ),
            DocumentChunk(
                chunk_id="conv_proto_4821",
                content="Protocolo CEP-4821: Decisão: Rejeitado. Contato: pesquisador@ufrj.br",
                metadata=ChunkMetadata(
                    chunk_id="conv_proto_4821",
                    doc_type="json",
                    source_file="raw/v1/pareceres_conversacional/pareceres_peer_review.json",
                    base_id="pareceres_conversacional",
                    natureza=BaseNatureza.CONVERSACIONAL,
                    sensitivity=SensitivityLevel.INTERNO,
                    campo_vigencia="2022-11-10"
                )
            )
        ]
