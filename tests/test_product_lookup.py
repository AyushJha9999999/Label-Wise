from src.product_lookup import compare_ingredients, enrich_with_barcode
from pathlib import Path


def test_open_food_facts_ingredient_disagreement_is_reported(monkeypatch):
    monkeypatch.setattr("src.product_lookup.detect_barcodes", lambda _path: ["1234567890123"])
    monkeypatch.setattr("src.product_lookup.lookup_open_food_facts", lambda _code: {
        "barcode": "1234567890123",
        "name": "Sample Crunch snack",
        "brands": "Example",
        "ingredients_text": "rice, oil, salt",
        "source": "Open Food Facts",
    })

    evidence = enrich_with_barcode("label.png", ["rice", "peanuts"], "Sample Crunch")

    assert evidence["status"] == "matched_with_discrepancy"
    assert evidence["ingredient_discrepancies"] == ["peanuts"]


def test_no_barcode_returns_transparent_not_detected_status(monkeypatch):
    monkeypatch.setattr("src.product_lookup.detect_barcodes", lambda _path: [])

    evidence = enrich_with_barcode("label.png", ["rice"])

    assert evidence == {
        "status": "not_detected",
        "barcode": None,
        "product": None,
        "ingredient_discrepancies": [],
    }


def test_ingredient_match_ignores_case_and_punctuation():
    assert compare_ingredients(["RED-CHILLI powder"], {"ingredients_text": "Rice, red chilli powder, salt"}) == []


def test_demo_label_barcode_is_detectable():
    from src.product_lookup import detect_barcodes

    image_path = Path(__file__).parents[1] / "samples" / "labels" / "labelwise_demo_peanut_diabetes.png"

    assert detect_barcodes(str(image_path)) == ["2001234567893"]


def test_unrelated_product_record_is_not_compared_as_ingredient_mismatch(monkeypatch):
    monkeypatch.setattr("src.product_lookup.detect_barcodes", lambda _path: ["2001234567893"])
    monkeypatch.setattr("src.product_lookup.lookup_open_food_facts", lambda _code: {
        "barcode": "2001234567893",
        "name": "Iraq DELAL Sauce",
        "brands": "DELAL",
        "ingredients_text": "tomato, salt, spices",
        "source": "Open Food Facts",
    })

    evidence = enrich_with_barcode("label.png", ["roasted peanuts (22%)"], "Chilli Peanut Crunch")

    assert evidence["status"] == "identity_unverified"
    assert evidence["ingredient_discrepancies"] == []
