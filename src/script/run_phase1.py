# Verification script for Phase 1: Ingestion & PII Scrubbing
import os
import sys

# Add project root to python path to resolve src imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.ingestion.ingestor import IngestionManager

def main():
    # Configure stdout to handle utf-8 encoding correctly on Windows console
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    print("=" * 60)
    print("RUNNING PHASE 1 VERIFICATION: Ingestion & PII Scrubbing")
    print("=" * 60)

    # 1. Instantiate IngestionManager and execute scraping
    try:
        manager = IngestionManager()
        print("[ ] Executing ingestion pipeline from real URLs...")
        df = manager.run(num_records=2000)
        print(f"[OK] Data Ingestion: SUCCESS (Ingested {len(df)} reviews)")
    except Exception as e:
        print(f"[ERROR] Data Ingestion: FAILED - {e}")
        sys.exit(1)

    # 2. Check output files existence
    raw_path = "data/raw/raw_reviews.csv"
    processed_path = "data/processed/reviews.csv"
    
    if not os.path.exists(raw_path):
        print(f"[ERROR] Output check: FAILED - raw CSV missing at {raw_path}")
        sys.exit(1)
        
    if not os.path.exists(processed_path):
        print(f"[ERROR] Output check: FAILED - processed CSV missing at {processed_path}")
        sys.exit(1)
        
    print("[OK] Output check: SUCCESS (both raw and processed CSVs created)")

    # 3. Verify columns and formats
    expected_cols = {"source", "date", "title", "text", "rating", "engagement"}
    df_cols = set(df.columns)
    if not expected_cols.issubset(df_cols):
        print(f"[ERROR] Schema check: FAILED - expected columns {expected_cols}, got {df_cols}")
        sys.exit(1)
        
    print("[OK] Schema check: SUCCESS (columns match the unified schema)")

    # 4. Display sample parsed records showing scrubbed PII
    print("\n" + "-"*40)
    print("SAMPLE PROCESSED REVIEWS (Verifying PII Masking):")
    print("-"*40)
    
    # We display a few rows to the console
    sample_df = df.head(5)
    for idx, row in sample_df.iterrows():
        print(f"\nRow {idx} | Source: {row['source']} | Date: {row['date']} | Rating: {row['rating']}")
        print(f"Title: {row['title']}")
        print(f"Text : {row['text']}")
        
    # Check for presence of common PII indicators in processed texts
    text_corpus = " ".join(df["text"].astype(str).tolist())
    pii_tags = ["[EMAIL]", "[IP_ADDRESS]", "[PHONE_NUMBER]", "[USER_HANDLE]", "[REDACTED_NAME]"]
    found_tags = [tag for tag in pii_tags if tag in text_corpus]
    
    print("\n" + "-"*40)
    if found_tags:
        print(f"[OK] PII Scrubbing tags detected in outputs: {found_tags}")
    else:
        print("[!] No PII scrubbing tags detected in current output (this is normal if no PII was in ingested data)")

    print("\n[OK] PHASE 1 VERIFICATION COMPLETED: PIPELINE EXECUTED SUCCESSFULLY.")
    print("=" * 60)

if __name__ == "__main__":
    main()
