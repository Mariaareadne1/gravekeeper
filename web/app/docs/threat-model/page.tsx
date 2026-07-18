import Link from "next/link";
import type { Metadata } from "next";
import ZombieMascot from "@/components/ZombieMascot";

export const metadata: Metadata = {
  title: "Threat model — GraveKeeper",
  description:
    "Exactly what GraveKeeper requests, why it's read-only, what it stores, and how 'dead' is inferred.",
};

export default function ThreatModelPage() {
  return (
    <main className="min-h-screen">
      <header className="border-b border-zombie-light/40 bg-surface/85">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2 font-display text-lg font-bold">
            <ZombieMascot size={30} animate={false} />
            GraveKeeper
          </Link>
          <Link href="/scan" className="text-sm font-medium text-dusk hover:text-ink">
            Scan
          </Link>
        </div>
      </header>

      <article className="mx-auto max-w-3xl px-6 py-12">
        <h1 className="font-display text-4xl font-bold">Threat model &amp; trust</h1>
        <p className="mt-4 text-lg text-dusk">
          Before you connect an account, the question worth asking is: what can this
          thing do to me? The short answer is that it reads, and nothing else.
        </p>

        <Section title="What we request, and why">
          <p>
            GraveKeeper only needs to enumerate identities and their metadata. It never
            needs write access to anything.
          </p>
          <p className="mt-3 font-semibold">AWS — the complete set of calls:</p>
          <ul className="mt-2 space-y-1">
            {[
              ["iam:ListUsers, iam:ListRoles", "enumerate the identities"],
              ["iam:ListAccessKeys, iam:GetAccessKeyLastUsed", "find keys and their last use"],
              ["iam:ListUserTags", "read an owner / created_by tag if present"],
              ["iam:List*Policies", "judge over-privilege"],
              ["iam:GetRole", "role last-used and permissions"],
            ].map(([call, why]) => (
              <li key={call} className="flex flex-wrap gap-x-2 text-sm">
                <code className="rounded bg-zombie-wash px-1.5 py-0.5 text-zombie-light">{call}</code>
                <span className="text-dusk">— {why}</span>
              </li>
            ))}
          </ul>
          <p className="mt-3">
            Every one is a <code>List</code>/<code>Get</code>. There is no create, update,
            put, delete, or attach in the set. GitHub is the same story: only HTTP{" "}
            <code>GET</code> requests. You attach our{" "}
            <a
              href="/gravekeeper-readonly-policy.json"
              download
              className="font-semibold text-zombie-light underline"
            >
              least-privilege IAM policy
            </a>
            , which grants exactly these and nothing else.
          </p>
        </Section>

        <Section title="Read-only — and the code proves it">
          <ul className="space-y-2">
            <Bullet>
              Each connector lists its complete set of API calls in its docstring — all reads.
            </Bullet>
            <Bullet>
              A test asserts every AWS action the connector declares starts with{" "}
              <code>List</code>, <code>Get</code>, or <code>Describe</code>.
            </Bullet>
            <Bullet>
              With the least-privilege policy attached, AWS would refuse a mutating call
              even if one existed — the credentials simply can&rsquo;t change anything.
            </Bullet>
          </ul>
        </Section>

        <Section title="Data handling">
          <ul className="space-y-2">
            <Bullet>
              <strong>Credentials are never persisted.</strong> They&rsquo;re used for the
              scan&rsquo;s read calls, then dropped.
            </Bullet>
            <Bullet>
              <strong>Results are stored only if you opt in.</strong> A saved scan holds
              identity metadata — names, dates, owners, permission names — never keys.
            </Bullet>
            <Bullet>
              <strong>Deletion cascades.</strong> Removing a scan removes its records and
              findings with it.
            </Bullet>
          </ul>
        </Section>

        <Section title="Honesty about “dead”">
          <p>
            We can&rsquo;t observe that an identity is abandoned. Every zombie candidate is
            an inference from signals — no recent activity, an owner who left or is missing,
            no owner at all, or broad permissions it never uses. Each finding shows its
            confidence and reasons, and a brand-new-but-unused identity is deliberately not
            flagged. A human confirms; the tool never claims certainty and never acts on its
            own.
          </p>
        </Section>

        <div className="mt-10 rounded-2xl border border-zombie-light/50 bg-zombie-wash/50 p-6">
          <div className="flex items-center gap-3">
            <ZombieMascot size={48} animate={false} />
            <p className="text-sm text-dusk">
              Ready to look? The{" "}
              <Link href="/demo" className="font-semibold text-zombie-light underline">
                live demo
              </Link>{" "}
              runs on a sample environment with zero risk, or{" "}
              <Link href="/scan" className="font-semibold text-zombie-light underline">
                scan your own accounts
              </Link>{" "}
              read-only.
            </p>
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
      <div className="mt-3 space-y-2 leading-relaxed text-ink/90">{children}</div>
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
