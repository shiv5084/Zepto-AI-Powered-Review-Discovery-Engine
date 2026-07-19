# LLM Call Optimization — Phase 2 Review Classification

> **Context:** Phase 2 currently sends every raw review to the Groq LLM for 7-dimension classification
> (sentiment, discovery pain points, recommendation frustrations, listening goals, repeat listening signals,
> unmet needs, segment classification). Even with batch grouping of 5 reviews per call, this produces
> `N / batch_size` LLM calls for N reviews — consuming heavy token quota, adding latency, and risking
> Groq TPD (tokens-per-day) exhaustion on large datasets.
>
> This document drafts **five concrete strategies** to reduce LLM calls while preserving analytical accuracy
> on the dashboard. Strategies are ordered from lowest implementation effort to highest.

---

## Strategy 1 — Rule-Based Pre-Filter (Lowest Effort, Immediate Win)

### Idea
Apply deterministic, keyword + rating based heuristics **before** any review reaches the LLM.
Reviews that are obviously classifiable (e.g., pure praise, pure rage, near-empty text) are assigned
default labels directly, bypassing the LLM entirely.

### Pre-filter Rules

| Condition | Auto-Assigned Labels | LLM Called? |
|---|---|---|
| `len(text.split()) < 8` (very short) | `neutral`, all fields → `None`, `Passive Listener` | ❌ No |
| `rating == 5` AND no negative keywords | `positive`, all pain fields → `None`, `Passive Listener` | ❌ No |
| `rating == 1` AND no positive keywords | `negative`, all pain fields → `None`, `Passive Listener` | ❌ No |
| Pure emoji / gibberish / non-ASCII only | `neutral`, all fields → `None`, `Passive Listener` | ❌ No |
| Duplicate review text (exact match) | Copy label from first occurrence | ❌ No |
| All other reviews | Full 7-dimension LLM classification | ✅ Yes |

### Negative Keywords (for rating-5 bypass check)
`bug, crash, broken, lag, freeze, worst, hate, annoying, ads, slow, doesn't work, fix`

### Positive Keywords (for rating-1 bypass check)
`love, great, perfect, amazing, best, awesome, excellent`

### Expected Impact
- Estimated **25–40% reduction** in LLM calls based on typical app-store review distributions.
- Zero accuracy cost — reviews that are hard-coded are genuinely unambiguous.
- Deduplication alone can reduce calls by ~10–15% on scraped datasets.

### Implementation Notes
- Add a `pre_filter_review(row) -> dict | None` function in `review_processor.py`.
  - Returns a label dict if the review is auto-classifiable, else returns `None`.
- In `process_reviews()`, collect only the `None`-returning reviews into the batch queue for the LLM.
- Save pre-filter stats (how many bypassed, how many sent to LLM) in the checkpoint log.

### Files to Modify
- `src/processing/review_processor.py` — add `pre_filter_review()`, update `process_reviews()`

---

## Strategy 2 — Embedding + Clustering → LLM Labels Only Centroids

### Idea
Instead of classifying every review individually, embed all reviews into vector space, cluster semantically
similar reviews together, and only send **one representative review per cluster** to the LLM.
Every review in the cluster inherits its centroid's label.

### Pipeline

```
Raw Reviews (N)
      │
      ▼
Embed all reviews ──────────────────── sentence-transformers (local, free)
      │                                 model: all-MiniLM-L6-v2 (~80MB)
      ▼
KMeans / HDBSCAN Clustering ─────────  k = sqrt(N) heuristic, or ~30–60 clusters
      │
      ▼
Extract centroid review per cluster ── review closest to cluster center
      │
      ▼
LLM classifies ~30–60 reviews ──────── instead of N reviews
      │
      ▼
Propagate label → all cluster members
      │
      ▼
Annotated reviews (N total, labelled)
```

### Expected Impact
- LLM calls drop from `N / 5` → `k / 5` where `k ≈ 30–60` regardless of N.
- For 1000 reviews at batch_size=5: **200 calls → ~8–12 calls** (94% reduction).
- Aggregate dashboard metrics (percentages, distributions) remain highly accurate.

### Accuracy Tradeoff
- Reviews within a cluster get identical labels — edge-case reviews near cluster boundaries may be
  slightly mis-labelled.
- Acceptable for analytics dashboards (statistical sampling, not per-review accuracy).
- To mitigate: increase `k` for better granularity; use HDBSCAN to let outliers form singleton clusters
  that get individually LLM-classified.

### Dependencies
```
sentence-transformers>=2.2.2
scikit-learn>=1.3.0
```

### Implementation Notes
- New module: `src/processing/embedder.py`
  - `embed_reviews(texts: List[str]) -> np.ndarray`
  - `cluster_reviews(embeddings, k) -> (labels, centroids_idx)`
- In `review_processor.py`: add `process_reviews_with_clustering()` as an opt-in alternative to
  `process_reviews()`.
- Config flag in `config.yaml`: `llm_strategy: "clustering"` vs `"full"`.

### Files to Create / Modify
- `src/processing/embedder.py` — **[NEW]** embedding + clustering logic
- `src/processing/review_processor.py` — add `process_reviews_with_clustering()`
- `config/config.yaml` — add `llm_strategy` flag

---

## Strategy 3 — Train a Lightweight Local Classifier (One-Time LLM Cost)

### Idea
Run the LLM **once** on a carefully sampled set of ~500–1,000 reviews to generate ground-truth labels.
Use those labels to train a local `scikit-learn` or small fine-tuned model. For all **future runs**,
the local model classifies reviews at zero API cost.

### Two-Phase Approach

**Phase A — Ground-Truth Generation (one-time)**
1. Stratified sample: ~200 reviews per star rating (1★–5★), ensuring source balance.
2. Run full LLM classification on this sample → save as `data/training/labelled_sample.json`.
3. This is the only LLM spend — treated as a one-time investment.

**Phase B — Local Model Training**
1. Featurize: TF-IDF on review text + numeric features (rating, text length).
2. Train separate `LogisticRegression` (or `LinearSVC`) per classification dimension
   (7 binary/multi-class classifiers).
3. Evaluate on held-out 20% split; target F1 > 0.75 per class.
4. Serialize models with `joblib` → `models/classifiers/`.

**Phase C — Production Inference**
- All new reviews → local classifiers → labels (no LLM, <1ms per review).
- LLM reserved for: confidence-low reviews, periodic model refresh.

### Expected Impact
- After one-time training cost: **100% LLM call reduction** for all future pipeline runs.
- Inference time: milliseconds for thousands of reviews (vs. minutes for LLM batching).

### Accuracy Tradeoff
- Local models (TF-IDF + LogReg) may struggle on nuanced reviews vs. LLM.
- Mitigation: add a `confidence_threshold` — reviews below threshold fall back to LLM.
- Refresh the training set quarterly as review language evolves.

### Dependencies
```
scikit-learn>=1.3.0
joblib>=1.3.0
```

### Files to Create / Modify
- `src/processing/local_classifier.py` — **[NEW]** train / infer / save / load logic
- `src/script/train_classifier.py` — **[NEW]** one-time training script
- `models/classifiers/` — **[NEW]** serialized model directory
- `data/training/` — **[NEW]** labelled sample storage
- `src/processing/review_processor.py` — add local classifier inference path

---

## Strategy 4 — Stratified Sampling (Quickest Dashboard-Safe Approach)

### Idea
Rather than classifying all N reviews, select a **statistically representative sample** and classify only
that. Dashboard percentages and distributions are estimated from the sample and extrapolated.

### Sampling Design

```
Total reviews: N
Target sample: min(500, N)  ← configurable via config.yaml: sample_size

Stratification axes:
  - Rating:  proportional allocation across 1★ to 5★
  - Source:  proportional allocation across ALL scraped sources (see below)
  - Date:    recency-weighted (reviews from last 3 months weighted 2×)
```

#### Actual Sources in Dataset (from `data/raw/raw_reviews.csv`)

| Source | Raw Count | % of Total | Sampling Approach |
|---|---|---|---|
| `app_store` | 500 | ~46% | Proportional |
| `google_play` | 500 | ~46% | Proportional |
| `reddit` | 25 | ~2.3% | Min-floor guaranteed |
| `product_reviews` | 24 | ~2.2% | Min-floor guaranteed |
| `spotify_community` | 20 | ~1.8% | Min-floor guaranteed |
| `twitter` | 9 | ~0.8% | Take all (too small to subsample) |

> **Min-floor rule:** Minority sources (`reddit`, `product_reviews`, `spotify_community`, `twitter`)
> get a guaranteed minimum of **all available reviews or 10 samples, whichever is smaller**, so they
> are never squeezed out by the proportional allocation. This preserves qualitative signal from
> community/social sources which often carry the highest-signal pain-point language despite low volume.

### Math Justification
A sample of n=500 from a population of N=5000 gives a **±4.4% margin of error** at 95% confidence
(using standard formula: `e = 1.96 * sqrt(0.25 / n)`). For dashboard KPIs (top pain points, segment
splits), this is more than sufficient precision.

### Expected Impact
- For N=2,000 reviews at batch_size=5: **400 calls → 100 calls** (75% reduction).
- The most straightforward to implement — no new dependencies needed.
- Dashboard becomes a "sample-based estimate" — label this clearly in the UI.

### Implementation Notes
- Add `src/processing/sampler.py`:
  - `stratified_sample(df, sample_size, strata_cols) -> pd.DataFrame`
- In `review_processor.py`: add `process_reviews_sampled()` that calls the sampler first.
- Add a `sample_coverage` field to `dashboard_data.json` to show users what % of reviews were analysed.
- Config key: `sampling.enabled: true`, `sampling.sample_size: 500`

### Files to Create / Modify
- `src/processing/sampler.py` — **[NEW]** stratified sampling utility
- `src/processing/review_processor.py` — add `process_reviews_sampled()`
- `config/config.yaml` — add `sampling` section
- `data/dashboard_data.json` schema — add `sample_coverage` field

---

## Strategy 5 — Two-Stage LLM Funnel (Coarse Filter → Full Classification)

### Idea
Split classification into two cheaper sequential LLM stages:

**Stage 1 (Cheap Gate):** A very short, single-question prompt:
> _"Does this review mention any specific product pain point, frustration, or feature need? Answer: yes / no"_

Reviews that answer **"no"** are auto-assigned all-`None` labels + sentiment only (cheap).
Only **"yes"** reviews proceed to Stage 2.

**Stage 2 (Full Classification):** The existing 7-dimension classification — but only for reviews
that passed the gate.

### Token Comparison

| Stage | Prompt tokens (approx.) | Reviews processed |
|---|---|---|
| Stage 1 gate | ~80 tokens/review | All N reviews |
| Stage 2 full | ~350 tokens/review | Only "yes" reviews (~40–60%) |
| **Current (no funnel)** | ~350 tokens/review | All N reviews |

### Expected Impact
- If 40% of reviews pass the gate: token usage drops by **~55%**.
- LLM calls: Stage 1 adds `N/5` cheap calls, Stage 2 reduces to `(0.4*N)/5` full calls.
  Net: **~35–45% fewer total tokens vs. current approach.**

### Implementation Notes
- Add `analyze_gate_batch(review_texts) -> List[bool]` in `review_processor.py`.
- Gate uses a separate lightweight system prompt; can use a smaller/faster Groq model for Stage 1
  (e.g., `llama3-8b-8192` as gate, `llama3-70b-8192` as classifier).
- Two model configs in `config.yaml`: `gate_model` and `classifier_model`.

### Files to Modify
- `src/processing/review_processor.py` — add `analyze_gate_batch()`, update `process_reviews()`
- `config/config.yaml` — add `gate_model` config key

---

## Comparison Summary

| # | Strategy | LLM Call Reduction | Accuracy Impact | Implementation Effort | New Dependencies |
|---|---|---|---|---|---|
| 1 | Rule-Based Pre-Filter | ~25–40% | None | Low | None |
| 2 | Embedding + Clustering | ~90–95% | Low (cluster boundary noise) | Medium | `sentence-transformers`, `scikit-learn` |
| 3 | Local Classifier (post-training) | ~100% (after training) | Medium (nuanced reviews) | High | `scikit-learn`, `joblib` |
| 4 | Stratified Sampling | ~70–80% | Low (sampling error ±4%) | Low | None |
| 5 | Two-Stage Funnel | ~35–45% token reduction | Very Low | Medium | None |

---

## Recommended Combination

For this project's constraints (Groq free tier, TPD limits, dashboard analytics use case):

```
Phase 2 Optimized Pipeline
═══════════════════════════════════════════════════════
Raw Reviews (N)
      │
      ▼
[Strategy 1] Rule-Based Pre-Filter
      ├── Auto-labelled reviews (~30%) ─────────────────► Skip to output
      └── Remaining reviews (~70%) ──────────────────────┐
                                                          ▼
                                              [Strategy 4] Stratified Sample
                                                  └── Sample ~500 reviews
                                                          │
                                                          ▼
                                              [Strategy 5] Two-Stage Funnel
                                                  ├── Gate: yes/no (~80 calls)
                                                  └── Full classify "yes" only (~40–60 calls)
                                                          │
                                                          ▼
                                              Propagate labels → full dataset
═══════════════════════════════════════════════════════
Total estimated LLM calls: ~100–140  (vs. N/5 without optimization)
Token savings: ~85–90% for N=1000 reviews
```

**Future upgrade path:** Once sampling labels are stable, use them as training data for
[Strategy 3] to eliminate LLM dependency entirely for routine runs.

---

## Open Questions / Decisions Needed

1. **Which strategy to implement first?** Recommendation: Strategy 1 + 4 together (lowest risk, fast). ans-4 & 5
2. **Acceptable accuracy tradeoff?** Clustering (Strategy 2) is most efficient but introduces label noise. ans- not now 
3. **Dashboard disclosure:** Should UI show "based on X% sample" when sampling is active? ans -yes 
4. **Model split for Strategy 5?** Use same Groq model for gate and classifier, or use a smaller model for gate to save quota? ans - yes
5. **Training data persistence for Strategy 3:** Where to store `labelled_sample.json` — git-tracked or gitignored? ans - no need 

---

*Document created: 2026-06-19 | Author: AI Optimization Draft | Status: Draft — Pending Review*
