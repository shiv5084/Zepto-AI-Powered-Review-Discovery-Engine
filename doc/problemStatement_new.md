# Zepto — Automated Weekly Product Review Pulse
## AI-Powered Cross-Category Discovery Engine (PRDE)

> [!NOTE]
> **Business Context**  
> Quick-commerce platforms like Zepto have successfully become a part of users' weekly routines, with millions of users placing recurring orders for groceries, snacks & beverages, and household essentials. However, over time, shopping behavior becomes highly repetitive — users often purchase the same set of products from the same categories and rarely explore new categories available on the platform. This limits meaningful cross-category discovery and perpetuates narrow purchasing patterns.  
> One of the company's strategic goals is to **increase the percentage of Monthly Active Customers who purchase products from at least one new category every month** (e.g., a user who buys groceries starts buying pet supplies; a user who buys snacks starts buying personal care products).  
> Before proposing any product solution, Zepto needs a scalable, AI-powered system capable of analyzing large volumes of user feedback across multiple channels to understand why cross-category discovery is failing for certain users.

---

## Goal

Build an **AI-Powered Cross-Category Discovery Engine (PRDE)** that continuously analyzes user feedback and conversations at scale to identify:
- **Cross-category discovery barriers** and friction points.
- **Repeat-purchasing drivers** and their underlying causes.
- **Current product discovery methods** and their effectiveness.
- **Habit-driven shopping behaviors** and their role in category lock-in.
- **Information gaps** that prevent users from trying new categories.
- **Recurring user frustrations** across the platform experience.
- **Segment-specific** exploration tendencies and challenges.
- **Emerging unmet needs** that represent product opportunities.

---

## Data Sources

The system must ingest and analyze unstructured feedback from the following channels:
*   **App Stores:** Google Play Store & Apple App Store Reviews
*   **Forums:** Reddit Discussions & Quick-Commerce Community Forums
*   **Social Media:** X (Twitter) Conversations
*   **Web:** Product review websites, blogs, and quick-commerce discussion threads

---

## Core Business Questions

The engine must be designed to answer the following eight core questions:
1. **Why** do users repeatedly buy from the same categories?
2. **What** prevents users from exploring new categories?
3. **How** do users discover products today?
4. **What** role do habits play in shopping behavior?
5. **What** information do users need before trying a new category?
6. **What** frustrations emerge repeatedly?
7. **Which** user segments are more likely to experiment?
8. **What** unmet needs emerge consistently across discussions?

---

## Technical Specifications & Requirements

### 1. Multi-Source Review Ingestion

Collect, ingest, and normalize reviews from the **last 8–12 weeks** from publicly available review sources.

#### Schema Specifications
For each record ingested, the system must capture:
- `source`: The origin platform (e.g., `reddit`, `play_store`, `app_store`).
- `date`: Timestamp/date of the post.
- `title`: Title of the review/post (if available).
- `text`: The raw text content of the review/post.
- `rating`: Rating score (1-5), if applicable.
- `engagement`: Upvotes, retweets, or engagement metrics, if applicable.

> [!IMPORTANT]
> **Compliance & Ingestion Constraints**
> - **Public Data Only:** Only use publicly available datasets or APIs.
> - **No Authenticated Scraping:** Do not scrape behind login walls or authenticate with user accounts.
> - **Zero PII (Personally Identifiable Information):** Strip all usernames, emails, IP addresses, device IDs, or other identifiable information *before* processing.
> - **Normalization & Storage:** Normalize the ingested data into a unified schema and save it as a structured CSV file.
> - **Data Cleaning:** Clean the data during ingestion:
>   - **Remove Emojis:** Strip out all emojis and special non-text symbols from review title and text fields.
>   - **Deduplication:** Filter out duplicate records based on text matching.
>   - **Sentence Length Filter:** Exclude any reviews/text entries containing less than 5 words to filter out uninformative input.
>   - **Spam Detection:** Identify and filter out spam reviews, advertisements, or repeating noise patterns (e.g., "aaaaaa").

---

### 2. Theme Discovery & Analysis (LLM-Powered)

> [!WARNING]
> **Crucial Implementation Instruction**  
> Do **NOT** create a single global list of general categories (e.g., *Delivery*, *Pricing*, *UI*, *Quality*).  
> Instead, perform **independent theme discovery** for **each** of the eight business questions below. Each question must have its own distinct set of discovered themes, count metrics, supporting quotes, and (where applicable) root-cause analyses.

#### Product Discovery Relevance Gate

Before performing theme classification, the LLM must first determine whether each review is relevant to **product/category discovery** on the platform:
- `is_product_discovery_related`: `true` or `false`
- **Only reviews classified as `true` should be considered** for theme analysis across all eight questions.
- Reviews about unrelated topics (e.g., pure delivery complaints with no category/product discovery angle) should be filtered out at this stage.

#### LLM Extraction Pipeline

For every ingested review that passes the discovery-relevance gate, the LLM pipeline must:
1. **Classify overall sentiment** — Label each review as `positive`, `neutral`, or `negative`. This is a **global, review-level classification** applied across all classified reviews, independent of any specific question's themes.
2. Extract repeat-purchasing drivers and category lock-in signals.
3. Extract cross-category exploration barriers.
4. Extract current product discovery methods mentioned.
5. Identify habit-driven shopping signals.
6. Extract information needs for trying new categories.
7. Extract platform frustrations and root causes (for complaint themes only).
8. Identify unmet product/feature needs.
9. Classify the user segment/persona.

#### Global Sentiment Distribution

After classifying sentiment for every review, compute the **overall sentiment distribution** across all product-discovery-relevant reviews:
- `positive_count`: Total reviews classified as positive.
- `neutral_count`: Total reviews classified as neutral.
- `negative_count`: Total reviews classified as negative.
- `positive_pct`: `positive_count ÷ total classified reviews` (float).
- `neutral_pct`: `neutral_count ÷ total classified reviews` (float).
- `negative_pct`: `negative_count ÷ total classified reviews` (float).

> [!NOTE]
> Sentiment is **not** calculated per theme or per question. It is a single, global metric across the entire classified review corpus.

Below are the detailed analytical tasks and expected outputs for each question:

---

#### QUESTION 1: Why do users repeatedly buy from the same categories?
*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Habit & Routine Lock-in` — Purchases become automatic/habitual, no thought given to alternatives
    - `Reorder Convenience` — Reorder/quick-add features make repeating easier than exploring
    - `Trust in Known Brands` — Users stick to brands they already know and trust
    - `Price Sensitivity` — Fear of wasting money on unfamiliar or potentially unsuitable products
    - `Limited Category Awareness` — Users don't realize the platform offers other categories beyond groceries
    - `Time Pressure` — Quick-commerce users prioritize speed; browsing new categories feels wasteful
    - `Satisfaction with Current Selection` — Users are genuinely happy with what they buy, no perceived need to change
    - `None` — No repeat-purchasing driver mentioned
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

*Example Output:*
```json
{
  "theme": "Habit & Routine Lock-in",
  "count": 38,
  "average_rating": 3.6,
  "evidence": [
    "I just reorder the same groceries every week, never even thought about checking other categories.",
    "My cart is basically the same 15 items on repeat, Zepto makes it too easy to just reorder."
  ]
}
```

---

#### QUESTION 2: What prevents users from exploring new categories?
*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Poor Category Visibility` — New categories hidden in UI, not surfaced or promoted prominently
    - `Irrelevant Recommendations` — Suggested products don't match user's lifestyle, needs, or preferences
    - `Lack of Product Information` — Insufficient descriptions, reviews, or images for unfamiliar products
    - `Trust Deficit in New Brands` — Reluctance to try unknown brands without ratings or social proof
    - `High Perceived Risk` — Fear of quality issues, returns hassle, or wasted money on new products
    - `Cluttered Home Screen` — Home screen dominated by reorder history, crowding out discovery surfaces
    - `No Incentive to Explore` — No discounts, free samples, or rewards for trying new categories
    - `None` — No exploration barrier mentioned
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

---

#### QUESTION 3: How do users discover products today?
*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Search-Driven Discovery` — Users find products through active keyword search on the app
    - `Banner & Promotion-Led` — Discovery through promotional banners, flash deals, and homepage offers
    - `Social Media Influence` — Recommendations from Instagram, YouTube, influencers, or viral content
    - `Word of Mouth` — Friends, family, or peer recommendations driving product trials
    - `Algorithmic Recommendations` — Platform's "recommended for you", "frequently bought together" suggestions
    - `Occasion-Triggered Browsing` — Festivals, parties, seasons, or life events prompt new category exploration
    - `Accidental / Serendipitous` — Stumbling upon products while scrolling or ordering regular items
    - `None` — No specific discovery method mentioned
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

---

#### QUESTION 4: What role do habits play in shopping behavior?
*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Autopilot Reordering` — Users reorder the same cart without thinking, one-tap repeat purchases
    - `Weekly Routine Anchoring` — Shopping tied to fixed weekly or daily schedule, no room for exploration
    - `Brand Loyalty Lock-in` — Habitual commitment to specific brands regardless of alternatives
    - `Comfort Zone Persistence` — Emotional comfort in buying familiar items, psychological resistance to change
    - `Cognitive Load Avoidance` — Users avoid the mental effort of evaluating, comparing, or choosing new products
    - `List-Based Shopping` — Users shop from pre-made grocery lists, never browse freely on the platform
    - `Trigger-Based Purchasing` — Buying triggered by specific cues (running out of stock, push notifications)
    - `None` — No habit-related shopping behavior mentioned
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

---

#### QUESTION 5: What information do users need before trying a new category?
*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Product Reviews & Ratings` — Need social proof — ratings, reviews, and testimonials from other buyers
    - `Price Comparison` — Need to compare pricing with other platforms, offline stores, or expected MRP
    - `Product Quality Assurance` — Need guarantees about quality, freshness, authenticity, or brand reliability
    - `Detailed Product Descriptions` — Need comprehensive specs, ingredients, usage instructions, or nutritional info
    - `Trial / Sample Options` — Need smaller quantities, sample packs, or try-before-you-commit options
    - `Return & Refund Policy` — Need clear, hassle-free return and refund policies for unfamiliar products
    - `Visual Content` — Need high-quality images, videos, usage demos, or unboxing content
    - `None` — No information need expressed
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

---

#### QUESTION 6: What frustrations emerge repeatedly?

> [!CAUTION]
> **Root-Cause Analysis Required**  
> All themes under this question are **complaint/negative themes**. Each theme's output must include a `root_cause` field — a concise explanation of the underlying systemic or product reason why this frustration occurs.

*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Poor Product Quality` — Received items don't match expectations, descriptions, or images
    - `Delivery Issues` — Late delivery, missing items, wrong products, or damaged packaging
    - `Limited Product Variety` — Insufficient options within categories — missing brands, sizes, or SKUs
    - `Misleading Pricing / Offers` — Hidden charges, inflated MRPs, bait-and-switch discounts, or deceptive promos
    - `App Usability Problems` — Confusing navigation, broken search, checkout friction, or poor UX
    - `Inconsistent Availability` — Products frequently out of stock, unavailable in user's area, or removed
    - `Poor Customer Support` — Unhelpful support, slow response, difficult refund/replacement process
    - `None` — No frustration mentioned
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Root Cause`: A concise explanation of the systemic or product-level reason behind this frustration (e.g., "Dark store inventory systems lack real-time sync with the app catalog, causing users to see products that are already out of stock").
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

*Example Output:*
```json
{
  "theme": "Inconsistent Availability",
  "count": 54,
  "average_rating": 1.8,
  "root_cause": "Dark store inventory systems lack real-time sync with the app catalog, causing users to see and add products that are already out of stock at their nearest hub.",
  "evidence": [
    "Half the items I add to cart show 'out of stock' at checkout. Why even show them?",
    "Zepto keeps removing products I buy regularly without any notice or alternative suggestion."
  ]
}
```

---

#### QUESTION 7: Which user segments are more likely to experiment?
*   **Predefined Personas (LLM classifies each review into exactly one):**
    - `Routine Replenishers` — Buy the same groceries/essentials on a fixed schedule. Low exploration tendency
    - `Deal-Driven Explorers` — Motivated by discounts and offers. Will try new categories if incentivized
    - `Occasion-Based Shoppers` — Shop based on events, festivals, or special occasions. Explore seasonally
    - `Health & Wellness Seekers` — Actively looking for healthier alternatives, organic products, wellness items across categories
    - `Impulse Browsers` — Enjoy browsing the app casually. High engagement, open to serendipitous discovery
*   **Output Metrics (per segment, calculated locally):**
    - `Segment`: One of the predefined persona labels above.
    - `Count`: Total reviews classified into this segment.
    - `% Sample`: `Count ÷ Total reviews classified and tagged across all 5 segments` (float). Represents the proportion of this segment relative to the entire classified population.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `% Negative Reviews`: Percentage of reviews in this segment that have **any** cross-category discovery pain point (from Q2 labels) — considering **all** Q2 barrier labels reported by reviewers in this segment, not limited to the top 3. Formula: `(Reviews in segment with any Q2 pain point) ÷ (Total reviews in segment)` (float).
    - `Severity Score`: `(5 − Average Rating) × (% Negative Reviews)`.
    - `Severity Rank`: Rank ordering from most to least underserved.
    - `Discovery Challenges`: Top 3 cross-category discovery pain points (from Q2 labels) reported by reviewers in this segment, ranked by count. Each entry includes:
      - `pain_point`: The Q2 exploration barrier label.
      - `count`: Number of reviews in this segment with that pain point.

---

#### QUESTION 8: What unmet needs emerge consistently across discussions?
*   **Predefined Themes (LLM classifies each review into exactly one):**
    - `Personalized Category Recommendations` — AI-driven suggestions for new categories based on user profile & purchase history
    - `Smart Bundle Suggestions` — Cross-category bundles (e.g., "hosting a party? add snacks, drinks, decor")
    - `Try-Before-You-Commit Packs` — Sample/mini packs for unfamiliar categories at lower commitment price points
    - `Social Shopping Features` — Shared carts, wishlists, "what friends are buying", community-driven discovery
    - `Contextual Discovery Prompts` — Occasion-aware nudges (monsoon → umbrella, exam season → stationery, baby → care)
    - `Better Search & Filters` — Need-based / lifestyle filters beyond product names (e.g., "party supplies", "gym essentials")
    - `Loyalty Rewards for Exploration` — Coins, points, cashback, or gamified incentives for purchasing from new categories
    - `None` — No unmet need expressed
*   **Output Metrics (per theme, calculated locally):**
    - `Theme Name`: One of the predefined theme labels above.
    - `Count`: Total reviews classified into this theme.
    - `Average Rating`: Arithmetic mean of star ratings for matching reviews.
    - `Opportunity Score`: `Count × (6 − Average Rating)`.
    - `Evidence`: Up to 2 verbatim review text quotes from matching reviews.

---

### 3. Weekly Pulse Note & Dashboard Data Generation

After performing the LLM analysis, generate a dual-purpose output:

1.  **Executive Pulse Note (Word/Markdown format):**
    - **Constraint:** Must be **≤ 700 words** and highly scannable.
    - **Content:**
        - Top 3 Repeat-Purchasing Drivers
        - Top 3 Exploration Barriers
        - Top 3 Current Discovery Methods
        - Top 3 Habit-Driven Behaviors
        - Top 3 Information Gaps
        - Top 3 User Frustrations (with Root Causes)
        - Top 3 Most Underserved User Segments
        - Top 3 Unmet Needs
        - Top 3 Product Opportunities
    - **Product Opportunity Structure:**
        - *Problem:* Clear definition of the user friction preventing cross-category discovery.
        - *Evidence:* Metrics and quote summary.
        - *Suggested AI Solution:* High-level recommendation.
        - *Expected Business Impact:* Cross-category adoption rate, new category penetration, or engagement.

2.  **Structured JSON Export:**
    - A JSON file mapping exactly to the dashboard requirements.

#### Example JSON Schema:
```json
{
  "week_ending": "2026-07-14",
  "pulse_note_text": "...",
  "total_reviews_analyzed": 1200,
  "product_discovery_relevant_reviews": 840,
  "sentiment_distribution": {
    "positive_count": 285,
    "neutral_count": 210,
    "negative_count": 345,
    "positive_pct": 0.34,
    "neutral_pct": 0.25,
    "negative_pct": 0.41
  },
  "metrics": {
    "repeat_purchase_drivers": [
      { "theme": "Habit & Routine Lock-in", "count": 38, "average_rating": 3.6 }
    ],
    "exploration_barriers": [
      { "theme": "Poor Category Visibility", "count": 52, "average_rating": 2.3 }
    ],
    "discovery_methods": [
      { "theme": "Banner & Promotion-Led", "count": 44, "average_rating": 3.8 }
    ],
    "habit_drivers": [
      { "theme": "Autopilot Reordering", "count": 61, "average_rating": 4.0 }
    ],
    "information_needs": [
      { "theme": "Product Reviews & Ratings", "count": 47, "average_rating": 2.9 }
    ],
    "top_frustrations": [
      {
        "theme": "Inconsistent Availability",
        "count": 54,
        "average_rating": 1.8,
        "root_cause": "Dark store inventory systems lack real-time sync with the app catalog, causing users to see products that are already out of stock."
      }
    ],
    "underserved_segments": [
      {
        "segment": "Deal-Driven Explorers",
        "count": 42,
        "pct_sample": 0.25,
        "average_rating": 2.5,
        "pct_negative_reviews": 0.76,
        "severity_score": 1.90,
        "severity_rank": 1,
        "discovery_challenges": [
          { "pain_point": "No Incentive to Explore", "count": 18 },
          { "pain_point": "Poor Category Visibility", "count": 10 },
          { "pain_point": "Trust Deficit in New Brands", "count": 6 }
        ]
      }
    ],
    "unmet_needs": [
      {
        "theme": "Try-Before-You-Commit Packs",
        "count": 35,
        "average_rating": 2.2,
        "opportunity_score": 133.0
      }
    ],
    "opportunities": [
      {
        "problem": "Users never discover categories beyond their usual groceries because the home screen is dominated by reorder history.",
        "evidence": "Mentioned in 52 reviews with an average rating of 2.3. Users report 'I didn't even know Zepto sells pet supplies.'",
        "suggested_ai_solution": "AI-powered contextual category surfacing based on user profile, occasion signals, and purchase gaps — replacing static reorder-heavy home layouts with dynamic discovery modules.",
        "expected_impact": "Increase monthly new-category adoption rate by 8% and cross-category cart penetration by 15%."
      }
    ]
  }
}
```

---

## Summary of Constraints

| Constraint | Requirement |
| :--- | :--- |
| **Data Privacy** | **Zero PII.** Scrub all usernames, emails, and device identifiers prior to ingestion/processing. |
| **Ingestion Scope** | Last **8–12 weeks** of feedback; public datasets only (no authenticated/login-wall scraping). |
| **Output Format** | Structured CSV for raw data; JSON and Markdown for final reports. |
| **Pulse Note Length** | Strict limit of **≤ 700 words** for the text note. |
| **Analysis Method** | Independent theme discovery for *each* core business question (no unified global themes). |
| **Discovery Relevance Gate** | Each review must be classified as `is_product_discovery_related` (true/false). Only `true` reviews are analyzed. |
| **Root-Cause Analysis** | Required for **Q6 (Frustrations)** complaint themes only. Each frustration theme must include a systemic `root_cause`. |
| **Metrics** | Report **count** of reviews per theme. Do **not** include frequency ratios. |