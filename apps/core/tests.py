import json
from unittest.mock import patch

from django.test import TestCase


class FindGuidanceTests(TestCase):
    url = "/api/guidance/"

    def post_question(self, query):
        return self.client.post(
            self.url,
            data=json.dumps({"query": query}),
            content_type="application/json",
        )

    def sample_result(self, content, title="Test Handbook"):
        return {
            "title": title,
            "content": content,
            "score": 0.75,
            "chunk_index": 1,
        }

    def test_invalid_json_returns_400(self):
        response = self.client.post(
            self.url,
            data="{invalid",
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_empty_question_returns_400(self):
        response = self.post_question("")
        self.assertEqual(response.status_code, 400)

    @patch("apps.core.views.generate_local_answer")
    @patch("apps.core.views.search_company_docs", return_value=[])
    def test_missing_handbook_results_abstain(self, search, generate):
        response = self.post_question("How do I configure VPN?")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["generated"])
        self.assertEqual(response.json()["sources"], [])
        generate.assert_not_called()

    @patch("apps.core.views.generate_local_answer", return_value="Follow the handbook steps.")
    @patch("apps.core.views.search_company_docs")
    def test_supported_general_question_uses_handbook(self, search, generate):
        search.return_value = [
            self.sample_result("Follow these documented VPN troubleshooting steps.")
        ]

        response = self.post_question("How do I troubleshoot VPN?")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["generated"])
        self.assertEqual(response.json()["answer"], "Follow the handbook steps.")
        self.assertEqual(len(response.json()["sources"]), 1)
        generate.assert_called_once()

    @patch("apps.core.views.generate_local_answer", return_value="The handbook confirms 20 annual leave days.")
    @patch("apps.core.views.search_company_docs")
    def test_hr_question_with_direct_policy_evidence_uses_evidence(self, search, generate):
        search.return_value = [
            self.sample_result(
                "Annual leave entitlement is 20 working days per calendar year.",
                "Approved Leave Policy",
            )
        ]

        response = self.post_question("How many annual leave days are available?")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["generated"])
        self.assertEqual(len(response.json()["sources"]), 1)
        generate.assert_called_once()

    @patch("apps.core.views.generate_local_answer")
    @patch("apps.core.views.search_company_docs")
    def test_hr_question_without_policy_details_preserves_source(self, search, generate):
        search.return_value = [
            self.sample_result(
                "## WP-005 - Leave, benefits, reimbursement, payroll, or HR policy "
                "Search the current authorized policy repository. Never infer leave entitlement.",
                "HR Policy Lookup Guide",
            )
        ]

        response = self.post_question("How many annual leave days do I get?")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["generated"])
        self.assertEqual(len(response.json()["sources"]), 1)
        generate.assert_not_called()

    @patch("apps.core.views.generate_local_answer", side_effect=ValueError("Ollama unavailable"))
    @patch("apps.core.views.search_company_docs")
    def test_generation_failure_preserves_retrieved_sources(self, search, generate):
        search.return_value = [
            self.sample_result("Documented troubleshooting guidance.")
        ]

        response = self.post_question("How do I troubleshoot this issue?")
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["generated"])
        self.assertEqual(len(response.json()["sources"]), 1)

    def test_get_method_is_not_allowed(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)


class TrackIssueTests(TestCase):
    create_url = "/api/tickets/create/"
    status_url = "/api/tickets/status/"

    def post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_create_ticket_success(self):
        response = self.post_json(
            self.create_url,
            {
                "description": "VPN is not connecting.",
                "category": "Network / Wi-Fi",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.assertTrue(response.json()["ticket_id"])
        self.assertEqual(response.json()["status"], "Open")

    def test_create_ticket_rejects_empty_description(self):
        response = self.post_json(
            self.create_url,
            {"description": "   ", "category": "Other"},
        )
        self.assertEqual(response.status_code, 400)

    def test_create_ticket_rejects_invalid_category(self):
        response = self.post_json(
            self.create_url,
            {"description": "Laptop issue", "category": "Invalid"},
        )
        self.assertEqual(response.status_code, 400)

    def test_create_ticket_rejects_description_over_limit(self):
        response = self.post_json(
            self.create_url,
            {"description": "x" * 10001, "category": "Other"},
        )
        self.assertEqual(response.status_code, 400)

    def test_status_lookup_rejects_invalid_uuid(self):
        response = self.post_json(
            self.status_url,
            {"ticket_id": "not-a-uuid"},
        )
        self.assertEqual(response.status_code, 400)

    def test_status_lookup_returns_404_for_unknown_ticket(self):
        response = self.post_json(
            self.status_url,
            {"ticket_id": "00000000-0000-0000-0000-000000000001"},
        )
        self.assertEqual(response.status_code, 404)

    def test_status_lookup_returns_created_ticket(self):
        created = self.post_json(
            self.create_url,
            {"description": "Cannot access company email.", "category": "Other"},
        )
        ticket_id = created.json()["ticket_id"]

        response = self.post_json(
            self.status_url,
            {"ticket_id": ticket_id},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["ticket_id"], ticket_id)
        self.assertEqual(response.json()["status"], "Open")

    def test_ticket_endpoints_reject_get(self):
        self.assertEqual(self.client.get(self.create_url).status_code, 405)
        self.assertEqual(self.client.get(self.status_url).status_code, 405)
