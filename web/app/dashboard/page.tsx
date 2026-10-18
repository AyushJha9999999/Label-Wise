"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { signOut } from "firebase/auth";
import { Activity, ArrowRight, BadgeCheck, Camera, Check, Clock3, FileImage, History, Leaf, LoaderCircle, LogOut, ShieldAlert, ShieldCheck, Sparkles, UploadCloud, UserRound, X } from "lucide-react";
import { VoiceRecorder } from "@/components/VoiceRecorder";
import { apiFetch, type HistoryItem, type Profile, type ScanResult } from "@/lib/api";
import { useAuth } from "@/lib/AuthProvider";
import { auth, firebaseConfigured } from "@/lib/firebase";

export default function DashboardPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [image, setImage] = useState<File | null>(null);
  const [imageUrl, setImageUrl] = useState("");
  const [audio, setAudio] = useState<File | null>(null);
  const [voiceTranscript, setVoiceTranscript] = useState("");
  const [transcribingVoice, setTranscribingVoice] = useState(false);
  const [transcriptConfirmed, setTranscriptConfirmed] = useState(false);
  const transcriptRequestId = useRef(0);
  const [profileText, setProfileText] = useState({ allergies: "", conditions: "", preferences: "" });
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [result, setResult] = useState<ScanResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [savingProfile, setSavingProfile] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => { if (!loading && !user) router.replace("/login"); }, [loading, user, router]);
  useEffect(() => {
    if (!user) return;
    const currentUser = user;
    Promise.all([apiFetch<Profile>(currentUser, "/api/profile"), apiFetch<HistoryItem[]>(currentUser, "/api/history")])
      .then(([nextProfile, nextHistory]) => {
        setProfileText({ allergies: nextProfile.allergies.join(", "), conditions: nextProfile.conditions.join(", "), preferences: nextProfile.preferences.join(", ") });
        setHistory(nextHistory);
      })
      .catch((cause) => setError(cause instanceof Error ? cause.message : "Could not load your account data."));
  }, [user]);
  useEffect(() => () => { if (imageUrl) URL.revokeObjectURL(imageUrl); }, [imageUrl]);

  if (loading || !user) return <div className="grid min-h-screen place-items-center bg-[#f8f7f1]"><LoaderCircle className="animate-spin text-[#46765a]" /></div>;

  function chooseImage(file?: File) {
    if (!file) return;
    if (!file.type.startsWith("image/")) { setError("Choose an image file for the label."); return; }
    setError(""); setResult(null); setImage(file); setImageUrl(URL.createObjectURL(file));
  }

  function chooseAudio(file: File | null) {
    if (!user) return;
    const currentUser = user;
    const requestId = ++transcriptRequestId.current;
    setAudio(file);
    setVoiceTranscript("");
    setTranscriptConfirmed(false);
    setError("");
    if (!file) { setTranscribingVoice(false); return; }

    setTranscribingVoice(true);
    const body = new FormData();
    body.append("audio", file);
    void apiFetch<{ transcript: string }>(currentUser, "/api/transcribe", { method: "POST", body })
      .then(({ transcript }) => {
        if (requestId === transcriptRequestId.current) {
          setVoiceTranscript(transcript === "[No speech detected in the voice note]" ? "" : transcript);
        }
      })
      .catch((cause) => {
        if (requestId === transcriptRequestId.current) {
          setError(cause instanceof Error ? cause.message : "Could not transcribe your voice note.");
        }
      })
      .finally(() => {
        if (requestId === transcriptRequestId.current) setTranscribingVoice(false);
      });
  }

  async function saveProfile(event: FormEvent) {
    if (!user) return;
    event.preventDefault(); setError(""); setNotice(""); setSavingProfile(true);
    try {
      await apiFetch<Profile>(user, "/api/profile", {
        method: "PUT",
        body: JSON.stringify({
          allergies: split(profileText.allergies), conditions: split(profileText.conditions), preferences: split(profileText.preferences),
        }),
      });
      setNotice("Your dietary profile is saved privately to your account.");
    } catch (cause) { setError(cause instanceof Error ? cause.message : "Could not save profile."); }
    finally { setSavingProfile(false); }
  }

  async function runScan(event: FormEvent) {
    if (!user) return;
    event.preventDefault(); setError(""); setNotice(""); setResult(null);
    if (!image || !audio) { setError("Add a label photo and a voice note to start your scan."); return; }
    if (transcribingVoice) { setError("Wait for Whisper to finish transcribing your voice note."); return; }
    if (!voiceTranscript.trim() || !transcriptConfirmed) { setError("Review and confirm the voice transcript before scanning."); return; }
    setBusy(true);
    try {
      const body = new FormData(); body.append("image", image); body.append("audio", audio); body.append("voice_text", voiceTranscript.trim());
      const next = await apiFetch<ScanResult>(user, "/api/analyze", { method: "POST", body });
      setResult(next); setHistory(await apiFetch<HistoryItem[]>(user, "/api/history"));
    } catch (cause) { setError(cause instanceof Error ? cause.message : "The scan could not be completed."); }
    finally { setBusy(false); }
  }

  async function logout() { if (auth) await signOut(auth); router.replace("/"); }
  async function switchAccount() { if (auth) await signOut(auth); router.replace("/login"); }

  return <main className="label-check-page relative isolate min-h-screen bg-transparent">
    <video className="dashboard-atmosphere-video" autoPlay muted loop playsInline preload="metadata" aria-hidden="true" tabIndex={-1}>
      <source src="/videos/labelwise-check-background.mp4" type="video/mp4" />
    </video>
    <div className="dashboard-atmosphere-overlay" />
    <header className="sticky top-0 z-20 border-b border-[#e7ece5] bg-[#fbfcf9]/90 backdrop-blur-xl"><div className="shell flex h-[72px] items-center justify-between">
      <Link href="/" className="brand-link inline-flex items-center gap-2.5 font-bold text-[#173d2e]"><span className="brand-icon grid size-9 place-items-center rounded-xl bg-[#dceee2] text-[#21563f]"><Leaf size={18} /></span><span className="brand-word text-lg">labelwise<span className="brand-dot text-[#85a893]">.</span></span></Link>
      <div className="flex items-center gap-2"><div className="hidden text-right sm:block"><div className="text-xs font-bold text-[#365242]">{user.displayName || user.email}</div><div className="text-[10px] text-[#8a978d]">Personal workspace</div></div><div className="grid size-9 place-items-center rounded-full bg-[#e7efe7] text-[#3c7150]"><UserRound size={17} /></div><button onClick={switchAccount} aria-label="Switch account" className="inline-flex items-center gap-2 rounded-full border border-[#dce5de] px-3.5 py-2 text-xs font-semibold text-[#557061] hover:bg-white"><UserRound size={14} /><span>Switch account</span></button><button onClick={logout} className="inline-flex items-center gap-2 rounded-full border border-[#dce5de] px-3.5 py-2 text-xs font-semibold text-[#557061] hover:bg-white"><LogOut size={14} /><span className="hidden sm:inline">Sign out</span></button></div>
    </div></header>

    <div className="shell relative z-10 py-9 sm:py-12">
      <div className="mb-8 flex flex-col justify-between gap-4 sm:flex-row sm:items-end"><div><div className="eyebrow">Your food clarity workspace</div><h1 className="serif mt-3 text-4xl text-[#183b2d] sm:text-[48px]">Good to see you, {(user.displayName || "there").split(" ")[0]}.</h1><p className="mt-2 text-sm text-[#77847b]">Bring the label. We’ll help you read what’s there—and what isn’t.</p></div><div className="flex items-center gap-2 rounded-full border border-[#e1e9e1] bg-white px-3.5 py-2 text-[11px] font-semibold text-[#66806e]"><Activity size={14} className="text-[#5a966b]" /> Gemini Flash-Lite · Whisper voice notes</div></div>

      {!firebaseConfigured && <div className="mb-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">Firebase web configuration is missing. Add your values in <code>web/.env.local</code> and restart Next.js.</div>}
      {error && <div role="alert" className="mb-5 flex items-start gap-3 rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800"><ShieldAlert size={17} className="mt-0.5 shrink-0" /><span>{error}</span><button className="ml-auto" onClick={() => setError("")} aria-label="Dismiss"><X size={16} /></button></div>}
      {notice && <div className="mb-5 flex items-center gap-2 rounded-2xl border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800"><Check size={16} />{notice}</div>}

      <div className="grid items-start gap-6 lg:grid-cols-[minmax(0,1.12fr)_minmax(330px,.88fr)]">
        <div className="space-y-6">
          <form onSubmit={runScan} className="card overflow-hidden">
            <div className="flex items-start justify-between border-b border-[#edf0eb] px-6 py-5 sm:px-8"><div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-[#82958a]">New analysis</div><h2 className="mt-1 text-xl font-bold text-[#244332]">Scan a food label</h2></div><span className="grid size-10 place-items-center rounded-xl bg-[#edf5ed] text-[#4f8060]"><ScanIcon /></span></div>
            <div className="space-y-6 p-6 sm:p-8">
              <div><div className="mb-2 flex items-center justify-between"><label className="text-xs font-bold text-[#3f5949]">01 · Label photo</label><span className="text-[10px] text-[#92a096]">Ingredients + allergen + nutrition panels</span></div>
                <div role="button" tabIndex={0} onClick={() => fileRef.current?.click()} onKeyDown={(e) => { if (e.key === "Enter") fileRef.current?.click(); }} onDragOver={(e) => e.preventDefault()} onDrop={(e) => { e.preventDefault(); chooseImage(e.dataTransfer.files[0]); }} className="group relative flex min-h-[220px] cursor-pointer items-center justify-center overflow-hidden rounded-2xl border border-dashed border-[#b9ccbe] bg-[#f8fbf7] transition hover:border-[#59866a] hover:bg-[#f3f9f3]">
                  {imageUrl ? <><img src={imageUrl} alt="Selected food label" className="absolute inset-0 h-full w-full object-contain p-3" /><div className="absolute bottom-3 right-3 rounded-full bg-white/95 px-3 py-1.5 text-[10px] font-bold text-[#45604e] shadow">Change photo</div></> : <div className="px-6 py-8 text-center"><div className="mx-auto grid size-12 place-items-center rounded-2xl bg-[#e6f1e6] text-[#4c805b]"><UploadCloud size={22} /></div><div className="mt-3 text-sm font-bold text-[#385342]">Drop a label photo here</div><div className="mt-1 text-xs text-[#89968c]">or click to browse · PNG, JPG, WEBP</div><div className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-[#e0e9e0] bg-white px-3 py-1.5 text-[10px] font-semibold text-[#617c69]"><Camera size={13} /> Clear, straight-on photos work best</div></div>}
                  <input ref={fileRef} className="sr-only" type="file" accept="image/*" onChange={(e) => chooseImage(e.target.files?.[0])} />
                </div>
              </div>
              <div><label className="mb-2 block text-xs font-bold text-[#3f5949]">02 · Your voice note</label><VoiceRecorder file={audio} onChange={chooseAudio} /></div>
              {audio && <div className="rounded-2xl border border-[#dfe9df] bg-[#f3f8f1] p-4">
                <div className="flex items-center gap-2 text-xs font-bold text-[#365a42]">{transcribingVoice ? <><LoaderCircle size={14} className="animate-spin" /> Whisper is transcribing locally…</> : <>Review what Whisper heard</>}</div>
                <label htmlFor="voice-transcript" className="mt-3 block text-[11px] font-semibold text-[#617568]">Your dietary note (edit any mistakes)</label>
                <textarea id="voice-transcript" rows={3} value={voiceTranscript} disabled={transcribingVoice} onChange={(event) => { setVoiceTranscript(event.target.value); setTranscriptConfirmed(false); }} placeholder="If no words were detected, type your allergies, conditions, or preferences here." className="input-field mt-1.5 min-h-20 resize-y !rounded-xl text-xs leading-5" />
                <label className="mt-3 flex cursor-pointer items-start gap-2 text-[11px] leading-4 text-[#536c5b]"><input type="checkbox" className="mt-0.5 accent-[#285d42]" checked={transcriptConfirmed} disabled={transcribingVoice || !voiceTranscript.trim()} onChange={(event) => setTranscriptConfirmed(event.target.checked)} /><span>I checked this text. It correctly states the dietary information I want considered.</span></label>
                <p className="mt-2 text-[10px] leading-4 text-[#87968a]">Whisper is open-source and runs on this server. Only the text you confirm is sent with the label for analysis.</p>
              </div>}
              <button disabled={busy || transcribingVoice || (!!audio && (!voiceTranscript.trim() || !transcriptConfirmed))} className="button-primary w-full !rounded-xl !py-3.5">{busy ? <><LoaderCircle className="animate-spin" size={17} /> Reading the label…</> : transcribingVoice ? <><LoaderCircle className="animate-spin" size={17} /> Transcribing your note…</> : <>Check this product <ArrowRight size={16} /></>}</button>
              <p className="-mt-3 text-center text-[10px] leading-4 text-[#95a097]">Review the transcribed note before the scan. Don’t use this as a substitute for medical advice.</p>
            </div>
          </form>

          <section className="card p-6 sm:p-8"><div className="flex items-start justify-between"><div><div className="text-[10px] font-bold uppercase tracking-[.16em] text-[#82958a]">Remembered for your account</div><h2 className="mt-1 text-xl font-bold text-[#244332]">Your dietary profile</h2><p className="mt-1 text-xs text-[#829087]">Saved privately under your sign-in.</p></div><div className="grid size-10 place-items-center rounded-xl bg-[#f1f3e9] text-[#838151]"><ShieldCheck size={19} /></div></div>
            <form onSubmit={saveProfile} className="mt-5 space-y-3"><ProfileInput label="Allergies" placeholder="e.g. peanuts, milk" value={profileText.allergies} onChange={(v) => setProfileText({ ...profileText, allergies: v })} /><ProfileInput label="Conditions" placeholder="e.g. diabetes" value={profileText.conditions} onChange={(v) => setProfileText({ ...profileText, conditions: v })} /><ProfileInput label="Preferences" placeholder="e.g. vegetarian, halal" value={profileText.preferences} onChange={(v) => setProfileText({ ...profileText, preferences: v })} /><div className="flex justify-end pt-1"><button disabled={savingProfile} className="button-secondary !px-4 !py-2.5 text-xs">{savingProfile ? "Saving…" : "Save profile"}</button></div></form>
          </section>
        </div>

        <aside className="space-y-6 lg:sticky lg:top-[94px]">
          {result ? <ResultCard result={result} imageUrl={imageUrl} /> : <div className="card flex min-h-[300px] flex-col items-center justify-center p-8 text-center"><div className="grid size-14 place-items-center rounded-2xl bg-[#edf5ed] text-[#5b8a68]"><Sparkles size={24} /></div><h2 className="mt-4 text-base font-bold text-[#385342]">Your result will appear here</h2><p className="mt-2 max-w-[270px] text-xs leading-5 text-[#849188]">Upload the complete label when possible. Missing panels can change what we can confirm.</p></div>}
          <section className="card overflow-hidden"><div className="flex items-center justify-between border-b border-[#edf0eb] px-5 py-4"><div className="flex items-center gap-2 text-sm font-bold text-[#355140]"><History size={16} /> Recent scans</div><span className="text-[10px] font-semibold text-[#91a096]">{history.length} saved</span></div>
            {history.length ? <div className="divide-y divide-[#f0f2ed]">{history.slice(0, 6).map((item, i) => <div key={`${item.timestamp}-${i}`} className="flex gap-3 px-5 py-3.5"><VerdictDot verdict={item.verdict} /><div className="min-w-0 flex-1"><div className="flex items-center justify-between gap-2"><span className="text-[10px] font-bold tracking-wide text-[#64766a]">{item.verdict}</span><span className="inline-flex shrink-0 items-center gap-1 text-[9px] text-[#9aa49c]"><Clock3 size={10} />{new Date(item.timestamp).toLocaleDateString()}</span></div><p className="mt-1 line-clamp-2 text-[11px] leading-4 text-[#7e8a81]">{item.summary}</p></div></div>)}</div> : <p className="px-5 py-7 text-center text-xs text-[#98a29a]">Your scans will show up here.</p>}
          </section>
          <div className="rounded-2xl border border-[#e2e9de] bg-[#edf4e9] p-4"><div className="flex gap-2.5"><BadgeCheck size={16} className="mt-0.5 shrink-0 text-[#5b8a62]" /><p className="text-[10px] leading-[1.6] text-[#627466]">LabelWise is a reading aid. For serious allergies, confirm the complete package and contact the manufacturer if anything is unclear.</p></div></div>
        </aside>
      </div>
      <footer className="mt-10 flex flex-col justify-between gap-2 border-t border-[#e5eae3] py-5 text-[10px] text-[#9aa49c] sm:flex-row"><span>LabelWise · Food label assistant</span><span>Your account history is stored separately by user on this app’s server.</span></footer>
    </div>
  </main>;
}

function split(value: string) { return value.split(",").map((part) => part.trim()).filter(Boolean); }
function ProfileInput({ label, placeholder, value, onChange }: { label: string; placeholder: string; value: string; onChange: (value: string) => void }) { return <label className="block text-[11px] font-semibold text-[#687c6e]">{label}<input className="input-field mt-1.5 !rounded-xl !py-2.5 text-xs" placeholder={placeholder} value={value} onChange={(e) => onChange(e.target.value)} /></label>; }
function ScanIcon() { return <FileImage size={19} />; }
function VerdictDot({ verdict }: { verdict: string }) { const color = verdict === "SAFE" ? "bg-emerald-500" : verdict === "AVOID" ? "bg-rose-500" : "bg-amber-500"; return <span className={`mt-1 size-2 shrink-0 rounded-full ${color}`} />; }
function ResultCard({ result, imageUrl }: { result: ScanResult; imageUrl: string }) {
  const type = result.verdict.toLowerCase();
  const Icon = result.verdict === "SAFE" ? ShieldCheck : result.verdict === "AVOID" ? ShieldAlert : Activity;
  return <section className={`card result-${type} overflow-hidden border p-6 sm:p-7`}>
    <div className="flex items-center justify-between"><div className="text-[10px] font-bold uppercase tracking-[.17em] text-[#718276]">Analysis result</div><span className="rounded-full border border-current/15 bg-white/70 px-3 py-1 text-[9px] font-bold uppercase tracking-wider text-[#68766b]">{result.confidence} confidence</span></div>
    <div className="mt-4 flex items-center gap-3"><span className={`grid size-12 place-items-center rounded-2xl ${result.verdict === "SAFE" ? "bg-[#d9f0df] text-[#328050]" : result.verdict === "AVOID" ? "bg-[#ffe0dc] text-[#b84c41]" : "bg-[#ffedc9] text-[#9b6d1d]"}`}><Icon size={23} /></span><div><div className="text-[10px] font-bold uppercase tracking-[.14em] text-[#89958b]">Verdict</div><h2 className={`text-3xl font-black tracking-tight ${result.verdict === "SAFE" ? "text-[#328050]" : result.verdict === "AVOID" ? "text-[#b84c41]" : "text-[#a36d12]"}`}>{result.verdict}</h2></div></div>
    <p className="mt-4 text-sm leading-6 text-[#405549]">{result.summary}</p>
    {result.flagged.length > 0 && <div className="mt-4 space-y-2">{result.flagged.map((flag, i) => <div key={i} className="rounded-xl border border-white/70 bg-white/70 p-3"><div className="text-xs font-bold text-[#7c433d]">{flag.ingredient}</div><p className="mt-1 text-[11px] leading-4 text-[#7a716c]">{flag.reason}</p></div>)}</div>}
    {result.ingredients_detected.length > 0 && <div className="mt-4 rounded-xl border border-white/70 bg-white/65 p-3"><div className="text-[9px] font-bold uppercase tracking-wider text-[#839087]">Ingredients detected</div><p className="mt-1 text-[11px] leading-5 text-[#58685c]">{result.ingredients_detected.join(" · ")}</p></div>}
    {result.ocr_evidence && <EvidencePanel evidence={result.ocr_evidence} imageUrl={imageUrl} />}
    {result.product_lookup && <div className="mt-4 rounded-xl border border-white/70 bg-white/65 p-3"><div className="text-[9px] font-bold uppercase tracking-wider text-[#839087]">Barcode cross-check</div>{result.product_lookup.status === "not_detected" ? <p className="mt-1 text-[11px] text-[#58685c]">No barcode detected in this photo.</p> : result.product_lookup.status === "unavailable_or_not_found" ? <p className="mt-1 text-[11px] text-[#58685c]">Barcode {result.product_lookup.barcode} detected, but no product record was returned. It may be missing from the database or the lookup may be unavailable.</p> : result.product_lookup.status === "identity_unverified" ? <><p className="mt-1 text-[11px] font-semibold text-[#405549]">{result.product_lookup.product?.name || "Product record found"}{result.product_lookup.product?.brands ? ` · ${result.product_lookup.product.brands}` : ""}</p><p className="mt-1 text-[11px] leading-4 text-[#9b6d1d]">We couldn’t verify this is the same product shown in the photo, so its ingredients were not compared. Check the barcode and package. Database records are community contributed.</p></> : <><p className="mt-1 text-[11px] font-semibold text-[#405549]">{result.product_lookup.product?.name || "Product found"}{result.product_lookup.product?.brands ? ` · ${result.product_lookup.product.brands}` : ""}</p>{result.product_lookup.ingredient_discrepancies.length > 0 ? <p className="mt-1 text-[11px] leading-4 text-[#9b6d1d]">Possible ingredient mismatch: {result.product_lookup.ingredient_discrepancies.join(", ")}. Verify the package. This record is community contributed.</p> : <p className="mt-1 text-[11px] leading-4 text-[#7a867c]">No obvious ingredient mismatch found against the community product record. Verify the physical package.</p>}</>}</div>}
    {result.notes && <p className="mt-4 border-t border-black/5 pt-3 text-[10px] leading-4 text-[#7e837b]">{result.notes}</p>}
  </section>;
}

function EvidencePanel({ evidence, imageUrl }: { evidence: NonNullable<ScanResult["ocr_evidence"]>; imageUrl: string }) {
  if (evidence.status !== "available") return <div className="mt-4 rounded-xl border border-amber-200 bg-amber-50 p-3"><div className="text-[9px] font-bold uppercase tracking-wider text-[#8c6827]">Independent OCR evidence</div><p className="mt-1 text-[11px] leading-4 text-[#716342]">{evidence.status === "unavailable" ? "Local OCR is not installed in the backend environment. From the LabelWise folder, run python -m pip install -r requirements.txt, then restart the backend to enable evidence highlighting." : "Local OCR could not read this image. Check that the label is clear and well lit."}</p></div>;
  const size = evidence.image_size;
  const marks = [
    ...evidence.allergen_matches.map((item) => ({ bbox: item.bbox, label: `${item.allergen} evidence`, color: "#df493c" })),
    ...(evidence.nutrition_matches || []).map((item) => ({ bbox: item.bbox, label: "nutrition evidence", color: "#d38a16" })),
  ].filter((item) => item.bbox);
  const coverage = evidence.panel_coverage;
  return <div className="mt-4 rounded-xl border border-[#dce8dc] bg-white/75 p-3"><div className="text-[9px] font-bold uppercase tracking-wider text-[#52715b]">Evidence from local OCR</div><p className="mt-1 text-[10px] leading-4 text-[#6f7c70]">{evidence.engine} independently read {evidence.lines.length} text lines. Colored boxes mark allergy and nutrition evidence; OCR confidence is a recognition score, not a safety probability.</p>
    {imageUrl && size && marks.length > 0 && <div role="img" aria-label="Label photo with OCR evidence highlighted" className="relative mt-3 h-64 w-full overflow-hidden rounded-lg bg-[#f2f3ed] bg-contain bg-center bg-no-repeat" style={{ backgroundImage: `url("${imageUrl}")` }}><svg className="pointer-events-none absolute inset-0 h-full w-full" viewBox={`0 0 ${size.width} ${size.height}`} preserveAspectRatio="xMidYMid meet" aria-hidden="true">{marks.map((mark, index) => { const [x1, y1, x2, y2] = mark.bbox!; return <rect key={`${mark.label}-${index}`} x={x1} y={y1} width={Math.max(1, x2 - x1)} height={Math.max(1, y2 - y1)} fill={mark.color} fillOpacity="0.12" stroke={mark.color} strokeWidth={Math.max(2, size.width / 400)} />; })}</svg><div className="absolute bottom-2 left-2 flex gap-2 rounded-md bg-white/90 px-2 py-1 text-[9px]"><span className="font-semibold text-[#df493c]">Red: allergy evidence</span><span className="font-semibold text-[#b5750f]">Amber: nutrition</span></div></div>}
    {evidence.allergen_matches.length > 0 && <div className="mt-3 space-y-1.5">{evidence.allergen_matches.map((match, index) => <p key={`${match.allergen}-${index}`} className="rounded-lg bg-rose-50 px-2.5 py-2 text-[10px] leading-4 text-[#82433b]">OCR read “{match.line}” for {match.allergen} ({Math.round(match.confidence * 100)}% text confidence; {match.kind === "advisory" ? "cross-contact advisory" : "label text"}).</p>)}</div>}
    <div className="mt-3 flex flex-wrap gap-1.5">{([['ingredients', 'Ingredients'], ['allergen_statement', 'Allergen statement'], ['nutrition', 'Nutrition']] as const).map(([key, label]) => <span key={key} className={`rounded-full px-2 py-1 text-[9px] font-semibold ${coverage[key] ? "bg-emerald-50 text-emerald-700" : "bg-amber-50 text-amber-800"}`}>{coverage[key] ? "Seen:" : "Not verified:"} {label}</span>)}</div>
    {evidence.unconfirmed_model_flags && evidence.unconfirmed_model_flags.length > 0 && <p className="mt-2 text-[10px] leading-4 text-amber-800">Gemini flagged {evidence.unconfirmed_model_flags.join(", ")}, but local OCR did not find those exact words. Inspect the highlighted text or retake the photo.</p>}
    <details className="mt-3"><summary className="cursor-pointer text-[10px] font-semibold text-[#52715b]">Review all OCR text ({evidence.lines.length} lines)</summary><div className="mt-2 max-h-40 space-y-1 overflow-auto rounded-lg bg-[#f6f7f2] p-2">{evidence.lines.map((line, index) => <p key={index} className="text-[10px] leading-4 text-[#58685c]">{line.text}<span className="ml-1 text-[#9aa49c]">{Math.round(line.confidence * 100)}%</span></p>)}</div></details>
  </div>;
}
