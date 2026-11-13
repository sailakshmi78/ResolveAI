from django.test import SimpleTestCase

from apps.core.views import build_grounded_procedure_answer


class GroundedProcedureAnswerTests(SimpleTestCase):
    def test_returns_exact_steps_when_heading_matches_question(self):
        results = [{
            "title": "ResolveAI Enterprise Knowledge Handbook V5",
            "score": 0.66,
            "content": (
                "## WP-001 — Request application access\n"
                "1. Identify application, business purpose, required role if known, and needed date.\n"
                "2. Search for an existing request.\n"
                "3. Use the official access-request workflow and supply only required information.\n"
                "4. Obtain approvals through the official workflow.\n"
            ),
        }]

        answer, source = build_grounded_procedure_answer(
            "How do I request access to an application?", results
        )

        self.assertIsNotNone(source)
        self.assertIn("Identify application", answer)
        self.assertIn("Search for an existing request", answer)
        self.assertIn("Obtain approvals", answer)

    def test_does_not_guess_when_heading_does_not_match(self):
        results = [{
            "title": "Handbook",
            "score": 0.70,
            "content": (
                "## SEC-009 — Endpoint protection blocks a legitimate application\n"
                "1. Record the application name and error message.\n"
            ),
        }]

        answer, source = build_grounded_procedure_answer(
            "How do I request access to an application?", results
        )

        self.assertIsNone(answer)
        self.assertIsNone(source)

    def test_ignores_low_confidence_results(self):
        results = [{
            "title": "Handbook",
            "score": 0.25,
            "content": (
                "## WP-001 — Request application access\n"
                "1. Search for an existing request.\n"
            ),
        }]

        answer, source = build_grounded_procedure_answer(
            "How do I request access to an application?", results
        )

        self.assertIsNone(answer)
        self.assertIsNone(source)
