"""Barcode-based product lookup and label/database consistency checks.

Open Food Facts data is community contributed. It is shown as corroborating
evidence only; it never proves that a product is safe.
"""

from __future__ import annotations

import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from difflib import SequenceMatcher


OFF_FIELDS = "product_name,brands,ingredients_text,nutriments,code"


def detect_barcodes(image_path: str) -> list[str]:
    """Read common retail barcodes from an image using OpenCV's barcode module."""
    try:
        import cv2
    except ImportError:
        return []

    image = cv2.imread(str(Path(image_path)))
    if image is None:
        return []
    values: list[str] = []
    if hasattr(cv2, "barcode_BarcodeDetector"):
        try:
            decoded = cv2.barcode_BarcodeDetector().detectAndDecode(image)
            # OpenCV wheels have exposed both a 3-value and a 4-value return shape.
            result = decoded[1] if len(decoded) == 4 else decoded[0]
            if result is not None:
                values.extend(str(value).strip() for value in result if value and str(value).strip())
        except (cv2.error, TypeError, ValueError):
            pass
    if not values:
        values.extend(_decode_ean13_rows(image))
    return list(dict.fromkeys(values))


def _decode_ean13_rows(image) -> list[str]:
    """Fallback decoder for clean EAN-13 photos when the OpenCV detector misses."""
    import cv2

    grayscale = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    height, width = grayscale.shape
    left_codes = {
        "0001101": ("0", "L"), "0011001": ("1", "L"), "0010011": ("2", "L"),
        "0111101": ("3", "L"), "0100011": ("4", "L"), "0110001": ("5", "L"),
        "0101111": ("6", "L"), "0111011": ("7", "L"), "0110111": ("8", "L"), "0001011": ("9", "L"),
        "0100111": ("0", "G"), "0110011": ("1", "G"), "0011011": ("2", "G"),
        "0100001": ("3", "G"), "0011101": ("4", "G"), "0111001": ("5", "G"),
        "0000101": ("6", "G"), "0010001": ("7", "G"), "0001001": ("8", "G"), "0010111": ("9", "G"),
    }
    right_codes = {
        "1110010": "0", "1100110": "1", "1101100": "2", "1000010": "3", "1011100": "4",
        "1001110": "5", "1010000": "6", "1000100": "7", "1001000": "8", "1110100": "9",
    }
    parity_to_first = {
        "LLLLLL": "0", "LLGLGG": "1", "LLGGLG": "2", "LLGGGL": "3", "LGLLGG": "4",
        "LGGLLG": "5", "LGGGLL": "6", "LGLGLG": "7", "LGLGGL": "8", "LGGLGL": "9",
    }

    row_step = max(1, height // 240)
    for y in range(0, height, row_step):
        row = grayscale[y] < 100
        dark = __import__("numpy").flatnonzero(row)
        if len(dark) < 30:
            continue
        start, end = int(dark[0]), int(dark[-1]) + 1
        module = (end - start) / 95
        if module < 1:
            continue
        bits = "".join("1" if row[min(width - 1, round(start + (i + 0.5) * module))] else "0" for i in range(95))
        if bits[:3] != "101" or bits[45:50] != "01010" or bits[92:] != "101":
            continue
        left = [left_codes.get(bits[offset:offset + 7]) for offset in range(3, 45, 7)]
        right = [right_codes.get(bits[offset:offset + 7]) for offset in range(50, 92, 7)]
        if any(item is None for item in left + right):
            continue
        parity = "".join(item[1] for item in left)
        first_digit = parity_to_first.get(parity)
        if first_digit is None:
            continue
        digits = first_digit + "".join(item[0] for item in left + right)
        checksum = sum(int(digit) * (1 if index % 2 == 0 else 3) for index, digit in enumerate(digits[:12]))
        if (10 - checksum % 10) % 10 == int(digits[-1]):
            return [digits]
    return []


def lookup_open_food_facts(barcode: str, timeout: float = 3.0) -> dict[str, Any] | None:
    """Fetch a small, public product record by barcode; fail gracefully offline."""
    if not re.fullmatch(r"\d{8,14}", barcode):
        return None
    url = f"https://world.openfoodfacts.org/api/v2/product/{barcode}.json?fields={OFF_FIELDS}"
    request = urllib.request.Request(url, headers={"User-Agent": "LabelWise/1.0 (local demo)"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = response.read(1_000_000)
        data = __import__("json").loads(payload)
    except (OSError, ValueError, urllib.error.URLError):
        return None
    if data.get("status") != 1 or not isinstance(data.get("product"), dict):
        return None

    product = data["product"]
    nutriments = product.get("nutriments") if isinstance(product.get("nutriments"), dict) else {}
    return {
        "barcode": barcode,
        "name": str(product.get("product_name") or "").strip(),
        "brands": str(product.get("brands") or "").strip(),
        "ingredients_text": str(product.get("ingredients_text") or "").strip(),
        "carbohydrates_100g": nutriments.get("carbohydrates_100g"),
        "source": "Open Food Facts",
    }


def compare_ingredients(label_ingredients: list[str], product: dict[str, Any]) -> list[str]:
    """Report obvious ingredient discrepancies without treating absence as proof."""
    database_text = str(product.get("ingredients_text") or "").lower()
    if not database_text:
        return []
    normalized_db = re.sub(r"[^a-z0-9]+", " ", database_text)
    missing = []
    for ingredient in label_ingredients:
        ingredient_text = re.sub(r"\s*\([^)]*\d+(?:[.,]\d+)?\s*%[^)]*\)", "", str(ingredient).lower())
        normalized = re.sub(r"[^a-z0-9]+", " ", ingredient_text).strip()
        if len(normalized) >= 3 and not re.search(rf"\b{re.escape(normalized)}\b", normalized_db):
            missing.append(str(ingredient))
    return missing


def _same_product(label_name: str, record_name: str) -> bool:
    """Require meaningful name evidence before comparing community ingredients."""
    ignored = {"food", "product", "snack", "brand", "the", "and", "with"}

    def tokens(value: str) -> set[str]:
        return {word for word in re.findall(r"[a-z0-9]+", value.lower()) if len(word) > 2 and word not in ignored}

    left, right = tokens(label_name), tokens(record_name)
    if not left or not right:
        return False
    overlap = left & right
    if overlap and len(overlap) / min(len(left), len(right)) >= 0.5:
        return True
    return SequenceMatcher(None, " ".join(sorted(left)), " ".join(sorted(right))).ratio() >= 0.72


def enrich_with_barcode(
    image_path: str,
    label_ingredients: list[str],
    label_product_name: str = "",
) -> dict[str, Any]:
    """Detect a barcode, look up its product, and compare ingredient lists."""
    barcodes = detect_barcodes(image_path)
    if not barcodes:
        return {"status": "not_detected", "barcode": None, "product": None, "ingredient_discrepancies": []}

    barcode = barcodes[0]
    product = lookup_open_food_facts(barcode)
    if product is None:
        return {"status": "unavailable_or_not_found", "barcode": barcode, "product": None, "ingredient_discrepancies": []}
    if not _same_product(label_product_name, str(product.get("name") or "")):
        return {
            "status": "identity_unverified",
            "barcode": barcode,
            "product": product,
            "ingredient_discrepancies": [],
        }
    discrepancies = compare_ingredients(label_ingredients, product)
    return {
        "status": "matched_with_discrepancy" if discrepancies else "matched",
        "barcode": barcode,
        "product": product,
        "ingredient_discrepancies": discrepancies,
    }
