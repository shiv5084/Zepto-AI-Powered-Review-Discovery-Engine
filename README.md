# ⚡ Zepto AI-Powered Cross-Category Discovery Engine (PRDE)

An end-to-end AI-powered product analytics pipeline that ingests multi-source Zepto user reviews, scrubs PII locally, annotates feedback via a Groq-hosted LLM (with model agnostic configs), stores data persistently in NeonDB (PostgreSQL) using incremental classification, aggregates cross-category insights, and generates executive weekly pulse notes via Google Gemini 2.5 Flash + a synchronized JSON dashboard. The application features a responsive Next.js frontend with premium analytics visualisations and a FastAPI backend with real-time log streaming over Server-Sent Events (SSE).

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=nextdotjs)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![NeonDB](https://img.shields.io/badge/Database-NeonDB%20Postgres-blue?logo=postgresql)](https://neon.tech/)

---

## 📋 Table of Contents

1. [System Overview & Architecture](#-system-overview--architecture)
2. [E2E Pipeline Workflow](#-e2e-pipeline-workflow)
3. [Phase-by-Phase Breakdown](#-phase-by-phase-breakdown)
4. [Directory Structure](#-directory-structure)
5. [Prerequisites](#-prerequisites)
6. [Setup & Installation](#-setup--installation)
7. [Running the Pipeline](#-running-the-pipeline)
8. [Testing Suite](#-testing-suite)
9. [Web UI: Run, Observe & Analyze](#-web-ui-run-observe--analyze)
10. [Key Design Decisions](#-key-design-decisions)
11. [Known Limitations](#-known-limitations)

---

## 🏗️ System Overview & Architecture

The project is organized into two primary blocks: the **Core Data Pipeline** (Python backend with NeonDB database storage + FastAPI server) and the **Executive Web Dashboard** (Next.js App Router). The pipeline is split into modular phases that run, test, and verify operations.

```mermaid
graph TD
    %% Phase 1: Source Ingestion
    subgraph Ingestion ["Phase 1 - Ingestion & PII Scrubbing"]
        A1[Google Play Store] -->|google-play-scraper| B[IngestionManager]
        A2[Apple App Store] -->|iTunes RSS JSON Feed| B
        A3[Reddit Discussions] -->|Search Query via Playwright| B
        A5[Twitter/X Conversations] -->|Playwright Scrape| B
        A6[Trustpilot] -->|BeautifulSoup + Playwright| B
        B -->|"Emoji strip, Dedup, 5-word filter, Spam detect"| C1[raw_reviews.csv]
        C1 -->|NeonDB raw_reviews table write| C2[(NeonDB Raw Reviews)]
        C2 -->|PIIScrubber - RegEx Masking| C3[reviews.csv]
    end

    %% Phase 2: LLM Optimization & Gate Funnel
    subgraph Phase2 ["Phase 2 - LLM-Optimized Annotation"]
        C3 -->|Incremental check: SELECT WHERE annotated_at IS NULL| D1[New Reviews Queue]
        D1 -->|Stratified Sampler| D3[Sampled Reviews]
        D3 -->|Relevance Gate Funnel: llama-3.1-8b-instant| D4[Gate Decision]
        D4 -->|Yes: Relevant| D5[Classifier Model: gpt-oss-120b]
        D4 -->|No: Irrelevant| D2[Fallback Neutral Mapping]
        D2 & D5 -->|NeonDB annotated_reviews write| D6[(NeonDB Annotated Reviews)]
    end

    %% Phase 3: Local Aggregation & Theme Discovery
    subgraph Phase3 ["Phase 3 - Local Aggregation & Theme Discovery"]
        D6 -->|ThemeDiscoverer| E1[8 Core Business Questions]
        E1 -->|Counts & Averages in Python| E2[Root Causes Q6: Gemini 2.5 Flash]
        E1 -->|% Sample & % Negative Q7| E3[Opportunity Scores Q8]
        E2 & E3 --> E4[analysis_results.json]
    end

    %% Phase 4+5: Reporting & Orchestration
    subgraph Reporting ["Phases 4 & 5 - Reporting & Orchestration"]
        E4 -->|Gemini 2.5 Flash Pulse Note Generator| F1[weekly_pulse_note.md]
        E4 -->|JSONExporter| F2[data/dashboard_data.json]
        F1 & F2 -->|E2E Orchestrator: src/main.py| F3[Pipeline Orchestrated Outcomes]
    end

    %% Backend Server
    subgraph Server ["FastAPI Server - src/server.py"]
        G1["GET /api/dashboard"]
        G2["POST /api/run-pipeline (SSE Log Stream)"]
    end

    %% Frontend
    subgraph Frontend ["Next.js Frontend - frontend/"]
        H1[Next.js Visualizer Pages] -->|GET /api/dashboard| G1
        H1 -->|SSE Log Stream| G2
        H1 --> H2["/dashboard - Recharts (Pie & Radar)"]
        H1 --> H3["/pulse-note - Markdown Viewer"]
        H1 --> H4["/opportunities - AI Opportunity Cards"]
        H1 --> H5["/voice-of-customer - Review text feed via /api/voc"]
    end

    style Ingestion fill:#1e1e24,stroke:#444,stroke-width:1px
    style Phase2 fill:#1a1f30,stroke:#444,stroke-width:1px
    style Phase3 fill:#171c26,stroke:#444,stroke-width:1px
    style Reporting fill:#1a2324,stroke:#444,stroke-width:1px
    style Server fill:#1c1e20,stroke:#444,stroke-width:1px
    style Frontend fill:#15221b,stroke:#444,stroke-width:1px
```

---

## 🔄 E2E Pipeline Workflow

The pipeline executes sequentially across 6 phases:

```
[Scrapers] ──► [Clean / Scrub] ──► [Stratified Sample S4] ──► [Strategy 5: Two-Stage Gate]
                                                                      │ (batches of 10 via llama-3.1-8b-instant)
                                             ┌────────────────────────┴────────────────────────┐
                                             ▼ [Gate: YES]                                     ▼ [Gate: NO]
                                    [Full LLM Classify]                             [Fallback Neutral Mapping]
                        (batches of 5 via openai/gpt-oss-120b)                 (delivery complaints, etc. Gated out)
                                             │                                                 │
                                             └────────────────────────┬────────────────────────┘
                                                                      ▼
                                                             [Local Aggregation]
                                                                      │
                                                                      ▼
                                                      [Pulse Note ≤700w] + [JSON Export]
                                                                      │
                                                                      ▼
                                                                 [Dashboard]
```

1. **Ingest & Prepare**: Multi-source crawlers scrape user reviews for Zepto (App Store, Play Store, Reddit, Twitter/X, Trustpilot). Text is cleaned, spam-filtered, deduplicated, and stored in the NeonDB `raw_reviews` database table. Deterministic regex scrubbing removes PII.
2. **Classify (Incremental)**: The pipeline queries NeonDB to isolate reviews that have not been annotated yet (`WHERE annotated_at IS NULL`). Minority sources are fully preserved, while majority sources are sub-sampled.
3. **Relevance Funnel & Labeling**: Reviews pass through the Relevance Gate (Groq `llama-3.1-8b-instant`). Irrelevant reviews are assigned fallback neutral metrics. Relevant reviews go to the classifier (Groq `openai/gpt-oss-120b` / or a model-agnostic equivalent) for detailed 8-question Quick Commerce taxonomy classification.
4. **Aggregate & Analyze**: The annotated reviews are queried, and the `ThemeDiscoverer` counts themes, average ratings, extracts user evidence quotes, and computes opportunity and severity scores in local Python processes. It runs a root-cause explanation for the frustrations theme using Gemini 2.5 Flash.
5. **Report & Export**: The reporting engine generates a ≤700-word Weekly Pulse Note in markdown via Gemini 2.5 Flash and exports structured JSON metrics to `dashboard_data.json` with fallback data validation.
6. **Dashboard & Web UI**: The Next.js dashboard reads the JSON metrics and renders interactive charts (Recharts Pie, Donut, and Radar charts) and reports.

```mermaid
sequenceDiagram
    autonumber
    actor User as User / Scheduler
    participant S as Scrapers (PlayStore, AppStore, Reddit, X, Trustpilot)
    participant DB as NeonDB (raw_reviews & annotated_reviews)
    participant PII as RegExp PII Scrubber
    participant Gate as Relevance Gate (llama-3.1-8b)
    participant Cls as Classifier (gpt-oss-120b)
    participant Agg as ThemeDiscoverer (Python)
    participant LLM as Gemini (Root Causes Q6 & Pulse Note)
    participant FE as Next.js Web UI

    User->>S: Triggers ingestion pipeline (manual or cron)
    S->>DB: Ingests raw reviews & saves to raw_reviews table
    DB->>PII: Extracts unannotated records
    PII->>Gate: Cleaned & regex PII-masked reviews
    Gate->>Cls: Funnels only relevant reviews (Relevance Gate)
    Cls->>DB: Saves structured classifications to annotated_reviews
    DB->>Agg: Fetches all annotated reviews to aggregate metrics
    Agg->>LLM: Requests root causes for frustration themes (Gemini)
    LLM-->>Agg: Returns root cause statements
    Agg->>LLM: Requests executive Weekly Pulse Note (Gemini)
    LLM-->>Agg: Returns pulse note text (≤ 700 words)
    Agg->>FE: Writes weekly_pulse_note.md & dashboard_data.json
    FE->>User: Displays dashboard page, opportunities, & VOC review list
```

---

## 📖 Phase-by-Phase Breakdown

- **Phase 1 — Ingestion & PII Scrubbing**: Handles data harvesting. Play Store count is set to 2000, App Store/Reddit/Twitter/Trustpilot are fetched, cleaned, deduplicated, and persisted in NeonDB. Deterministic RegExp patterns scrub emails, phones, IPs, and social handles locally.
- **Phase 2 — LLM Classification**: Only classifies unannotated database rows. Applies a Stratified Sampler to handle dataset imbalance and processes reviews through the relevance gate before applying the GPT-OSS 120B classification model. Writes annotations to NeonDB.
- **Phase 3 — Theme Discovery & Aggregation**: Groups results in local Python processes (zero LLM calls for counting) based on predefined Quick-Commerce registries. Runs Gemini 2.5 Flash to compute operational root causes for frustration themes (Question 6). Mapped outputs are written to `analysis_results.json`.
- **Phase 4 — Weekly Pulse Note Generation**: Generates the markdown Pulse Note using Gemini 2.5 Flash, enforcing a ≤700-word limit via local programmatic word count truncation, and extracting opportunity cards.
- **Phase 5 — E2E Pipeline Orchestration**: Uses `main.py` and `run_phase5.py` to run and verify the E2E pipeline execution limit controls, output files, schema keys, and word limits.
- **Phase 6 — Web UI Dashboard**: Next.js client-side visualizer pages (`/dashboard`, `/pulse-note`, `/opportunities`, `/voice-of-customer`) which load data dynamically, rendering high-fidelity interactive Recharts visualisations.

---

### Component Descriptions

#### Phase 1 — Ingestion & PII Scrubbing
*   **scrapers.py**: Connects to App Store ID (`1575323645`), Google Play Store Package (`com.zeptoconsumerapp`), Reddit (via Search URL query on Playwright), Twitter/X (`@ZeptoNow` mentions), and Trustpilot reviews. Play Store scrape size is set to 2000.
*   **ingestor.py**: Cleans raw reviews (deduplicating, stripping emojis, filtering out sentences shorter than 5 words, rules-based spam detection) and writes raw reviews to the NeonDB `raw_reviews` table.
*   **pii_scrubber.py**: Run local, regex-only PII masking (removing emails, phone numbers, IP addresses, card numbers, user handles).

#### Phase 2 — Optimized LLM Annotation
*   **review_processor.py**: Implements incremental runs by querying NeonDB for unannotated rows (`WHERE annotated_at IS NULL`). Only relevant reviews (filtered by `llama-3.1-8b-instant` Relevance Gate) are forwarded to the classification model `gpt-oss-120b` for full taxonomy tagging. Writes classifications to `annotated_reviews` NeonDB table and updates local `annotated_reviews.json` checkpoint.
*   **sampler.py**: Stratifies raw reviews to handle dataset imbalance (retaining minority sources and proportionally sub-sampling majority sources down to a representative size of 1000).
*   **llm_client.py**: Model-agnostic wrapper initializing Groq and Gemini clients via environment keys (`GROQ_CLASSIFIER_MODEL`, `GROQ_GATE_MODEL`, `GEMINI_SUMMARY_MODEL`).

#### Phase 3 — Local Aggregation & Theme Discovery
*   **theme_discoverer.py**: Performs Python-based grouping (no LLM calls) across the 8 business questions based on predefined registries. Computes counts, averages, and opportunity scores (`Count × (6 − Average Rating)`). Formulates segment percentages (`% Sample`, `% Negative Reviews`) for underserved user segments. Resolves frustration themes in Question 6 by prompting Gemini 2.5 Flash (`GeminiClient`) to generate a single-sentence operational root cause. Mapped outputs are written to `analysis_results.json`.

#### Phase 4 — Pulse Note Generation & JSON Export
*   **pulse_generator.py**: Connects to Gemini 2.5 Flash to compile the executive Weekly Pulse Note, structured into the exact 9 segments required. Enforces a ≤700-word limit via local programmatic word count truncation, and extracts opportunity cards.
*   **json_exporter.py**: Exposes a fallback validator to format, sync, and write the consolidated metrics, sentiment distributions, and summaries into `dashboard_data.json` for React ingestion.

#### Phase 5 — E2E Pipeline Orchestration
*   **main.py**: Orchestrates the execution of all phases via simple `--phase` flags.
*   **run_phase5.py**: Verification script validating generated output files, schema keys, word limits, and heading keywords.

#### Phase 6 — Web UI Dashboard
*   **server.py**: FastAPI server exposing `/api/dashboard` and `/api/run-pipeline` (streaming stdout logs in real-time over SSE).
*   **Next.js Visualizer Pages**: Client-side visualizer pages (`/dashboard`, `/pulse-note`, `/opportunities`, `/voice-of-customer`) which load data dynamically, rendering high-fidelity interactive Recharts visualisations (Pie/Donut and Radar) and markdown Pulse Note containers.
*   **voc/route.ts**: Exposes the `/api/voc` backend route to dynamically load, sample, and slice 50 reviews from the local `annotated_reviews.json` dataset.

## 📁 Directory Structure

See [implementationplan.md](file:///d:/Zepto-AI-Powered%20Review%20Discovery%20Engine/doc/implementationplan.md) for the detailed file-level project structure.

---

## ⚙️ Prerequisites

*   Python 3.10+
*   Node.js 18+
*   Groq API Key (with access to the designated classifier model)
*   Gemini API Key (Google AI Studio)
*   NeonDB Connection String (PostgreSQL)

---

## 🚀 Setup & Installation

### Step 1 — Clone the Repository
```bash
git clone https://github.com/<your-username>/Zepto-AI-Powered-Review-Discovery-Engine.git
cd "Zepto-AI-Powered Review Discovery Engine"
```

### Step 2 — Create Virtual Environment
```powershell
python -m venv venv
./venv/Scripts/Activate.ps1
pip install -r requirements.txt
playwright install
```

### Step 3 — Configure Environment Variables
Copy `.env.template` to `.env` in the root folder:
```powershell
copy .env.template .env
```
Fill in the API keys, database connection URL, App IDs, and model names in `.env`.

### Step 4 — Verify Configuration (Phase 0)
```powershell
python src/script/run_phase0.py
```

---

## 🏃 Running the Pipeline

### End-to-End Pipeline Execution
```powershell
python src/main.py --phase all
```

### Standalone Incremental Executions
Run ingestion:
```powershell
python src/main.py --phase 1
```
Run optimized classification (only classifies unclassified items in NeonDB):
```powershell
python src/main.py --phase 2
```

### 🤖 GitHub Actions Workflow (Weekly Automation)

The pipeline is fully automated via GitHub Actions (`.github/workflows/weekly_pipeline.yml`):
- **Schedule**: Automatically runs every Monday at 9:20 AM IST (`50 3 * * 1` UTC).
- **Execution**: Checks out the repository, installs dependencies, sets up Playwright, verifies API keys/database credentials, runs the pipeline end-to-end (`python src/main.py --phase all`), and runs validation tests.
- **State Sync & Commit**: Copies `dashboard_data.json` into the Next.js `public/` directory and automatically commits/pushes the updated dashboard JSON back to the repository so the frontend visualizer is updated.
- **Error Policy**: Employs a strict no-silent-failures policy (`set -euo pipefail`), ensuring any build, script, API, or DB connection issue fails the action immediately.

---

## 🧪 Testing Suite

### Unit Testing Suite
Run the automated pytest testing suite to verify scaffolding, regex operations, database connection reconnection, and mathematical calculations:
```powershell
python -m pytest -v tests/
```

### Integration Testing Suite
Run the automated backend-frontend integration test. This automatically launches the Next.js server, tests all JSON schemas, pages, API routes, and clean shutdowns:
```powershell
python src/script/test_integration.py
```

---

## 🖥️ Web UI: Run, Observe & Analyze

The FastAPI backend and Next.js frontend are decoupled but seamlessly integrated:

### 1. Launch the Backend Server
Run the FastAPI backend server using the virtual environment's Python interpreter to bypass launcher issues:
```powershell
venv\Scripts\python.exe -m uvicorn src.server:app --host 127.0.0.1 --port 8000
```
This launches the backend API on port 8000 and exposes real-time log streaming endpoints over Server-Sent Events (SSE).

### 2. Launch the Frontend Visualizer
In a new terminal, navigate to the frontend directory and start Next.js:
```powershell
cd frontend
npm run dev
```
Open `http://localhost:3000` to interact with the responsive dashboard.

### 3. Observe Pipeline Executions in Real-Time
On the Web UI Navbar, click **"Run Pipeline"**:
- A console modal will open showing a live-streamed bash console.
- The modal triggers the backend pipeline `/api/run-pipeline` and streams stdout logs in real-time over SSE (Server-Sent Events) directly into the UI console log window.
- When execution finishes, the UI automatically refreshes to display the newly computed metrics.

### 4. Analyze Results
- **Dashboard**: Review interactive Recharts Pie/Donut (User Sentiment Breakdown) and Radar charts (Underserved User Segments mapped by severity score) along with key Quick Commerce metrics.
- **Pulse Note**: View the executive AI-generated markdown summary, structured into the exact 9 segments required.
- **Opportunities**: View the synthesized product opportunity cards highlighting the user evidence, proposed AI solutions, and expected business impact.
- **Voice of Customer**: View a text-only feed of up to 50 annotated reviews loaded directly from `annotated_reviews.json` with search filtering and sentiment badges.
