"""Independent local OCR evidence for food-label analysis (RapidOCR/ONNX)."""

from __future__ import annotations

import re
import threading
from pathlib import Path
from typing import Any

from PIL import Image


_engine = None
_engine_lock = threading.Lock()


def _get_engine():
    global _engine
    if _engine is None:
        with _engine_lock:
            if _engine is None:
                from rapidocr import RapidOCR

                _engine = RapidOCR(params={"Rec.lang_type": "en"})
    return _engine


def _value(output: Any, key: str):
    return output.get(key) if isinstance(output, dict) else getattr(output, key, None)


def build_ocr_evidence(
    texts: Any,
    scores: Any,
    boxes: Any,
    image_size: tuple[int, int],
    allergies: list[str],
    ingredients_detected: list[str] | None = None,
) -> dict:
    """Convert OCR output into UI-safe lines and evidence matches."""
    width, height = image_size
    text_list = list(texts) if texts is not None else []
    score_list = list(scores) if scores is not None else []
    box_list = list(boxes) if boxes is not None else []
    lines = []
    joined_parts = []
    for index, text in enumerate(text_list[:100]):
        value = str(text).strip()
        if not value:
            continue
        try:
            score = float(score_list[index])
        except (IndexError, TypeError, ValueError):
            score = 0.0
        bbox = None
        try:
            points = box_list[index]
            xs = [float(point[0]) for point in points]
            ys = [float(point[1]) for point in points]
            bbox = [
                max(0, min(width, round(min(xs)))),
                max(0, min(height, round(min(ys)))),
                max(0, min(width, round(max(xs)))),
                max(0, min(height, round(max(ys)))),
            ]
        except (IndexError, TypeError, ValueError):
            pass
        lines.append({"text": value, "confidence": round(max(0.0, min(1.0, score)), 3), "bbox": bbox})
        joined_parts.append(value.lower())

    joined = "\n".join(joined_parts)
    all_ingredients = " ".join(str(item).lower() for item in (ingredients_detected or []))
    ingredient_heading = bool(re.search(r"\bingredients?\b", joined))
    ingredient_overlap = any(
        len(term) > 2 and re.search(rf"\b{re.escape(term)}\b", joined)
        for term in re.findall(r"[a-z0-9]+", all_ingredients)
    )
    coverage = {
        "ingredients": ingredient_heading or ingredient_overlap,
        "allergen_statement": bool(re.search(r"\b(contains|may contain|free from|allergen|traces of)\b", joined)),
        "nutrition": bool(re.search(r"\b(nutrition|carbohydrate|carbs|energy|nutrition facts)\b", joined)),
    }
    nutrition_matches = [
        {"line": line["text"], "confidence": line["confidence"], "bbox": line["bbox"]}
        for line in lines
        if re.search(r"\b(nutrition|carbohydrate|carbs|sugars?|serving size|energy)\b", line["text"], re.I)
    ]

    allergen_aliases = {
        "peanut": ("peanut", "peanuts", "groundnut", "groundnuts"),
        "milk": ("milk", "dairy"), "egg": ("egg", "eggs"), "wheat": ("wheat",),
        "soy": ("soy", "soya", "soybean", "soybeans"), "sesame": ("sesame",),
        "fish": ("fish",), "shellfish": ("shellfish",),
        "almond": ("almond", "almonds"), "cashew": ("cashew", "cashews"),
        "walnut": ("walnut", "walnuts"), "hazelnut": ("hazelnut", "hazelnuts"),
        "pistachio": ("pistachio", "pistachios"), "pecan": ("pecan", "pecans"),
    }
    matches = []
    for allergy in allergies:
        normalized = re.sub(r"[^a-z0-9]+", " ", str(allergy).lower()).strip()
        terms = allergen_aliases.get(normalized, (normalized,))
        for line in lines:
            line_text = line["text"].lower()
            term = next((term for term in terms if re.search(rf"\b{re.escape(term)}\b", line_text)), None)
            if not term:
                continue
            negative = re.search(
                rf"\b(no|not|free from|free of|without)\s+(?:\w+\s+){{0,2}}{re.escape(term)}\b"
                rf"|\b{re.escape(term)}[- ]free\b",
                line_text,
            )
            if negative:
                continue
            advisory = bool(re.search(r"\b(may contain|traces of|made in a facility|shared equipment)\b", line_text))
            matches.append({
                "allergen": str(allergy),
                "matched_text": term,
                "line": line["text"],
                "confidence": line["confidence"],
                "bbox": line["bbox"],
                "kind": "advisory" if advisory else "ingredient_or_contains",
            })
    return {
        "status": "available",
        "engine": "RapidOCR (PP-OCR)",
        "image_size": {"width": width, "height": height},
        "lines": lines,
        "allergen_matches": matches,
        "nutrition_matches": nutrition_matches,
        "panel_coverage": coverage,
    }


def extract_ocr_evidence(
    image_path: str,
    allergies: list[str],
    ingredients_detected: list[str] | None = None,
) -> dict:
    """Run local OCR; report absence/failure as a status, never crash scans."""
    try:
        engine = _get_engine()
    except ImportError:
        return {"status": "unavailable", "engine": "RapidOCR", "lines": [], "allergen_matches": [], "nutrition_matches": [], "panel_coverage": {}}
    try:
        output = engine(str(Path(image_path)))
        with Image.open(image_path) as image:
            image_size = image.size
        return build_ocr_evidence(
            _value(output, "txts"), _value(output, "scores"), _value(output, "boxes"),
            image_size, allergies, ingredients_detected,
        )
    except Exception as exc:
        print(f"[ocr] Independent label OCR failed ({type(exc).__name__}).", flush=True)
        return {"status": "error", "engine": "RapidOCR", "lines": [], "allergen_matches": [], "nutrition_matches": [], "panel_coverage": {}}


def warmup_ocr() -> None:
    """Initialize the OCR engine when available; OCR remains optional at startup."""
    try:
        _get_engine()
        print("[ocr] RapidOCR engine initialized.", flush=True)
    except ImportError:
        print("[ocr] RapidOCR unavailable; install project requirements to enable evidence OCR.", flush=True)
    except Exception as exc:
        print(f"[ocr] RapidOCR initialization failed ({type(exc).__name__}).", flush=True)
