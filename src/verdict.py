"""
LabelWise — src/verdict.py
Parses the raw model output string and enforces safety rules.

The model returns a string that may contain:
  1. Thinking blocks  → <|channel>thought\n...<channel|>
  2. Tool-call blocks → <tool_call>{"name":...}</tool_call>
  3. The final JSON verdict block

This module strips 1 & 2 and extracts the JSON verdict, applying hard
safety overrides before returning a clean VerdictResult dataclass.
"""

import json
import re
from dataclasses import dataclass, field

# ── Result dataclass ───────────────────────────────────────────────────────────
@dataclass
class VerdictResult:
    """Normalised output returned to the UI."""
    verdict:              str          # SAFE | CAUTION | AVOID
    summary:              str          # one-line plain-English summary
    product_name:         str          = ""
    ingredients_detected: list[str]   = field(default_factory=list)
    flagged:              list[dict]   = field(default_factory=list)
    user_restrictions:    dict         = field(default_factory=dict)
    confidence:           str          = "low"  # high | medium | low
    notes:                str          = ""
    raw_json:             dict | None  = None    # parsed model JSON, for debugging
    parse_error:          str | None   = None    # set if parsing failed


# ── Regex patterns ─────────────────────────────────────────────────────────────
# Strips optional model thinking blocks: <|channel>thought\n...<channel|>
_THINK_RE = re.compile(r"<\|channel>thought.*?<channel\|>", re.DOTALL)

# Strips tool-call blocks: <tool_call>...</tool_call>
_TOOL_CALL_RE = re.compile(r"<tool_call>.*?</tool_call>", re.DOTALL)



# ── JSON extractor ─────────────────────────────────────────────────────────────
def _extract_json(text: str) -> str | None:
    """Return the first complete JSON object or array embedded in *text*."""
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, end = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if isinstance(value, (dict, list)):
            return text[start:end]
    return None


# ── Core parser ────────────────────────────────────────────────────────────────
def parse_verdict(raw_response: str) -> VerdictResult:
    """
    Extract and validate the verdict JSON from the model's raw output.

    Safety contract:
      • Returns CAUTION on ANY parse error — never returns SAFE on a guess.
      • Upgrades verdict to AVOID if flagged list is non-empty but verdict
        was SAFE (should not happen with a good prompt, but belt-and-braces).
      • Normalises verdict to uppercase.
    """
    # ── Step 1: strip thinking and tool-call blocks ─────────────────────────
    cleaned = _THINK_RE.sub("", raw_response)
    cleaned = _TOOL_CALL_RE.sub("", cleaned)
    # Strip any lingering model-specific special-token markers  <|...|>
    cleaned = re.sub(r"<\|[^|>]+\|>", "", cleaned)
    cleaned = cleaned.strip()

    # ── Step 2: find JSON block ─────────────────────────────────────────────
    json_str = _extract_json(cleaned)
    if not json_str:
        print(f"[verdict] No JSON found. Cleaned text preview: {cleaned[:300]!r}")
        return VerdictResult(
            verdict="CAUTION",
            summary="Could not parse model response. Defaulting to CAUTION for safety.",
            confidence="low",
            notes="Raw response did not contain a JSON block.",
            parse_error=f"No JSON found in: {cleaned[:200]!r}",
        )

    # ── Step 3: parse JSON ──────────────────────────────────────────────────
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as exc:
        print(f"[verdict] JSON decode error: {exc}. JSON string preview: {json_str[:300]!r}")
        return VerdictResult(
            verdict="CAUTION",
            summary="Model returned malformed JSON. Defaulting to CAUTION for safety.",
            confidence="low",
            notes=str(exc),
            parse_error=str(exc),
        )

    if not isinstance(data, dict):
        return VerdictResult(
            verdict="CAUTION",
            summary="Model returned an unexpected response shape. Defaulting to CAUTION for safety.",
            confidence="low",
            notes="Expected a JSON object containing a verdict.",
            parse_error="JSON response was not an object.",
        )

    # ── Step 4: extract fields with safe defaults ───────────────────────────
    verdict     = str(data.get("verdict", "CAUTION")).upper().strip()
    flagged     = data.get("flagged", [])
    confidence  = str(data.get("confidence", "low")).lower().strip()
    summary     = str(data.get("summary", "") or "")
    notes       = str(data.get("notes", "") or "")
    ingredients = data.get("ingredients_detected", [])
    product_name = str(data.get("product_name", "") or "").strip()
    restrictions= data.get("user_restrictions", {})
    nutrition = data.get("nutrition_facts", {})
    allergen_advisories = data.get("allergen_advisories", [])
    allergen_statement_visible = data.get("allergen_statement_visible") is True

    if not isinstance(flagged, list):
        flagged = []
    if not isinstance(ingredients, list):
        ingredients = []
    ingredients = [str(item) for item in ingredients]
    if not isinstance(restrictions, dict):
        restrictions = {}
    if not isinstance(nutrition, dict):
        nutrition = {}
    if not isinstance(allergen_advisories, list):
        allergen_advisories = []
    if confidence not in ("high", "medium", "low"):
        confidence = "low"
        notes += " [override: unknown confidence normalised to low]"

    # ── Step 5: safety overrides ────────────────────────────────────────────

    # 5a. Only allow valid verdicts
    if verdict not in ("SAFE", "CAUTION", "AVOID"):
        verdict = "CAUTION"
        notes += " [override: unknown verdict normalised to CAUTION]"

    # 5b. Cannot be SAFE if there are flagged items
    if verdict == "SAFE" and flagged:
        verdict = "AVOID"
        notes += " [override: flagged items present, verdict upgraded to AVOID]"

    # 5c. Low confidence → at least CAUTION
    if confidence == "low" and verdict == "SAFE":
        verdict = "CAUTION"
        notes += " [override: low confidence, verdict downgraded to CAUTION]"

    # 5d. "AVOID" must have a reason — if flagged is empty, be cautious
    if verdict == "AVOID" and not flagged:
        verdict = "CAUTION"
        notes += " [override: AVOID with no flagged items changed to CAUTION]"

    # A cropped ingredient panel cannot establish whether precautionary
    # cross-contact warnings appear elsewhere on the package.
    allergies = restrictions.get("allergies", []) if isinstance(restrictions, dict) else []
    conditions = restrictions.get("conditions", []) if isinstance(restrictions, dict) else []
    if isinstance(allergies, str):
        allergies = [allergies]
    if not isinstance(allergies, list):
        allergies = []
    if isinstance(conditions, str):
        conditions = [conditions]
    if not isinstance(conditions, list):
        conditions = []
    has_allergy = bool(allergies)
    if verdict != "AVOID" and has_allergy and (allergen_advisories or not allergen_statement_visible):
        verdict = "CAUTION"
        summary = "This image does not show enough of the package to verify the ingredients and allergen warnings. Check the full package before eating."
        notes += " [override: allergen warning area is missing or a warning is present]"

    # Do not let a low sugar value hide a high total-carbohydrate value.
    condition_text = " ".join(str(value).lower() for value in conditions)
    has_diabetes = any(term in condition_text for term in ("diabet", "blood sugar", "blood glucose"))
    carbs = nutrition.get("total_carbohydrate_g") if isinstance(nutrition, dict) else None
    basis = str(nutrition.get("basis", "unknown")).lower() if isinstance(nutrition, dict) else "unknown"
    try:
        carbs_value = float(carbs) if carbs is not None else None
    except (TypeError, ValueError):
        carbs_value = None
    if verdict != "AVOID" and has_diabetes:
        # 20 g/100 g is a conservative review trigger for this app, not a
        # medical threshold or a claim that smaller portions are safe.
        high_carbs_per_100g = carbs_value is not None and carbs_value >= 20 and "100" in basis
        if carbs_value is None or high_carbs_per_100g:
            verdict = "CAUTION"
            if high_carbs_per_100g:
                summary = f"The label lists {carbs_value:g} g total carbohydrate {basis}; low sugar does not mean low carbohydrate. Check the portion size against your diabetes meal plan."
                notes += " [override: high total carbohydrate per 100 g]"
            else:
                summary = "Total carbohydrate information is missing or unclear, so this cannot be marked safe for diabetes based on sugar content alone. Check the serving size and label."
                notes += " [override: total carbohydrate not confirmed]"

    # 5e. Ensure flagged items have expected keys
    cleaned_flagged = []
    for item in flagged:
        if isinstance(item, dict):
            cleaned_flagged.append({
                "ingredient": str(item.get("ingredient", "Unknown")),
                "reason":     str(item.get("reason", "No reason provided")),
            })

    return VerdictResult(
        verdict=verdict,
        summary=summary or _auto_summary(verdict, cleaned_flagged),
        product_name=product_name,
        ingredients_detected=ingredients,
        flagged=cleaned_flagged,
        user_restrictions=restrictions,
        confidence=confidence,
        notes=notes,
        raw_json=data,
    )


_ALLERGEN_GROUPS = (
    {"peanut", "peanuts", "groundnut", "groundnuts"},
    {"milk", "dairy"},
    {"egg", "eggs"},
    {"wheat"},
    {"soy", "soya", "soybean", "soybeans"},
    {"sesame", "sesame seed", "sesame seeds"},
    {"fish"},
    {"shellfish"},
    {"almond", "almonds"},
    {"cashew", "cashews"},
    {"walnut", "walnuts"},
    {"hazelnut", "hazelnuts"},
    {"pistachio", "pistachios"},
    {"pecan", "pecans"},
)


def enforce_declared_allergy(result: VerdictResult, profile_allergies: list[str], voice_text: str) -> VerdictResult:
    """Force AVOID when a declared allergy is present in detected ingredients.

    This deterministic check protects against the model overlooking either a
    clear allergy in the spoken note or a matching ingredient it detected.
    """
    declared = {str(item).strip().lower() for item in profile_allergies if str(item).strip()}
    spoken = voice_text.lower()
    allergen_names = sorted({name for group in _ALLERGEN_GROUPS for name in group}, key=len, reverse=True)
    for name in allergen_names:
        escaped = re.escape(name)
        for match in re.finditer(rf"\b(?:allergic\s+to|allergy\s+to)\s+{escaped}\b", spoken):
            prefix = spoken[max(0, match.start() - 18):match.start()]
            if not re.search(r"\b(?:not|never)\s+$", prefix):
                declared.add(name)

    if not declared:
        return result

    def allergen_group(value: str) -> set[str]:
        normalized = re.sub(r"[^a-z0-9 ]", " ", value.lower()).strip()
        normalized = re.sub(r"\s+", " ", normalized)
        for group in _ALLERGEN_GROUPS:
            if any(re.search(rf"\b{re.escape(alias)}\b", normalized) for alias in group):
                return group
        return {normalized}

    declared_groups = [allergen_group(value) for value in declared]
    matching_ingredient = next((
        ingredient
        for ingredient in result.ingredients_detected
        if allergen_group(ingredient) and any(allergen_group(ingredient) & group for group in declared_groups)
    ), None)
    if matching_ingredient is None:
        return result

    declared_label = ", ".join(sorted(declared))
    reason = f"The label lists {matching_ingredient}, which matches your stated allergy ({declared_label})."
    if not any(flag.get("ingredient", "").lower() == matching_ingredient.lower() for flag in result.flagged):
        result.flagged.append({"ingredient": matching_ingredient, "reason": reason})
    result.verdict = "AVOID"
    result.summary = f"Avoid this product: the label lists {matching_ingredient}, matching your stated allergy ({declared_label})."
    restrictions = result.user_restrictions if isinstance(result.user_restrictions, dict) else {}
    restrictions["allergies"] = sorted(declared)
    result.user_restrictions = restrictions
    result.notes = "Deterministic safety check matched a listed ingredient to an allergy you stated."
    return result


# ── Fallback summary generator ────────────────────────────────────────────────
def _auto_summary(verdict: str, flagged: list[dict]) -> str:
    """Generate a plain-English summary if the model didn't provide one."""
    if verdict == "SAFE":
        return "All ingredients appear safe for your dietary restrictions."
    if verdict == "AVOID":
        names = [f["ingredient"] for f in flagged[:3]]
        return f"Contains problematic ingredient(s): {', '.join(names)}. Do not eat."
    # CAUTION
    if flagged:
        names = [f["ingredient"] for f in flagged[:2]]
        return f"Possible concern with: {', '.join(names)}. Check carefully."
    return "Unable to confirm safety. Check the label manually."


# ── Colour helper for the UI ──────────────────────────────────────────────────
VERDICT_COLORS = {
    "SAFE":    "#22c55e",   # green-500
    "CAUTION": "#f59e0b",   # amber-500
    "AVOID":   "#ef4444",   # red-500
}

VERDICT_ICONS = {
    "SAFE":    "✅",
    "CAUTION": "⚠️",
    "AVOID":   "🚫",
}


def verdict_color(verdict: str) -> str:
    """Return hex colour for the verdict badge."""
    return VERDICT_COLORS.get(verdict.upper(), "#6b7280")


def verdict_icon(verdict: str) -> str:
    """Return emoji icon for the verdict."""
    return VERDICT_ICONS.get(verdict.upper(), "❓")
