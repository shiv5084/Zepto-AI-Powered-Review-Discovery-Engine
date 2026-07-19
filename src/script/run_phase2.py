# Verification script for Phase 2: Theme Extraction & Metric Parsing (LLM-Powered)
import os
import sys
import pandas as pd

# Add project root to python path to resolve src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.processing.llm_client import GroqClient
from src.processing.review_processor import ReviewProcessor
from src.db.neon_client import NeonClient

def main():
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass

    print("=" * 60)
    print("RUNNING PHASE 2 VERIFICATION: Theme Extraction & Metric Parsing")
    print("=" * 60)

    # 1. Check if processed reviews from Phase 1 exist
    processed_path = "data/processed/reviews.csv"
    if not os.path.exists(processed_path):
        print(f"[ERROR] Processed reviews CSV not found at '{processed_path}'.")
        print("Please run Phase 1 first via: python src/script/run_phase1.py")
        sys.exit(1)

    print(f"[OK] Found processed reviews file at: {processed_path}")

    # 2. Read processed reviews dataset
    try:
        df = pd.read_csv(processed_path)
        print(f"[OK] Processed reviews loaded successfully. Total records: {len(df)}")
    except Exception as e:
        print(f"[ERROR] Failed to load processed reviews CSV: {e}")
        sys.exit(1)

    if df.empty:
        print("[ERROR] processed/reviews.csv is empty. Cannot perform LLM analysis.")
        sys.exit(1)

    # 3. Initialize GroqClient, NeonClient, and ReviewProcessor
    try:
        print("[ ] Initializing Groq client...")
        client = GroqClient()
        neon_client = NeonClient()
        processor = ReviewProcessor(client)
        print("[OK] Groq client, NeonDB client, and ReviewProcessor initialized successfully.")
    except Exception as e:
        print(f"[ERROR] Initialization failed: {e}")
        print("Please verify that GROQ_API_KEY and NEON_DATABASE_URL are defined in your .env file.")
        sys.exit(1)

    # 4. Run annotation (check optimization settings first)
    opt_config = client.config.get("optimization", {})
    opt_enabled = opt_config.get("enabled", True)

    if opt_enabled:
        sampling_cfg = opt_config.get("sampling", {})
        sample_size = sampling_cfg.get("sample_size", 500)
        min_floor_sources = sampling_cfg.get("min_floor_sources", ["reddit", "product_reviews", "twitter"])
        
        gate_cfg = opt_config.get("gate", {})
        gate_enabled = gate_cfg.get("enabled", True)
        gate_batch_size = gate_cfg.get("batch_size", 10)
        
        print(f"\n[ ] Running OPTIMIZED pipeline (Strategy 4 + 5)...")
        print(f"    - Target Sample Size: {sample_size}")
        print(f"    - Min-floor sources: {min_floor_sources}")
        print(f"    - Gate enabled: {gate_enabled}")
        if gate_enabled:
            print(f"    - Gate batch size: {gate_batch_size}")
            
        try:
            annotated_df, coverage = processor.process_reviews_optimized(
                df,
                sample_size=sample_size,
                min_floor_sources=min_floor_sources,
                gate_enabled=gate_enabled,
                gate_batch_size=gate_batch_size,
                neon_client=neon_client
            )
            print(f"[OK] LLM Annotation batch run: SUCCESS (Annotated {len(annotated_df)} reviews)")
            
            # Print coverage/optimization stats
            print("\n" + "=" * 60)
            print("LLM OPTIMIZATION STATS:")
            print("-" * 60)
            print(f"Total reviews in system      : {coverage.get('total_reviews')}")
            print(f"Sampled reviews (S4)         : {coverage.get('sampled_count')} ({coverage.get('coverage_pct')}% coverage)")
            if gate_enabled:
                print(f"Gate passed (S5 - full LLM)  : {coverage.get('gate_passed')}")
                print(f"Gate rejected (auto-labeled) : {coverage.get('gate_rejected')}")
            print(f"LLM calls made               : {coverage.get('llm_calls_made')}")
            print(f"LLM calls saved vs full run  : {coverage.get('llm_calls_saved_vs_full')}")
            print("=" * 60)
        except Exception as e:
            print(f"[ERROR] LLM Annotation failed: {e}")
            neon_client.close()
            sys.exit(1)
    else:
        sample_size = min(300, len(df))
        print(f"\n[ ] Processing batch of {sample_size} reviews through LLM (non-optimized, rate-limit safe)...")
        try:
            annotated_df = processor.process_reviews(df, num_records=sample_size)
            print(f"[OK] LLM Annotation batch run: SUCCESS (Annotated {len(annotated_df)} reviews)")
        except Exception as e:
            print(f"[ERROR] LLM Annotation failed: {e}")
            neon_client.close()
            sys.exit(1)

    neon_client.close()

    # 5. Output Verification
    annotated_path = "data/processed/annotated_reviews.json"
    if not os.path.exists(annotated_path):
        print(f"[ERROR] Annotated JSON check: FAILED - file missing at {annotated_path}")
        sys.exit(1)

    print(f"[OK] Output file created successfully at: {annotated_path}")

    # 6. Verify required columns (Zepto Q-Commerce)
    required_cols = {
        "source", "date", "title", "text", "rating", "engagement",
        "sentiment", "is_product_discovery_related", "repeat_purchase_drivers",
        "exploration_barriers", "discovery_methods", "habit_drivers",
        "information_needs", "frustrations", "unmet_needs", "segment_classification"
    }
    cols = set(annotated_df.columns)
    if not required_cols.issubset(cols):
        print(f"[ERROR] Schema check: FAILED - expected columns {required_cols}, got {cols}")
        sys.exit(1)

    print("[OK] Schema check: SUCCESS (all 16 quick-commerce fields are present)")

    # 7. Print Sample Results (first 3 only)
    print("\n" + "-" * 60)
    print("SAMPLE ANNOTATED REVIEWS RESULT (first 3):")
    print("-" * 60)
    
    for idx, row in annotated_df.head(3).iterrows():
        print(f"\nReview {idx + 1} | Source: {row['source']} | Rating: {row['rating']}")
        print(f"Text       : {row['text']}")
        print(f"Sentiment  : {row['sentiment']}")
        print(f"Discovery? : {row['is_product_discovery_related']}")
        print(f"Segment    : {row['segment_classification']}")
        print(f"Repeat Buy : {row['repeat_purchase_drivers']}")
        print(f"Barriers   : {row['exploration_barriers']}")
        print(f"Discovery  : {row['discovery_methods']}")
        print(f"Habit      : {row['habit_drivers']}")
        print(f"Info Gaps  : {row['information_needs']}")
        print(f"Frustration: {row['frustrations']}")
        print(f"Unmet Needs: {row['unmet_needs']}")
        print("-" * 40)

    print("\n[OK] PHASE 2 VERIFICATION COMPLETED: ALL PIPELINE STAGES VERIFIED.")
    print("=" * 60)

if __name__ == "__main__":
    main()
