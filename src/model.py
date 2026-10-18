"""
LabelWise — src/model.py
Uses Google's hosted Gemini Flash-Lite API for low-latency multimodal inference.

Set GOOGLE_API_KEY environment variable before running.
Get your free key at: https://aistudio.google.com/app/apikey
"""

import os
import time
from pathlib import Path

from google import genai
from google.genai import types
from PIL import Image

from .prompts  import build_system_prompt, build_user_message_text
from .tools    import get_profile, log_scan
from .verdict  import enforce_declared_allergy, parse_verdict, VerdictResult
from .product_lookup import enrich_with_barcode
from .ocr_evidence import extract_ocr_evidence, warmup_ocr

# ── Configuration ──────────────────────────────────────────────────────────────
GEMINI_MODEL = os.getenv("LABELWISE_MODEL", "gemini-3.5-flash-lite")

# Whisper model size for audio transcription
WHISPER_MODEL = os.getenv("LABELWISE_WHISPER", "tiny")

# ── Singleton holders ──────────────────────────────────────────────────────────
_gemini_client = None
_whisper       = None   # lazy-loaded


# ── Gemini client ──────────────────────────────────────────────────────────────
def _get_client():
    """Initialize Gemini client once."""
    global _gemini_client
    if _gemini_client is not None:
        return _gemini_client

    api_key = os.getenv("GOOGLE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is not set.\n"
            "Get a free key at https://aistudio.google.com/app/apikey\n"
            "Then run:  $env:GOOGLE_API_KEY='your-key-here'; python app.py"
        )

    _gemini_client = genai.Client(api_key=api_key)
    print(f"[model] Gemini client ready ({GEMINI_MODEL}) ✓")
    return _gemini_client


# ── Whisper audio transcriber ──────────────────────────────────────────────────
def _transcribe_audio(audio_path: str) -> str:
    """
    Transcribe a voice note to text using OpenAI Whisper.
    Loads audio via librosa (no ffmpeg needed on Windows).
    """
    global _whisper
    import whisper
    import librosa
    import torch

    if _whisper is None:
        print(f"[model] Loading Whisper '{WHISPER_MODEL}'...")
        _whisper = whisper.load_model(WHISPER_MODEL)
        print("[model] Whisper ready ✓")

    p = Path(audio_path)
    if not p.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_path}")

    print(f"[model] Transcribing audio: {p.name}")
    audio_array, _ = librosa.load(str(p), sr=16_000, mono=True)
    result = _whisper.transcribe(audio_array, fp16=torch.cuda.is_available())
    text   = result.get("text", "").strip()
    return text if text else "[No speech detected in the voice note]"


def transcribe_voice_note(audio_path: str) -> str:
    """Expose local Whisper transcription for user review before analysis."""
    return _transcribe_audio(audio_path)


# ── Tool-call processor ────────────────────────────────────────────────────────
def warmup_models() -> None:
    """Initialize API and local speech model before the first user scan."""
    _get_client()
    global _whisper
    if _whisper is None:
        import whisper

        print(f"[model] Warming Whisper '{WHISPER_MODEL}'...")
        _whisper = whisper.load_model(WHISPER_MODEL)
        print("[model] Whisper ready ✓")
    warmup_ocr()


# ── Main analysis function ─────────────────────────────────────────────────────
def analyze_label(image_path: str, audio_path: str,
                  saved_profile: dict | None = None,
                  log_result: bool = True,
                  voice_text_override: str | None = None) -> VerdictResult:
    """
    Run Gemini multimodal analysis on a food label image + voice note.

    Steps:
      1. Transcribe audio → text via Whisper.
      2. Load saved user profile.
      3. Build prompt text.
      4. Send image + text to Gemini API.
      5. Parse verdict JSON and apply local safety rules.
      6. Log the scan.
    """
    started_at = time.perf_counter()

    # 1. Transcribe audio
    step_started = time.perf_counter()
    voice_text = voice_text_override.strip() if voice_text_override and voice_text_override.strip() else _transcribe_audio(audio_path)
    print(f"[timing] audio transcription: {time.perf_counter() - step_started:.2f}s")

    # 2. Saved profile
    if saved_profile is None:
        saved_profile = get_profile()

    # 3. Build text prompt
    text_prompt = build_user_message_text(voice_text, saved_profile)

    # 4. Load image for Gemini
    print(f"[model] Loading image: {image_path}")
    img = Image.open(image_path).convert("RGB")
    # Keep label text readable while avoiding needlessly large camera uploads.
    max_dimension = int(os.getenv("LABELWISE_IMAGE_MAX", "2048"))
    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    # 5. Call Gemini API
    client = _get_client()
    print(f"[model] Calling {GEMINI_MODEL} API...")
    step_started = time.perf_counter()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[img, text_prompt],
        config=types.GenerateContentConfig(
            system_instruction=build_system_prompt(),
            max_output_tokens=768,
            response_mime_type="application/json",
            thinking_config=types.ThinkingConfig(thinking_level="minimal"),
        ),
    )
    raw_text = response.text
    print(f"[timing] model request: {time.perf_counter() - step_started:.2f}s")
    print(f"[model] Gemini response received ({len(raw_text)} chars).")

    # 6. Parse verdict
    result = parse_verdict(raw_text)
    result = enforce_declared_allergy(result, saved_profile.get("allergies", []), voice_text)

    restrictions = result.user_restrictions if isinstance(result.user_restrictions, dict) else {}
    declared_allergies = restrictions.get("allergies", [])
    if isinstance(declared_allergies, str):
        declared_allergies = [declared_allergies]
    if not isinstance(declared_allergies, list):
        declared_allergies = []
    declared_allergies = list(dict.fromkeys(
        [str(item).strip() for item in saved_profile.get("allergies", []) if str(item).strip()]
        + [str(item).strip() for item in declared_allergies if str(item).strip()]
    ))
    ocr_evidence = extract_ocr_evidence(
        image_path, declared_allergies, result.ingredients_detected
    )
    result.ocr_evidence = ocr_evidence

    # Independent OCR can trigger a transparent, deterministic check when it
    # reads the declared allergen more clearly than the vision model did.
    for match in ocr_evidence.get("allergen_matches", []):
        if match.get("confidence", 0) < 0.65:
            continue
        allergy = match["allergen"]
        line = match["line"]
        if match["kind"] == "advisory":
            if result.verdict != "AVOID":
                result.verdict = "CAUTION"
                result.summary = f"The label has a possible cross-contact warning for {allergy}. Verify the full package before eating."
                result.flagged.append({"ingredient": allergy, "reason": f"OCR evidence: {line}"})
        else:
            result.verdict = "AVOID"
            result.summary = f"Avoid this product: local OCR read {allergy} on the label, matching your stated allergy."
            if not any(str(item.get("ingredient", "")).lower() == allergy.lower() for item in result.flagged):
                result.flagged.append({"ingredient": allergy, "reason": f"Independent OCR evidence: {line}"})

    if (
        ocr_evidence.get("status") == "available"
        and declared_allergies
        and not ocr_evidence.get("panel_coverage", {}).get("allergen_statement")
        and result.verdict != "AVOID"
    ):
        result.verdict = "CAUTION"
        result.summary = "Local OCR could not verify the package allergen statement. Include that panel in a clearer photo before relying on this scan."

    if ocr_evidence.get("status") == "available":
        ocr_text = " ".join(line["text"].lower() for line in ocr_evidence.get("lines", []))
        unconfirmed = [
            item["ingredient"] for item in result.flagged
            if item["ingredient"].lower() not in ocr_text
        ]
        ocr_evidence["unconfirmed_model_flags"] = unconfirmed

    # Barcode data is a second evidence source. A disagreement cannot turn a
    # result SAFE; it lowers confidence and asks the user to verify the package.
    barcode_evidence = enrich_with_barcode(
        image_path, result.ingredients_detected, result.product_name
    )
    result.product_lookup = barcode_evidence
    if barcode_evidence["status"] == "matched_with_discrepancy":
        result.verdict = "CAUTION" if result.verdict == "SAFE" else result.verdict
        result.confidence = "low"
        discrepancies = ", ".join(barcode_evidence["ingredient_discrepancies"][:4])
        result.summary = (
            "The label photo and barcode product record disagree about ingredients "
            f"({discrepancies}). Check the package before relying on this result."
        )
        result.notes = "Open Food Facts is community-contributed and is used only as a cross-check."

    # 8. Log scan
    if log_result:
        try:
            log_scan(
                product="",
                verdict=result.verdict,
                flagged=result.flagged,
                summary=result.summary,
            )
        except Exception as e:
            print(f"[model] log_scan failed (non-fatal): {e}")

    print(f"[timing] total analysis: {time.perf_counter() - started_at:.2f}s")
    return result
