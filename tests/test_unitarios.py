import unittest
from src.retrieve import compute_rrf
from src.schema import DocumentChunk, ChunkMetadata, BaseNatureza, SensitivityLevel, RAGResponse
from src.generate import evaluate_query_guardrails, generate_rag_response
from src.schema import QueryAnalysis


class TestUnitariosEContrato(unittest.TestCase):
    def setUp(self):
        self.chunk1 = DocumentChunk(
            chunk_id="c_01",
            content="Texto do chunk 1",
            metadata=ChunkMetadata(
                chunk_id="c_01",
                doc_type="json",
                source_file="raw/v1/producao_estruturada/data.json",
                base_id="producao_estruturada",
                natureza=BaseNatureza.ESTRUTURADA,
                sensitivity=SensitivityLevel.PUBLICO
            )
        )
        self.chunk2 = DocumentChunk(
            chunk_id="c_02",
            content="Texto do chunk 2",
            metadata=ChunkMetadata(
                chunk_id="c_02",
                doc_type="txt",
                source_file="raw/v1/editais_normativo/edital.txt",
                base_id="editais_normativo",
                natureza=BaseNatureza.NORMATIVA,
                sensitivity=SensitivityLevel.PUBLICO
            )
        )

    def test_calculo_rrf(self):
        """Valida se o cálculo de Reciprocal Rank Fusion combina rankings corretamente."""
        dense_results = [(self.chunk1, 0.9), (self.chunk2, 0.8)]
        bm25_results = [(self.chunk2, 5.0), (self.chunk1, 2.0)]

        # RRF k=60
        # Score chunk1: 1/(60+1) + 1/(60+2) = 1/61 + 1/62 = 0.01639 + 0.01613 = 0.03252
        # Score chunk2: 1/(60+2) + 1/(60+1) = 0.03252 (ambos aparecem em rank 1 e 2)
        fused = compute_rrf(dense_results, bm25_results, k=60, top_n=2)
        self.assertEqual(len(fused), 2)
        self.assertAlmostEqual(fused[0][1], 0.03252, places=4)

    def test_contrato_recusa_sources_vazias(self):
        """Valida a regra de contrato: is_refusal=True implica sources_used vazia."""
        analysis = QueryAnalysis(
            query_id="q_test_refusal",
            original_query="Quem foi o parecerista anônimo do protocolo?",
            intent="consulta_pareceres_peer_review",
            target_bases=["pareceres_conversacional"],
            requires_cross_source=False
        )
        response = generate_rag_response(analysis, [self.chunk1], run_id="test_run")
        self.assertTrue(response.is_refusal)
        self.assertEqual(len(response.sources_used), 0, "Quando há recusa, sources_used DEVE ser vazia")
        self.assertIsNotNone(response.refusal_reason)


if __name__ == "__main__":
    unittest.main()
