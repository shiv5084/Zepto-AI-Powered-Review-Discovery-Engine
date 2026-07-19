import json
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
annotated_path = os.path.join(PROJECT_ROOT, "data", "processed", "annotated_reviews.json")

if not os.path.exists(annotated_path):
    print("annotated_reviews.json not found!")
    exit(1)

with open(annotated_path, "r", encoding="utf-8") as f:
    reviews = json.load(f)

# Define mappings from Spotify metrics to Zepto metrics
segment_map = {
    "Casual Listener": "Routine Replenishers",
    "Playlist Dependents": "Routine Replenishers",
    "Music Explorer": "Deal-Driven Explorers",
    "New Music Seekers": "Deal-Driven Explorers",
    "Passive Listener": "Impulsive Buyers",
    "Trend Follower": "Healthy/Organic Seekers",
    "Power User": "Local Brand Adapters",
    "Genre Hoppers": "Local Brand Adapters"
}

barriers_map = {
    "Lack of Mood/Context Filters": "Poor Category Visibility",
    "Lack of Discovery Filters": "Poor Category Visibility",
    "Poor Recommendation Quality": "Trust Deficit in New Brands"
}

methods_map = {
    "Mood/Activity-Based Listening": "Search-Driven Discovery",
    "Mood-Based Listening": "Search-Driven Discovery",
    "Relying on Familiar Playlists": "Banner & Promotion-Led",
    "Background/Passive Listening": "Algorithmic Recommendations",
    "Background Focus Listening": "Algorithmic Recommendations"
}

drivers_map = {
    "Mood Mismatch": "Habit & Routine Lock-in",
    "Offline/Data Saving": "Habit & Routine Lock-in",
    "Social Sharing": "Reorder Convenience"
}

needs_map = {
    "Smart Playlist Refresh": "Try-Before-You-Commit Packs",
    "Advanced Library Sorting": "Try-Before-You-Commit Packs",
    "Cross-Genre Discovery Mode": "Local Artisan Showcase",
    "Intent-Based Recommendations": "Local Artisan Showcase"
}

migrated_count = 0
migrated_reviews = []

for r in reviews:
    migrated_count += 1
    
    # 1. Base metadata
    migrated_r = {
        "source": r.get("source", "google_play"),
        "date": r.get("date", ""),
        "title": r.get("title", ""),
        "text": r.get("text", ""),
        "rating": r.get("rating", 3),
        "engagement": r.get("engagement", 0),
        "sentiment": r.get("sentiment", "neutral"),
        "is_product_discovery_related": r.get("is_product_discovery_related", True)
    }
    
    # 2. Map segment
    old_seg = r.get("segment_classification")
    migrated_r["segment_classification"] = segment_map.get(old_seg, "Routine Replenishers")
    
    # 3. Map barriers (Q2)
    old_pain = r.get("discovery_pain_points")
    migrated_r["exploration_barriers"] = barriers_map.get(old_pain, "None")
    
    # 4. Map frustrations (Q6)
    migrated_r["frustrations"] = r.get("recommendation_frustrations", "None")
    
    # 5. Map methods (Q3)
    old_goal = r.get("listening_goals_intentions")
    migrated_r["discovery_methods"] = methods_map.get(old_goal, "Search-Driven Discovery")
    
    # 6. Map repeat purchase drivers (Q1)
    old_repeat = r.get("repeat_listening_signals")
    migrated_r["repeat_purchase_drivers"] = drivers_map.get(old_repeat, "Habit & Routine Lock-in")
    
    # 7. Map unmet needs (Q8)
    old_need = r.get("unmet_needs")
    migrated_r["unmet_needs"] = needs_map.get(old_need, "Try-Before-You-Commit Packs")
    
    # 8. Add newly required Zepto Q-Commerce fields (Q4, Q5)
    migrated_r["habit_drivers"] = "Autopilot Reordering"
    migrated_r["information_needs"] = "None"
    
    migrated_reviews.append(migrated_r)

with open(annotated_path, "w", encoding="utf-8") as f:
    json.dump(migrated_reviews, f, indent=2, ensure_ascii=False)

print(f"Successfully migrated {migrated_count} reviews in annotated_reviews.json from Spotify schema to Zepto schema.")
