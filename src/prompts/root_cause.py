def build_prompt(theme_name: str, review_snippets: list) -> str:
    """Builds the prompt to request root-cause analysis for Q6 frustrations."""
    snippets_str = "\n".join([f"- {s}" for s in review_snippets])
    return (
        f"You are a Senior Systems Analyst at Zepto. Analyze these user review snippets regarding the frustration theme: '{theme_name}'.\n"
        "Your task is to identify and summarize a concise, single-sentence root cause explaining the product, inventory, or operational failure leading to this complaint. Do not just restate the complaints; explain the underlying system issue.\n\n"
        "## Review Snippets:\n"
        f"{snippets_str}\n\n"
        "## Output:\n"
        "Provide ONLY the single-sentence root cause, under 30 words. No introduction, no quotes."
    )
