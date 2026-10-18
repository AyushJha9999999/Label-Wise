"""
LabelWise — src/prompts.py
Builds the system prompt and user message template for multimodal label analysis.
"""

import json

# ── Output schema that the model must follow exactly ──────────────────────────
OUTPUT_SCHEMA = {
    "product_name": "<product or brand name visible on the package, or empty string>",
    "ingredients_detected": ["<list of all ingredients read from the label>"],
    "user_restrictions": {
        "allergies": ["<from audio>"],
        "conditions": ["<from audio>"],
    },
    "allergen_advisories": [],
    "allergen_statement_visible": False,
    "nutrition_facts": {
        "total_carbohydrate_g": None,
        "sugars_g": None,
        "basis": "<per serving, per 100 g, or unknown>",
    },
    "verdict": "<SAFE | CAUTION | AVOID>",
    "flagged": [
        {
            "ingredient": "<exact text from label>",
            "reason": "<plain-English explanation>",
        }
    ],
    "summary": "<one sentence, plain language>",
    "confidence": "<high | medium | low>",
    "notes": "<e.g. blurry text, partial label, etc. — empty string if none>",
}

# ── Verdict rules embedded in the system prompt ───────────────────────────────
VERDICT_RULES = """
VERDICT DECISION RULES — follow these strictly:
• AVOID  : a clearly identified ingredient matches a stated allergy.
• CAUTION: allergen advisory is present; OR the image does not show the allergen
           advisory area for a stated allergy; OR the label text is partially
           unreadable/cut off; OR confidence is low.
• For diabetes, assess TOTAL CARBOHYDRATE and serving size. Low sugars do not mean
  low carbohydrates. Never call a product SAFE just because sugars are low.
  If carbohydrate amount or serving basis is missing, or carbohydrate is high,
  return CAUTION and explain that portion decisions depend on the user's plan.
• SAFE   : ALL ingredients were clearly readable AND none conflict with the
           user's restrictions, allergen advisory area is visible and clear, and
           carbohydrate information is adequate for any stated diabetes concern.

>> When in doubt, return CAUTION. NEVER return SAFE when uncertain. <<
"""

# ── Full system prompt ─────────────────────────────────────────────────────────
def build_system_prompt() -> str:
    """Return the complete system prompt for label analysis."""
    return f"""You are LabelWise, a food safety assistant for people with allergies and dietary restrictions.

YOUR JOB:
1. Read ALL ingredients from the food label image — even small print.
   Also read the product or brand name if it is visible; otherwise return an empty string.
2. Extract the user's allergies, medical conditions, and preferences from their voice note.
3. Check common alternate ingredient names, such as groundnut for peanut.
4. Compare every detected ingredient against the user's restrictions.
5. Return your result as a SINGLE valid JSON object — no explanation text, no markdown, just the JSON.

{VERDICT_RULES}

OUTPUT FORMAT — return only this JSON structure:
{json.dumps(OUTPUT_SCHEMA, indent=2)}

IMPORTANT SAFETY RULES:
• Never give medical advice or diagnose conditions.
• Only report what appears on the label.
• If the label image is blurry, dark, or partially cut off, set confidence to "low" or "medium" and verdict to CAUTION.
• Hidden names must be flagged: e.g. "groundnut oil" = peanut, "maltodextrin" = fast-digesting sugar.
• "May contain traces of" warnings must trigger CAUTION even if the user has a firm allergy.
• Report total carbohydrate separately from sugars and preserve the label's basis (per serving/per 100 g).
• Explain in simple, short sentences that a non-expert can understand.
• Do NOT output anything outside the JSON block.
"""


def build_user_message_text(voice_text: str,
                            saved_profile: dict | None = None) -> str:
    """
    Build the text-only prompt for Gemini API.
    The image is passed separately as a PIL Image object.
    """
    profile_note = ""
    if saved_profile:
        allergies   = saved_profile.get("allergies", [])
        conditions  = saved_profile.get("conditions", [])
        preferences = saved_profile.get("preferences", [])
        if any([allergies, conditions, preferences]):
            profile_note = (
                f"\n\n[Previously saved profile]\n"
                f"Allergies:   {', '.join(allergies) or 'none'}\n"
                f"Conditions:  {', '.join(conditions) or 'none'}\n"
                f"Preferences: {', '.join(preferences) or 'none'}\n"
                "The user's voice note may update or confirm these restrictions."
            )

    return (
        "Please analyse this food label image. "
        "The user's voice note (transcribed below) describes their dietary restrictions.\n\n"
        f"USER VOICE NOTE: {voice_text}"
        + profile_note
        + "\n\nRead every ingredient from the label image, compare them against the "
        "user's restrictions, and return the structured JSON verdict."
    )


# Keep backward compat — old HuggingFace multimodal format (unused now)
def build_user_message(image_path: str, voice_text: str,
                        saved_profile: dict | None = None) -> list[dict]:
    """Legacy HuggingFace format — kept for compatibility."""
    text = build_user_message_text(voice_text, saved_profile)
    return [
        {"type": "image", "url": image_path},
        {"type": "text",  "text": text},
    ]
