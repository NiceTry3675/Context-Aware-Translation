import unittest

from core.validation.structured import map_cases_to_v1_fields


class TestValidationMapping(unittest.TestCase):
    def test_mapping_routes_by_dimension_and_severity(self):
        cases = [
            {"dimension": "completeness", "severity": 2, "reason": "문장 하나 누락"},
            {"dimension": "addition", "severity": 1, "reason": "불필요한 문장 추가"},
            {"dimension": "name_consistency", "severity": 3, "reason": "이름 불일치: John → 존"},
            {"dimension": "accuracy", "severity": 3, "reason": "의미 왜곡"},
            {"dimension": "accuracy", "severity": 2, "reason": "어색한 번역"},
            {"dimension": "dialogue_style", "severity": 1, "reason": "말투 부적절 (해요체/반말)"},
            {"dimension": "flow", "severity": 2, "reason": "부자연스러운 표현"},
            {"dimension": "other", "severity": 1, "reason": "기타 사소한 문제"},
        ]

        mapped = map_cases_to_v1_fields(cases)

        self.assertEqual(mapped["missing_content"], ["문장 하나 누락"])
        self.assertEqual(mapped["added_content"], ["불필요한 문장 추가"])
        self.assertEqual(mapped["name_inconsistencies"], ["이름 불일치: John → 존"])

        # severity 3 accuracy → critical
        self.assertIn("의미 왜곡", mapped["critical_issues"])
        # severity 2 accuracy → minor
        self.assertIn("어색한 번역", mapped["minor_issues"])
        # dialogue_style/flow/other with low severity → minor
        self.assertIn("말투 부적절 (해요체/반말)", mapped["minor_issues"])
        self.assertIn("부자연스러운 표현", mapped["minor_issues"])
        self.assertIn("기타 사소한 문제", mapped["minor_issues"])


if __name__ == "__main__":
    unittest.main()

