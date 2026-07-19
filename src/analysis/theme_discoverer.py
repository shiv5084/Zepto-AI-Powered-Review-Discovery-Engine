import os
import json
import logging
from collections import Counter
from typing import List, Dict, Any, Optional
import pandas as pd
from src.processing.llm_client import GeminiClient
from src.processing.review_processor import call_groq_with_retry
from src.prompts.root_cause import build_prompt as build_root_cause_prompt

logger = logging.getLogger(__name__)

# Predefined Theme Registries
Q1_THEMES = [
    "Habit & Routine Lock-in",
    "Reorder Convenience",
    "Trust in Known Brands",
    "Price Sensitivity",
    "Limited Category Awareness",
    "Time Pressure",
    "Satisfaction with Current Selection"
]

Q2_THEMES = [
    "Poor Category Visibility",
    "Irrelevant Recommendations",
    "Lack of Product Information",
    "Trust Deficit in New Brands",
    "High Perceived Risk",
    "Cluttered Home Screen",
    "No Incentive to Explore"
]

Q3_THEMES = [
    "Search-Driven Discovery",
    "Banner & Promotion-Led",
    "Social Media Influence",
    "Word of Mouth",
    "Algorithmic Recommendations",
    "Occasion-Triggered Browsing",
    "Accidental / Serendipitous"
]

Q4_THEMES = [
    "Autopilot Reordering",
    "Weekly Routine Anchoring",
    "Brand Loyalty Lock-in",
    "Comfort Zone Persistence",
    "Cognitive Load Avoidance",
    "List-Based Shopping",
    "Trigger-Based Purchasing"
]

Q5_THEMES = [
    "Product Reviews & Ratings",
    "Price Comparison",
    "Product Quality Assurance",
    "Detailed Product Descriptions",
    "Trial / Sample Options",
    "Return & Refund Policy",
    "Visual Content"
]

Q6_THEMES = [
    "Poor Product Quality",
    "Delivery Issues",
    "Limited Product Variety",
    "Misleading Pricing / Offers",
    "App Usability Problems",
    "Inconsistent Availability",
    "Poor Customer Support"
]

Q7_PERSONAS = [
    "Routine Replenishers",
    "Deal-Driven Explorers",
    "Occasion-Based Shoppers",
    "Health & Wellness Seekers",
    "Impulse Browsers",
    "None"
]

Q8_THEMES = [
    "Personalized Category Recommendations",
    "Smart Bundle Suggestions",
    "Try-Before-You-Commit Packs",
    "Social Shopping Features",
    "Contextual Discovery Prompts",
    "Better Search & Filters",
    "Loyalty Rewards for Exploration"
]


def _aggregate_by_label(
    reviews: List[dict],
    field: str,
    valid_labels: List[str],
    sort_key: str = "count",
    extra_fields_fn=None,
) -> List[dict]:
    """Groups reviews by a single-value classification field.
    
    Computes count, average_rating, and evidence quotes. Excludes 'None' values.
    """
    buckets: Dict[str, List[dict]] = {label: [] for label in valid_labels}
    for r in reviews:
        label = r.get(field, "None")
        if label and label != "None" and label in buckets:
            buckets[label].append(r)

    results = []
    for label, matched in buckets.items():
        count = len(matched)
        if count == 0:
            continue

        ratings = [r.get("rating") for r in matched if r.get("rating") is not None and not pd.isna(r.get("rating"))]
        avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
        evidence = [r.get("text", "") for r in matched[:2] if r.get("text")]

        entry = {
            "theme": label,
            "count": count,
            "average_rating": avg_rating,
            "evidence": evidence,
        }
        if extra_fields_fn:
            entry.update(extra_fields_fn(label, matched))

        results.append(entry)

    results.sort(key=lambda x: x[sort_key], reverse=True)
    return results


class ThemeDiscoverer:
    """Groups annotated reviews by predefined Literal fields and computes count-based metrics."""

    def __init__(self, gemini_client: GeminiClient = None):
        self.gemini_client = gemini_client

    def run_theme_discovery_q1(self, reviews: List[dict]) -> List[dict]:
        """Q1: What drives users to repeat purchase from the same categories?"""
        logger.info("Q1: Aggregating repeat-purchasing drivers locally...")
        return _aggregate_by_label(reviews, "repeat_purchase_drivers", Q1_THEMES)

    def run_theme_discovery_q2(self, reviews: List[dict]) -> List[dict]:
        """Q2: What barriers prevent users from exploring other categories?"""
        logger.info("Q2: Aggregating exploration barriers locally...")
        return _aggregate_by_label(reviews, "exploration_barriers", Q2_THEMES)

    def run_theme_discovery_q3(self, reviews: List[dict]) -> List[dict]:
        """Q3: How do users currently discover products in new categories?"""
        logger.info("Q3: Aggregating discovery methods locally...")
        return _aggregate_by_label(reviews, "discovery_methods", Q3_THEMES)

    def run_theme_discovery_q4(self, reviews: List[dict]) -> List[dict]:
        """Q4: What behaviors indicate habit-driven shopping?"""
        logger.info("Q4: Aggregating habit-driven signals locally...")
        return _aggregate_by_label(reviews, "habit_drivers", Q4_THEMES)

    def run_theme_discovery_q5(self, reviews: List[dict]) -> List[dict]:
        """Q5: What information do users need before buying from a new category?"""
        logger.info("Q5: Aggregating information needs locally...")
        return _aggregate_by_label(reviews, "information_needs", Q5_THEMES)

    def run_theme_discovery_q6(self, reviews: List[dict]) -> List[dict]:
        """Q6: What frustrations do users face during product discovery?
        
        Also generates a single-sentence root cause for each frustration theme.
        """
        logger.info("Q6: Aggregating frustrations and generating root causes...")
        
        def frustration_extra(label: str, matched: List[dict]) -> dict:
            # Gather up to 5 snippets to analyze the root cause
            snippets = [r.get("text", "") for r in matched[:5] if r.get("text")]
            root_cause = "Root cause analysis unavailable."
            
            if self.gemini_client and snippets:
                try:
                    prompt = build_root_cause_prompt(label, snippets)
                    logger.info(f"Generating root cause for '{label}' using Gemini model: {self.gemini_client.model_name}...")
                    rc_text = self.gemini_client.generate_content(prompt, temperature=0.1)
                    if rc_text:
                        root_cause = rc_text
                except Exception as e:
                    logger.warning(f"Root cause generation failed for '{label}': {e}. Using default.")
            
            return {"root_cause": root_cause}

        return _aggregate_by_label(
            reviews=reviews,
            field="frustrations",
            valid_labels=Q6_THEMES,
            extra_fields_fn=frustration_extra
        )

    def run_theme_discovery_q7(self, reviews: List[dict]) -> List[dict]:
        """Q7: Which user segments are most underserved by the current platform?
        
        Metrics:
          - pct_sample: count in segment / total classified reviews
          - pct_negative_reviews: percentage of reviews in segment with any Q2 pain point
          - priority_score: (5 - average_rating) * pct_negative_reviews
        """
        logger.info("Q7: Aggregating underserved user segments locally...")
        total_len = len(reviews)
        buckets: Dict[str, List[dict]] = {p: [] for p in Q7_PERSONAS}

        for r in reviews:
            seg = r.get("segment_classification", "None") or "None"
            if seg in buckets:
                buckets[seg].append(r)

        total_active_segments_count = sum(len(buckets[p]) for p in Q7_PERSONAS if p != "None")

        segments_list = []
        for seg_name, seg_reviews in buckets.items():
            if seg_name == "None":
                continue
            count = len(seg_reviews)
            if count == 0:
                continue

            pct_sample = round(count / total_active_segments_count, 4) if total_active_segments_count > 0 else 0.0
            ratings = [r.get("rating") for r in seg_reviews if r.get("rating") is not None and not pd.isna(r.get("rating"))]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
            evidence = [r.get("text", "") for r in seg_reviews[:2] if r.get("text")]

            # Calculate % negative reviews (any review in this segment having any Q2 exploration barrier)
            # A review has a Q2 barrier if exploration_barriers is not 'None'
            reviews_with_barriers = sum(1 for r in seg_reviews if r.get("exploration_barriers", "None") != "None")
            pct_negative_reviews = round(reviews_with_barriers / count, 4) if count > 0 else 0.0
            
            # Priority score = 1.5 * pct_sample + 2.0 * pct_negative_reviews + 0.40 * (5.0 - avg_rating)
            priority_score = round(1.5 * pct_sample + 2.0 * pct_negative_reviews + 0.40 * (5.0 - avg_rating), 2)

            # Cross-aggregate discovery_pain_points (Q2 barriers) within this segment
            pain_point_counts: Counter = Counter()
            for r in seg_reviews:
                pain = r.get("exploration_barriers", "None")
                if pain and pain != "None":
                    pain_point_counts[pain] += 1

            discovery_challenges = []
            for pain_point, pain_count in pain_point_counts.most_common(3):
                discovery_challenges.append({
                    "pain_point": pain_point,
                    "count": pain_count,
                    "frequency_within_segment": round(pain_count / count, 4) if count > 0 else 0.0,
                })

            segments_list.append({
                "segment": seg_name,
                "count": count,
                "pct_sample": pct_sample,
                "average_rating": avg_rating,
                "evidence": evidence,
                "pct_negative_reviews": pct_negative_reviews,
                "priority_score": priority_score,
                "discovery_challenges": discovery_challenges,
            })

        segments_list.sort(key=lambda x: x["priority_score"], reverse=True)
        for rank, item in enumerate(segments_list):
            item["priority_rank"] = rank + 1

        return segments_list

    def run_theme_discovery_q8(self, reviews: List[dict]) -> List[dict]:
        """Q8: What unmet needs emerge consistently across reviews?
        
        Opportunity Score = Count * (6.0 - Average Rating)
        """
        logger.info("Q8: Aggregating unmet needs locally...")
        
        def unmet_extra(label: str, matched: List[dict]) -> dict:
            ratings = [r.get("rating") for r in matched if r.get("rating") is not None and not pd.isna(r.get("rating"))]
            avg_rating = round(sum(ratings) / len(ratings), 2) if ratings else 0.0
            count = len(matched)
            return {"opportunity_score": round(count * (6.0 - avg_rating), 4)}

        results = _aggregate_by_label(
            reviews=reviews,
            field="unmet_needs",
            valid_labels=Q8_THEMES,
            extra_fields_fn=unmet_extra
        )
        results.sort(key=lambda x: x.get("opportunity_score", 0.0), reverse=True)
        return results

    def compute_sentiment_distribution(self, reviews: List[dict]) -> dict:
        """Counts positive/neutral/negative sentiments across all reviews."""
        counts = {"positive": 0, "neutral": 0, "negative": 0}
        for r in reviews:
            sent = r.get("sentiment", "neutral")
            if isinstance(sent, str):
                sent = sent.lower()
            if sent in counts:
                counts[sent] += 1
            else:
                counts["neutral"] += 1

        total = len(reviews)
        return {
            "positive_count": counts["positive"],
            "neutral_count": counts["neutral"],
            "negative_count": counts["negative"],
            "positive_pct": round(counts["positive"] / total, 4) if total > 0 else 0.0,
            "neutral_pct": round(counts["neutral"] / total, 4) if total > 0 else 0.0,
            "negative_pct": round(counts["negative"] / total, 4) if total > 0 else 0.0,
            "total_reviews": total
        }

    def perform_full_analysis(self, input_json_path: str, output_json_path: str = None) -> dict:
        """Loads annotated_reviews.json, runs all 8 local aggregation pipelines, and saves results."""
        if not os.path.exists(input_json_path):
            raise FileNotFoundError(f"Annotated reviews JSON not found at: {input_json_path}")

        with open(input_json_path, "r", encoding="utf-8") as f:
            reviews = json.load(f)

        # Filter to only include reviews where is_product_discovery_related == True
        classified_reviews = [r for r in reviews if r.get("is_product_discovery_related") is True]
        logger.info(f"Loaded {len(reviews)} total reviews; {len(classified_reviews)} classified as product discovery related.")

        q1_results = self.run_theme_discovery_q1(classified_reviews)
        q2_results = self.run_theme_discovery_q2(classified_reviews)
        q3_results = self.run_theme_discovery_q3(classified_reviews)
        q4_results = self.run_theme_discovery_q4(classified_reviews)
        q5_results = self.run_theme_discovery_q5(classified_reviews)
        q6_results = self.run_theme_discovery_q6(classified_reviews)
        q7_results = self.run_theme_discovery_q7(classified_reviews)
        q8_results = self.run_theme_discovery_q8(classified_reviews)

        analysis_output = {
            "question_1": q1_results,
            "question_2": q2_results,
            "question_3": q3_results,
            "question_4": q4_results,
            "question_5": q5_results,
            "question_6": q6_results,
            "question_7": q7_results,
            "question_8": q8_results,
            "total_reviews_analyzed": len(reviews),
            "product_discovery_relevant_reviews": len(classified_reviews),
            "sentiment_distribution": self.compute_sentiment_distribution(classified_reviews)
        }

        if output_json_path:
            out_dir = os.path.dirname(output_json_path)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
            with open(output_json_path, "w", encoding="utf-8") as f:
                json.dump(analysis_output, f, indent=2, ensure_ascii=False)
            logger.info(f"Analysis results saved successfully to {output_json_path}")

        return analysis_output
