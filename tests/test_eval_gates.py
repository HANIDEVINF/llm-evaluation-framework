import unittest
import json
import os

class TestEvalGateHarness(unittest.TestCase):
    def setUp(self):
        self.suite_file = os.path.join(os.path.dirname(__file__), '..', 'benchmarks', 'benchmark_suite_v1.json')

    def test_benchmark_file_exists_and_valid_json(self):
        self.assertTrue(os.path.exists(self.suite_file), "benchmark_suite_v1.json must exist")
        with open(self.suite_file) as f:
            data = json.load(f)
        self.assertEqual(data["total_cases"], 150)
        self.assertIn("categories", data)

    def test_hipaa_gate_is_zero_tolerance(self):
        with open(self.suite_file) as f:
            data = json.load(f)
        hipaa_threshold = data["categories"]["medical_privacy_hipaa"]["min_threshold"]
        self.assertEqual(hipaa_threshold, 1.0, "Medical privacy must enforce 100% (zero tolerance)")

    def test_latency_bound_sanity(self):
        with open(self.suite_file) as f:
            data = json.load(f)
        p95 = data["categories"]["latency_and_budget_bounds"]["max_latency_p95_ms"]
        self.assertLessEqual(p95, 1000, "p95 threshold must be strictly under 1000ms")

if __name__ == '__main__':
    unittest.main()
