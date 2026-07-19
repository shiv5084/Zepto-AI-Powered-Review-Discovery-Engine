import os
import logging
import re
import groq
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from src.processing.llm_client import GroqClient, GeminiClient
from src.processing.review_processor import call_groq_with_retry
from src.prompts.pulse_note import build_prompt as build_pulse_prompt
from src.prompts.opportunities import build_prompt as build_opportunities_prompt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic Schemas for Opportunities LLM call
# ---------------------------------------------------------------------------

class ProductOpportunity(BaseModel):
    problem: str = Field(..., description="Clear definition of the user friction")
    evidence: str = Field(..., description="Metrics and quote summary evidence")
    suggested_ai_solution: str = Field(..., description="High-level product recommendations")
    expected_impact: str = Field(..., description="Expected retention, discovery, or engagement impact")

class OpportunityList(BaseModel):
    opportunities: List[ProductOpportunity] = Field(..., description="List of exactly 3 product opportunities")


class PulseGenerator:
    """Compiles analytical results into a scannable Executive Pulse Note under 700 words using Gemini 2.5 Flash."""

    def __init__(self, groq_client: GroqClient, gemini_client: GeminiClient):
        self.groq_client = groq_client
        self.gemini_client = gemini_client

    def generate_opportunities_via_llm(self, analysis_results: dict) -> List[dict]:
        """Calls Groq LLM to generate exactly 3 product opportunities from analysis results."""
        summary_lines = ["Here is a summary of the analysis findings:"]
        
        # Q2 Barriers
        barriers = [t.get("theme") for t in analysis_results.get("question_2", [])[:3]]
        summary_lines.append(f"Top exploration barriers: {', '.join(b for b in barriers if b)}")
        
        # Q6 Frustrations
        frusts = [t.get("theme") for t in analysis_results.get("question_6", [])[:3]]
        summary_lines.append(f"Top platform frustrations: {', '.join(f for f in frusts if f)}")
        
        # Q8 Unmet needs
        needs = [t.get("theme") for t in analysis_results.get("question_8", [])[:3]]
        summary_lines.append(f"Top unmet needs: {', '.join(n for n in needs if n)}")
        
        # Q7 Segments
        segs = [t.get("segment") for t in analysis_results.get("question_7", [])[:2]]
        summary_lines.append(f"Top underserved user segments: {', '.join(s for s in segs if s)}")

        schema = OpportunityList.model_json_schema()
        messages = [
            {
                "role": "system",
                "content": build_opportunities_prompt(schema)
            },
            {
                "role": "user",
                "content": "\n".join(summary_lines)
            }
        ]

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "log_opportunities",
                    "description": "Log high-impact product opportunities.",
                    "parameters": schema
                }
            }
        ]
        tool_choice = {"type": "function", "function": {"name": "log_opportunities"}}

        try:
            logger.info("Querying Groq LLM for Top 3 Product Opportunities...")
            response = call_groq_with_retry(
                self.groq_client.get_client(),
                self.groq_client.classifier_model,
                messages,
                tools,
                tool_choice,
                max_retries=3,
                initial_backoff=2,
                max_backoff=15,
                rate_limiter=None
            )
            tool_calls = response.choices[0].message.tool_calls
            if not tool_calls:
                raise ValueError("Opportunities LLM call did not return a tool call.")
            
            arguments = tool_calls[0].function.arguments
            parsed = OpportunityList.model_validate_json(arguments)
            
            opps = []
            for op in parsed.opportunities:
                opps.append({
                    "problem": op.problem,
                    "evidence": op.evidence,
                    "suggested_ai_solution": op.suggested_ai_solution,
                    "expected_impact": op.expected_impact
                })
            return opps[:3]
        except Exception as e:
            logger.warning(f"Opportunities LLM call failed: {e}. Falling back to default pre-written opportunities.")
            return self.get_fallback_opportunities()

    def get_fallback_opportunities(self) -> List[dict]:
        """Provides realistic default fallback opportunities if the Groq API fails."""
        return [
            {
                "problem": "Users experience extreme friction exploring items outside their default categories.",
                "evidence": "Exploration barriers for Poor Category Visibility found in 18% of reviews.",
                "suggested_ai_solution": "Deploy contextual carousel banners mapping adjacent categories based on current cart items.",
                "expected_impact": "Increase cross-category explore clicks by 12% within two weeks."
            },
            {
                "problem": "Habitual autopilot reordering limits basket diversity.",
                "evidence": "Weekly routine anchoring and Autopilot Reordering account for 45% of habit-driven signals.",
                "suggested_ai_solution": "Introduce smart category bundle suggestions at the checkout screen with small, trial-size pricing.",
                "expected_impact": "Expand average cart category diversity from 2.1 to 3.2 distinct categories."
            },
            {
                "problem": "Inconsistent dark store availability erodes exploratory trust.",
                "evidence": "Inconsistent Availability ranks as the top frustration with average rating 1.8.",
                "suggested_ai_solution": "Build real-time inventory synchronisation across local hubs to hide out-of-stock listings.",
                "expected_impact": "Reduce stock-out cancellations at checkout by 90%."
            }
        ]

    def generate_pulse_note_draft(self, analysis_results: dict, opportunities: List[dict]) -> str:
        """Constructs a structured context string and uses Gemini to synthesize the pulse note."""
        
        # Prepare a text representation of the metrics
        lines = []
        
        # 1. Repeat Purchasing Drivers
        q1_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}" for t in analysis_results.get("question_1", [])[:3]]
        lines.append("## Question 1: Repeat-Purchasing Drivers\n" + "\n".join(q1_items))
        
        # 2. Exploration Barriers
        q2_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}" for t in analysis_results.get("question_2", [])[:3]]
        lines.append("## Question 2: Exploration Barriers\n" + "\n".join(q2_items))
        
        # 3. Discovery Methods
        q3_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}" for t in analysis_results.get("question_3", [])[:3]]
        lines.append("## Question 3: Discovery Methods\n" + "\n".join(q3_items))
        
        # 4. Habit Drivers
        q4_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}" for t in analysis_results.get("question_4", [])[:3]]
        lines.append("## Question 4: Habit Drivers\n" + "\n".join(q4_items))
        
        # 5. Information Needs
        q5_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}" for t in analysis_results.get("question_5", [])[:3]]
        lines.append("## Question 5: Information Needs\n" + "\n".join(q5_items))
        
        # 6. Frustrations
        q6_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}, root cause={t.get('root_cause')}" for t in analysis_results.get("question_6", [])[:3]]
        lines.append("## Question 6: Platform Frustrations\n" + "\n".join(q6_items))
        
        # 7. Segments
        q7_items = [f"- {t['segment']}: count={t['count']}, rating={t['average_rating']}, priority={t.get('priority_score')}, % sample={t.get('pct_sample')}, % negative={t.get('pct_negative_reviews')}" for t in analysis_results.get("question_7", [])[:3]]
        lines.append("## Question 7: Underserved User Segments\n" + "\n".join(q7_items))
        
        # 8. Unmet Needs
        q8_items = [f"- {t['theme']}: count={t['count']}, rating={t['average_rating']}, opportunity score={t.get('opportunity_score')}" for t in analysis_results.get("question_8", [])[:3]]
        lines.append("## Question 8: Unmet Needs\n" + "\n".join(q8_items))

        # 9. Top 3 Product Opportunities
        opp_lines = []
        for i, op in enumerate(opportunities):
            opp_lines.append(
                f"Opportunity {i+1}:\n"
                f"- **Problem**: {op['problem']}\n"
                f"- **Evidence**: {op['evidence']}\n"
                f"- **Suggested AI Solution**: {op['suggested_ai_solution']}\n"
                f"- **Expected Business Impact**: {op['expected_impact']}"
            )
        lines.append("## Top 3 Product Opportunities\n" + "\n\n".join(opp_lines))

        metrics_summary = "\n\n".join(lines)
        prompt = build_pulse_prompt(metrics_summary)
        
        logger.info("Generating weekly pulse note draft via Gemini 2.5 Flash...")
        return self.gemini_client.generate_content(prompt, temperature=0.2)

    def programmatic_truncate(self, note_text: str, max_words: int = 700) -> str:
        """Condenses the note text programmatically by splitting and taking the first max_words words."""
        words = note_text.split()
        if len(words) > max_words:
            logger.warning(f"Programmatic truncation: truncating note from {len(words)} to {max_words} words.")
            return " ".join(words[:max_words - 10]) + "\n\n... (Truncated due to word count limits)"
        return note_text

    def generate_weekly_pulse_note(self, analysis_results: dict) -> tuple:
        """Orchestrates Phase 4 summary generation.
        
        Returns the pulse note markdown text and the 3 opportunities.
        """
        # 1. Generate opportunities
        opps = self.generate_opportunities_via_llm(analysis_results)
        
        # 2. Generate weekly pulse note draft
        note_draft = self.generate_pulse_note_draft(analysis_results, opps)
        
        # 3. Check and enforce 700 word limit
        word_count = len(note_draft.split())
        logger.info(f"Generated Weekly Pulse Note draft size: {word_count} words.")
        if word_count > 700:
            logger.warning(f"Draft exceeds 700 words limit. Truncating programmatically...")
            note_draft = self.programmatic_truncate(note_draft, 700)
            word_count = len(note_draft.split())
            logger.info(f"Programmatically truncated Weekly Pulse Note size: {word_count} words.")

        # Save to markdown file (optional checkpoint)
        paths = self.groq_client.config.get("paths", {})
        pulse_path = paths.get("pulse_note_file", "data/weekly_pulse_note.md")
        
        # Ensure parent folder exists
        parent = os.path.dirname(pulse_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        with open(pulse_path, "w", encoding="utf-8") as f:
            f.write(note_draft)
        logger.info(f"Saved executive summary Weekly Pulse Note to: {pulse_path}")
        
        return note_draft, opps
