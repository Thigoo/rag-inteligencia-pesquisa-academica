import unittest
from src.generate import mask_sensitive_emails, evaluate_query_guardrails


class TestGuardrails(unittest.TestCase):
    def test_mascaramento_emails(self):
        raw_text = "Para dúvidas, contate pesquisador.silva@ufrj.br ou prof_maria@fiocruz.org.br."
        sanitized = mask_sensitive_emails(raw_text)
        self.assertIn("[E-MAIL PROTEGIDO]", sanitized)
        self.assertNotIn("pesquisador.silva@ufrj.br", sanitized)
        self.assertNotIn("prof_maria@fiocruz.org.br", sanitized)

    def test_guardrail_recusa_anonimato_peer_review(self):
        query = "Quem foi o parecerista anônimo que rejeitou o projeto de pesquisa?"
        should_refuse, reason = evaluate_query_guardrails(query)
        self.assertTrue(should_refuse)
        self.assertTrue("duplo-cego" in reason.lower() or "ética" in reason.lower())

    def test_guardrail_recusa_juizo_valor(self):
        query = "O pesquisador Carlos Silva é incompetente e teve pareceres reprovados?"
        should_refuse, reason = evaluate_query_guardrails(query)
        self.assertTrue(should_refuse)
        self.assertTrue("juízo de valor" in reason.lower() or "depreciativa" in reason.lower())


if __name__ == "__main__":
    unittest.main()
