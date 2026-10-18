"""FastAPI backend for the LabelWise Next.js app."""

import base64
import json
import os
import tempfile
import threading
from pathlib import Path

import firebase_admin
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from firebase_admin import auth as firebase_auth, credentials
from pydantic import BaseModel, Field

from src.model import analyze_label, transcribe_voice_note, warmup_models
from src import user_store


_firebase_app_init_lock = threading.Lock()


def _origins() -> list[str]:
    return [item.strip() for item in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000").split(",") if item.strip()]


def _token_diagnostic(token: str) -> str:
    """Return only non-user-identifying token metadata for local auth debugging."""
    try:
        header_part, payload_part, _ = token.split(".", 2)

        def decode(part: str) -> dict:
            padded = part + "=" * (-len(part) % 4)
            return json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))

        header = decode(header_part)
        payload = decode(payload_part)
        project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
        return (
            f"audience_matches_project={payload.get('aud') == project_id}, "
            f"issuer_matches_project={payload.get('iss') == f'https://securetoken.google.com/{project_id}'}, "
            f"algorithm={header.get('alg')!r}, signing_key_id_present={bool(header.get('kid'))}"
        )
    except Exception:
        return "token_metadata=unreadable"


def _token_failure_diagnostic(exc: Exception) -> str:
    """Describe token verification failure without logging token or claim values."""
    chain: list[BaseException] = []
    current: BaseException | None = exc
    while current is not None and len(chain) < 4:
        chain.append(current)
        current = current.__cause__ or current.__context__

    names = "->".join(type(item).__name__ for item in chain)
    messages = " ".join(str(item).lower() for item in chain)
    if "token expired" in messages or any(type(item).__name__ == "ExpiredIdTokenError" for item in chain):
        category = "expired_token"
    elif "signature" in messages or any(type(item).__name__ == "InvalidSignature" for item in chain):
        category = "signature_verification_failed"
    elif "used too early" in messages or "issued in the future" in messages or "not yet valid" in messages:
        category = "token_time_check_failed"
    elif "kid" in messages or "key" in messages and "find" in messages:
        category = "signing_key_lookup_failed"
    else:
        category = "unclassified"
    return f"category={category}, exception_chain={names}"


app = FastAPI(title="LabelWise API", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)


class ProfileBody(BaseModel):
    allergies: list[str] = Field(default_factory=list)
    conditions: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)


def _get_firebase_app():
    try:
        return firebase_admin.get_app()
    except ValueError:
        # Profile and history requests arrive concurrently on first load. Recheck
        # after taking the lock so only one request initializes the default app.
        with _firebase_app_init_lock:
            try:
                return firebase_admin.get_app()
            except ValueError:
                project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
                service_account = os.getenv("FIREBASE_SERVICE_ACCOUNT", "").strip()
                options = {"projectId": project_id} if project_id else None
                if service_account:
                    return firebase_admin.initialize_app(
                        credentials.Certificate(service_account), options=options
                    )
                if project_id:
                    return firebase_admin.initialize_app(options=options)
                raise RuntimeError("Set FIREBASE_PROJECT_ID and FIREBASE_SERVICE_ACCOUNT for backend token verification.")


def current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    try:
        firebase_app = _get_firebase_app()
    except Exception as exc:
        print(f"[auth] Firebase Admin initialization failed ({type(exc).__name__}).", flush=True)
        raise HTTPException(status_code=503, detail="Firebase backend configuration could not be loaded.") from exc

    try:
        # Client-issued tokens can arrive a few seconds before the verifier's
        # clock reaches their `iat`; tolerate limited clock skew while still
        # enforcing signature, issuer, audience, and expiry checks.
        claims = firebase_auth.verify_id_token(
            token, app=firebase_app, clock_skew_seconds=30
        )
    except firebase_auth.CertificateFetchError as exc:
        # Distinguish network/certificate-service failures from invalid sessions.
        print("[auth] Firebase signing-certificate fetch failed; check backend internet access.", flush=True)
        raise HTTPException(status_code=503, detail="Could not reach Firebase to verify your session. Please retry.") from exc
    except Exception as exc:
        # Keep credentials and token contents out of logs; the exception class is
        # enough to identify the common verification failure without exposing secrets.
        print(f"[auth] Firebase ID-token verification failed ({type(exc).__name__}).", flush=True)
        if isinstance(exc, firebase_auth.InvalidIdTokenError):
            print(f"[auth] Safe token metadata: {_token_diagnostic(token)}.", flush=True)
            print(f"[auth] Safe verification detail: {_token_failure_diagnostic(exc)}.", flush=True)
        raise HTTPException(status_code=401, detail="Your session expired. Please sign in again.") from exc
    return {"uid": claims["uid"], "email": claims.get("email", ""), "name": claims.get("name", "")}


@app.on_event("startup")
async def startup() -> None:
    # Cache the local speech model before the user's first scan.
    await run_in_threadpool(warmup_models)


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "model": os.getenv("LABELWISE_MODEL", "gemini-3.5-flash-lite")}


@app.get("/api/me")
def me(user: dict = Depends(current_user)) -> dict:
    return user


@app.get("/api/profile")
def profile(user: dict = Depends(current_user)) -> dict:
    return user_store.get_profile(user["uid"])


@app.put("/api/profile")
def update_profile(body: ProfileBody, user: dict = Depends(current_user)) -> dict:
    return user_store.save_profile(
        user["uid"], body.allergies, body.conditions, body.preferences
    )


@app.get("/api/history")
def history(user: dict = Depends(current_user)) -> list[dict]:
    return user_store.get_history(user["uid"])


@app.post("/api/transcribe")
async def transcribe(audio: UploadFile = File(...), user: dict = Depends(current_user)) -> dict:
    audio_bytes = await audio.read(20 * 1024 * 1024 + 1)
    if len(audio_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be smaller than 20 MB.")

    audio_suffix = Path(audio.filename or "voice.wav").suffix.lower()
    if audio_suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".webm"}:
        audio_suffix = ".wav"

    with tempfile.TemporaryDirectory(prefix="labelwise-voice-") as temp_dir:
        audio_path = Path(temp_dir) / f"voice{audio_suffix}"
        audio_path.write_bytes(audio_bytes)
        try:
            transcript = await run_in_threadpool(transcribe_voice_note, str(audio_path))
        except Exception as exc:
            print(f"[model] Local Whisper transcription failed ({type(exc).__name__}).", flush=True)
            raise HTTPException(status_code=422, detail="Could not transcribe that voice note. Try a clearer recording.") from exc

    return {"transcript": transcript}


@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    audio: UploadFile = File(...),
    voice_text: str | None = Form(default=None),
    user: dict = Depends(current_user),
) -> dict:
    image_bytes = await image.read(15 * 1024 * 1024 + 1)
    audio_bytes = await audio.read(20 * 1024 * 1024 + 1)
    if len(image_bytes) > 15 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Image must be smaller than 15 MB.")
    if len(audio_bytes) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Audio must be smaller than 20 MB.")

    image_suffix = Path(image.filename or "label.jpg").suffix.lower()
    if image_suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        image_suffix = ".jpg"
    audio_suffix = Path(audio.filename or "voice.wav").suffix.lower()
    if audio_suffix not in {".wav", ".mp3", ".m4a", ".ogg", ".webm"}:
        audio_suffix = ".wav"

    with tempfile.TemporaryDirectory(prefix="labelwise-") as temp_dir:
        image_path = Path(temp_dir) / f"label{image_suffix}"
        audio_path = Path(temp_dir) / f"voice{audio_suffix}"
        image_path.write_bytes(image_bytes)
        audio_path.write_bytes(audio_bytes)
        saved_profile = user_store.get_profile(user["uid"])
        try:
            result = await run_in_threadpool(
                analyze_label, str(image_path), str(audio_path), saved_profile, False, voice_text
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Analysis failed: {exc}") from exc

    payload = {
        "verdict": result.verdict,
        "summary": result.summary,
        "ingredients_detected": result.ingredients_detected,
        "flagged": result.flagged,
        "user_restrictions": result.user_restrictions,
        "confidence": result.confidence,
        "notes": result.notes,
        "product_lookup": getattr(result, "product_lookup", None),
        "ocr_evidence": getattr(result, "ocr_evidence", None),
    }
    user_store.log_scan(user["uid"], payload)
    return payload
