import os
import json
import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static Fallback Data for Zepto (shown only when live pipeline returns < 3 items)
# ---------------------------------------------------------------------------

_FALLBACK_Q1 = [
    {"theme": "Habit & Routine Lock-in", "count": 48, "average_rating": 3.8, "evidence": [], "is_fallback": True},
    {"theme": "Reorder Convenience",     "count": 35, "average_rating": 4.2, "evidence": [], "is_fallback": True},
    {"theme": "Trust in Known Brands",   "count": 28, "average_rating": 4.0, "evidence": [], "is_fallback": True},
]

_FALLBACK_Q2 = [
    {"theme": "Poor Category Visibility",   "count": 52, "average_rating": 2.3, "evidence": [], "is_fallback": True},
    {"theme": "Trust Deficit in New Brands", "count": 38, "average_rating": 2.6, "evidence": [], "is_fallback": True},
    {"theme": "Lack of Product Information", "count": 30, "average_rating": 2.8, "evidence": [], "is_fallback": True},
]

_FALLBACK_Q3 = [
    {"theme": "Search-Driven Discovery",      "count": 58, "average_rating": 3.5, "evidence": [], "is_fallback": True},
    {"theme": "Banner & Promotion-Led",       "count": 44, "average_rating": 3.9, "evidence": [], "is_fallback": True},
    {"theme": "Algorithmic Recommendations",  "count": 32, "average_rating": 3.0, "evidence": [], "is_fallback": True},
]

_FALLBACK_Q4 = [
    {"theme": "Autopilot Reordering",       "count": 61, "average_rating": 4.4, "evidence": [], "is_fallback": True},
    {"theme": "Weekly Routine Anchoring",    "count": 40, "average_rating": 4.1, "evidence": [], "is_fallback": True},
    {"theme": "Cognitive Load Avoidance",    "count": 25, "average_rating": 3.8, "evidence": [], "is_fallback": True},
]

_FALLBACK_Q5 = [
    {"theme": "Product Reviews & Ratings",      "count": 47, "average_rating": 2.9, "evidence": [], "is_fallback": True},
    {"theme": "Detailed Product Descriptions",  "count": 32, "average_rating": 3.2, "evidence": [], "is_fallback": True},
    {"theme": "Product Quality Assurance",      "count": 28, "average_rating": 2.5, "evidence": [], "is_fallback": True},
]

_FALLBACK_Q6 = [
    {
        "theme": "Poor Product Quality", 
        "count": 38, 
        "average_rating": 1.9, 
        "root_cause": "Local hub handlers do not separate fresh fruits from heavy items, causing bruising.", 
        "evidence": [], 
        "is_fallback": True
    },
    {
        "theme": "Delivery Issues", 
        "count": 35, 
        "average_rating": 2.1, 
        "root_cause": "Inaccurate delivery time estimates fail to account for local traffic patterns.", 
        "evidence": [], 
        "is_fallback": True
    },
    {
        "theme": "Inconsistent Availability", 
        "count": 30, 
        "average_rating": 1.8, 
        "root_cause": "Inventory replenishment schedules at dark stores lag behind consumer demand spikes.", 
        "evidence": [], 
        "is_fallback": True
    },
]

_FALLBACK_Q7 = [
    {
        "segment": "Routine Replenishers", "count": 65, "pct_sample": 0.45, "average_rating": 3.8,
        "pct_negative_reviews": 0.22, "severity_score": 0.26, "severity_rank": 3, "evidence": [], "is_fallback": True,
        "discovery_challenges": [
            {"pain_point": "Poor Category Visibility", "count": 10, "frequency_within_segment": 0.15},
            {"pain_point": "Trust Deficit in New Brands", "count": 4, "frequency_within_segment": 0.06},
        ],
    },
    {
        "segment": "Deal-Driven Explorers", "count": 42, "pct_sample": 0.25, "average_rating": 2.5,
        "pct_negative_reviews": 0.76, "severity_score": 1.90, "severity_rank": 1, "evidence": [], "is_fallback": True,
        "discovery_challenges": [
            {"pain_point": "No Incentive to Explore", "count": 18, "frequency_within_segment": 0.43},
            {"pain_point": "Poor Category Visibility", "count": 10, "frequency_within_segment": 0.24},
            {"pain_point": "Trust Deficit in New Brands", "count": 6, "frequency_within_segment": 0.14},
        ],
    },
    {
        "segment": "Occasion-Based Shoppers", "count": 30, "pct_sample": 0.18, "average_rating": 2.9,
        "pct_negative_reviews": 0.50, "severity_score": 1.05, "severity_rank": 2, "evidence": [], "is_fallback": True,
        "discovery_challenges": [
            {"pain_point": "Cluttered Home Screen", "count": 8, "frequency_within_segment": 0.27},
            {"pain_point": "Poor Category Visibility", "count": 5, "frequency_within_segment": 0.17},
        ],
    },
]

_FALLBACK_Q8 = [
    {"theme": "Smart Bundle Suggestions",             "count": 35, "average_rating": 2.2, "opportunity_score": 133.0, "evidence": [], "is_fallback": True},
    {"theme": "Personalized Category Recommendations", "count": 28, "average_rating": 2.0, "opportunity_score": 112.0, "evidence": [], "is_fallback": True},
    {"theme": "Try-Before-You-Commit Packs",           "count": 25, "average_rating": 2.4, "opportunity_score": 90.0,  "evidence": [], "is_fallback": True},
]


def _fill_to_three(live_list: list, fallbacks: list, key: str = "theme") -> list:
    """Returns up to 3 items, prioritizing live_list entries."""
    result = list(live_list)
    live_labels = {item.get(key, "") for item in result}
    needed = 3 - len(result)
    for fb in fallbacks:
        if needed <= 0:
            break
        if fb.get(key, "") not in live_labels:
            result.append(fb)
            live_labels.add(fb.get(key, ""))
            needed -= 1
    return result


def pad_analysis_results(analysis_results: dict) -> dict:
    """Pads each of the 8 question lists to exactly 3 items using static fallbacks."""
    padded = dict(analysis_results)

    raw_q1 = [dict(t, is_fallback=False) for t in analysis_results.get("question_1", [])]
    raw_q2 = [dict(t, is_fallback=False) for t in analysis_results.get("question_2", [])]
    raw_q3 = [dict(t, is_fallback=False) for t in analysis_results.get("question_3", [])]
    raw_q4 = [dict(t, is_fallback=False) for t in analysis_results.get("question_4", [])]
    raw_q5 = [dict(t, is_fallback=False) for t in analysis_results.get("question_5", [])]
    raw_q6 = [dict(t, is_fallback=False) for t in analysis_results.get("question_6", [])]
    raw_q8 = [dict(t, is_fallback=False) for t in analysis_results.get("question_8", [])]

    raw_q7 = []
    live_q7 = analysis_results.get("question_7", [])
    for s in live_q7:
        s_copy = dict(s, is_fallback=False)
        seg_name = s_copy.get("segment", "")
        live_challenges = list(s_copy.get("discovery_challenges", []))
        
        if len(live_challenges) == 0 and len(live_q7) <= 1:
            fallback_matches = [fb for fb in _FALLBACK_Q7 if fb["segment"] == seg_name]
            if fallback_matches:
                s_copy = dict(fallback_matches[0], is_fallback=True)
                raw_q7.append(s_copy)
                continue

        fallback_matches = [fb for fb in _FALLBACK_Q7 if fb["segment"] == seg_name]
        fallback_challenges = fallback_matches[0]["discovery_challenges"] if fallback_matches else []
        
        padded_challenges = list(live_challenges)
        existing_points = {c["pain_point"] for c in padded_challenges}
        needed = 3 - len(padded_challenges)
        for fc in fallback_challenges:
            if needed <= 0:
                break
            if fc["pain_point"] not in existing_points:
                padded_challenges.append(fc)
                existing_points.add(fc["pain_point"])
                needed -= 1
        s_copy["discovery_challenges"] = padded_challenges
        raw_q7.append(s_copy)

    padded["question_1"] = _fill_to_three(raw_q1, _FALLBACK_Q1, key="theme")
    padded["question_2"] = _fill_to_three(raw_q2, _FALLBACK_Q2, key="theme")
    padded["question_3"] = _fill_to_three(raw_q3, _FALLBACK_Q3, key="theme")
    padded["question_4"] = _fill_to_three(raw_q4, _FALLBACK_Q4, key="theme")
    padded["question_5"] = _fill_to_three(raw_q5, _FALLBACK_Q5, key="theme")
    padded["question_6"] = _fill_to_three(raw_q6, _FALLBACK_Q6, key="theme")
    padded["question_8"] = _fill_to_three(raw_q8, _FALLBACK_Q8, key="theme")
    
    padded_q7 = _fill_to_three(raw_q7, _FALLBACK_Q7, key="segment")
    padded_q7.sort(key=lambda x: x.get("severity_score", 0.0), reverse=True)
    for rank, item in enumerate(padded_q7):
        item["severity_rank"] = rank + 1
    padded["question_7"] = padded_q7

    return padded


class JSONExporter:
    """Exports structured metrics, opportunities, and pulse note text to dashboard_data.json."""

    def __init__(self, config_or_path: Any = "config.yaml"):
        self.config = {}
        if isinstance(config_or_path, dict):
            self.config = config_or_path
        elif isinstance(config_or_path, str) and os.path.exists(config_or_path):
            try:
                with open(config_or_path, "r", encoding="utf-8") as f:
                    self.config = json.load(f)
            except Exception:
                pass

    def export_dashboard_json(self, analysis_results: dict, opportunities: list, pulse_note_text: str, output_path: str = None) -> str:
        """Pads and writes final metrics into dashboard_data.json, copying it to frontend/public/."""
        # Sync metrics padding
        padded_results = pad_analysis_results(analysis_results)
        
        # Prepare final output structure
        output_data = {
            "week_ending": datetime.now().strftime("%Y-%m-%d"),
            "pulse_note_text": pulse_note_text,
            "total_reviews_analyzed": padded_results.get("total_reviews_analyzed", 0),
            "product_discovery_relevant_reviews": padded_results.get("product_discovery_relevant_reviews", 0),
            "sentiment_distribution": padded_results.get("sentiment_distribution", {}),
            "metrics": {
                "repeat_purchase_drivers": padded_results.get("question_1", []),
                "exploration_barriers": padded_results.get("question_2", []),
                "discovery_methods": padded_results.get("question_3", []),
                "habit_drivers": padded_results.get("question_4", []),
                "information_needs": padded_results.get("question_5", []),
                "top_frustrations": padded_results.get("question_6", []),
                "underserved_segments": padded_results.get("question_7", []),
                "unmet_needs": padded_results.get("question_8", []),
                "opportunities": opportunities
            }
        }

        if not output_path:
            # Fallback path resolve
            output_path = "data/dashboard_data.json"
        
        parent = os.path.dirname(output_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        logger.info(f"Dashboard data exported to: {output_path}")

        # Also copy to frontend/public/ folder to make it accessible to Next.js in fallback dev mode
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        frontend_public = os.path.join(project_root, "frontend", "public")
        if os.path.exists(frontend_public):
            copy_path = os.path.join(frontend_public, "dashboard_data.json")
            try:
                with open(copy_path, "w", encoding="utf-8") as f:
                    json.dump(output_data, f, indent=2, ensure_ascii=False)
                logger.info(f"Auto-synced dashboard data to frontend: {copy_path}")
            except Exception as e:
                logger.warning(f"Failed to auto-sync to frontend public folder: {e}")

        return output_path
