import Link from "next/link";
import type { Metadata } from "next";
import ZombieMascot from "@/components/ZombieMascot";

export const metadata: Metadata = {
  title: "What are zombie agents? Orphan AI agents and agent sprawl — GraveKeeper",
  description:
    "A plain-English explainer on zombie agents, orphan AI agents, non-human identities, and agent sprawl: what they are, why they pile up, why they're risky, and how to find them.",
  keywords: [
    "zombie agents",
    "orphan AI agents",
    "agent sprawl",
    "non-human identities",
    "machine identity security",
    "service account cleanup",
    "shadow AI",
  ],
};

export default function AboutPage() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-zombie-light/40 bg-bone/85">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2 font-display text-lg font-bold">
            <ZombieMascot size={30} animate={false} />
            GraveKeeper
          </Link>
          <Link href="/demo" className="text-sm font-medium text-dusk hover:text-ink">
            Live demo
          </Link>
        </div>
      </header>

      <article className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="font-display text-4xl font-bold leading-tight">
          Zombie agents, orphan AI agents, and agent sprawl
        </h1>
        <p className="mt-4 text-lg text-dusk">
          A plain-English explainer on the identities nobody owns anymore — what they are,
          why every company now has them, and why they&rsquo;re worth finding.
        </p>

        <Section title="What is a zombie agent?">
          <p>
            A zombie agent is a <strong>non-human identity</strong> — a service account, API
            key, OAuth app, CI bot, or AI agent — that still has live access to your systems
            but has no owner and no purpose. It isn&rsquo;t switched off; it keeps running,
            acting on whatever logic it was given, while nobody is watching it. &ldquo;Orphan
            agent&rdquo; means the same thing: the human who created it is gone, but the
            automation they left behind is very much alive.
          </p>
        </Section>

        <Section title="Why every company has them now">
          <p>
            Machine identities have quietly come to outnumber human ones — estimates range
            from 25:1 to over 100:1, with a common figure around 80 machine identities per
            employee. They&rsquo;re created in seconds and, unlike a person&rsquo;s account,
            almost never cleaned up. That gap is <strong>agent sprawl</strong>, and it grows
            three ways:
          </p>
          <ul className="mt-3 space-y-2">
            <Bullet>
              <strong>Built fast, without governance.</strong> A key or agent is wired up for
              a one-off task and simply never removed.
            </Bullet>
            <Bullet>
              <strong>The offboarding gap.</strong> When someone leaves, their human account
              is disabled — the automations they built are not.
            </Bullet>
            <Bullet>
              <strong>Shadow AI.</strong> A team connects an AI agent to email or production
              outside any central inventory, and no one else knows it exists.
            </Bullet>
          </ul>
        </Section>

        <Section title="Why they're risky">
          <p>
            Two reasons they&rsquo;re worse than ordinary clutter. First, they keep{" "}
            <em>acting</em>: a forgotten automation runs on stale assumptions until something
            breaks — a single dormant function at Knight Capital fired millions of orders in
            45 minutes and cost about $440M. Second, they&rsquo;re the softest target in the
            building: an attacker who finds an unwatched credential effectively owns it,
            because there&rsquo;s no human who would notice it being misused. And most teams
            can&rsquo;t even answer the first question — how many agents are running here, and
            who owns each one? — because the data is scattered across a dozen consoles.
          </p>
        </Section>

        <Section title="How do you find them?">
          <p>
            You consolidate the scattered records into one inventory, then look for the
            tell-tale signals of abandonment: no activity for a long time, an owner who has
            left or been disabled, no documented owner at all, or broad permissions the
            identity never actually uses. None of these prove an identity is dead — but
            together they make a strong, reviewable case. That&rsquo;s exactly what GraveKeeper
            does, read-only, and it shows you the confidence and reasons behind every
            candidate so a human makes the final call.
          </p>
        </Section>

        <div className="mt-10 rounded-2xl border border-zombie-light/50 bg-zombie-wash/50 p-6 text-center">
          <ZombieMascot size={70} />
          <p className="mt-3 text-dusk">
            See it on a sample environment in one click, or scan your own accounts read-only.
          </p>
          <div className="mt-4 flex justify-center gap-3">
            <Link
              href="/demo"
              className="rounded-full bg-zombie px-5 py-2 text-sm font-semibold text-white hover:bg-zombie-dark"
            >
              Live demo
            </Link>
            <Link
              href="/scan"
              className="rounded-full border border-zombie-dark px-5 py-2 text-sm font-semibold text-zombie-dark hover:bg-zombie-wash"
            >
              Scan my accounts
            </Link>
          </div>
        </div>
      </article>
    </main>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-10">
      <h2 className="font-display text-2xl font-bold">{title}</h2>
      <div className="mt-3 leading-relaxed text-ink/90">{children}</div>
    </section>
  );
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="mt-2 h-2 w-2 flex-none rounded-full bg-zombie" />
      <span className="text-ink/90">{children}</span>
    </li>
  );
}
