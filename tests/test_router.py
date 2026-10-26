import unittest
from src.router import analyze_and_route


class TestRouter(unittest.TestCase):
    def test_pergunta_profa_ana_cross_source(self):
        """Profa. Ana: abstract semântico + metadado estruturado de financiamento."""
        query = "Quais trabalhos publicados pelo nosso programa nos últimos três anos se enquadram na linha de 'saúde digital', e quais tiveram financiamento externo?"
        analysis = analyze_and_route(query)
        self.assertTrue(analysis.requires_cross_source)
        self.assertIn("producao_estruturada", analysis.target_bases)

    def test_pergunta_lucas_agregada_bibliometrica(self):
        """Lucas (Pergunta 1): agregação / trabalhos mais citados."""
        query = "Quais os trabalhos mais citados sobre detecção de fraude em séries temporais?"
        analysis = analyze_and_route(query)
        self.assertIn("metricas_agregada", analysis.target_bases)

    def test_pergunta_lucas_normativa_cep(self):
        """Lucas (Pergunta 2): rota normativa de ética em pesquisa."""
        query = "meu estudo usa dados públicos anonimizados, preciso submeter ao CEP?"
        analysis = analyze_and_route(query)
        self.assertIn("editais_normativo", analysis.target_bases)

    def test_pergunta_beatriz_composta(self):
        """Beatriz: edital normativa -> lista aprovados estruturada -> produção associada."""
        query = "Os projetos aprovados na chamada de 2022 produziram publicações alinhadas ao objetivo do edital?"
        analysis = analyze_and_route(query)
        self.assertTrue(analysis.requires_cross_source)
        self.assertIn("editais_normativo", analysis.target_bases)
        self.assertIn("producao_estruturada", analysis.target_bases)


if __name__ == "__main__":
    unittest.main()
