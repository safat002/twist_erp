from django.test import TestCase

from backend.modules.report_builder.calculations import evaluate_calculations


class CalculationEvaluationTests(TestCase):
    def test_simple_expression(self):
        rows = [{"revenue": 1000, "cost": 400}]
        calculations = [{"id": "gross_margin", "expression": "revenue - cost"}]

        result = evaluate_calculations(rows, calculations)

        self.assertEqual(result[0]["gross_margin"], 600)

    def test_handles_invalid_expression(self):
        rows = [{"value": 10}]
        calculations = [{"id": "broken", "expression": "value / 0"}]
        result = evaluate_calculations(rows, calculations)
        self.assertIsNone(result[0]["broken"])
