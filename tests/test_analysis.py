import os
import json
import unittest
from src.analysis.theme_discoverer import ThemeDiscoverer

class TestThemeDiscovery(unittest.TestCase):

    def _make_reviews(self):
        """Returns a small set of mock annotated reviews matching the Zepto quick-commerce schema."""
        return [
            {
                "text": "Zepto only shows my previous milk and bread orders. I want to discover organic vegetables but they are hidden.",
                "rating": 2,
                "is_product_discovery_related": True,
                "repeat_purchase_drivers": "Habit & Routine Lock-in",
                "exploration_barriers": "Poor Category Visibility",
                "discovery_methods": "Search-Driven Discovery",
                "habit_drivers": "Autopilot Reordering",
                "information_needs": "None",
                "frustrations": "Catalog Stock Disconnects",
                "unmet_needs": "Try-Before-You-Commit Packs",
                "segment_classification": "Deal-Driven Explorers",
                "sentiment": "negative"
            },
            {
                "text": "Great UI and easy search.",
                "rating": 5,
                "is_product_discovery_related": True,
                "repeat_purchase_drivers": "None",
                "exploration_barriers": "None",
                "discovery_methods": "None",
                "habit_drivers": "None",
                "information_needs": "None",
                "frustrations": "None",
                "unmet_needs": "None",
                "segment_classification": "Routine Replenishers",
                "sentiment": "positive"
            },
            {
                "text": "I get so many out of stock items, please fix the catalog updates.",
                "rating": 1,
                "is_product_discovery_related": True,
                "repeat_purchase_drivers": "Reorder Convenience",
                "exploration_barriers": "Poor Category Visibility",
                "discovery_methods": "Algorithmic Recommendations",
                "habit_drivers": "Weekly Routine Anchoring",
                "information_needs": "None",
                "frustrations": "Catalog Stock Disconnects",
                "unmet_needs": "Try-Before-You-Commit Packs",
                "segment_classification": "Routine Replenishers",
                "sentiment": "negative"
            }
        ]

    def setUp(self):
        self.discoverer = ThemeDiscoverer()
        self.reviews = self._make_reviews()

    def test_q1_repeat_purchase_drivers(self):
        """Q1 groups repeat_purchase_drivers correctly and excludes 'None'."""
        results = self.discoverer.run_theme_discovery_q1(self.reviews)
        themes = [r["theme"] for r in results]
        self.assertNotIn("None", themes)
        self.assertIn("Habit & Routine Lock-in", themes)
        self.assertIn("Reorder Convenience", themes)

    def test_q1_count_and_avg_rating(self):
        """Q1 count and average rating computed correctly."""
        results = self.discoverer.run_theme_discovery_q1(self.reviews)
        habit_theme = next(r for r in results if r["theme"] == "Habit & Routine Lock-in")
        self.assertEqual(habit_theme["count"], 1)
        self.assertEqual(habit_theme["average_rating"], 2.0)

    def test_q2_exploration_barriers(self):
        """Q2 groups exploration barriers and calculates counts correctly."""
        results = self.discoverer.run_theme_discovery_q2(self.reviews)
        themes = [r["theme"] for r in results]
        self.assertNotIn("None", themes)
        self.assertIn("Poor Category Visibility", themes)
        vis_theme = next(r for r in results if r["theme"] == "Poor Category Visibility")
        # Review 0 (rating 2) and Review 2 (rating 1) have "Poor Category Visibility"
        self.assertEqual(vis_theme["count"], 2)
        self.assertEqual(vis_theme["average_rating"], 1.5)

    def test_q7_segments_percentages(self):
        """Q7 computes segment metrics including % Sample and % Negative Reviews."""
        results = self.discoverer.run_theme_discovery_q7(self.reviews)
        segments = {r["segment"]: r for r in results}
        self.assertIn("Routine Replenishers", segments)
        routine_seg = segments["Routine Replenishers"]
        self.assertEqual(routine_seg["count"], 2)
        # 2 reviews out of 3 total classified/tagged reviews = 2/3 = 0.67
        self.assertAlmostEqual(routine_seg["pct_sample"], 2.0 / 3.0, places=2)
        # Of the 2 reviews in Routine Replenishers, Review 2 has a cross-category pain point (Poor Category Visibility from Q2)
        # Review 1 has "None". So % Negative Reviews for Q2 pain points = 1 / 2 = 0.50
        self.assertEqual(routine_seg["pct_negative_reviews"], 0.50)
        # priority_score = 1.5 * (2/3) + 2.0 * 0.50 + 0.40 * (5 - 3) = 1.0 + 1.0 + 0.8 = 2.80
        self.assertAlmostEqual(routine_seg["priority_score"], 2.80, places=2)
        self.assertEqual(routine_seg["priority_rank"], 2)

    def test_q8_opportunity_score(self):
        """Q8 computes opportunity_score correctly based on Count * (6 - Avg Rating)."""
        results = self.discoverer.run_theme_discovery_q8(self.reviews)
        themes = {r["theme"]: r for r in results}
        self.assertIn("Try-Before-You-Commit Packs", themes)
        try_theme = themes["Try-Before-You-Commit Packs"]
        # Review 0 (rating 2) and Review 2 (rating 1) have "Try-Before-You-Commit Packs"
        # Count = 2, Avg Rating = 1.5. Opportunity = 2 * (6 - 1.5) = 2 * 4.5 = 9.0
        self.assertEqual(try_theme["count"], 2)
        self.assertEqual(try_theme["average_rating"], 1.5)
        self.assertEqual(try_theme["opportunity_score"], 9.0)

    def test_perform_full_analysis_structure(self):
        """perform_full_analysis returns all 8 question keys and sentiment_distribution."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
            json.dump(self.reviews, f)
            tmp_path = f.name
        try:
            results = self.discoverer.perform_full_analysis(tmp_path)
            for key in ["question_1", "question_2", "question_3", "question_4", "question_5", "question_6", "question_7", "question_8", "sentiment_distribution"]:
                self.assertIn(key, results)
            
            dist = results["sentiment_distribution"]
            self.assertEqual(dist["positive_count"], 1)
            self.assertEqual(dist["neutral_count"], 0)
            self.assertEqual(dist["negative_count"], 2)
            self.assertEqual(dist["total_reviews"], 3)
        finally:
            os.unlink(tmp_path)
