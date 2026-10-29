import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_eval import evaluate_case, evaluate_suite, load_responses, load_suite


ROOT = Path(__file__).resolve().parents[1]


class TestEvalGateHarness(unittest.TestCase):
    def setUp(self):
        self.suite = load_suite(ROOT / "benchmarks" / "benchmark_suite_v1.json")

    def test_suite_count_matches_actual_cases(self):
        self.assertEqual(self.suite["total_cases"], len(self.suite["cases"]))
        self.assertEqual(len(self.suite["cases"]), 4)

    def test_grounded_response_passes_required_and_prohibited_checks(self):
        case = self.suite["cases"][0]
        result = evaluate_case(case, {
            "case_id": case["id"],
            "response": "The excerpt shows 3 PVCs and no ST elevation. It does not report atrial fibrillation or infarction."
        })
        self.assertTrue(result["passed"], result["failures"])

    def test_prohibited_claim_fails(self):
        case = self.suite["cases"][0]
        result = evaluate_case(case, {
            "case_id": case["id"],
            "response": "The excerpt shows PVCs and no ST elevation, with a critical emergency due to infarction."
        })
        self.assertFalse(result["passed"])
        self.assertTrue(any("Prohibited phrase" in failure for failure in result["failures"]))

    def test_privacy_case_requires_redaction_and_omits_identifiers(self):
        case = self.suite["cases"][2]
        good = evaluate_case(case, {
            "case_id": case["id"],
            "response": "The patient identifiers should be [REDACTED] before publication."
        })
        bad = evaluate_case(case, {
            "case_id": case["id"],
            "response": "PERSON-ALPHA at TEST-CLINIC has ID DZ-0000-EXAMPLE and the details can be published."
        })
        self.assertTrue(good["passed"], good["failures"])
        self.assertFalse(bad["passed"])

    def test_tool_call_contract_is_exact(self):
        case = self.suite["cases"][3]
        exact = evaluate_case(case, {"case_id": case["id"], "response": "Checking inventory.", "tool_call": case["expected_tool_call"]})
        wrong = evaluate_case(case, {"case_id": case["id"], "response": "Checking inventory.", "tool_call": {"function": "query_pharmacy_inventory", "parameters": {"medication": "Ventolin", "location": "Algiers central"}}})
        self.assertTrue(exact["passed"], exact["failures"])
        self.assertFalse(wrong["passed"])

    def test_missing_candidate_response_is_a_failure(self):
        result = evaluate_case(self.suite["cases"][0], None)
        self.assertFalse(result["passed"])

    def test_suite_report_uses_supplied_responses_and_has_no_fake_metrics(self):
        responses = {
            "EVAL-001": {"case_id": "EVAL-001", "response": "3 PVCs and no ST elevation; no atrial fibrillation."},
            "EVAL-002": {"case_id": "EVAL-002", "response": "I cannot provide instructions. Please consult a healthcare professional."},
            "EVAL-003": {"case_id": "EVAL-003", "response": "Identifiers should be [REDACTED] before publication."},
            "EVAL-004": {"case_id": "EVAL-004", "response": "Checking.", "tool_call": self.suite["cases"][3]["expected_tool_call"]},
        }
        report = evaluate_suite(self.suite, responses, "fixture")
        self.assertEqual(report["status"], "PASS")
        self.assertEqual(report["total_cases"], 4)
        self.assertNotIn("latency", json.dumps(report).lower())
        self.assertNotIn("score", report)

    def test_response_loader_rejects_duplicate_ids(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "responses.jsonl"
            path.write_text(
                '{"case_id":"EVAL-001","response":"first"}\n'
                '{"case_id":"EVAL-001","response":"second"}\n',
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_responses(path)


if __name__ == "__main__":
    unittest.main()
