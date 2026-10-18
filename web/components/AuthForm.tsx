"use client";

import Link from "next/link";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { createUserWithEmailAndPassword, GoogleAuthProvider, signInWithEmailAndPassword, signInWithPopup, updateProfile } from "firebase/auth";
import { ArrowLeft, Eye, EyeOff, Leaf, LoaderCircle, LockKeyhole, Mail } from "lucide-react";
import { auth, firebaseConfigured } from "@/lib/firebase";

export function AuthForm({ mode }: { mode: "login" | "signup" }) {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const signup = mode === "signup";

  async function withBusy(action: () => Promise<unknown>) {
    setError(""); setBusy(true);
    try { await action(); router.replace("/dashboard"); }
    catch (cause) { setError(cause instanceof Error ? cause.message : "Authentication failed. Please try again."); }
    finally { setBusy(false); }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!auth) { setError("Firebase isn’t configured yet. Add the web app keys to web/.env.local."); return; }
    const currentAuth = auth;
    void withBusy(async () => {
      if (signup) {
        const credential = await createUserWithEmailAndPassword(currentAuth, email, password);
        if (name.trim()) await updateProfile(credential.user, { displayName: name.trim() });
      } else await signInWithEmailAndPassword(currentAuth, email, password);
    });
  }

  function googleSignIn() {
    if (!auth) { setError("Firebase isn’t configured yet. Add the web app keys to web/.env.local."); return; }
    const currentAuth = auth;
    const provider = new GoogleAuthProvider();
    provider.setCustomParameters({ prompt: "select_account" });
    void withBusy(() => signInWithPopup(currentAuth, provider));
  }

  return <main className="auth-backdrop min-h-screen px-4 py-6 sm:px-8">
    <header className="mx-auto flex w-full max-w-[1180px] items-center justify-between"><Link href="/" className="brand-link inline-flex items-center gap-2.5 font-bold text-[#173d2e]"><span className="brand-icon grid size-9 place-items-center rounded-xl bg-[#dceee2] text-[#21563f]"><Leaf size={18} /></span><span className="brand-word text-lg">labelwise<span className="brand-dot text-[#85a893]">.</span></span></Link><Link href="/" className="inline-flex items-center gap-2 text-xs font-semibold text-[#64776c]"><ArrowLeft size={15} /> Back to home</Link></header>
    <div className="mx-auto grid min-h-[calc(100vh-100px)] w-full max-w-[1020px] items-center gap-10 py-10 lg:grid-cols-[.92fr_1.08fr]">
      <section className="hidden px-5 lg:block"><div className="eyebrow">Personal food clarity</div><h1 className="serif mt-5 text-5xl leading-[1.08] text-[#183b2d]">Your needs.<br />Your labels.<br /><em className="font-normal text-[#70947a]">One clear place.</em></h1><p className="mt-6 max-w-sm text-sm leading-7 text-[#718076]">Save dietary preferences and review your scan history from one private account.</p><div className="mt-11 rounded-3xl border border-white/90 bg-white/75 p-5 shadow-sm"><div className="text-[10px] font-bold uppercase tracking-[.16em] text-[#829389]">A careful assistant</div><p className="mt-3 text-sm leading-6 text-[#435e4c]">“When a label is incomplete, LabelWise will tell you what it can’t confirm.”</p></div></section>
      <section className="card mx-auto w-full max-w-[470px] p-7 sm:p-10">
        <div className="eyebrow">{signup ? "Start with LabelWise" : "Welcome back"}</div><h2 className="serif mt-3 text-[38px] leading-tight text-[#193d2e]">{signup ? "Create your account" : "Sign in to continue"}</h2><p className="mt-2 text-sm text-[#7b897f]">{signup ? "Your label history will be kept with your account." : "Pick up where your last food scan left off."}</p>
        {!firebaseConfigured && <div className="mt-5 rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900">Firebase setup is needed. Copy <code>web/.env.local.example</code> to <code>web/.env.local</code> and add your Firebase web app values.</div>}
        <button onClick={googleSignIn} disabled={busy} className="button-secondary mt-7 w-full !rounded-xl !py-3.5"><GoogleMark /> Continue with Google</button>
        <div className="my-6 flex items-center gap-3 text-[10px] font-bold uppercase tracking-[.15em] text-[#9ba79e]"><span className="h-px flex-1 bg-[#e8ede8]" />or with email<span className="h-px flex-1 bg-[#e8ede8]" /></div>
        <form onSubmit={submit} className="space-y-4">
          {signup && <label className="block text-xs font-semibold text-[#445d4d]">Name<input className="input-field mt-2" value={name} onChange={(e) => setName(e.target.value)} autoComplete="name" placeholder="Your name" /></label>}
          <label className="block text-xs font-semibold text-[#445d4d]">Email<div className="relative mt-2"><Mail size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#8da194]" /><input className="input-field !pl-11" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" placeholder="you@example.com" /></div></label>
          <label className="block text-xs font-semibold text-[#445d4d]">Password<div className="relative mt-2"><LockKeyhole size={16} className="absolute left-4 top-1/2 -translate-y-1/2 text-[#8da194]" /><input className="input-field !pl-11 !pr-11" type={showPassword ? "text" : "password"} required minLength={6} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete={signup ? "new-password" : "current-password"} placeholder="At least 6 characters" /><button type="button" aria-label={showPassword ? "Hide password" : "Show password"} onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 p-1 text-[#8da194]">{showPassword ? <EyeOff size={16} /> : <Eye size={16} />}</button></div></label>
          {error && <div role="alert" className="rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-xs leading-5 text-rose-800">{error}</div>}
          <button disabled={busy} className="button-primary mt-2 w-full !rounded-xl !py-3.5">{busy ? <><LoaderCircle className="animate-spin" size={17} /> Please wait</> : signup ? "Create account" : "Log in"}</button>
        </form>
        <p className="mt-6 text-center text-xs text-[#718076]">{signup ? "Already have an account?" : "New to LabelWise?"} <Link className="font-bold text-[#285d42] hover:underline" href={signup ? "/login" : "/signup"}>{signup ? "Log in" : "Create an account"}</Link></p>
        <p className="mt-5 text-center text-[10px] leading-5 text-[#97a198]">By continuing, you agree to use LabelWise as a reading aid—not a substitute for checking the package or medical advice.</p>
      </section>
    </div>
  </main>;
}

function GoogleMark() { return <svg aria-hidden="true" width="18" height="18" viewBox="0 0 48 48"><path fill="#FFC107" d="M43.6 24.5c0-1.4-.1-2.8-.4-4.1H24v7.8h11a9.4 9.4 0 0 1-4.1 6.2v5.1h6.6c3.8-3.5 6.1-8.7 6.1-15Z"/><path fill="#34A853" d="M24 44c5.5 0 10.1-1.8 13.5-4.8l-6.6-5.1c-1.8 1.2-4.1 2-6.9 2-5.3 0-9.8-3.6-11.4-8.4H5.8v5.3A20 20 0 0 0 24 44Z"/><path fill="#4A90E2" d="M12.6 27.7a12 12 0 0 1 0-7.4V15H5.8a20 20 0 0 0 0 18l6.8-5.3Z"/><path fill="#EA4335" d="M24 12.1c3 0 5.7 1 7.8 3.1l5.9-5.9A19.7 19.7 0 0 0 24 4 20 20 0 0 0 5.8 15l6.8 5.3c1.6-4.8 6.1-8.2 11.4-8.2Z"/></svg>; }
