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
      <HowItWorks />
      <DemoTeaser />
      <TrustSection />
      <Faq />
      <SiteFooter />
    </main>
  );
}

function SiteHeader() {
  return (
    <header className="sticky top-0 z-20 border-b border-zombie-light/40 bg-surface/85 backdrop-blur">
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
          <span className="inline-flex items-center gap-2 rounded-full border border-zombie-light bg-zombie-wash px-3 py-1 text-xs font-semibold uppercase tracking-wide text-zombie-light">
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
              className="rounded-full border border-zombie-light px-6 py-3 text-center font-semibold text-zombie-light transition hover:bg-zombie-wash"
            >
              See a live demo
            </Link>
          </div>
          <p className="mt-4 text-sm text-dusk">
            No signup for the demo. Read-only always — we never create, modify, or delete anything.
          </p>
        </div>

        <div className="relative flex flex-col items-center gap-6">
          <div className="rounded-full shadow-glow">
            <ZombieMascot variant="grave" size={200} />
          </div>
          <MindlessCursor className="max-w-sm" />
        </div>
      </div>
    </section>
  );
}

function WhatIsAZombie() {
  return (
    <section id="what" className="border-y border-zombie-light/40 bg-surface">
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

function HowItWorks() {
  const steps = [
    {
      n: "1",
      title: "Connect, read-only",
      body: "Attach a least-privilege, read-only role or paste a read-only token. GraveKeeper can only list and describe — it holds no permission to change anything.",
      icon: (
        <path d="M7 13a5 5 0 0 1 5-5h2a5 5 0 0 1 0 10h-1M17 11a5 5 0 0 1-5 5h-2a5 5 0 0 1 0-10h1" />
      ),
    },
    {
      n: "2",
      title: "Scan",
      body: "It pulls every service account, key, OAuth app, and agent, along with last-used dates, owners, and permissions, into one inventory.",
      icon: <path d="M11 4a7 7 0 1 0 0 14 7 7 0 0 0 0-14ZM20 20l-4-4" />,
    },
    {
      n: "3",
      title: "See your zombies",
      body: "Each identity gets a confidence score and plain-language reasons. You decide what to keep and what to retire. Nothing is touched without you.",
      icon: <path d="M4 12s3-6 8-6 8 6 8 6-3 6-8 6-8-6-8-6Z M12 10a2 2 0 1 0 0 4 2 2 0 0 0 0-4Z" />,
    },
  ];

  return (
    <section id="how" className="border-y border-zombie-light/40 bg-surface">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="font-display text-3xl font-bold sm:text-4xl">How it works</h2>
        <p className="mt-3 max-w-2xl text-lg text-dusk">
          Three steps, and the whole thing is read-only. We never create, modify, or delete
          anything in your accounts.
        </p>
        <div className="mt-10 grid gap-6 md:grid-cols-3">
          {steps.map((s) => (
            <div
              key={s.n}
              className="rounded-2xl border border-zombie-light/50 bg-surface-light p-6 shadow-sm"
            >
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-full bg-zombie-wash text-zombie-light">
                  <svg
                    width="22"
                    height="22"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  >
                    {s.icon}
                  </svg>
                </span>
                <span className="font-display text-2xl font-bold text-zombie-light">{s.n}</span>
              </div>
              <h3 className="mt-4 text-xl font-semibold">{s.title}</h3>
              <p className="mt-2 leading-relaxed text-dusk">{s.body}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

function DemoTeaser() {
  // A small, static preview of the results dashboard populated with SAFE
  // synthetic rows, mirroring what /demo renders in full.
  const rows = [
    { name: "billing-reconciler", src: "aws", last: "214 days ago", owner: "owner left", conf: 0.92 },
    { name: "ci-deploy-bot", src: "github", last: "5 days ago", owner: "platform-team", conf: 0.08 },
    { name: "legacy-metrics-key", src: "aws", last: "398 days ago", owner: "no owner", conf: 0.86 },
  ];

  return (
    <section className="mx-auto max-w-6xl px-6 py-16">
      <div className="grid items-center gap-10 lg:grid-cols-2">
        <div>
          <h2 className="font-display text-3xl font-bold sm:text-4xl">See it before you connect anything</h2>
          <p className="mt-4 text-lg leading-relaxed text-dusk">
            The live demo runs a full scan against a sample environment — 30-some identities with
            planted zombies and healthy accounts — so you can see exactly what a real result looks
            like. One click, no login, no credentials.
          </p>
          <Link
            href="/demo"
            className="mt-6 inline-block rounded-full bg-zombie px-6 py-3 font-semibold text-white shadow-sm transition hover:bg-zombie-dark"
          >
            Open the live demo
          </Link>
        </div>

        <div className="rounded-2xl border border-zombie-light/60 bg-surface p-5 shadow-md">
          <div className="flex items-center justify-between border-b border-zombie-light/50 pb-3">
            <span className="font-semibold">Example scan</span>
            <span className="rounded-full bg-rot/10 px-3 py-1 text-sm font-semibold text-rot">
              12 look abandoned
            </span>
          </div>
          <table className="mt-3 w-full text-left text-sm">
            <thead className="text-xs uppercase tracking-wide text-dusk">
              <tr>
                <th className="py-2">Identity</th>
                <th>Last active</th>
                <th>Owner</th>
                <th className="text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.name} className="border-t border-zombie-light/30">
                  <td className="py-2.5 font-medium">
                    <span className="mr-2 rounded bg-zombie-wash px-1.5 py-0.5 text-xs uppercase text-zombie-light">
                      {r.src}
                    </span>
                    {r.name}
                  </td>
                  <td className={r.conf > 0.5 ? "text-rot" : "text-dusk"}>{r.last}</td>
                  <td>
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                        r.owner === "owner left" || r.owner === "no owner"
                          ? "bg-rot/10 text-rot"
                          : "bg-zombie-wash text-zombie-light"
                      }`}
                    >
                      {r.owner}
                    </span>
                  </td>
                  <td>
                    <div className="ml-auto flex w-24 items-center gap-2">
                      <div className="h-1.5 flex-1 rounded-full bg-zombie-wash">
                        <div
                          className={`h-full rounded-full ${r.conf > 0.5 ? "bg-rot" : "bg-zombie"}`}
                          style={{ width: `${Math.round(r.conf * 100)}%` }}
                        />
                      </div>
                      <span className="w-8 text-right text-xs tabular-nums text-dusk">
                        {Math.round(r.conf * 100)}%
                      </span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}

function TrustSection() {
  const points = [
    ["Read-only, provably", "Every connector calls only list/describe APIs. The code holds no create, update, or delete calls at all."],
    ["Nothing stored without consent", "Credentials are used for the scan and dropped. Results are only saved if you opt in."],
    ["Honest about “dead”", "We can’t observe that an identity is abandoned — we infer it from signals and show you the reasons. You confirm."],
    ["Least privilege", "For AWS we hand you a minimal read-only IAM policy that grants only the calls the scan needs — nothing more."],
  ];
  return (
    <section id="trust" className="border-y border-zombie-light/40 bg-zombie-wash/40">
      <div className="mx-auto max-w-6xl px-6 py-16">
        <h2 className="font-display text-3xl font-bold sm:text-4xl">Safe to connect</h2>
        <p className="mt-3 max-w-2xl text-lg text-dusk">
          The first question a security-minded person asks is &ldquo;what can this thing do to my
          accounts?&rdquo; The answer is: read, and nothing else.
        </p>
        <div className="mt-10 grid gap-5 sm:grid-cols-2">
          {points.map(([title, body]) => (
            <div key={title} className="flex gap-4 rounded-2xl border border-zombie-light/50 bg-surface p-5">
              <svg
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="#5C7B41"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="mt-0.5 flex-none"
              >
                <path d="M12 3l7 3v5c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6l7-3Z" />
                <path d="M9 12l2 2 4-4" />
              </svg>
              <div>
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-1 text-sm leading-relaxed text-dusk">{body}</p>
              </div>
            </div>
          ))}
        </div>
        <p className="mt-6 text-sm text-dusk">
          Want the detail? Read the{" "}
          <Link href="/docs/threat-model" className="font-semibold text-zombie-light underline">
            threat model
          </Link>{" "}
          — exactly what we request, what we store, and how &ldquo;dead&rdquo; is scored.
        </p>
      </div>
    </section>
  );
}

function Faq() {
  const items = [
    [
      "What is a zombie agent?",
      "A non-human identity — service account, API key, OAuth app, CI bot, or AI agent — that still has live access but no owner and no purpose. It keeps running while nobody watches it.",
    ],
    [
      "Is this safe to connect?",
      "Yes. GraveKeeper only ever makes read-only API calls. It cannot create, modify, or delete anything, and for AWS you attach a minimal read-only policy that limits it to exactly the calls it needs.",
    ],
    [
      "Do you store my data?",
      "Credentials are used for the scan and then dropped. Scan results are only persisted if you opt in, and you can delete them at any time.",
    ],
    [
      "What counts as “dead”?",
      "We don’t claim certainty. An identity becomes a candidate when signals line up — no activity for a long time, an owner who left or was disabled, no owner at all, or broad permissions it never uses. Each candidate shows its confidence and reasons so you can judge.",
    ],
    [
      "Who is this for?",
      "Anyone responsible for an environment full of automations — a solo founder with a pile of old keys, a platform team, or a security lead who needs to answer “how many agents are running here, and who owns each one?”",
    ],
  ];
  return (
    <section id="faq" className="mx-auto max-w-3xl px-6 py-16">
      <h2 className="font-display text-3xl font-bold sm:text-4xl">Questions</h2>
      <div className="mt-8 divide-y divide-zombie-light/40 rounded-2xl border border-zombie-light/50 bg-surface">
        {items.map(([q, a]) => (
          <details key={q} className="group px-5 py-4">
            <summary className="flex cursor-pointer list-none items-center justify-between font-semibold">
              {q}
              <span className="ml-4 text-zombie-light transition group-open:rotate-45">+</span>
            </summary>
            <p className="mt-3 leading-relaxed text-dusk">{a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}

function SiteFooter() {
  return (
    <footer className="border-t border-zombie-light/40 bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between gap-4 px-6 py-10 sm:flex-row">
        <div className="flex items-center gap-2 font-display text-lg font-bold">
          <ZombieMascot size={30} animate={false} />
          GraveKeeper
        </div>
        <p className="text-sm text-dusk">
          A solo project — early and actively building. Read-only by design.
        </p>
        <nav className="flex gap-4 text-sm font-medium text-dusk">
          <Link href="/about" className="hover:text-ink">
            About
          </Link>
          <Link href="/demo" className="hover:text-ink">
            Demo
          </Link>
          <Link href="/scan" className="hover:text-ink">
            Scan
          </Link>
          <Link href="/docs/threat-model" className="hover:text-ink">
            Trust
          </Link>
        </nav>
      </div>
    </footer>
  );
}
