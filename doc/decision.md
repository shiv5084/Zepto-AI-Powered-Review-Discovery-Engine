# Architectural & Business Decisions (decision.md)

This document records the foundational technical and business decisions for the **Zepto AI-Powered Cross-Category Discovery Engine (PRDE)**.

---

## 1. Programming Language & Core Stack
* **Decision**: Python 3.10+
* **Rationale**: Python is the industry standard for LLM integration, data preprocessing, and scripting. It has first-class library support for APIs, databases, and test frameworks (pytest).

---

## 2. LLM Provider & Model-Agnostic Design
* **Decision**: Dual LLM provider configuration via **Groq API** and **Google Gemini API**, structured as fully model-agnostic.
* **Rationale**: 
  - **Model Agnostic**: No model names are hardcoded in python source code or configuration YAML. Models are loaded dynamically from environment variables (`GROQ_CLASSIFIER_MODEL`, `GROQ_GATE_MODEL`, `GEMINI_SUMMARY_MODEL`), allowing instant hot-swapping.
  - **Groq Classifier Model**: Handles high-performance multi-class review tagging and schema-enforcement (using structured JSON outputs).
  - **Groq Gate Model**: A fast, inexpensive model for binary filtering to determine if reviews are product-discovery related before full analysis.
  - **Gemini Summary Model**: Utilizes Google Gemini 2.5 Flash for summarizing long documents and synthesizing the weekly pulse notes.

---

## 3. PII Scrubbing Methodology
* **Decision**: Local Rule-Based Regex Engine ONLY. Remove all Microsoft Presidio dependencies.
* **Rationale**: 
  - Rule-based regex matches for common patterns (emails, IP addresses, phone numbers, social handles) are fast, lightweight, and deterministic.
  - Removing Presidio eliminates heavy library dependencies and potential download/import issues, ensuring a simpler runtime environment.
  - Scrubbing happens *before* any text is saved or sent to LLM APIs, maintaining CCPA/GDPR data compliance.

---

## 4. Theme Discovery & Optimization pipeline
* **Decision**: Two-stage "Map-Reduce" LLM theme discovery combined with rule-based pre-filtering (Strategy 1), stratified sampling (Strategy 4), and binary gating (Strategy 5).
* **Rationale**:
  - **Strategy 1 (Pre-filter)**: Determined auto-classifiable reviews (e.g. extremely short text, simple 5-star or 1-star reviews with no positive/negative contradictions) are labeled automatically to bypass LLMs.
  - **Strategy 4 (Sampling)**: Restricts majority sources (App Store, Google Play) to a statistically representative sample (e.g., 500 reviews) to save token budgets while retaining all minority sources.
  - **Strategy 5 (Gate)**: Employs a binary classifier to screen out unrelated reviews, sending only high-relevance items to the full classification pipeline.

---

## 5. Storage & Database Architecture
* **Decision**: NeonDB PostgreSQL Database for raw and annotated reviews, combined with local CSV/JSON file exports for frontend consumption.
* **Rationale**:
  - Ingested reviews are written to a `raw_reviews` table.
  - Annotated and classified reviews are written to an `annotated_reviews` table.
  - Using a database enables persistent historical metrics and enables incremental runs.
  - Aggregated final metrics are exported as local CSV/JSON files to easily feed the Next.js frontend.

---

## 6. Incremental Classification Logic
* **Decision**: Only new, unclassified reviews are processed on subsequent runs.
* **Rationale**:
  - To prevent re-classifying reviews and wasting token quotas, the processor checks NeonDB for existing annotations.
  - It retrieves only unclassified records (`WHERE annotated_at IS NULL`) for new classification.
  - Aggregation and theme summaries run on the *entire* historical annotated database.

---

## 7. Word Count Enforcement for Pulse Note
* **Decision**: Heuristic formatting prompt combined with programmatic validation and LLM-driven compaction, limited to **≤ 700 words**.
* **Rationale**:
  - The business brief allows up to 700 words.
  - A programmatic check flags any generated pulse note that exceeds 700 words, invoking a secondary compaction step via Gemini to shrink it while retaining the required 9 sections.

---

## 8. Centralized Prompt Management
* **Decision**: Extract all LLM prompt strings into a dedicated folder (`src/prompts/`).
* **Rationale**:
  - Keeping prompts separate from application code prevents pollution of main scripts.
  - Prompts are organized as parameterized Python files, facilitating versioning, updates, and testing.

---

## 9. Premium Web UI
* **Decision**: Responsive Next.js Frontend with dark professional aesthetics and interactive Recharts visualizations.
* **Rationale**:
  - Avoids default styles in favor of a sleek, dark quick-commerce themed design.
  - Renders dashboard components using custom charts (Pie charts for sentiment, Bar charts for themes/unmet needs, and Radar charts for user segments) to provide premium product analytics.
