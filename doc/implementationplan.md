# Zepto PRDE — Implementation Plan (implementationplan.md)

This implementation plan outlines the development path for the **Zepto AI-Powered Cross-Category Discovery Engine (PRDE)**. The work is split into modular phases to migrate the system from Spotify to Zepto, integrating NeonDB database persistent storage, model-agnostic environment loading, LLM call optimizations, and a Next.js premium frontend.

---

## 1. Project Directory Structure Map

The project structure will look as follows:

```
Zepto-AI-Powered Review Discovery Engine/
├── data/
│   ├── raw/                  # Raw, unscrubbed scraper outputs (CSV)
│   └── processed/            # Cleaned, PII-scrubbed, normalized CSVs
├── doc/
│   ├── problemStatement_new.md # Requirements and predefined themes
│   ├── implementationplan.md   # This document
│   ├── decision.md             # Architectural decisions
│   ├── eval.md                 # Phase-wise testing & exit criteria
│   └── llm_optimization.md    # LLM optimization strategies
├── src/
│   ├── __init__.py
│   ├── db/                   # [NEW] Database Access Layer
│   │   ├── __init__.py
│   │   └── neon_client.py    # NeonDB PostgreSQL connector
│   ├── ingestion/            # Phase 1: Data scraping & normalization
│   │   ├── __init__.py
│   │   ├── scrapers.py       # Scrapers for App Store, Play Store, Reddit, Twitter, Trustpilot
│   │   ├── pii_scrubber.py   # Regex-only PII scrubber (no Presidio)
│   │   └── ingestor.py       # Ingestion runner & NeonDB raw store
│   ├── prompts/              # [NEW] Centralized Prompt Templates Folder
│   │   ├── __init__.py
│   │   ├── classifier_system.py
│   │   ├── gate_system.py
│   │   ├── batch_system.py
│   │   ├── pulse_note.py
│   │   └── root_cause.py
│   ├── processing/           # Phase 2: Core LLM sentiment & metric extractor
│   │   ├── __init__.py
│   │   ├── llm_client.py     # Model-agnostic Groq + Gemini client initializer
│   │   ├── review_processor.py # Classifier with Pre-filter, Gate, and Incremental Logic
│   │   └── sampler.py        # Stratified sampling (Strategy 4)
│   ├── analysis/             # Phase 3: Theme clustering
│   │   ├── __init__.py
│   │   └── theme_discoverer.py # Quick-commerce aggregation logic
│   ├── reporting/            # Phase 4: Executive Pulse Note & JSON export
│   │   ├── __init__.py
│   │   ├── pulse_generator.py # ≤ 700-word Gemini pulse note generator
│   │   └── json_exporter.py   # Dashboard JSON exporter
│   ├── server.py             # FastAPI backend
│   └── main.py               # E2E pipeline orchestrator
├── frontend/                 # Premium React/Next.js dashboard (TypeScript, Recharts)
├── tests/                    # E2E and Unit Tests
├── config.yaml               # Ingestion & pipeline settings
├── requirements.txt          # Python dependencies
└── .env / .env.template      # Credentials & model settings
```

---

## Phase 0: Project Scaffold & Environment Setup

### Objectives & Scope
- Establish database connection pools and schemas in NeonDB.
- Set up model-agnostic variables in `.env` (`GROQ_CLASSIFIER_MODEL`, `GROQ_GATE_MODEL`, `GEMINI_SUMMARY_MODEL`).
- Ensure no dependency on `presidio-analyzer` or `presidio-anonymizer` exists.
- Establish the `src/prompts/` directory to centralize LLM prompts.

---

## Phase 1: Ingestion Pipeline & PII Scrubbing

### Objectives & Scope
- **Scraper Targets**:
  - **Google Play Store**: `com.zeptoconsumerapp` (using `google-play-scraper`).
  - **Apple App Store**: RSS JSON feed for ID `1575323645`.
  - **Reddit**: `r/zepto`, `r/quickcommerce`.
  - **X (Twitter)**: Handle `ZeptoNow` via Playwright search scraper.
  - **Product Review Site**: Trustpilot Zepto review page.
- **PII Scrubbing**: Regex-only local anonymization (emails, IPs, phone numbers, handles).
- **Persistent Storage**: Write raw reviews to NeonDB `raw_reviews` table using `text_hash` to skip duplicates.

---

## Phase 2: Theme Extraction & Metric Parsing (LLM-Powered)

### Objectives & Scope
- **Incremental logic**: Read from NeonDB and only process reviews `WHERE annotated_at IS NULL`.
- **Pre-filtering (Strategy 1)**: Reviews containing < 8 words or clear 1★/5★ ratings without conflicting words bypass the LLM and are annotated automatically.
- **Stratified Sampling (Strategy 4)**: Sample majority sources to a representative budget (e.g. 500 reviews) while preserving all minority source reviews.
- **Two-Stage Gate (Strategy 5)**: First pass reviews through the fast gate model to filter out non-discovery related comments. Remaining records undergo full 8-question classification using the classifier model.
- **Prompts Extraction**: Pull prompts from `src/prompts/` folder.

---

## Phase 3: Analytical Theme Aggregation

### Objectives & Scope
- Group reviews by the 8 quick-commerce question theme registries.
- **Metrics Rules**:
  - Omit all `frequency` fields.
  - Compute counts only.
  - Q6 frustrations include a `root_cause` explaining the systemic reason.
  - Q7 underserved segments include `% Sample` and `% Negative Reviews` (using all Q2 pain points).
  - Q8 Opportunity Score equals `Count × (6 − Average Rating)`.
  - Generate a global `sentiment_distribution` containing counts and percentages of positive, neutral, and negative reviews.

---

## Phase 4: Pulse Note Generation & JSON Export

### Objectives & Scope
- **Executive Pulse Note**: Summarize 9 sections in **≤ 700 words** using Gemini. Programmatic compaction rewrites the note if it exceeds the limit.
- **JSON Export**: Output `dashboard_data.json` matching the new count-based dashboard schema.

---

## Phase 5: Web UI Dashboard

### Objectives & Scope
- Build a premium Next.js dashboard inspired by modern analytical applications.
- Incorporate **lucid Recharts visualizations**:
  - Pie/Donut charts for global sentiment distribution.
  - Horizontal Bar charts for the 8 theme count metrics.
  - Radar charts/Bar charts for underserved user segments.
- Complete dark professional UI layout with CSS Modules (no Tailwind).

---

## Phase 6: E2E Pipeline, Evaluation, Performance & Guardrails

### Objectives & Scope
- Wire all pipeline stages into `main.py` as a single E2E orchestrator supporting **incremental classification**.
- Establish evaluation criteria, performance benchmarks, and operational guardrails to ensure production-grade reliability.
- Define edge-case handling for every external dependency (NeonDB, Groq, Gemini, scrapers).

---

### 6.1 E2E Pipeline Orchestration (`main.py`)

The full pipeline follows two execution modes:

**Run 1 (Cold Start):**
```
Scrape → NeonDB insert → Classify ALL → NeonDB annotate → Aggregate → Report → Dashboard JSON
```

**Run 2+ (Incremental):**
```
Scrape → NeonDB insert (dedup by text_hash)
       → Query unclassified reviews (annotated_at IS NULL)
       → Classify ONLY new reviews via Strategy 1+4+5 pipeline
       → NeonDB annotate new reviews
       → Aggregate ALL annotated reviews (old + new)
       → Report → Dashboard JSON
```

- Initialize both `GroqClient` (classifier + gate) and `GeminiClient` (summarization) at startup.
- NeonDB store step after each phase for persistence and crash recovery.
- If 0 new unclassified reviews exist, skip classification entirely and re-aggregate existing annotations.

---

### 6.2 LLM Optimization Pipeline (Strategy 1 + 4 + 5)

```
Processed Reviews (N)
      │
      ▼
[Strategy 1] Rule-Based Pre-Filter
      ├── Auto-labelled reviews (~30%) ──────────────► Skip to output
      └── Remaining reviews (~70%) ──────────────────┐
                                                      ▼
                                          [Strategy 4] Stratified Sample
                                              └── Sample ~500 reviews
                                                      │
                                                      ▼
                                          [Strategy 5] Two-Stage Gate Funnel
                                              ├── Gate (cheap model): is_product_discovery_related yes/no
                                              └── Full classify "yes" only (classifier model)
                                                      │
                                                      ▼
                                          Annotated Reviews → NeonDB
```

---

### 6.3 Evaluation Criteria

#### Classification Quality

| Metric | Target | Measurement |
|---|---|---|
| Pydantic schema validation rate | 100% | All LLM outputs must pass `ReviewAnalysis.model_validate_json()` |
| Product discovery gate accuracy | ≥ 85% precision | Validated against gold-standard review set |
| Sentiment classification accuracy | ≥ 90% | Cross-checked against star rating heuristic |
| Theme assignment consistency | ≥ 80% | Same review → same theme on re-run (with temperature 0.1) |
| Incremental classification correctness | 0 redundant LLM calls | No review with `annotated_at IS NOT NULL` re-enters the LLM pipeline |

#### Aggregation Quality

| Metric | Target | Measurement |
|---|---|---|
| Q6 Root-cause presence | 100% of frustration themes | Every Q6 theme entry includes a non-empty `root_cause` string |
| Q7 `% Sample` math | Sum of all segment `pct_sample` = 1.0 | Verified programmatically |
| Q7 `% Negative Reviews` range | 0.0 ≤ value ≤ 1.0 | Validated per segment |
| Q8 Opportunity Score formula | `Count × (6 − Average Rating)` | Verified against manual calculation on test data |
| Frequency field leakage | 0 occurrences | No `frequency` key in any theme output |
| Global sentiment distribution | Sum of counts = total classified reviews | `positive_count + neutral_count + negative_count = total` |

#### Report Quality

| Metric | Target | Measurement |
|---|---|---|
| Pulse note word count | ≤ 700 words | Programmatic count; Gemini compaction if exceeded |
| Pulse note section count | 9 sections present | Repeat-Purchasing, Exploration Barriers, Discovery Methods, Habit Drivers, Information Needs, Frustrations, Underserved Segments, Unmet Needs, Product Opportunities |
| JSON schema validation | 100% pass rate | Dashboard JSON matches `problemStatement_new.md` example schema |

---

### 6.4 Performance Benchmarks

| Pipeline Stage | Target | Notes |
|---|---|---|
| Full ingestion (6 channels) | < 5 min | Google Play + App Store + Reddit + Forums + Twitter + Trustpilot |
| NeonDB raw insert (1000 rows) | < 10s | Bulk upsert with `text_hash` UNIQUE constraint |
| Strategy 1 pre-filter pass | < 2s for 1000 reviews | Local regex + word-count check, no LLM |
| Strategy 4 stratified sampling | < 1s | In-memory pandas sampling |
| Strategy 5 gate pass (500 reviews) | < 90s | Cheap gate model (`llama-3.1-8b-instant`), batch_size=10 |
| Full classification (350 gated reviews) | < 300s | Classifier model (`gpt-oss-120b`), batch_size=5, TPM=8K |
| Theme aggregation (8 questions) | < 5s | Local Python computation, no LLM |
| Gemini pulse note generation | < 30s | Single Gemini API call |
| JSON export + frontend sync | < 2s | File write + optional copy to `frontend/public/` |
| **Total E2E pipeline** | **< 10 min** | Cold start; incremental runs < 5 min |

#### LLM Budget Constraints

| Constraint | Limit | Handling |
|---|---|---|
| Groq Tokens Per Day (TPD) | 200,000 | Track cumulative usage; stop classification if exhausted |
| Groq Tokens Per Minute (TPM) | 8,000 | Rate-limiter with exponential backoff (5s → 120s) |
| Gemini API | Standard free-tier | Single summarization call per run; retry once on failure |

---

### 6.5 Guardrails & Edge Cases

| # | Edge Case | Guardrail |
|---|---|---|
| 1 | **NeonDB connection failure** | Fallback to local CSV pipeline; log warning; pipeline continues without persistent storage |
| 2 | **Groq TPD exhausted (200K tokens)** | Catch `GroqTokenDailyLimitError`; save partial annotations; log remaining unclassified count |
| 3 | **Groq TPM throttling (8K)** | Reduce batch size from 5 → 2; increase inter-request delay to 5s; exponential backoff up to 120s |
| 4 | **Gemini API failure** | Fallback to Groq classifier model for summarization; log degradation warning |
| 5 | **All reviews = `is_product_discovery_related: false`** | Use all reviews with a disclaimer flag in the pulse note; log warning |
| 6 | **Zero new unclassified reviews on Run 2+** | Skip classification; re-aggregate existing NeonDB annotations; log info |
| 7 | **Model env var missing** | `KeyError` raised at startup with clear message: `"Set GROQ_CLASSIFIER_MODEL in .env"` |
| 8 | **Root cause LLM generation failure (Q6)** | Default to `"Root cause analysis unavailable"` |
| 9 | **NeonDB tables don't exist** | `CREATE TABLE IF NOT EXISTS` auto-executed on first connect |
| 10 | **Empty theme after product-discovery gate** | Show `"Insufficient data"` placeholder in dashboard card |
| 11 | **Pre-filter classifies > 60% of reviews** | Log warning; pipeline continues but flags potential over-filtering |
| 12 | **Very long reviews exceed token limits** | Truncate review text to 1500 characters before LLM call |
| 13 | **Duplicate reviews across scraper runs** | `text_hash` UNIQUE constraint in NeonDB prevents double-insert silently |
| 14 | **LLM returns invalid Pydantic schema** | Retry once; if still invalid, skip review and mark `is_db_write_skip = True` (not saved to DB) |
| 15 | **Pulse note exceeds 700 words after Gemini** | Programmatic truncation to 690 words with `"... (Truncated)"` suffix |
| 16 | **Scraper returns 0 reviews from a channel** | Log warning per channel; pipeline continues with remaining channels |

---

### 6.6 CI/CD Verification (GitHub Actions)

The weekly pipeline (`.github/workflows/weekly_pipeline.yml`) validates:

1. **Credentials check**: Verify `GROQ_API_KEY`, `GEMINI_API_KEY`, and `NEON_DATABASE_URL` secrets are non-empty.
2. **Unit test gate**: Run `pytest tests/` — all 23+ tests must pass before pipeline execution.
3. **Schema validation**: Post-pipeline JSON output must contain:
   - `week_ending`, `pulse_note_text`, `total_reviews_analyzed`, `product_discovery_relevant_reviews`
   - `sentiment_distribution` with `positive_count`, `neutral_count`, `negative_count`
   - `metrics` with all 8 sections + `opportunities`
4. **Word count enforcement**: Pulse note must be ≤ 700 words.

### 6.7 Exit Criteria & Quality Gates

- **E2E Success**: Pipeline runs end-to-end without unhandled exceptions on both cold start and incremental modes.
- **Data Integrity**: All annotated reviews in NeonDB have `annotated_at IS NOT NULL` and valid theme assignments.
- **Zero PII Leakage**: No raw usernames, emails, IPs, or handles present in processed output files.
- **Schema Compliance**: 100% of JSON exports validate against the `problemStatement_new.md` schema.
- **Performance**: Total E2E pipeline completes within 10 minutes on standard hardware.
- **Guardrail Coverage**: Every edge case in the table above has a corresponding code path (verified by unit tests or integration tests).
