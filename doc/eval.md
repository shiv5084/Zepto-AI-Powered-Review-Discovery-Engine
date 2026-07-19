# Phase-Wise Testing & Exit Criteria (eval.md)

This document aggregates the testing strategies, test cases, and quality gates required to verify and sign off on each phase of the **Zepto AI-Powered Cross-Category Discovery Engine (PRDE)**.

---

## Phase 0: Project Scaffold & Environment Setup

### 1. Test Strategy
Testing focuses on verifying environment consistency, database configuration, model-agnostic variables, prompts structure, and API registration.

### 2. Test Cases & Verification Steps
#### Test Case 0.1: Dependency Resolution & Import Checks
* **Goal**: Validate that all packages specified in `requirements.txt` are installed (including `psycopg2` and `google-generativeai`) and that no references to `presidio-analyzer` or `presidio-anonymizer` exist.
* **Verification**: Run `pytest tests/test_scaffold.py` asserting success for imports of `groq`, `google.generativeai`, `pydantic`, `pandas`, `yaml`, `dotenv`, and `psycopg2`.

#### Test Case 0.2: Config Schema Parsing
* **Goal**: Validate that `config.yaml` is formatted correctly, contains no hardcoded model names, and is readable by Python.
* **Verification**: Ensure system paths, rate limit parameters, and sampling parameters load correctly.

#### Test Case 0.3: Secure Environment & Model-Agnostic Setup
* **Goal**: Confirm that environment variables are loaded securely from `.env` and all required model name variables are defined.
* **Verification**: Assert that `GROQ_CLASSIFIER_MODEL`, `GROQ_GATE_MODEL`, and `GEMINI_SUMMARY_MODEL` are present and non-empty. Assert that if any of these are missing, initialization raises an exception.

#### Test Case 0.4: Database Connectivity
* **Goal**: Confirm connection to NeonDB PostgreSQL and verify table creation statements.
* **Verification**: Connect via `psycopg2` using `NEON_DATABASE_URL`, execute a test query, and confirm tables `raw_reviews` and `annotated_reviews` exist or can be created.

### 3. Exit Criteria & Quality Gates
- **Module Readiness**: 100% of defined third-party packages import successfully in Python. No Presidio dependencies present.
- **Credential Safety**: `.env` is listed in `.gitignore` and successfully loaded.
- **Model Configs**: Correct model keys parsed without defaults.
- **Database Status**: NeonDB connection is active and tables are prepared.

---

## Phase 1: Ingestion & PII Scrubbing

### 1. Test Strategy
Testing verifies review scraping from Zepto-specific sources, regex-only PII masking, deduplication, and database insertion.

### 2. Test Cases & Verification Steps
#### Test Case 1.1: Schema Normalization & DB Insertion
* **Goal**: Verify that reviews from App Store (ID `1575323645`), Google Play (`com.zeptoconsumerapp`), Reddit (`r/zepto`, `r/quickcommerce`), and X (`ZeptoNow`) standardise to unified columns and are stored correctly in NeonDB.
* **Expected Result**: 
  - Fields map to `source`, `date`, `title`, `text`, `rating`, `engagement`.
  - Database records are created with a unique `text_hash` constraint.
  - Re-ingesting duplicate text raises no error but skips duplicates (database deduplication).

#### Test Case 1.2: PII Scrubbing Accuracy (Regex-Only)
* **Goal**: Validate that sensitive user information is stripped locally prior to storage without using Presidio.
* **Input**: Test reviews containing email addresses, IP addresses, phone numbers, and social handles.
* **Expected Result**: Verify outputs replace targets with `[EMAIL]`, `[IP_ADDRESS]`, `[PHONE_NUMBER]`, and `[USER_HANDLE]`.

### 3. Exit Criteria & Quality Gates
- **PII Leakage**: **0% leakage** of seeded regex PII.
- **Schema Compliance**: **100% of reviews** match the columns in NeonDB.
- **Scraper Completeness**: Scrapers run successfully for Zepto App ID, Android package, subreddits, and Trustpilot.

### Performance Metrics

| Metric | Target | Notes |
|---|---|---|
| Google Play Store scrape (`com.zeptoconsumerapp`, 1000 reviews) | < 120s | `google-play-scraper` library, `Sort.NEWEST`, count=1000 |
| Apple App Store scrape (RSS JSON, up to 500 reviews) | < 60s | 10 pages × 50 reviews, paginated RSS/JSON via `itunes.apple.com` |
| Reddit Discussions (`r/zepto` + `r/quickcommerce`, ~20–50 posts) | < 30s | JSON API with RSS fallback; 2 subreddits |
| Quick-Commerce Forums (Trustpilot forum-mode, ~10–20 reviews) | < 45s | Playwright-based; `ZEPTO_TRUSTPILOT_URL` |
| X / Twitter (`@ZeptoNow`, ~10–15 tweets) | < 45s | Playwright-based; anti-bot scrolling |
| Trustpilot Product Reviews (`zepto.com`, ~10–20 reviews) | < 45s | Playwright-based; blog fallback if empty |
| **Combined Raw reviews** | **≥ 1000 reviews** | Sum of all 6 channels before dedup |
| Deduplication rate (NeonDB `text_hash`) | ≤ 15% duplicate removal | Measured across incremental runs |
| **Cleaned & Processed reviews** | **≥ 800 reviews** | After emoji strip, sentence-length filter, spam removal, PII scrub |
| PII Regex scrub latency (per review) | < 5ms | Email, phone, IP, username patterns |
| NeonDB `raw_reviews` bulk insert | < 10s for 1000 rows | `text_hash` UNIQUE constraint for dedup |
| Schema compliance (processed CSV) | 100% | All 7 columns: `db_id`, `source`, `date`, `title`, `text`, `rating`, `engagement` |



---

## Phase 2: Theme Extraction & Metric Parsing (LLM-Powered)

### 1. Test Strategy
Testing focuses on Pydantic structured output mapping for 8 business questions, Strategy 1 (Pre-filter), Strategy 5 (Gate funnel), and incremental classification logic.

### 2. Test Cases & Verification Steps
#### Test Case 2.1: Pre-filter Bypass Rules (Strategy 1)
* **Goal**: Confirm that simple/short reviews bypass the LLM entirely and are assigned default tags.
* **Expected Result**:
  - Reviews with < 8 words auto-tag as all-`None` and `Routine Replenishers`.
  - Unambiguous 1★/5★ reviews auto-tag without executing LLM calls.

#### Test Case 2.2: Product Discovery Gate (Strategy 5)
* **Goal**: Verify that reviews undergo the binary relevance gate (`is_product_discovery_related: true/false`).
* **Expected Result**:
  - Reviews about delivery delays with no category browsing mention tag as `false`.
  - Only `true` reviews undergo full theme extraction.

#### Test Case 2.3: Incremental Classification Logic
* **Goal**: Ensure only new reviews are classified, while already annotated reviews are skipped.
* **Verification**:
  - Run pipeline on 50 reviews → check DB for 50 entries with `annotated_at IS NOT NULL`.
  - Add 10 new reviews → re-run pipeline → verify LLM is only called 10 times.

#### Test Case 2.4: Prompts Centralization Check
* **Goal**: Ensure no hardcoded prompt strings exist in processing files.
* **Verification**: Confirm `review_processor.py` imports all prompts from `src/prompts/`.

### 3. Exit Criteria & Quality Gates
- **JSON Schema Pass Rate**: 100% Pydantic validation checks on 10 runs using the model set in `.env`.
- **Incremental Accuracy**: 0 redundant LLM calls on previously classified database rows.

---

## Phase 3: Analytical Theme Discovery & Cluster Analysis

### 1. Test Strategy
Verify theme registries, metrics, Opportunity Score math (using Count), and underserved segments calculations.

### 2. Test Cases & Verification Steps
#### Test Case 3.1: Theme Registries Verification
* **Goal**: Assert that discovered themes correspond to the 8 quick-commerce registries.
* **Verification**: Confirm counts map to predefined categories such as `Habit & Routine Lock-in`, `Poor Category Visibility`, etc.

#### Test Case 3.2: Math & Score Logic
* **Goal**: Validate custom metric calculations.
* **Expected Result**:
  - No `frequency` field is present in theme outputs.
  - Q6 frustrations include a string `root_cause` field.
  - Q7 underserved segments include `% Sample` and `% Negative Reviews`.
  - Q8 Opportunity Score mathematically evaluates as `Count × (6 − Average Rating)`.

### 3. Exit Criteria & Quality Gates
- **No Frequency Leakage**: All aggregated outputs omit frequency metrics.
- **Root-Cause Presence**: 100% of Q6 themes include a root cause.
- **Mathematical Integrity**: 100% accuracy of Opportunity Score sorting.

---

## Phase 4: Pulse Note Generation & JSON Export

### 1. Test Strategy
Verify pulse note length, 9 sections, Gemini summarization execution, and final JSON schema validation.

### 2. Test Cases & Verification Steps
#### Test Case 4.1: Pulse Note Word Count Enforcement
* **Goal**: Ensure note is ≤ 700 words.
* **Verification**: Test compaction step. If Gemini note exceeds 700 words, verify programmatic truncation/compaction reduces it below 700.

#### Test Case 4.2: Structured Content Verification
* **Goal**: Confirm the pulse note contains all 9 required sections.

#### Test Case 4.3: JSON Schema Validation
* **Goal**: Validate JSON export matches the updated schema.
* **Verification**: Assert presence of `sentiment_distribution`, `total_reviews_analyzed`, and `product_discovery_relevant_reviews`.

### 3. Exit Criteria & Quality Gates
- **Word Count**: Programmatic note length ≤ 700 words.
- **Section Presence**: 100% of the 9 quick-commerce summary sections are present.
- **JSON Validation**: Output validates against the Next.js frontend contract.
