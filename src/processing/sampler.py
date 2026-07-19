"""
sampler.py — Strategy 4: Stratified Sampling for Phase 2 LLM Optimization

Selects a statistically representative sample of reviews to send to the LLM,
reducing API calls while preserving coverage across all sources and rating bands.

Sampling rules:
- Minority sources (reddit, spotify_community, twitter, product_reviews) are
  fully included via a min-floor guarantee — they are too small to sub-sample
  and carry high-signal language (feature requests, pain points).
- Majority sources (app_store, google_play) are proportionally allocated the
  remaining budget, then further stratified by star rating (1–5★) to ensure
  the sample mirrors the true rating distribution.
- Reviews with no rating are handled as a separate "unrated" group within each
  majority source.
- random_state=42 is used for reproducibility: the same sample is chosen every run.
"""

import logging
import pandas as pd
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)

_DEFAULT_MIN_FLOOR_SOURCES = [
    "reddit",
    "product_reviews",
    "twitter",
]


def stratified_sample(
    df: pd.DataFrame,
    sample_size: int = 500,
    min_floor_sources: List[str] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Return a stratified sample from df and a coverage metadata dict.

    Parameters
    ----------
    df : pd.DataFrame
        Full reviews DataFrame (output of Phase 1).
    sample_size : int
        Maximum number of reviews to include in the sample.
    min_floor_sources : List[str]
        Source values whose reviews are always fully included regardless of budget.

    Returns
    -------
    sampled_df : pd.DataFrame
        The selected sample with reset index.
    coverage : dict
        Metadata about sampling coverage for dashboard disclosure.
        Keys: total_reviews, sampled_count, coverage_pct, per_source.
        Gate-related keys (gate_passed, gate_rejected, llm_calls_made,
        llm_calls_saved_vs_full) are initialized to None and filled later
        by ReviewProcessor after the gate pass.
    """
    if min_floor_sources is None:
        min_floor_sources = _DEFAULT_MIN_FLOOR_SOURCES

    df = df.copy().reset_index(drop=True)
    total = len(df)

    if total == 0:
        logger.warning("Empty DataFrame passed to stratified_sample.")
        return df, _empty_coverage()

    # ── Step 1: Separate minority (min-floor) and majority sources ────────────
    min_floor_mask = df["source"].isin(min_floor_sources)
    minority_df = df[min_floor_mask].copy()
    majority_df = df[~min_floor_mask].copy()

    minority_count = len(minority_df)
    remaining_budget = max(0, sample_size - minority_count)

    logger.info(
        f"Sampler: {total} total reviews | "
        f"minority (min-floor) = {minority_count} | "
        f"majority pool = {len(majority_df)} | "
        f"remaining budget = {remaining_budget}"
    )

    # ── Step 2: Proportional + rating-stratified sampling from majority ───────
    sampled_majority_parts: List[pd.DataFrame] = []

    if remaining_budget > 0 and not majority_df.empty:
        total_majority = len(majority_df)

        for source, source_group in majority_df.groupby("source", sort=False):
            # Proportional budget for this source
            source_budget = round(remaining_budget * len(source_group) / total_majority)
            source_budget = min(source_budget, len(source_group))

            if source_budget <= 0:
                continue

            sampled_source = _sample_with_rating_strata(
                source_group, source_budget, source=source
            )
            sampled_majority_parts.append(sampled_source)

    # ── Step 3: Combine minority + sampled majority ───────────────────────────
    parts: List[pd.DataFrame] = [minority_df]
    if sampled_majority_parts:
        parts.extend(sampled_majority_parts)

    sampled_df = (
        pd.concat(parts, ignore_index=True)
        .drop_duplicates(subset=["text"], keep="first")
        .reset_index(drop=True)
    )

    # ── Step 4: Build coverage metadata ──────────────────────────────────────
    per_source: Dict[str, Dict[str, int]] = {}
    for src in sorted(df["source"].unique()):
        per_source[src] = {
            "total": int((df["source"] == src).sum()),
            "sampled": int((sampled_df["source"] == src).sum()),
        }

    sampled_count = len(sampled_df)
    coverage: Dict[str, Any] = {
        "total_reviews": total,
        "sampled_count": sampled_count,
        "coverage_pct": round(sampled_count / total * 100, 1) if total > 0 else 0.0,
        # Gate fields — populated later by ReviewProcessor
        "gate_passed": None,
        "gate_rejected": None,
        "llm_calls_made": None,
        "llm_calls_saved_vs_full": None,
        "per_source": per_source,
    }

    logger.info(
        f"Stratified sample selected: {sampled_count}/{total} reviews "
        f"({coverage['coverage_pct']}% coverage). "
        f"Per-source: { {s: v['sampled'] for s, v in per_source.items()} }"
    )

    return sampled_df, coverage


# ── Internal helpers ──────────────────────────────────────────────────────────

def _sample_with_rating_strata(
    group: pd.DataFrame,
    budget: int,
    source: str = "",
) -> pd.DataFrame:
    """
    Within a single source group, allocate `budget` slots proportionally
    across star-rating bands (1–5★) plus an 'unrated' band for NaN ratings.
    """
    if budget >= len(group):
        # Budget covers everything — take all
        return group.copy()

    # Split rated vs unrated
    rated_mask = group["rating"].notna()
    rated = group[rated_mask]
    unrated = group[~rated_mask]

    total_group = len(group)
    parts: List[pd.DataFrame] = []
    allocated = 0

    # Allocate budget proportionally between rated and unrated
    rated_budget = round(budget * len(rated) / total_group) if total_group > 0 else 0
    unrated_budget = budget - rated_budget

    # Sample unrated as its own group
    if unrated_budget > 0 and len(unrated) > 0:
        n = min(unrated_budget, len(unrated))
        parts.append(unrated.sample(n=n, random_state=42))
        allocated += n

    # Stratify rated by star rating
    remaining = budget - allocated
    if remaining > 0 and not rated.empty:
        total_rated = len(rated)
        already_used_idx: set = set()
        for rt, rt_group in rated.groupby("rating", sort=True):
            rt_budget = round(remaining * len(rt_group) / total_rated)
            rt_budget = min(rt_budget, len(rt_group))
            if rt_budget > 0:
                sampled_rt = rt_group.sample(n=rt_budget, random_state=42)
                parts.append(sampled_rt)
                already_used_idx.update(sampled_rt.index.tolist())

        # Top-up: fill any leftover slots due to rounding
        current_total = sum(len(p) for p in parts)
        leftover_budget = budget - current_total
        if leftover_budget > 0:
            leftover_pool = rated[~rated.index.isin(already_used_idx)]
            n = min(leftover_budget, len(leftover_pool))
            if n > 0:
                parts.append(leftover_pool.sample(n=n, random_state=42))

    if not parts:
        # Fallback: plain random sample
        logger.warning(
            f"Sampler: rating stratification yielded no parts for source={source!r}. "
            "Falling back to plain random sample."
        )
        return group.sample(n=min(budget, len(group)), random_state=42)

    return pd.concat(parts, ignore_index=True)


def _empty_coverage() -> Dict[str, Any]:
    return {
        "total_reviews": 0,
        "sampled_count": 0,
        "coverage_pct": 0.0,
        "gate_passed": None,
        "gate_rejected": None,
        "llm_calls_made": None,
        "llm_calls_saved_vs_full": None,
        "per_source": {},
    }
