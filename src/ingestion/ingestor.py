import os
import re
import pandas as pd
import logging
from src.ingestion.scrapers import PublicReviewScraper
from src.ingestion.pii_scrubber import PIIScrubber
from src.db.neon_client import NeonClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def strip_emojis(text: str) -> str:
    """Remove emojis and non-standard symbols."""
    emoji_pattern = re.compile(
        r'[\U00010000-\U0010ffff]|[\u2600-\u27ff]|[\u3000-\u303f]|[\u2000-\u206f]',
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def clean_sentence_length(text: str) -> str:
    """Remove sentences containing less than 5 words."""
    # Split text by sentence boundaries (.!? followed by space)
    sentences = re.split(r'(?<=[.!?])\s+', text)
    clean_sentences = []
    for sentence in sentences:
        words = [w for w in sentence.split() if w.strip()]
        if len(words) >= 5:
            clean_sentences.append(sentence)
    return " ".join(clean_sentences)

def is_spam(text: str) -> bool:
    """Detect if review is spam, contains excessive character repetitions or ads."""
    text_lower = text.lower()
    spam_keywords = ["buy now", "click link", "promo code", "make money", "discount code", "advertisement"]
    if any(kw in text_lower for kw in spam_keywords):
        return True
    # 5+ repeating characters like aaaaa or !!!!!
    if re.search(r'(.)\1{4,}', text_lower):
        return True
    # Three repeating words consecutively
    words = text_lower.split()
    for i in range(len(words) - 2):
        if words[i] == words[i+1] == words[i+2]:
            return True
    return False

class IngestionManager:
    """Orchestrates data collection, cleaning, local PII scrubbing, and database persistence."""

    def __init__(self, raw_dir: str = "data/raw", processed_dir: str = "data/processed"):
        self.raw_dir = raw_dir
        self.processed_dir = processed_dir
        
        # Ensure directories exist
        os.makedirs(self.raw_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)
        
        self.scraper = PublicReviewScraper()
        self.scrubber = PIIScrubber()
        
        # Initialize NeonDB client if connection string is configured
        self.db_client = NeonClient()

    def run(self, num_records: int = 100) -> pd.DataFrame:
        """Execute the ingestion workflow: Scrape per channel -> Save individually -> Save to NeonDB -> Clean & Scrub -> Save Processed."""
        logger.info("Starting Multi-Source Review Ingestion...")
        
        # 1. Scrape each channel individually
        app_store = self.scraper.scrape_app_store()
        google_play = self.scraper.scrape_google_play()
        reddit = self.scraper.scrape_reddit()
        twitter = self.scraper.scrape_twitter()
        trustpilot = self.scraper.scrape_trustpilot()
        
        # 2. Store individual raw reviews files under data/raw/
        df_app_store = self._save_raw_channel(app_store, "raw_apple_app_store.csv")
        df_google_play = self._save_raw_channel(google_play, "raw_google_play.csv")
        df_reddit = self._save_raw_channel(reddit, "raw_reddit.csv")
        df_twitter = self._save_raw_channel(twitter, "raw_twitter.csv")
        df_trustpilot = self._save_raw_channel(trustpilot, "raw_trustpilot.csv")
        
        # 3. Combine all raw reviews
        dfs = [df_app_store, df_google_play, df_reddit, df_twitter, df_trustpilot]
        raw_df = pd.concat(dfs, ignore_index=True)
        
        # Save combined raw reviews CSV (contains ALL raw reviews from all channels)
        raw_path = os.path.join(self.raw_dir, "raw_reviews.csv")
        raw_df.to_csv(raw_path, index=False, encoding="utf-8-sig")
        logger.info(f"Combined raw reviews saved to: {raw_path} ({len(raw_df)} rows)")

        # 4. Insert into NeonDB raw_reviews table for persistent storage and deduplication
        if self.db_client.enabled:
            logger.info("Writing raw reviews to NeonDB...")
            self.db_client.insert_raw_reviews(raw_df)
            
            # Retrieve back all raw reviews from NeonDB (which now are deduplicated across historical runs)
            # This enables us to run cleaning and processing on the clean unique database set.
            with self.db_client.conn.cursor() as cur:
                cur.execute("SELECT id, source, date, title, text, rating, engagement FROM raw_reviews")
                rows = cur.fetchall()
                db_df = pd.DataFrame(rows, columns=["db_id", "source", "date", "title", "text", "rating", "engagement"])
                # Ensure date is string format
                db_df["date"] = db_df["date"].astype(str)
                logger.info(f"Retrieved {len(db_df)} raw reviews from NeonDB.")
                processing_df = db_df
        else:
            logger.info("NeonDB is disabled/unavailable. Processing local raw reviews.")
            # Set a dummy db_id for local-only execution fallback
            processing_df = raw_df.copy()
            processing_df["db_id"] = range(1, len(processing_df) + 1)
        
        # 5. Normalize and clean data fields
        processed_records = []
        for idx, row in processing_df.iterrows():
            source = str(row["source"]).strip()
            date = str(row["date"]).strip()
            title = str(row["title"]).strip() if pd.notna(row["title"]) else ""
            raw_text = str(row["text"]).strip()
            db_id = int(row["db_id"])
            
            rating = int(row["rating"]) if pd.notna(row["rating"]) and row["rating"] is not None else None
            engagement = int(row["engagement"]) if pd.notna(row["engagement"]) and row["engagement"] is not None else None
            
            # --- Data Cleaning ---
            # A. Emoji Removal
            cleaned_text = strip_emojis(raw_text)
            cleaned_title = strip_emojis(title)
            
            # B. Sentence Length Filter (remove sentences with less than 5 words)
            cleaned_text = clean_sentence_length(cleaned_text)
            
            # C. Spam Detection
            if is_spam(cleaned_text) or is_spam(cleaned_title):
                logger.info(f"Skipping record {idx}: classified as spam.")
                continue
                
            # Skip if text is empty after sentence filtering
            if not cleaned_text.strip():
                logger.info(f"Skipping record {idx}: empty text after sentence length check.")
                continue
            
            # 6. Apply local PII scrubbing (Regex-only)
            scrubbed_text = self.scrubber.scrub(cleaned_text)
            scrubbed_title = self.scrubber.scrub(cleaned_title)
            
            processed_records.append({
                "db_id": db_id,
                "source": source,
                "date": date,
                "title": scrubbed_title,
                "text": scrubbed_text,
                "rating": rating,
                "engagement": engagement
            })
            
        processed_df = pd.DataFrame(processed_records)
        
        # D. Deduplication
        if not processed_df.empty:
            processed_df.drop_duplicates(subset=["text"], keep="first", inplace=True)
            processed_df.reset_index(drop=True, inplace=True)
        
        # Slice to respect num_records limit if specified, shuffling first to ensure representation from all sources
        if num_records is not None and len(processed_df) > num_records:
            processed_df = processed_df.sample(frac=1, random_state=42).reset_index(drop=True)
            processed_df = processed_df.head(num_records)

        # Save processed CSV
        processed_path = os.path.join(self.processed_dir, "reviews.csv")
        processed_df.to_csv(processed_path, index=False, encoding="utf-8-sig")
        logger.info(f"Processed, scrubbed reviews saved to: {processed_path} ({len(processed_df)} rows)")
        
        return processed_df

    def _save_raw_channel(self, reviews: list, filename: str) -> pd.DataFrame:
        """Helper to format and save a raw channel's scraped reviews list to CSV."""
        cols = ["source", "date", "title", "text", "rating", "engagement"]
        df = pd.DataFrame(reviews)
        if df.empty:
            df = pd.DataFrame(columns=cols)
        else:
            # Ensure all unified columns exist
            for col in cols:
                if col not in df.columns:
                    df[col] = None
            df = df[cols]
        path = os.path.join(self.raw_dir, filename)
        df.to_csv(path, index=False, encoding="utf-8-sig")
        logger.info(f"Saved raw channel reviews to: {path} ({len(df)} rows)")
        return df

    def close(self):
        if hasattr(self, "db_client") and self.db_client:
            self.db_client.close()

if __name__ == "__main__":
    manager = IngestionManager()
    manager.run(150)
    manager.close()
