import type { User } from "firebase/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function apiFetch<T>(user: User, path: string, init: RequestInit = {}): Promise<T> {
  const send = async (forceRefresh: boolean) => {
    const token = await user.getIdToken(forceRefresh);
    const headers = new Headers(init.headers);
    headers.set("Authorization", `Bearer ${token}`);
    if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
    return fetch(`${API_URL}${path}`, { ...init, headers });
  };

  let response = await send(false);
  if (response.status === 401) response = await send(true);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export type Profile = { allergies: string[]; conditions: string[]; preferences: string[]; last_updated?: string | null };
export type ScanResult = {
  verdict: "SAFE" | "CAUTION" | "AVOID";
  summary: string;
  ingredients_detected: string[];
  flagged: { ingredient: string; reason: string }[];
  user_restrictions: Record<string, string[]>;
  confidence: string;
  notes: string;
  product_lookup?: {
    status: "not_detected" | "unavailable_or_not_found" | "identity_unverified" | "matched" | "matched_with_discrepancy";
    barcode: string | null;
    product: { name: string; brands: string; ingredients_text: string; carbohydrates_100g: number | string | null; source: string } | null;
    ingredient_discrepancies: string[];
  };
  ocr_evidence?: {
    status: "available" | "unavailable" | "error";
    engine?: string;
    image_size?: { width: number; height: number };
    lines: { text: string; confidence: number; bbox: [number, number, number, number] | null }[];
    allergen_matches: { allergen: string; matched_text: string; line: string; confidence: number; bbox: [number, number, number, number] | null; kind: string }[];
    nutrition_matches?: { line: string; confidence: number; bbox: [number, number, number, number] | null }[];
    panel_coverage: { ingredients?: boolean; allergen_statement?: boolean; nutrition?: boolean };
    unconfirmed_model_flags?: string[];
  };
};
export type HistoryItem = { timestamp: string; verdict: string; summary: string; flagged: { ingredient: string; reason: string }[] };
