import json
import unittest
from pathlib import Path
from src.schema import DocumentChunk

FIXTURES_FILE = Path(__file__).parent / "fixtures" / "chunks_sample.json"


class TestChunksContract(unittest.TestCase):
    def setUp(self):
        with open(FIXTURES_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.chunks_fixture = [DocumentChunk(**item) for item in data]

    def test_todo_chunk_tem_metadado_obrigatorio(self):
        """
        Teste de Contrato (exato do Grande Desafio):
        Garante que todo chunk indexado possui metadados obrigatórios.
        """
        obrigatorios = {"source_file", "doc_type", "chunk_id", "sensitivity", "base_id"}
        for c in self.chunks_fixture:
            meta_dict = c.metadata.model_dump()
            faltando = obrigatorios - set(meta_dict.keys())
            self.assertFalse(faltando, f"{c.metadata.chunk_id} sem: {faltando}")
            self.assertTrue(bool(c.metadata.chunk_id), "chunk_id não pode ser vazio")
            self.assertTrue(bool(c.metadata.source_file), "source_file não pode ser vazio")
            self.assertTrue(bool(c.metadata.base_id), "base_id não pode ser vazio")


if __name__ == "__main__":
    unittest.main()
