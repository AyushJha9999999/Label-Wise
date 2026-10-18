import Link from "next/link";
import { ArrowDown, ArrowRight, AudioLines, Leaf, ScanLine, ShieldCheck, Sparkles } from "lucide-react";

function Brand({ inverse = false }: { inverse?: boolean }) {
  return <Link href="/" className={`brand-link inline-flex items-center gap-2.5 font-bold tracking-tight ${inverse ? "brand-link-inverse text-white" : "text-[#173d2e]"}`}>
    <span className="brand-icon grid size-9 place-items-center rounded-xl bg-[#dceee2] text-[#21563f]"><Leaf size={19} strokeWidth={2.3} /></span>
    <span className="brand-word text-[19px]">labelwise<span className="brand-dot text-[#85a893]">.</span></span>
  </Link>;
}

export default function Home() {
  return <main className="overflow-hidden">
    <section className="landing-hero relative min-h-[720px] overflow-hidden bg-[#f8f7f1]">
      <video className="landing-hero-video" autoPlay muted loop playsInline preload="metadata" aria-hidden="true" tabIndex={-1}>
        <source src="/videos/labelwise-shopping.mp4" type="video/mp4" />
      </video>
      <div className="landing-hero-overlay" />
      <div className="absolute inset-0 z-[2] opacity-30" style={{ backgroundImage: "radial-gradient(#9eb9a5 0.65px, transparent 0.65px)", backgroundSize: "20px 20px", maskImage: "linear-gradient(90deg, transparent, black 70%)" }} />
      <header className="shell relative z-10 flex h-[84px] items-center justify-between border-b border-[#dfe7df]">
        <Brand />
        <nav className="hidden items-center gap-9 text-[13px] font-medium text-[#557062] md:flex">
          <a href="#how-it-works" className="hover:text-[#193d2f]">How it works</a><a href="#why-labelwise" className="hover:text-[#193d2f]">Why LabelWise</a>
        </nav>
        <div className="flex items-center gap-3"><Link href="/login" className="hidden px-3 py-2 text-sm font-semibold text-[#244937] sm:block">Log in</Link><Link href="/signup" className="button-primary !px-5 !py-3">Get started <ArrowRight size={16} /></Link></div>
      </header>

      <div className="shell relative z-10 grid min-h-[620px] items-center gap-14 py-16 lg:grid-cols-[1.02fr_.98fr] lg:py-20">
        <div className="max-w-[570px]">
          <div className="eyebrow">Food clarity, made personal</div>
          <h1 className="serif mt-6 text-[56px] leading-[1.02] text-[#183b2d] sm:text-[72px]">Know what’s<br />in your <em className="font-normal text-[#6b9276]">food.</em></h1>
          <p className="mt-7 max-w-[475px] text-[17px] leading-8 text-[#66766c]">A label can hide a lot in tiny print. Take a photo, say what matters to you, and get a clear, careful read of the ingredients.</p>
          <div className="mt-9 flex flex-wrap items-center gap-3"><Link href="/signup" className="button-primary">Check a label <ArrowRight size={17} /></Link><a href="#how-it-works" className="button-secondary">See how it works <ArrowDown size={15} /></a></div>
          <div className="mt-10">
            <div className="flex items-center gap-2.5 text-[12px] font-semibold text-[#a8c0ae]"><ShieldCheck size={16} className="text-[#73d697]" /> Readable evidence. Careful decisions.</div>
            <div className="mt-4 grid max-w-[510px] grid-cols-3 gap-2">
              <div className="proof-chip"><ScanLine size={15} /><span>Local OCR</span></div>
              <div className="proof-chip"><ShieldCheck size={15} /><span>Allergy rules</span></div>
              <div className="proof-chip"><Sparkles size={15} /><span>Barcode check</span></div>
            </div>
          </div>
        </div>

        <div className="relative mx-auto w-full max-w-[530px]">
          <div className="absolute -right-5 -top-8 size-32 rounded-full bg-[#dcecdf] blur-2xl" />
          <div className="relative rotate-[1.5deg] rounded-[30px] border border-[#e0e8df] bg-white p-5 shadow-[0_28px_80px_#274b3722] sm:p-7">
            <div className="flex items-center justify-between border-b border-[#edf0eb] pb-5"><div><div className="text-[11px] font-bold uppercase tracking-[.16em] text-[#789181]">Your latest scan</div><div className="mt-1 text-sm font-semibold text-[#304c3c]">Roasted chickpea snack</div></div><span className="rounded-full bg-[#fff2d9] px-3 py-1.5 text-[10px] font-bold tracking-wide text-[#9a6a18]">CAUTION</span></div>
            <div className="mt-5 flex gap-4 rounded-2xl bg-[#f8f8f3] p-4"><div className="grid size-11 shrink-0 place-items-center rounded-xl bg-[#e2eee3] text-[#376b4d]"><ScanLine size={22} /></div><div><div className="text-[13px] font-bold text-[#2a4736]">A closer look matters</div><p className="mt-1 text-xs leading-5 text-[#718076]">No peanut listed in the visible ingredients. The package warning area isn’t shown.</p></div></div>
            <div className="mt-4 grid grid-cols-2 gap-3"><div className="rounded-2xl border border-[#e9ede7] p-4"><div className="text-[10px] font-bold uppercase tracking-wider text-[#8a978d]">Total carbs</div><div className="mt-1 text-2xl font-bold text-[#244b36]">61<span className="ml-1 text-xs font-semibold text-[#819087]">g / 100g</span></div></div><div className="rounded-2xl border border-[#e9ede7] p-4"><div className="text-[10px] font-bold uppercase tracking-wider text-[#8a978d]">Sugar</div><div className="mt-1 text-2xl font-bold text-[#244b36]">0.5<span className="ml-1 text-xs font-semibold text-[#819087]">g / 100g</span></div></div></div>
            <div className="mt-4 rounded-2xl bg-[#eff6ef] p-4 text-xs leading-5 text-[#55725f]"><Sparkles size={14} className="mr-1 inline" /> Low sugar doesn’t always mean low carbohydrate. Check serving size and your own plan.</div>
          </div>
          <div className="absolute -bottom-8 -left-8 hidden items-center gap-3 rounded-2xl border border-[#e5ebe3] bg-white px-4 py-3 shadow-xl sm:flex"><div className="grid size-9 place-items-center rounded-xl bg-[#eef6ed] text-[#4e875f]"><AudioLines size={19} /></div><div><div className="text-xs font-bold text-[#355442]">Your needs, heard</div><div className="text-[10px] text-[#87948a]">Allergies · conditions · preferences</div></div></div>
        </div>
      </div>
      <div className="absolute -bottom-24 -left-24 size-72 rounded-full bg-[#e4ecd8] opacity-55 blur-3xl" />
    </section>

    <section id="how-it-works" className="bg-white py-24">
      <div className="shell"><div className="eyebrow">A simple scan, a clearer choice</div><div className="mt-4 grid gap-8 md:grid-cols-[.8fr_1.2fr] md:items-end"><h2 className="serif max-w-[430px] text-4xl leading-tight text-[#1d4030] sm:text-5xl">From tiny print to useful context.</h2><p className="max-w-[500px] text-sm leading-7 text-[#718076]">LabelWise reads the visible label and compares it with the dietary needs you share. When information is missing or uncertain, it says so.</p></div>
        <div className="mt-12 grid gap-4 md:grid-cols-3">{[
          { n: "01", icon: ScanLine, title: "Capture the label", body: "Upload a clear photo of the ingredients, allergen statements, and nutrition panel." },
          { n: "02", icon: AudioLines, title: "Tell us what matters", body: "Record your allergies, health considerations, or food preferences in your own words." },
          { n: "03", icon: ShieldCheck, title: "Review a careful result", body: "See a plain-language verdict, flagged ingredients, and uncertainty to check on pack." },
        ].map(({ n, icon: Icon, title, body }) => <article key={n} className="rounded-[23px] border border-[#e8ece6] bg-[#fbfcf9] p-7"><div className="flex items-center justify-between"><span className="text-xs font-bold tracking-[.2em] text-[#91a598]">{n}</span><Icon size={20} className="text-[#588165]" /></div><h3 className="mt-8 text-lg font-bold text-[#244332]">{title}</h3><p className="mt-3 text-sm leading-6 text-[#748177]">{body}</p></article>)}</div>
      </div>
    </section>

    <section id="why-labelwise" className="bg-[#e9f1e9] py-20"><div className="shell flex flex-col justify-between gap-8 md:flex-row md:items-center"><div><div className="eyebrow">Clarity over guesswork</div><h2 className="serif mt-4 max-w-[620px] text-4xl leading-tight text-[#1c4030] sm:text-5xl">The label stays the source.<br />You stay in control.</h2></div><div className="max-w-[360px]"><p className="text-sm leading-7 text-[#617468]">LabelWise is a reading aid, not a medical decision-maker. For serious allergies, verify the complete package and contact the manufacturer when a warning is unclear.</p><Link href="/signup" className="mt-6 inline-flex items-center gap-2 text-sm font-bold text-[#24563c]">Create your account <ArrowRight size={16} /></Link></div></div></section>

    <footer className="bg-[#173b2d] py-8 text-white"><div className="shell flex flex-col justify-between gap-4 sm:flex-row sm:items-center"><Brand inverse /><p className="text-xs text-[#c0d0c4]">Read carefully. Choose confidently.</p><p className="text-[11px] text-[#8fa99a]">LabelWise · Food label assistant</p></div></footer>
  </main>;
}
