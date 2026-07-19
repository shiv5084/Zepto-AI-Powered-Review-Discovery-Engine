import os
import hashlib
import logging
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

class NeonClient:
    """Manages the NeonDB PostgreSQL connection and CRUD operations for reviews."""

    def __init__(self, dsn: str = None):
        load_dotenv()
        self.dsn = dsn or os.environ.get("NEON_DATABASE_URL")
        if not self.dsn:
            logger.warning("NEON_DATABASE_URL environment variable is not set. Database operations will fail.")
            self.enabled = False
        else:
            self.enabled = True
            try:
                self.conn = psycopg2.connect(self.dsn)
                self.conn.autocommit = True
                self._create_tables()
                logger.info("Successfully connected to NeonDB and initialized tables.")
            except Exception as e:
                logger.error(f"Failed to connect to NeonDB: {e}. Falling back to disabled mode.")
                self.enabled = False

    def _create_tables(self):
        """Creates the raw_reviews and annotated_reviews tables if they do not exist."""
        if not self.enabled:
            return

        with self.conn.cursor() as cur:
            # Create raw_reviews table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS raw_reviews (
                    id SERIAL PRIMARY KEY,
                    source VARCHAR(50) NOT NULL,
                    date DATE NOT NULL,
                    title TEXT,
                    text TEXT NOT NULL,
                    rating INTEGER,
                    engagement INTEGER DEFAULT 0,
                    text_hash VARCHAR(64) UNIQUE NOT NULL,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create annotated_reviews table
            cur.execute("""
                CREATE TABLE IF NOT EXISTS annotated_reviews (
                    id SERIAL PRIMARY KEY,
                    review_id INTEGER UNIQUE REFERENCES raw_reviews(id) ON DELETE CASCADE,
                    sentiment VARCHAR(10) NOT NULL,
                    is_product_discovery_related BOOLEAN NOT NULL,
                    q1_theme VARCHAR(100),
                    q2_theme VARCHAR(100),
                    q3_theme VARCHAR(100),
                    q4_theme VARCHAR(100),
                    q5_theme VARCHAR(100),
                    q6_theme VARCHAR(100),
                    q7_theme VARCHAR(100),
                    q8_theme VARCHAR(100),
                    root_cause TEXT,
                    annotated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            logger.debug("NeonDB tables verified/created successfully.")

    def ensure_connection(self):
        """Ensures that the connection is active. Reconnects if closed or dead."""
        if not self.enabled:
            return
        
        is_closed = True
        if hasattr(self, "conn") and self.conn is not None:
            if self.conn.closed == 0:
                try:
                    with self.conn.cursor() as cur:
                        cur.execute("SELECT 1")
                    is_closed = False
                except Exception:
                    try:
                        self.conn.close()
                    except Exception:
                        pass
                    is_closed = True

        if is_closed:
            logger.info("NeonDB connection is closed or inactive. Reconnecting...")
            try:
                self.conn = psycopg2.connect(self.dsn)
                self.conn.autocommit = True
                logger.info("Successfully reconnected to NeonDB.")
            except Exception as e:
                logger.error(f"Failed to reconnect to NeonDB: {e}.")
                raise

    def insert_raw_reviews(self, df: pd.DataFrame) -> int:
        """Inserts raw reviews from a DataFrame using bulk upsert with hash deduplication.
        
        Returns the number of new reviews actually inserted.
        """
        self.ensure_connection()
        if not self.enabled or df.empty:
            return 0

        # Prepare records for insertion, generating SHA256 hash for each review text
        records = []
        for _, row in df.iterrows():
            text = str(row.get("text", "")).strip()
            if not text:
                continue
            text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            
            # Parse date
            date_val = row.get("date")
            if isinstance(date_val, str):
                try:
                    date_val = datetime.strptime(date_val[:10], "%Y-%m-%d").date()
                except ValueError:
                    date_val = datetime.now().date()
            elif not date_val:
                date_val = datetime.now().date()

            # Ensure engagement is int
            eng = row.get("engagement")
            try:
                eng = int(eng) if pd.notna(eng) else 0
            except (ValueError, TypeError):
                eng = 0

            # Ensure rating is int
            rat = row.get("rating")
            try:
                rat = int(rat) if pd.notna(rat) else None
            except (ValueError, TypeError):
                rat = None

            records.append((
                str(row.get("source", "unknown")),
                date_val,
                str(row.get("title", "")) if pd.notna(row.get("title")) else "",
                text,
                rat,
                eng,
                text_hash
            ))

        if not records:
            return 0

        inserted_count = 0
        with self.conn.cursor() as cur:
            # We use ON CONFLICT DO NOTHING to deduplicate by text_hash
            query = """
                INSERT INTO raw_reviews (source, date, title, text, rating, engagement, text_hash)
                VALUES %s
                ON CONFLICT (text_hash) DO NOTHING
            """
            execute_values(cur, query, records)
            inserted_count = cur.rowcount
            logger.info(f"NeonDB: Inserted {inserted_count} new raw reviews (skipped duplicates).")

        return inserted_count

    def get_unclassified_reviews(self) -> pd.DataFrame:
        """Retrieves raw reviews that have not been annotated yet (annotated_reviews has no entry)."""
        try:
            self.ensure_connection()
        except Exception:
            pass
        if not self.enabled:
            return pd.DataFrame()

        query = """
            SELECT r.id, r.source, r.date, r.title, r.text, r.rating, r.engagement
            FROM raw_reviews r
            LEFT JOIN annotated_reviews a ON r.id = a.review_id
            WHERE a.id IS NULL
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=columns)
            if not df.empty:
                # Ensure dates are converted to string format YYYY-MM-DD
                if "date" in df.columns:
                    df["date"] = df["date"].astype(str)
                df = df.where(pd.notnull(df), None)
            return df
        except Exception as e:
            logger.error(f"Failed to query unclassified reviews from NeonDB: {e}")
            return pd.DataFrame()

    def get_all_annotated_reviews(self) -> pd.DataFrame:
        """Retrieves all annotated reviews combined with their raw metadata."""
        try:
            self.ensure_connection()
        except Exception:
            pass
        if not self.enabled:
            return pd.DataFrame()

        query = """
            SELECT r.source, r.date, r.title, r.text, r.rating, r.engagement,
                   a.sentiment, a.is_product_discovery_related,
                   a.q1_theme, a.q2_theme, a.q3_theme, a.q4_theme, a.q5_theme,
                   a.q6_theme, a.q7_theme, a.q8_theme, a.root_cause
            FROM raw_reviews r
            JOIN annotated_reviews a ON r.id = a.review_id
        """
        try:
            with self.conn.cursor() as cur:
                cur.execute(query)
                columns = [desc[0] for desc in cur.description]
                rows = cur.fetchall()
            df = pd.DataFrame(rows, columns=columns)
            if not df.empty:
                if "date" in df.columns:
                    df["date"] = df["date"].astype(str)
                # Replace all Pandas NaN / NaT / Nulls with None so they serialize to JSON null
                df = df.where(pd.notnull(df), None)
            return df
        except Exception as e:
            logger.error(f"Failed to retrieve annotated reviews from NeonDB: {e}")
            return pd.DataFrame()

    def save_annotations(self, annotations: list) -> int:
        """Saves a batch of annotations into NeonDB.
        
        annotations: List of dicts, each containing:
          - review_id (int)
          - sentiment (str)
          - is_product_discovery_related (bool)
          - q1_theme (str)
          - q2_theme (str)
          - q3_theme (str)
          - q4_theme (str)
          - q5_theme (str)
          - q6_theme (str)
          - q7_theme (str)
          - q8_theme (str)
          - root_cause (str or None)
        """
        self.ensure_connection()
        if not self.enabled or not annotations:
            return 0

        records = []
        for ann in annotations:
            review_id = ann.get("db_id") or ann.get("review_id")
            if not review_id:
                logger.warning(f"Skipping annotation database write due to missing review_id/db_id: {ann}")
                continue
                
            records.append((
                review_id,
                ann.get("sentiment", "neutral"),
                bool(ann.get("is_product_discovery_related", False)),
                ann.get("repeat_purchase_drivers") or ann.get("q1_theme"),
                ann.get("exploration_barriers") or ann.get("q2_theme"),
                ann.get("discovery_methods") or ann.get("q3_theme"),
                ann.get("habit_drivers") or ann.get("q4_theme"),
                ann.get("information_needs") or ann.get("q5_theme"),
                ann.get("frustrations") or ann.get("q6_theme"),
                ann.get("segment_classification") or ann.get("q7_theme"),
                ann.get("unmet_needs") or ann.get("q8_theme"),
                ann.get("root_cause")
            ))

        inserted_count = 0
        with self.conn.cursor() as cur:
            query = """
                INSERT INTO annotated_reviews (
                    review_id, sentiment, is_product_discovery_related,
                    q1_theme, q2_theme, q3_theme, q4_theme, q5_theme,
                    q6_theme, q7_theme, q8_theme, root_cause
                ) VALUES %s
                ON CONFLICT (review_id) DO UPDATE SET
                    sentiment = EXCLUDED.sentiment,
                    is_product_discovery_related = EXCLUDED.is_product_discovery_related,
                    q1_theme = EXCLUDED.q1_theme,
                    q2_theme = EXCLUDED.q2_theme,
                    q3_theme = EXCLUDED.q3_theme,
                    q4_theme = EXCLUDED.q4_theme,
                    q5_theme = EXCLUDED.q5_theme,
                    q6_theme = EXCLUDED.q6_theme,
                    q7_theme = EXCLUDED.q7_theme,
                    q8_theme = EXCLUDED.q8_theme,
                    root_cause = EXCLUDED.root_cause,
                    annotated_at = CURRENT_TIMESTAMP
            """
            execute_values(cur, query, records)
            inserted_count = cur.rowcount

        return inserted_count

    def close(self):
        if self.enabled and hasattr(self, "conn") and self.conn:
            self.conn.close()
            logger.info("NeonDB connection closed.")
