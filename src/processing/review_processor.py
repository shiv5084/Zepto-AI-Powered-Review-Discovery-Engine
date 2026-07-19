import os
import json
import time
import random
import logging
from typing import List, Literal, Optional, Tuple, Dict, Any
import pandas as pd
import groq
from pydantic import BaseModel, Field
from src.processing.llm_client import GroqClient
from src.processing.sampler import stratified_sample
from src.prompts.classifier_system import build_prompt as build_classifier_prompt
from src.prompts.gate_system import build_prompt as build_gate_prompt
from src.prompts.batch_system import build_prompt as build_batch_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------

class ReviewAnalysis(BaseModel):
    """Structured representation of Zepto review metrics."""
    sentiment: Literal["positive", "neutral", "negative"] = Field(
        ...,
        description="Sentiment of the review. Must be exactly 'positive', 'neutral', or 'negative'."
    )
    is_product_discovery_related: bool = Field(
        ...,
        description="True if the review is related to product/category discovery, habits, usability, and related signals. False otherwise."
    )
    repeat_purchase_drivers: Literal[
        "Habit & Routine Lock-in",
        "Reorder Convenience",
        "Trust in Known Brands",
        "Price Sensitivity",
        "Limited Category Awareness",
        "Time Pressure",
        "Satisfaction with Current Selection",
        "None"
    ] = Field(
        ...,
        description="Classify repeat-purchasing driver."
    )
    exploration_barriers: Literal[
        "Poor Category Visibility",
        "Irrelevant Recommendations",
        "Lack of Product Information",
        "Trust Deficit in New Brands",
        "High Perceived Risk",
        "Cluttered Home Screen",
        "No Incentive to Explore",
        "None"
    ] = Field(
        ...,
        description="Classify exploration barrier."
    )
    discovery_methods: Literal[
        "Search-Driven Discovery",
        "Banner & Promotion-Led",
        "Social Media Influence",
        "Word of Mouth",
        "Algorithmic Recommendations",
        "Occasion-Triggered Browsing",
        "Accidental / Serendipitous",
        "None"
    ] = Field(
        ...,
        description="Classify discovery method."
    )
    habit_drivers: Literal[
        "Autopilot Reordering",
        "Weekly Routine Anchoring",
        "Brand Loyalty Lock-in",
        "Comfort Zone Persistence",
        "Cognitive Load Avoidance",
        "List-Based Shopping",
        "Trigger-Based Purchasing",
        "None"
    ] = Field(
        ...,
        description="Classify habit driver."
    )
    information_needs: Literal[
        "Product Reviews & Ratings",
        "Price Comparison",
        "Product Quality Assurance",
        "Detailed Product Descriptions",
        "Trial / Sample Options",
        "Return & Refund Policy",
        "Visual Content",
        "None"
    ] = Field(
        ...,
        description="Classify information need."
    )
    frustrations: Literal[
        "Poor Product Quality",
        "Delivery Issues",
        "Limited Product Variety",
        "Misleading Pricing / Offers",
        "App Usability Problems",
        "Inconsistent Availability",
        "Poor Customer Support",
        "None"
    ] = Field(
        ...,
        description="Classify frustration."
    )
    unmet_needs: Literal[
        "Personalized Category Recommendations",
        "Smart Bundle Suggestions",
        "Try-Before-You-Commit Packs",
        "Social Shopping Features",
        "Contextual Discovery Prompts",
        "Better Search & Filters",
        "Loyalty Rewards for Exploration",
        "None"
    ] = Field(
        ...,
        description="Classify unmet need."
    )
    segment_classification: Literal[
        "Routine Replenishers",
        "Deal-Driven Explorers",
        "Occasion-Based Shoppers",
        "Health & Wellness Seekers",
        "Impulse Browsers",
        "None"
    ] = Field(
        ...,
        description="Classify user segment."
    )


class BatchReviewAnalysis(BaseModel):
    """Container for batch reviews analysis."""
    analyses: List[ReviewAnalysis] = Field(
        ...,
        description="List of structured review analysis results matching the input reviews in order."
    )


class GateBatchResult(BaseModel):
    """Strategy 5 gate: yes/no signal decision per review in a batch."""
    decisions: List[Literal["yes", "no"]] = Field(
        ...,
        description="List of 'yes'/'no' gate decisions matching the input reviews in order."
    )

# ---------------------------------------------------------------------------
# Rate Limiter & Fallback Utilities
# ---------------------------------------------------------------------------

class GroqRateLimiter:
    """Proactive throttle to stay under Groq RPM/TPM limits."""

    def __init__(self, min_interval_seconds: float = 3.0, tpm_budget_per_minute: int = 8000):
        self.min_interval = min_interval_seconds
        self.tpm_budget = tpm_budget_per_minute
        self._last_request_at = 0.0
        self._token_window: List[Tuple[float, int]] = []

    def wait_before_request(self) -> None:
        elapsed = time.time() - self._last_request_at
        wait_time = self.min_interval - elapsed
        if wait_time > 0:
            logger.debug(f"Rate limiter: waiting {wait_time:.2f}s...")
            time.sleep(wait_time)
        self._last_request_at = time.time()

    def record_token_usage(self, total_tokens: int) -> None:
        if total_tokens <= 0:
            return
        now = time.time()
        self._token_window.append((now, total_tokens))
        self._token_window = [(ts, tokens) for ts, tokens in self._token_window if now - ts < 60]
        tokens_in_window = sum(tokens for _, tokens in self._token_window)
        if tokens_in_window > self.tpm_budget:
            extra_wait = 60 - (now - self._token_window[0][0]) + random.uniform(0.5, 1.5)
            logger.info(f"Approaching TPM budget ({tokens_in_window}/{self.tpm_budget}). Pausing {extra_wait:.1f}s...")
            time.sleep(extra_wait)


class GroqTokenDailyLimitError(RuntimeError):
    """Raised when Groq tokens-per-day (TPD) quota is exhausted."""
    pass


def _extract_retry_after_seconds(error: Exception) -> Optional[float]:
    response = getattr(error, "response", None)
    if response is None:
        return None
    headers = getattr(response, "headers", None)
    if not headers:
        return None
    retry_after = headers.get("retry-after") or headers.get("Retry-After")
    if retry_after is None:
        return None
    try:
        return float(retry_after)
    except (TypeError, ValueError):
        return None


def _is_rate_limit_error(error: Exception) -> bool:
    if isinstance(error, groq.RateLimitError):
        return True
    if isinstance(error, groq.APIStatusError) and getattr(error, "status_code", None) == 429:
        return True
    return False


def _is_tpd_exhausted(error: Exception) -> bool:
    msg = str(error).lower()
    return "tokens per day" in msg or "tpd" in msg or "per day" in msg


def call_groq_with_retry(
    client: groq.Groq,
    model: str,
    messages: list,
    tools: list,
    tool_choice: dict,
    max_retries: int = 5,
    initial_backoff: int = 5,
    max_backoff: int = 120,
    rate_limiter: Optional[GroqRateLimiter] = None,
) -> Any:
    backoff = initial_backoff
    for attempt in range(max_retries):
        if rate_limiter is not None:
            rate_limiter.wait_before_request()
        try:
            kwargs = {
                "model": model,
                "messages": messages,
                "temperature": 0.1
            }
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = tool_choice
            response = client.chat.completions.create(**kwargs)
            usage = getattr(response, "usage", None)
            if rate_limiter is not None and usage is not None:
                total_tokens = getattr(usage, "total_tokens", 0) or 0
                if isinstance(total_tokens, (int, float)):
                    rate_limiter.record_token_usage(int(total_tokens))
            return response
        except Exception as e:
            if not _is_rate_limit_error(e):
                logger.error(f"Groq API error: {e}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(backoff + random.uniform(0, 1))
                backoff = min(backoff * 2, max_backoff)
                continue

            if _is_tpd_exhausted(e):
                logger.error("Groq daily token quota (TPD) exhausted. Aborting Phase 2.")
                raise GroqTokenDailyLimitError("Groq tokens-per-day limit reached.") from e

            retry_after = _extract_retry_after_seconds(e)
            wait_time = retry_after if retry_after is not None else backoff
            wait_time += random.uniform(0, 1)
            if wait_time > 30:
                logger.warning(f"Rate limit wait time {wait_time:.1f}s is too long. Failing fast.")
                raise e
            logger.warning(f"Rate limit hit (attempt {attempt + 1}/{max_retries}). Retrying in {wait_time:.1f}s...")
            time.sleep(wait_time)
            backoff = min(backoff * 2, max_backoff)

    raise RuntimeError("Failed to get response from Groq API after maximum retries.")

# ---------------------------------------------------------------------------
# Review Processor Class
# ---------------------------------------------------------------------------

class ReviewProcessor:
    """Handles structured LLM sentiment extraction and metric parsing for reviews."""

    def __init__(self, client: GroqClient):
        self.llm_client = client
        self.client = client.get_client()
        self.classifier_model = client.classifier_model
        self.gate_model = client.gate_model
        
        rate_cfg = getattr(client, "rate_limit", None) or {}
        self.batch_size = int(rate_cfg.get("batch_size", 5))
        self.max_retries = int(rate_cfg.get("max_retries", 5))
        self.initial_backoff = int(rate_cfg.get("initial_backoff_seconds", 5))
        self.max_backoff = int(rate_cfg.get("max_backoff_seconds", 120))
        self.rate_limiter = GroqRateLimiter(
            min_interval_seconds=float(rate_cfg.get("min_request_interval_seconds", 3.0)),
            tpm_budget_per_minute=int(rate_cfg.get("tpm_budget", 8000)),
        )

    def _groq_call_kwargs(self) -> dict:
        return {
            "max_retries": self.max_retries,
            "initial_backoff": self.initial_backoff,
            "max_backoff": self.max_backoff,
            "rate_limiter": self.rate_limiter,
        }

    @staticmethod
    def _analysis_to_dict(analysis: ReviewAnalysis) -> dict:
        return {
            "sentiment": analysis.sentiment,
            "is_product_discovery_related": analysis.is_product_discovery_related,
            "repeat_purchase_drivers": analysis.repeat_purchase_drivers,
            "exploration_barriers": analysis.exploration_barriers,
            "discovery_methods": analysis.discovery_methods,
            "habit_drivers": analysis.habit_drivers,
            "information_needs": analysis.information_needs,
            "frustrations": analysis.frustrations,
            "unmet_needs": analysis.unmet_needs,
            "segment_classification": analysis.segment_classification,
        }

    @staticmethod
    def _neutral_analysis_dict() -> dict:
        return {
            "sentiment": "neutral",
            "is_product_discovery_related": False,
            "repeat_purchase_drivers": "None",
            "exploration_barriers": "None",
            "discovery_methods": "None",
            "habit_drivers": "None",
            "information_needs": "None",
            "frustrations": "None",
            "unmet_needs": "None",
            "segment_classification": "None",
        }

    @staticmethod
    def _fallback_analysis_dict(rating: Any = None) -> dict:
        sentiment = "neutral"
        if rating is not None and not pd.isna(rating):
            try:
                val = float(rating)
                if val >= 4.0:
                    sentiment = "positive"
                elif val <= 2.0:
                    sentiment = "negative"
            except (ValueError, TypeError):
                pass

        return {
            "sentiment": sentiment,
            "is_product_discovery_related": False,
            "repeat_purchase_drivers": "None",
            "exploration_barriers": "None",
            "discovery_methods": "None",
            "habit_drivers": "None",
            "information_needs": "None",
            "frustrations": "None",
            "unmet_needs": "None",
            "segment_classification": "None",
        }


    def analyze_single_review(self, review_text: str) -> ReviewAnalysis:
        """Calls Groq LLM to parse a single review text using classifier system prompt."""
        if not review_text.strip():
            return ReviewAnalysis(**self._neutral_analysis_dict())

        schema = ReviewAnalysis.model_json_schema()
        messages = [
            {"role": "system", "content": build_classifier_prompt(schema)},
            {"role": "user", "content": json.dumps({"review": {"text": review_text}}, ensure_ascii=False)}
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_review",
                    "description": "Return structured review analysis.",
                    "parameters": schema
                }
            }
        ]
        tool_choice = {"type": "function", "function": {"name": "analyze_review"}}

        response = call_groq_with_retry(
            self.client,
            self.classifier_model,
            messages,
            tools,
            tool_choice,
            **self._groq_call_kwargs(),
        )

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError("No tool call returned by the model.")

        arguments = tool_calls[0].function.arguments
        return ReviewAnalysis.model_validate_json(arguments)

    def analyze_batch_reviews(self, review_texts: List[str]) -> List[ReviewAnalysis]:
        """Analyzes a list of reviews in a single LLM prompt call."""
        if not review_texts:
            return []

        schema = BatchReviewAnalysis.model_json_schema()
        
        # Format payload
        payload = {
            "reviews": [
                {"index": i, "text": text}
                for i, text in enumerate(review_texts)
            ]
        }
        
        messages = [
            {"role": "system", "content": build_batch_prompt(schema)},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "analyze_review_batch",
                    "description": "Return structured batch review analyses.",
                    "parameters": schema
                }
            }
        ]
        tool_choice = {"type": "function", "function": {"name": "analyze_review_batch"}}

        response = call_groq_with_retry(
            self.client,
            self.classifier_model,
            messages,
            tools,
            tool_choice,
            **self._groq_call_kwargs(),
        )

        tool_calls = response.choices[0].message.tool_calls
        if not tool_calls:
            raise ValueError("No tool call returned by the model.")

        arguments = tool_calls[0].function.arguments
        batch_output = BatchReviewAnalysis.model_validate_json(arguments)
        return batch_output.analyses

    def analyze_gate_batch(self, review_texts: List[str]) -> List[bool]:
        """Strategy 5 gate: cheap yes/no filter before full classification."""
        if not review_texts:
            return []

        schema = GateBatchResult.model_json_schema()
        
        payload = {
            "reviews": [
                {"index": i, "text": text}
                for i, text in enumerate(review_texts)
            ]
        }
        
        messages = [
            {"role": "system", "content": build_gate_prompt()},
            {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}
        ]
        
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "gate_reviews",
                    "description": "Return yes/no gate decisions for each review.",
                    "parameters": schema,
                },
            }
        ]
        tool_choice = {"type": "function", "function": {"name": "gate_reviews"}}

        try:
            response = call_groq_with_retry(
                self.client,
                self.gate_model,
                messages,
                tools,
                tool_choice,
                **self._groq_call_kwargs(),
            )
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                return [True] * len(review_texts)

            result = GateBatchResult.model_validate_json(tool_calls[0].function.arguments)
            if len(result.decisions) != len(review_texts):
                return [True] * len(review_texts)

            return [d == "yes" for d in result.decisions]

        except Exception as e:
            logger.warning(f"Gate analysis failed ({e}). Passing all through.")
            return [True] * len(review_texts)

    def _build_annotated_records(self, df: pd.DataFrame, results: list) -> list:
        annotated_records = []
        for idx, row in df.iterrows():
            record = {
                "db_id": int(row.get("db_id")) if pd.notna(row.get("db_id")) else None,
                "source": str(row.get("source", "")),
                "date": str(row.get("date", "")),
                "title": str(row.get("title", "")) if pd.notna(row.get("title")) else "",
                "text": str(row.get("text", "")),
                "rating": int(row.get("rating")) if pd.notna(row.get("rating")) and row.get("rating") is not None else None,
                "engagement": int(row.get("engagement")) if pd.notna(row.get("engagement")) and row.get("engagement") is not None else None,
            }
            if results[idx] is not None:
                record.update(results[idx])
            else:
                record.update(self._neutral_analysis_dict())
            annotated_records.append(record)
        return annotated_records

    def _save_annotated_json(self, annotated_records: list) -> str:
        processed_dir = self.llm_client.config.get("paths", {}).get("processed_data_dir", "data/processed")
        os.makedirs(processed_dir, exist_ok=True)
        out_path = os.path.join(processed_dir, "annotated_reviews.json")
        
        # Clean any float('nan') or pd.NA values to ensure 100% valid JSON output
        import pandas as pd
        cleaned_records = []
        for r in annotated_records:
            cleaned_r = {}
            for k, v in r.items():
                if pd.isna(v) if isinstance(v, (float, type(pd.NA))) else False:
                    cleaned_r[k] = None
                else:
                    cleaned_r[k] = v
            cleaned_records.append(cleaned_r)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(cleaned_records, f, indent=2, ensure_ascii=False)
        logger.info(f"Annotated reviews exported to: {out_path}")

        # Also copy to frontend/public/ folder to make it accessible to Next.js in fallback dev mode
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        frontend_public = os.path.join(project_root, "frontend", "public")
        if os.path.exists(frontend_public):
            copy_path = os.path.join(frontend_public, "annotated_reviews.json")
            try:
                with open(copy_path, "w", encoding="utf-8") as f:
                    json.dump(cleaned_records, f, indent=2, ensure_ascii=False)
                logger.info(f"Auto-synced annotated reviews to frontend: {copy_path}")
            except Exception as e:
                logger.warning(f"Failed to auto-sync annotated reviews to frontend public folder: {e}")
        return out_path

    def _save_sample_coverage(self, coverage_dict: dict) -> str:
        processed_dir = self.llm_client.config.get("paths", {}).get("processed_data_dir", "data/processed")
        os.makedirs(processed_dir, exist_ok=True)
        out_path = os.path.join(processed_dir, "sample_coverage.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(coverage_dict, f, indent=2, ensure_ascii=False)
        return out_path

    def process_reviews_optimized(
        self,
        df: pd.DataFrame,
        sample_size: int = 500,
        min_floor_sources: List[str] = None,
        gate_enabled: bool = True,
        gate_batch_size: int = 10,
        neon_client: Optional[Any] = None
    ) -> Tuple[pd.DataFrame, Dict]:
        """Optimized Phase 2 pipeline incorporating NeonDB incremental classification and Strategies 1, 4, 5."""
        if min_floor_sources is None:
            min_floor_sources = ["reddit", "product_reviews", "twitter"]

        if df.empty:
            logger.warning("Empty DataFrame passed. Returning empty.")
            return df, {}

        # 1. Incremental classification check:
        # Query NeonDB to see which db_ids are already annotated
        annotated_ids = set()
        if neon_client and neon_client.enabled:
            try:
                with neon_client.conn.cursor() as cur:
                    cur.execute("SELECT review_id FROM annotated_reviews")
                    annotated_ids = {r[0] for r in cur.fetchall()}
                logger.info(f"NeonDB: Found {len(annotated_ids)} already classified reviews.")
            except Exception as e:
                logger.warning(f"Could not read annotated_reviews table: {e}. Running on all items.")
        
        # Filter input reviews to only include those not yet annotated
        if "db_id" in df.columns and annotated_ids:
            df_to_classify = df[~df["db_id"].isin(annotated_ids)].copy().reset_index(drop=True)
            logger.info(f"Incremental Filter: {len(df_to_classify)} of {len(df)} reviews require classification.")
        else:
            df_to_classify = df.copy()

        if df_to_classify.empty:
            logger.info("All reviews in this batch are already annotated. Loading existing annotations from NeonDB...")
            all_records = []
            if neon_client and neon_client.enabled:
                try:
                    db_df = neon_client.get_all_annotated_reviews()
                    if not db_df.empty:
                        rename_map = {
                            "q1_theme": "repeat_purchase_drivers",
                            "q2_theme": "exploration_barriers",
                            "q3_theme": "discovery_methods",
                            "q4_theme": "habit_drivers",
                            "q5_theme": "information_needs",
                            "q6_theme": "frustrations",
                            "q7_theme": "segment_classification",
                            "q8_theme": "unmet_needs"
                        }
                        db_df = db_df.rename(columns=rename_map)
                        all_records = db_df.to_dict(orient="records")
                except Exception as e:
                    logger.warning(f"Could not retrieve all annotated reviews: {e}.")
            
            if all_records:
                self._save_annotated_json(all_records)
                logger.info(f"Loaded {len(all_records)} accumulated reviews from NeonDB.")
            else:
                logger.warning("No existing annotations found in database.")
                
            coverage_data = {"total_reviews": len(df), "sampled_count": 0, "coverage_pct": 100.0}
            self._save_sample_coverage(coverage_data)
            return pd.DataFrame(all_records), coverage_data

        total_to_classify = len(df_to_classify)

        # ── Strategy 4: Stratified Sampling on those needing classification ──
        logger.info(f"[S4] Stratified sampling: target {sample_size} from {total_to_classify} reviews...")
        sampled_df, coverage = stratified_sample(df_to_classify, sample_size, min_floor_sources)
        sampled_df = sampled_df.reset_index(drop=True)
        sampled_count = len(sampled_df)
        logger.info(f"[S4] Sample size: {sampled_count} reviews.")

        results = [None] * sampled_count
        llm_calls_count = 0

        to_classify_indices = list(range(sampled_count))

        gate_passed_indices = []
        gate_rejected_indices = []

        if to_classify_indices:
            # Create sub-dataframe for remaining items
            llm_df = sampled_df.iloc[to_classify_indices].copy().reset_index(drop=True)
            llm_count = len(llm_df)
            llm_results = [None] * llm_count

            if gate_enabled:
                # ── Strategy 5: Two-Stage Gate ──
                logger.info(f"[S5] Gate funnel on {llm_count} reviews in batches of {gate_batch_size}...")
                gate_decisions = []
                for gate_start in range(0, llm_count, gate_batch_size):
                    gate_end = min(gate_start + gate_batch_size, llm_count)
                    gate_chunk_texts = [str(llm_df.iloc[k].get("text", "")).strip() for k in range(gate_start, gate_end)]
                    chunk_decisions = self.analyze_gate_batch(gate_chunk_texts)
                    gate_decisions.extend(chunk_decisions)
                    llm_calls_count += 1
                
                gate_passed_indices = [k for k, d in enumerate(gate_decisions) if d]
                gate_rejected_indices = [k for k, d in enumerate(gate_decisions) if not d]
                
                logger.info(f"[S5] Gate complete: {len(gate_passed_indices)} passed, {len(gate_rejected_indices)} rejected.")
                
                # Auto-label gate-rejected reviews
                for k in gate_rejected_indices:
                    rating = llm_df.iloc[k].get("rating")
                    llm_results[k] = self._fallback_analysis_dict(rating)

                # Full classification for gate-passed reviews
                if gate_passed_indices:
                    pass_texts = [str(llm_df.iloc[k].get("text", "")).strip() for k in gate_passed_indices]
                    tpd_halt = False
                    
                    for chunk_start in range(0, len(gate_passed_indices), self.batch_size):
                        chunk_end = min(chunk_start + self.batch_size, len(gate_passed_indices))
                        chunk_texts = pass_texts[chunk_start:chunk_end]
                        chunk_global_indices = gate_passed_indices[chunk_start:chunk_end]
                        
                        logger.info(f"Classifying {chunk_start + 1}–{chunk_end} of {len(gate_passed_indices)} reviews...")
                        
                        success = False
                        try:
                            batch_analyses = self.analyze_batch_reviews(chunk_texts)
                            llm_calls_count += 1
                            if len(batch_analyses) == len(chunk_texts):
                                for j, analysis in enumerate(batch_analyses):
                                    llm_results[chunk_global_indices[j]] = self._analysis_to_dict(analysis)
                                success = True
                        except GroqTokenDailyLimitError:
                            tpd_halt = True
                            break
                        except Exception as e:
                            logger.warning(f"Batch failed: {e}. Fallback to sequential.")

                        if not success:
                            for j, sub_idx in enumerate(chunk_global_indices):
                                try:
                                    analysis = self.analyze_single_review(chunk_texts[j])
                                    llm_calls_count += 1
                                    llm_results[sub_idx] = self._analysis_to_dict(analysis)
                                except GroqTokenDailyLimitError:
                                    tpd_halt = True
                                    break
                                except Exception:
                                    rating = llm_df.iloc[sub_idx].get("rating")
                                    llm_results[sub_idx] = self._fallback_analysis_dict(rating)
                                    llm_results[sub_idx]["is_db_write_skip"] = True
                        if tpd_halt:
                            break
            else:
                # Gate disabled: classify all remaining directly
                tpd_halt = False
                for chunk_start in range(0, llm_count, self.batch_size):
                    chunk_end = min(chunk_start + self.batch_size, llm_count)
                    chunk_texts = [str(llm_df.iloc[k].get("text", "")).strip() for k in range(chunk_start, chunk_end)]
                    
                    success = False
                    try:
                        batch_analyses = self.analyze_batch_reviews(chunk_texts)
                        llm_calls_count += 1
                        if len(batch_analyses) == len(chunk_texts):
                            for j, analysis in enumerate(batch_analyses):
                                llm_results[chunk_start + j] = self._analysis_to_dict(analysis)
                            success = True
                    except GroqTokenDailyLimitError:
                        tpd_halt = True
                        break
                    except Exception:
                        pass

                    if not success:
                        for j in range(len(chunk_texts)):
                            try:
                                analysis = self.analyze_single_review(chunk_texts[j])
                                llm_calls_count += 1
                                llm_results[chunk_start + j] = self._analysis_to_dict(analysis)
                            except GroqTokenDailyLimitError:
                                tpd_halt = True
                                break
                            except Exception:
                                rating = llm_df.iloc[chunk_start + j].get("rating")
                                llm_results[chunk_start + j] = self._fallback_analysis_dict(rating)
                                llm_results[chunk_start + j]["is_db_write_skip"] = True
                    if tpd_halt:
                        break

            # Map sub-results back to main results array
            for j, main_idx in enumerate(to_classify_indices):
                res = llm_results[j]
                if res is None:
                    rating = sampled_df.iloc[main_idx].get("rating")
                    res = self._fallback_analysis_dict(rating)
                    res["is_db_write_skip"] = True
                results[main_idx] = res

        # Ensure all indices are populated
        for idx in range(sampled_count):
            if results[idx] is None:
                rating = sampled_df.iloc[idx].get("rating")
                results[idx] = self._fallback_analysis_dict(rating)
                results[idx]["is_db_write_skip"] = True

        # Populate coverage statistics
        if gate_enabled and to_classify_indices:
            coverage["gate_passed"] = len(gate_passed_indices)
            coverage["gate_rejected"] = len(gate_rejected_indices)
        else:
            coverage["gate_passed"] = 0
            coverage["gate_rejected"] = 0
            
        coverage["llm_calls_made"] = llm_calls_count
        coverage["llm_calls_saved_vs_full"] = max(0, len(df) - llm_calls_count)

        # ── Persistent Storage: Save to NeonDB annotated_reviews ──
        annotated_records = self._build_annotated_records(sampled_df, results)
        if neon_client and neon_client.enabled:
            db_records = [r for r in annotated_records if not r.get("is_db_write_skip")]
            if db_records:
                logger.info(f"Writing {len(db_records)} successfully classified annotations to NeonDB...")
                try:
                    neon_client.save_annotations(db_records)
                except Exception as db_err:
                    logger.error(f"Failed to write annotations to NeonDB: {db_err}. Proceeding with local checkpoint generation.")
            else:
                logger.info("No successful classifications to write to NeonDB (all were skipped/fallback).")

        # Save to local processed files as checkpoint
        # Retrieve all annotated reviews from NeonDB (including newly classified ones)
        # to build a consolidated analysis set.
        all_records = []
        if neon_client and neon_client.enabled:
            logger.info("Retrieving all annotated reviews from NeonDB to build consolidated dataset...")
            try:
                db_df = neon_client.get_all_annotated_reviews()
                if not db_df.empty:
                    rename_map = {
                        "q1_theme": "repeat_purchase_drivers",
                        "q2_theme": "exploration_barriers",
                        "q3_theme": "discovery_methods",
                        "q4_theme": "habit_drivers",
                        "q5_theme": "information_needs",
                        "q6_theme": "frustrations",
                        "q7_theme": "segment_classification",
                        "q8_theme": "unmet_needs"
                    }
                    db_df = db_df.rename(columns=rename_map)
                    all_records = db_df.to_dict(orient="records")
            except Exception as e:
                logger.warning(f"Could not retrieve all annotated reviews: {e}. Falling back to current run records.")

        if not all_records:
            all_records = annotated_records

        out_path = self._save_annotated_json(all_records)
        self._save_sample_coverage(coverage)

        results_df = pd.DataFrame(results)
        annotated_df = pd.concat([sampled_df.reset_index(drop=True), results_df.reset_index(drop=True)], axis=1)
        return annotated_df, coverage
