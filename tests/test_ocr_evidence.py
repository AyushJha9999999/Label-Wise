from src.ocr_evidence import build_ocr_evidence


def test_ocr_evidence_returns_exact_allergen_and_panel_lines():
    evidence = build_ocr_evidence(
        texts=["INGREDIENTS", "Puffed rice, roasted peanuts, salt", "CONTAINS PEANUTS", "Total carbohydrate 61 g per 100 g"],
        scores=[0.99, 0.95, 0.98, 0.93],
        boxes=[[[0, 0], [120, 0], [120, 20], [0, 20]]] * 4,
        image_size=(1200, 1580),
        allergies=["peanut"],
        ingredients_detected=["Peanuts"],
    )

    assert evidence["panel_coverage"] == {"ingredients": True, "allergen_statement": True, "nutrition": True}
    assert evidence["allergen_matches"][0]["line"] == "Puffed rice, roasted peanuts, salt"
    assert evidence["allergen_matches"][0]["bbox"] == [0, 0, 120, 20]
    assert any("carbohydrate" in item["line"].lower() for item in evidence["nutrition_matches"])


def test_cross_contact_phrase_is_classified_as_advisory():
    evidence = build_ocr_evidence(
        texts=["May contain traces of sesame"], scores=[0.91],
        boxes=[[[1, 2], [100, 2], [100, 20], [1, 20]]],
        image_size=(400, 200), allergies=["sesame"],
    )

    assert evidence["allergen_matches"][0]["kind"] == "advisory"


def test_negated_free_from_statement_is_not_reported_as_allergen_presence():
    evidence = build_ocr_evidence(
        texts=["Peanut free"], scores=[0.91],
        boxes=[[[1, 2], [100, 2], [100, 20], [1, 20]]],
        image_size=(400, 200), allergies=["peanut"],
    )

    assert evidence["allergen_matches"] == []
