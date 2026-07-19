import json

def build_prompt(schema: dict) -> str:
    """Builds the system prompt for generating product opportunities."""
    return (
        "You are a Principal Product Manager at Zepto. Based on the analysis findings, "
        "synthesize exactly 3 high-impact Product Opportunities.\n\n"
        "## Strict Rules:\n"
        "1. For each opportunity, you must provide 'problem', 'evidence', 'suggested_ai_solution', and 'expected_impact' fields.\n"
        "2. CRITICAL: Use the exact keys 'problem', 'evidence', 'suggested_ai_solution', and 'expected_impact' in the tool call arguments. "
        "Do NOT rename them to 'problemStatement', 'solution', or 'impact'. They must strictly match this schema:\n"
        f"{json.dumps(schema, indent=2)}"
    )
