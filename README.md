# LabelWise

LabelWise helps people compare a food label with allergies, health considerations, and preferences they share. The current prototype uses Gemini Flash-Lite for image analysis and local, open-source Whisper for voice transcription. Before analysis, users can review and correct what Whisper heard so a misheard allergy or condition is less likely to silently affect a result. The confirmed transcript is sent with the label image to Gemini; raw audio is not sent to Gemini.

## Stack

- **Web app:** Next.js App Router, React, TypeScript, Tailwind CSS
- **Authentication:** Firebase Authentication with email/password and Google Sign-In
- **API:** FastAPI + Firebase Admin ID-token verification
- **Label analysis:** Gemini `gemini-3.5-flash-lite`, cross-checked with local RapidOCR text evidence and deterministic allergy rules
- **Voice transcription:** Local Whisper `tiny`
- **User profile and scan history:** Per-user JSON files under `data/users/` for this local prototype

The backend verifies every API request with a Firebase ID token and stores data under that token's user ID. Supabase is not needed for the local demo. For a multi-instance deployment, move `data/users/` to a managed database or object store.

## Setup

### 1. Create Firebase configuration

In the Firebase console:

1. Create a Firebase project and add a Web app.
2. Under **Authentication → Sign-in method**, enable **Email/Password** and **Google**.
3. Under **Authentication → Settings → Authorized domains**, add `localhost` for development.
4. Copy the Firebase Web app config values into `web/.env.local` (see below).
5. Create a service account key for local backend verification. Keep its JSON file outside this repository and never commit or share it.

Firebase uses its web SDK for Google sign-in and account creation. The backend uses Firebase Admin to verify ID tokens; see the [Firebase Google sign-in guide](https://firebase.google.com/docs/auth/web/google-signin) and [Admin token verification guide](https://firebase.google.com/docs/auth/admin/verify-id-tokens).

### 2. Configure the Python API

Use Python 3.11 or newer. Create a virtual environment, then install dependencies:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and set:

```dotenv
GOOGLE_API_KEY=your-Gemini-key
FIREBASE_PROJECT_ID=your-firebase-project-id
FIREBASE_SERVICE_ACCOUNT=C:\secure\path\firebase-service-account.json
FRONTEND_ORIGINS=http://localhost:3000
```

Start the API from the repository root:

```powershell
python app.py
```

The API listens on `http://localhost:8000`; it warms Whisper and initializes RapidOCR during startup. RapidOCR reads text locally and returns line boxes and recognition scores for the evidence panel. If OCR packages are missing, scans still work with Gemini, but the UI marks independent OCR evidence unavailable. Install the Python requirements to enable it.

### 3. Configure and start Next.js

Copy `web/.env.local.example` to `web/.env.local` and fill in the Firebase Web app values:

```dotenv
NEXT_PUBLIC_FIREBASE_API_KEY=...
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
NEXT_PUBLIC_FIREBASE_APP_ID=...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Then run the frontend:

```powershell
cd web
npm install
npm run dev
```

Open `http://localhost:3000`. Next.js currently requires Node.js 20.9 or newer; see the [Next.js setup guide](https://nextjs.org/docs/app/getting-started/installation).

### Firebase console details

The Firebase Web API key and app ID are client configuration values, not service-account credentials. Never put the Firebase Admin service-account JSON or Gemini API key in a `NEXT_PUBLIC_` variable. Keep `.env`, `web/.env.local`, and the service-account JSON private.

## App flow

1. Landing page explains the product.
2. Login and sign-up support email/password and **Continue with Google**.
3. Signed-in users reach the dashboard, where they can save restrictions, upload a label image, and record or upload a voice note. Local Whisper transcribes the note; users review and confirm the text before the scan proceeds.
4. The API verifies the Firebase ID token, runs analysis, applies local safety checks, and returns the verdict.
5. Profile and history are stored in a UID-scoped folder under `data/users/`.

## Safety behavior

The app can return **SAFE**, **CAUTION**, or **AVOID**. Incomplete label photos, unverified allergen warnings, or diabetes-related carbohydrate uncertainty should lead to caution. The result is a reading aid, not medical advice; users with severe allergies should verify the full package and contact the manufacturer if needed.

