"use client";

import { useState } from "react";
import Link from "next/link";
import { runScan, getScan } from "@/lib/api";
import type { ScanResult, Source } from "@/lib/types";
import ResultsDashboard from "@/components/ResultsDashboard";
import ZombieMascot from "@/components/ZombieMascot";

type Phase = "connect" | "scanning" | "done";

export default function ScanPage() {
  const [source, setSource] = useState<Source>("aws");
  const [phase, setPhase] = useState<Phase>("connect");
  const [error, setError] = useState<string | null>(null);
  const [scan, setScan] = useState<ScanResult | null>(null);

  // AWS fields
  const [awsKey, setAwsKey] = useState("");
  const [awsSecret, setAwsSecret] = useState("");
  const [awsToken, setAwsToken] = useState("");
  // GitHub fields
  const [ghToken, setGhToken] = useState("");
  const [ghOrg, setGhOrg] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPhase("scanning");
    const credentials =
      source === "aws"
        ? {
            aws_access_key_id: awsKey.trim(),
            aws_secret_access_key: awsSecret.trim(),
            ...(awsToken.trim() ? { aws_session_token: awsToken.trim() } : {}),
          }
        : { token: ghToken.trim(), ...(ghOrg.trim() ? { org: ghOrg.trim() } : {}) };
    try {
      const summary = await runScan({ connector: source, credentials });
      const full = await getScan(summary.scan_id);
      setScan(full);
      setPhase("done");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Scan failed.");
      setPhase("connect");
    }
  }

  if (phase === "done" && scan) {
    return (
      <main className="min-h-screen">
        <TopBar />
        <ResultsDashboard initial={scan} />
      </main>
    );
  }

  return (
    <main className="min-h-screen">
      <TopBar />
      <div className="mx-auto max-w-lg px-6 py-12">
        <div className="flex items-center gap-3">
          <ZombieMascot size={56} />
          <div>
            <h1 className="font-display text-2xl font-bold">Scan your accounts</h1>
            <p className="text-sm text-dusk">Read-only. Nothing is created, changed, or deleted.</p>
          </div>
        </div>

        <div className="mt-6 flex gap-2">
          <SourceTab active={source === "aws"} onClick={() => setSource("aws")}>
            AWS
          </SourceTab>
          <SourceTab active={source === "github"} onClick={() => setSource("github")}>
            GitHub
          </SourceTab>
        </div>

        <form
          onSubmit={submit}
          className="mt-4 rounded-2xl border border-zombie-light/50 bg-white/70 p-6"
        >
          {source === "aws" ? (
            <>
              <Field label="Access key ID" value={awsKey} onChange={setAwsKey} required />
              <Field
                label="Secret access key"
                value={awsSecret}
                onChange={setAwsSecret}
                type="password"
                required
              />
              <Field
                label="Session token (optional)"
                value={awsToken}
                onChange={setAwsToken}
                type="password"
              />
              <p className="mt-3 text-xs text-dusk">
                Use temporary, read-only credentials. Attach our{" "}
                <a
                  href="/gravekeeper-readonly-policy.json"
                  className="font-semibold text-zombie-dark underline"
                  download
                >
                  least-privilege IAM policy
                </a>{" "}
                — it grants only the list/get calls the scan needs, nothing else.
              </p>
            </>
          ) : (
            <>
              <Field
                label="Read-only token (PAT)"
                value={ghToken}
                onChange={setGhToken}
                type="password"
                required
              />
              <Field label="Organization (optional)" value={ghOrg} onChange={setGhOrg} />
              <p className="mt-3 text-xs text-dusk">
                A fine-grained token with read access to metadata and contents (plus org read to
                see app installations) is enough.
              </p>
            </>
          )}

          {error && (
            <div className="mt-4 rounded-lg bg-rot/10 px-3 py-2 text-sm text-rot">{error}</div>
          )}

          <button
            type="submit"
            className="mt-5 w-full rounded-full bg-zombie px-6 py-3 font-semibold text-white transition hover:bg-zombie-dark"
          >
            Run read-only scan
          </button>
          <p className="mt-3 text-center text-xs text-dusk">
            Credentials are used for this scan and never stored.{" "}
            <Link href="/docs/threat-model" className="underline">
              How this stays safe
            </Link>
          </p>
        </form>

        <p className="mt-6 text-center text-sm text-dusk">
          Not ready to connect?{" "}
          <Link href="/demo" className="font-semibold text-zombie-dark underline">
            See the live demo
          </Link>{" "}
          on a sample environment first.
        </p>
      </div>

      {phase === "scanning" && <ScanningOverlay source={source} />}
    </main>
  );
}

function TopBar() {
  return (
    <header className="border-b border-zombie-light/40 bg-bone/85">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-display text-lg font-bold">
          <ZombieMascot size={30} animate={false} />
          GraveKeeper
        </Link>
        <Link href="/demo" className="text-sm font-medium text-dusk hover:text-ink">
          Live demo
        </Link>
      </div>
    </header>
  );
}

function SourceTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex-1 rounded-full px-4 py-2 text-sm font-semibold transition ${
        active ? "bg-zombie text-white" : "border border-zombie-light text-dusk hover:bg-zombie-wash"
      }`}
    >
      {children}
    </button>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  required = false,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  required?: boolean;
}) {
  return (
    <label className="mt-4 block first:mt-0">
      <span className="text-sm font-medium">{label}</span>
      <input
        type={type}
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
        autoComplete="off"
        spellCheck={false}
        className="mt-1 w-full rounded-lg border border-zombie-light bg-bone px-3 py-2 text-sm outline-none focus:border-zombie-dark"
      />
    </label>
  );
}

function ScanningOverlay({ source }: { source: Source }) {
  return (
    <div className="fixed inset-0 z-40 flex flex-col items-center justify-center gap-4 bg-bone/80 backdrop-blur">
      <ZombieMascot size={120} />
      <p className="font-display text-xl font-bold">Reading your {source.toUpperCase()} account…</p>
      <p className="text-sm text-dusk">List and get calls only — this changes nothing.</p>
    </div>
  );
}
