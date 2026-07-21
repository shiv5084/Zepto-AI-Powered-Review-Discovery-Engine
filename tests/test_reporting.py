import unittest
import json
import os
from unittest.mock import MagicMock, patch
from src.reporting.pulse_generator import PulseGenerator
from src.reporting.json_exporter import JSONExporter

class TestReporting(unittest.TestCase):

    def _make_mock_analysis(self):
        return {
            "question_1": [{"theme": "Habit & Routine Lock-in", "count": 10, "average_rating": 2.5, "evidence": ["Same items again and again."]}],
            "question_2": [{"theme": "Poor Category Visibility", "count": 8, "average_rating": 2.8, "evidence": ["Never surfaces new items."]}],
            "question_3": [{"theme": "Search-Driven Discovery", "count": 6, "average_rating": 3.5, "evidence": ["I want to search for local goods."]}],
            "question_4": [{"theme": "Autopilot Reordering", "count": 7, "average_rating": 3.0, "evidence": ["I just tap reorder."]}],
            "question_5": [{"theme": "Product Information Gaps", "count": 5, "average_rating": 4.0, "evidence": ["Needs ingredients details."]}],
            "question_6": [{"theme": "Catalog Stock Disconnects", "count": 12, "average_rating": 1.5, "root_cause": "Inventory sync delays", "evidence": ["Showed in stock but refunded."]}],
            "question_7": [{"segment": "Deal-Driven Explorers", "count": 9, "average_rating": 2.3, "severity_score": 1.21, "severity_rank": 1, "pct_sample": 0.35, "pct_negative_reviews": 0.65, "discovery_challenges": [{"pain_point": "Poor Category Visibility", "count": 5}]}],
            "question_8": [{"theme": "Try-Before-You-Commit Packs", "count": 5, "average_rating": 2.0, "opportunity_score": 20.0, "evidence": ["Wish I could buy small trials."]}],
            "sentiment_distribution": {
                "positive_count": 15,
                "neutral_count": 65,
                "negative_count": 20,
                "total_reviews": 100
            }
        }

    def _make_mock_opps(self):
        return [
            {"problem": "P1", "evidence": "E1", "suggested_ai_solution": "S1", "expected_impact": "I1"},
            {"problem": "P2", "evidence": "E2", "suggested_ai_solution": "S2", "expected_impact": "I2"},
            {"problem": "P3", "evidence": "E3", "suggested_ai_solution": "S3", "expected_impact": "I3"},
        ]

    @patch("src.reporting.pulse_generator.build_pulse_prompt")
    def test_markdown_pulse_note_draft_generation(self, mock_build_prompt):
        """Verifies that generate_pulse_note_draft builds the draft correctly and formats metrics."""
        mock_build_prompt.return_value = "Mocked Prompt"
        
        mock_groq = MagicMock()
        mock_gemini = MagicMock()
        mock_gemini.generate_content.return_value = "Mocked Gemini Response"

        generator = PulseGenerator(mock_groq, mock_gemini)
        report_text = generator.generate_pulse_note_draft(self._make_mock_analysis(), self._make_mock_opps())

        self.assertEqual(report_text, "Mocked Gemini Response")
        mock_build_prompt.assert_called_once()
        
        # Verify metrics representation sent to prompt builder
        metrics_summary = mock_build_prompt.call_args[0][0]
        self.assertIn("Repeat-Purchasing Drivers", metrics_summary)
        self.assertIn("Exploration Barriers", metrics_summary)
        self.assertIn("Discovery Methods", metrics_summary)
        self.assertIn("Habit Drivers", metrics_summary)
        self.assertIn("Information Needs", metrics_summary)
        self.assertIn("Platform Frustrations", metrics_summary)
        self.assertIn("Underserved User Segments", metrics_summary)
        self.assertIn("Unmet Needs", metrics_summary)
        self.assertIn("Top 3 Product Opportunities", metrics_summary)

    def test_json_exporter_schema_mapping(self):
        """Verifies JSONExporter pads each section to exactly 3 items,
        with live data first and deduplicated fallback items padded at the end.
        """
        mock_analysis = self._make_mock_analysis()
        mock_opps = [{"problem": "P1", "evidence": "E1", "suggested_ai_solution": "S1", "expected_impact": "I1"}]

        exporter = JSONExporter()
        output_file = "data/test_dashboard_data.json"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        data_path = exporter.export_dashboard_json(mock_analysis, mock_opps, "# Pulse Note Draft", output_file)
        
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("week_ending", data)
        self.assertEqual(data["pulse_note_text"], "# Pulse Note Draft")

        metrics = data["metrics"]

        # Most metric sections must have exactly 3 items (1 live + 2 fallback),
        # but underserved_segments must have exactly 5 items (representing all 5 shopper personas).
        section_keys_3 = [
            "repeat_purchase_drivers", "exploration_barriers", "discovery_methods",
            "habit_drivers", "information_needs", "top_frustrations", 
            "unmet_needs"
        ]
        for section_key in section_keys_3:
            self.assertEqual(len(metrics[section_key]), 3, f"{section_key} should have 3 items")
        self.assertEqual(len(metrics["underserved_segments"]), 5, "underserved_segments should have 5 items")

        # First item in each section is the live data
        self.assertFalse(metrics["repeat_purchase_drivers"][0].get("is_fallback"))
        self.assertEqual(metrics["repeat_purchase_drivers"][0]["theme"], "Habit & Routine Lock-in")
        self.assertEqual(metrics["repeat_purchase_drivers"][0]["count"], 10)
        self.assertEqual(metrics["repeat_purchase_drivers"][0]["average_rating"], 2.5)

        # Padded items (index 1 and 2) must be flagged as fallback
        self.assertTrue(metrics["repeat_purchase_drivers"][1].get("is_fallback"))
        self.assertTrue(metrics["repeat_purchase_drivers"][2].get("is_fallback"))

        # Verify sentiment distribution fallback is present (overridden to 150 total reviews since 100 < 150)
        self.assertIn("sentiment_distribution", data)
        self.assertEqual(data["sentiment_distribution"]["positive_count"], 45)
        self.assertEqual(data["sentiment_distribution"]["neutral_count"], 18)
        self.assertEqual(data["sentiment_distribution"]["negative_count"], 87)
        self.assertEqual(data["sentiment_distribution"]["total_reviews"], 150)

        # Opportunities: not padded, only 1 provided
        self.assertEqual(len(metrics["opportunities"]), 1)
        self.assertEqual(metrics["opportunities"][0]["problem"], "P1")
        
        # Cleanup
        if os.path.exists(output_file):
            os.remove(output_file)
