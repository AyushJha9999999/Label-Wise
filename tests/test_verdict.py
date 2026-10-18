import json

from src.verdict import enforce_declared_allergy, parse_verdict


def parse(payload: object) -> object:
    return parse_verdict(json.dumps(payload))


def test_malformed_response_defaults_to_caution():
    result = parse_verdict("not json")

    assert result.verdict == "CAUTION"
    assert result.confidence == "low"
    assert result.parse_error


def test_non_object_json_defaults_to_caution():
    result = parse_verdict("[\"SAFE\"]")

    assert result.verdict == "CAUTION"
    assert result.parse_error == "JSON response was not an object."


def test_flags_cannot_be_returned_as_safe():
    result = parse({
        "verdict": "SAFE",
        "confidence": "high",
        "flagged": [{"ingredient": "peanut", "reason": "Allergy"}],
    })

    assert result.verdict == "AVOID"
    assert result.flagged[0]["ingredient"] == "peanut"


def test_low_confidence_cannot_be_returned_as_safe():
    result = parse({"verdict": "SAFE", "confidence": "low"})

    assert result.verdict == "CAUTION"


def test_missing_allergen_statement_causes_caution_for_allergies():
    result = parse({
        "verdict": "SAFE",
        "confidence": "high",
        "user_restrictions": {"allergies": ["peanut"]},
        "allergen_statement_visible": False,
    })

    assert result.verdict == "CAUTION"
    assert "does not show enough" in result.summary


def test_malformed_model_fields_are_normalized_safely():
    result = parse({
        "verdict": "SAFE",
        "confidence": None,
        "flagged": None,
        "ingredients_detected": "peanuts",
        "user_restrictions": None,
        "nutrition_facts": [],
        "allergen_advisories": "may contain peanuts",
        "notes": None,
    })

    assert result.verdict == "CAUTION"
    assert result.confidence == "low"
    assert result.flagged == []
    assert result.ingredients_detected == []
    assert result.user_restrictions == {}


def test_stated_voice_allergy_overrides_safe_when_detected_ingredient_matches():
    result = parse({
        "verdict": "SAFE",
        "confidence": "high",
        "ingredients_detected": ["Puffed Rice", "Peanuts", "Salt"],
        "user_restrictions": {"allergies": []},
    })

    result = enforce_declared_allergy(result, [], "I'm allergic to peanuts. Can I eat this?")

    assert result.verdict == "AVOID"
    assert result.flagged[0]["ingredient"] == "Peanuts"
    assert "peanuts" in result.user_restrictions["allergies"]


def test_saved_profile_allergy_overrides_safe_on_alias_match():
    result = parse({
        "verdict": "SAFE",
        "confidence": "high",
        "ingredients_detected": ["Groundnut oil"],
    })

    result = enforce_declared_allergy(result, ["peanut"], "Can I eat this?")

    assert result.verdict == "AVOID"


def test_explicit_negated_voice_allergy_is_not_treated_as_declared():
    result = parse({
        "verdict": "SAFE",
        "confidence": "high",
        "ingredients_detected": ["Peanuts"],
    })

    result = enforce_declared_allergy(result, [], "I'm not allergic to peanuts.")

    assert result.verdict == "SAFE"
