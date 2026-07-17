import Link from "next/link";
import ZombieMascot from "@/components/ZombieMascot";
import MindlessCursor from "@/components/MindlessCursor";
import Stat from "@/components/Stat";

export default function LandingPage() {
  return (
    <main className="min-h-screen">
      <SiteHeader />
      <Hero />
      <WhatIsAZombie />
      <WhyItCosts />
      <PlaceholderFooter />
    </main>
  );
}

// Temporary footer until the How-it-works, Demo, Trust, and FAQ sections land.
function PlaceholderFooter() {
  return (
    <footer className="border-t border-zombie-light/40 py-10 text-center text-sm text-dusk">
      GraveKeeper — a solo project, early and actively building.
    </footer>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-zombie-light/40 bg-bone/85 backdrop-blur">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-display text-xl font-bold">
          <ZombieMascot size={34} animate={false} />
          GraveKeeper
        </Link>
        <nav className="flex items-center gap-4 text-sm font-medium">
          <Link href="/demo" className="hidden text-dusk hover:text-ink sm:inline">
            Live demo
          </Link>
          <Link
            href="/scan"
            className="rounded-full bg-zombie px-4 py-2 font-semibold text-white shadow-sm transition hover:bg-zombie-dark"
          >
            Scan my accounts
          </Link>
        </nav>
      </div>
    </header>
  );
}

function Hero() {
  return (
    <section className="paper-grain relative overflow-hidden">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-16 sm:py-24 lg:grid-cols-2">
        <div>
          <span className="inline-flex items-center gap-2 rounded-full border border-zombie-light bg-zombie-wash px-3 py-1 text-xs font-semibold uppercase tracking-wide text-zombie-dark">
            Read-only · self-serve · cross-platform
          </span>
          <h1 className="mt-5 font-display text-4xl font-bold leading-[1.05] sm:text-5xl lg:text-6xl">
            The agents nobody turned off are still running.
          </h1>
          <p className="mt-5 max-w-xl text-lg leading-relaxed text-dusk">
            GraveKeeper connects to your cloud and SaaS accounts, inventories every AI agent,
            automation, and non-human identity, and flags the zombies — the ones with live
            credentials, no owner, and no recent purpose.
          </p>
          <div className="mt-8 flex flex-col gap-3 sm:flex-row">
            <Link
              href="/scan"
              className="rounded-full bg-zombie px-6 py-3 text-center font-semibold text-white shadow-sm transition hover:bg-zombie-dark"
            >
              Try it on your own accounts
            </Link>
            <Link
              href="/demo"
              className="rounded-full border border-zombie-dark px-6 py-3 text-center font-semibold text-zombie-dark transition hover:bg-zombie-wash"
            >
              See a live demo
            </Link>
          </div>
          <p className="mt-4 text-sm text-dusk">
            No signup for the demo. Read-only always — we never create, modify, or delete anything.
          </p>
        </div>

        <div className="relative flex flex-col items-center gap-6">
          <ZombieMascot size={200} />
          <MindlessCursor className="max-w-sm" />
        </div>
      </div>
    </section>
  );
}

function WhatIsAZombie() {
  return (
    <section id="what" className="border-y border-zombie-light/40 bg-white/50">
      <div className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-16 lg:grid-cols-[1fr_1.4fr]">
        <div className="flex justify-center">
          <ZombieMascot size={170} />
        </div>
        <div>
          <h2 className="font-display text-3xl font-bold sm:text-4xl">What is a zombie agent?</h2>
          <p className="mt-4 text-lg leading-relaxed text-dusk">
            A zombie agent is a non-human identity — a service account, API key, OAuth app, CI bot,
            or AI agent — that is still alive with real access, but has no owner and no purpose.
            It keeps acting on stale logic while nobody is watching it.
          </p>
          <p className="mt-4 font-semibold text-ink">They&rsquo;re usually born one of three ways:</p>
          <ul className="mt-3 space-y-3">
            {[
              [
                "Built fast, without governance",
                "Someone wires up a key or an agent for a one-off task and never cleans it up.",
              ],
              [
                "An offboarding gap",
                "The person who made it leaves. Their human account is disabled — the automation they created is not.",
              ],
              [
                "Shadow AI",
                "A team connects an AI agent to email or production outside any central inventory. Nobody else knows it exists.",
              ],
            ].map(([title, body]) => (
              <li key={title} className="flex gap-3">
                <span className="mt-1.5 h-2.5 w-2.5 flex-none rounded-full bg-zombie" />
                <span>
                  <span className="font-semibold text-ink">{title}.</span>{" "}
                  <span className="text-dusk">{body}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function WhyItCosts() {
  return (
    <section id="why" className="mx-auto max-w-6xl px-6 py-16">
      <div className="max-w-2xl">
        <h2 className="font-display text-3xl font-bold sm:text-4xl">Why this costs companies money</h2>
        <p className="mt-4 text-lg leading-relaxed text-dusk">
          Abandoned identities aren&rsquo;t just clutter. They keep taking actions on stale logic,
          they&rsquo;re the softest target an attacker can find, and they quietly run up spend and
          audit risk. These are industry findings, not our own measurements:
        </p>
      </div>

      <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        <Stat
          end={80}
          suffix=":1"
          headline="Machines outnumber humans"
          caption="Non-human identities outnumber employees up to 80 to 1 in a typical enterprise."
        />
        <Stat
          end={68}
          suffix="%"
          headline="of incidents involve machines"
          caption="A majority of security incidents now involve machine identities, not human logins."
        />
        <Stat
          end={440}
          prefix="$"
          suffix="M"
          headline="lost in 45 minutes"
          caption="One forgotten automation at Knight Capital fired millions of orders before anyone could stop it."
        />
        <Stat
          end={172}
          prefix="$"
          suffix="K/yr"
          headline="just to manage credentials"
          caption="Estimated annual cost to manage machine credentials per 10 developers."
        />
      </div>
    </section>
  );
}

// The remaining sections (How it works, Demo teaser, Trust, FAQ, Footer)
// are defined below.
