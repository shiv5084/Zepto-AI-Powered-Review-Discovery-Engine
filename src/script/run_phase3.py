# Verification script for Phase 3: Analytical Theme Discovery & Cluster Analysis
import os
import sys
import json

# Add project root to python path to resolve src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.processing.llm_client import GeminiClient
from src.analysis.theme_discoverer import ThemeDiscoverer

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 60)
    print("RUNNING PHASE 3 VERIFICATION: Theme Discovery & Clustering (Zepto)")
    print("=" * 60)

    # 1. Check if annotated reviews from Phase 2 exist
    annotated_path = "data/processed/annotated_reviews.json"
    if not os.path.exists(annotated_path):
        print(f"[ERROR] Annotated reviews JSON not found at '{annotated_path}'.")
        print("Please run Phase 2 verification first via: python src/script/run_phase2.py")
        sys.exit(1)

    print(f"[OK] Found annotated reviews file at: {annotated_path}")

    # 2. Initialize GeminiClient and ThemeDiscoverer
    try:
        print("[ ] Initializing Gemini client...")
        gemini_client = GeminiClient()
        discoverer = ThemeDiscoverer(gemini_client)
        print("[OK] Gemini client and ThemeDiscoverer initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        print("Please verify that GEMINI_API_KEY and GEMINI_SUMMARY_MODEL are defined in your .env file.")
        sys.exit(1)

    # 3. Perform Theme Discovery
    output_path = "data/processed/analysis_results.json"
    print(f"\n[ ] Running theme discovery and cluster analysis pipeline...")
    try:
        results = discoverer.perform_full_analysis(annotated_path, output_path)
        print("[OK] Theme discovery and clustering analysis: SUCCESS")
    except Exception as e:
        print(f"[ERROR] Theme discovery pipeline failed: {e}")
        sys.exit(1)

    # 4. Output Verification
    if not os.path.exists(output_path):
        print(f"[ERROR] Analysis output check: FAILED - file missing at {output_path}")
        sys.exit(1)

    print(f"[OK] Output file created successfully at: {output_path}")

    # 5. Schema verification
    required_keys = {"question_1", "question_2", "question_3", "question_4", "question_5", "question_6", "question_7", "question_8"}
    keys = set(results.keys())
    if not required_keys.issubset(keys):
        print(f"[ERROR] Schema check: FAILED - expected keys {required_keys}, got {keys}")
        sys.exit(1)

    print("[OK] Schema check: SUCCESS (All 8 core business questions are mapped)")

    # 6. Sample output print
    print("\n" + "-" * 60)
    print("SAMPLE ANALYSIS RESULTS:")
    print("-" * 60)

    # Q1 print
    print("\nQUESTION 1: Repeat Purchase Drivers")
    for item in results["question_1"][:2]:
        print(f"  Theme       : {item['theme']}")
        print(f"  Count       : {item['count']}")
        print(f"  Avg Rating  : {item['average_rating']}")
        print(f"  Quote (Ex)  : \"{item['evidence'][0] if item['evidence'] else 'N/A'}\"")
        print("  " + "-" * 30)

    # Q2 print
    print("\nQUESTION 2: Exploration Barriers")
    for item in results["question_2"][:2]:
        print(f"  Theme       : {item['theme']}")
        print(f"  Count       : {item['count']}")
        print(f"  Avg Rating  : {item['average_rating']}")
        print("  " + "-" * 30)

    # Q6 frustrations print
    print("\nQUESTION 6: Frustrations & Root Causes")
    for item in results["question_6"][:2]:
        print(f"  Theme       : {item['theme']}")
        print(f"  Count       : {item['count']}")
        print(f"  Avg Rating  : {item['average_rating']}")
        print(f"  Root Cause  : {item.get('root_cause', 'N/A')}")
        print("  " + "-" * 30)

    # Q7 segments print
    print("\nQUESTION 7: Underserved User Segments (Top Priorities)")
    for item in results["question_7"][:2]:
        print(f"  Segment     : {item['segment']}")
        print(f"  Count       : {item['count']}")
        print(f"  % Sample    : {round(item.get('pct_sample', 0) * 100, 1)}%")
        print(f"  % Negative  : {round(item.get('pct_negative_reviews', 0) * 100, 1)}%")
        print(f"  Priority Rank: {item.get('priority_rank')} (Score: {item.get('priority_score')})")
        print(f"  Challenges  : {item['discovery_challenges'][:2]}")
        print("  " + "-" * 30)

    # Q8 print
    print("\nQUESTION 8: Unmet Needs & Opportunity Scores")
    for item in results["question_8"][:2]:
        print(f"  Theme       : {item['theme']}")
        print(f"  Count       : {item['count']}")
        print(f"  Avg Rating  : {item['average_rating']}")
        print(f"  Opportunity Score : {item['opportunity_score']}")
        print("  " + "-" * 30)

    print("\n[OK] PHASE 3 VERIFICATION COMPLETED: ALL PIPELINE STAGES VERIFIED.")
    print("=" * 60)

if __name__ == "__main__":
    main()
