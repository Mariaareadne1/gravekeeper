"use client";

import { useId, useState } from "react";
import Link from "next/link";
import { runScan, getScan } from "@/lib/api";
import type { ScanResult, Source } from "@/lib/types";
import ResultsDashboard from "@/components/ResultsDashboard";
import ZombieMascot from "@/components/ZombieMascot";

type Phase = "connect" | "scanning" | "done";

// The connectors the UI can actually select — the synthetic demo source is not
// offered here. Narrowing the state to this lets buildCredentials assert
// exhaustiveness against a `never` and stay build-green.
type Connector = Exclude<Source, "synthetic">;

export default function ScanPage() {
  const [source, setSource] = useState<Connector>("aws");
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
  // GCP fields
  const [gcpProjectId, setGcpProjectId] = useState("");
  const [gcpKeyJson, setGcpKeyJson] = useState("");
  const [gcpJsonError, setGcpJsonError] = useState<string | null>(null);
  // Azure fields
  const [azTenantId, setAzTenantId] = useState("");
  const [azClientId, setAzClientId] = useState("");
  const [azClientSecret, setAzClientSecret] = useState("");

  // Build the connector-specific credential dict. Returns null when local
  // validation fails (e.g. GCP JSON that won't parse) so submit can bail early.
  function buildCredentials(): Record<string, unknown> | null {
    if (source === "aws") {
      return {
        aws_access_key_id: awsKey.trim(),
        aws_secret_access_key: awsSecret.trim(),
        ...(awsToken.trim() ? { aws_session_token: awsToken.trim() } : {}),
      };
    }
    if (source === "github") {
      return { token: ghToken.trim(), ...(ghOrg.trim() ? { org: ghOrg.trim() } : {}) };
    }
    if (source === "gcp") {
      let serviceAccount: unknown;
      try {
        serviceAccount = JSON.parse(gcpKeyJson);
      } catch {
        setGcpJsonError(
          "That doesn't look like valid JSON. Paste the full contents of your downloaded service-account key file."
        );
        return null;
      }
      // Light shape check for faster feedback before the request goes out.
      if (
        typeof serviceAccount !== "object" ||
        serviceAccount === null ||
        !("private_key" in serviceAccount)
      ) {
        setGcpJsonError(
          "That JSON is missing a \"private_key\" field. Paste the full contents of your downloaded service-account key file."
        );
        return null;
      }
      return { project_id: gcpProjectId.trim(), service_account_json: serviceAccount };
    }
    if (source === "azure") {
      return {
        tenant_id: azTenantId.trim(),
        client_id: azClientId.trim(),
        client_secret: azClientSecret,
      };
    }
    // Exhaustiveness: every selectable connector is handled above. Adding a new
    // Source (or leaking `synthetic` here) fails to compile instead of silently
    // sending Azure-shaped credentials.
    const _exhaustive: never = source;
    throw new Error(`Unhandled connector: ${String(_exhaustive)}`);
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setGcpJsonError(null);
    const credentials = buildCredentials();
    if (!credentials) return; // local validation failed — stay on the form
    setPhase("scanning");
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

        <div role="group" aria-label="Choose connector" className="mt-6 flex flex-wrap gap-2">
          <SourceTab active={source === "aws"} onClick={() => setSource("aws")}>
            AWS
          </SourceTab>
          <SourceTab active={source === "github"} onClick={() => setSource("github")}>
            GitHub
          </SourceTab>
          <SourceTab active={source === "gcp"} onClick={() => setSource("gcp")}>
            GCP
          </SourceTab>
          <SourceTab active={source === "azure"} onClick={() => setSource("azure")}>
            Azure
          </SourceTab>
        </div>

        <form
          onSubmit={submit}
          className="mt-4 rounded-2xl border border-zombie-light/50 bg-white/70 p-6"
        >
          {source === "aws" && (
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
          )}

          {source === "github" && (
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

          {source === "gcp" && (
            <>
              <Field
                label="Project ID"
                value={gcpProjectId}
                onChange={setGcpProjectId}
                required
              />
              <TextAreaField
                label="Service-account key JSON"
                value={gcpKeyJson}
                onChange={(v) => {
                  setGcpJsonError(null);
                  setGcpKeyJson(v);
                }}
                required
                error={gcpJsonError}
                placeholder='Paste the full contents of your downloaded key file: {"type": "service_account", ...}'
              />
              <p className="mt-3 text-xs text-dusk">
                Create a read-only service account, download its JSON key, and paste the file
                contents here. We use it for this scan only — it is never stored.
              </p>
            </>
          )}

          {source === "azure" && (
            <>
              <Field label="Tenant ID" value={azTenantId} onChange={setAzTenantId} required />
              <Field label="Client ID" value={azClientId} onChange={setAzClientId} required />
              <Field
                label="Client secret"
                value={azClientSecret}
                onChange={setAzClientSecret}
                type="password"
                required
              />
              <p className="mt-3 text-xs text-dusk">
                Register a read-only app (Reader role) and use its tenant, client ID, and a
                client secret. We use these for this scan only — they are never stored.
              </p>
            </>
          )}

          {error && (
            <div
              role="alert"
              className="mt-4 rounded-lg bg-rot/10 px-3 py-2 text-sm text-rot"
            >
              {error}
            </div>
          )}

          <button
            type="submit"
            className="mt-5 w-full rounded-full bg-zombie-dark px-6 py-3 font-semibold text-white transition hover:brightness-95"
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
        <nav className="flex items-center gap-4">
          <Link href="/registry" className="text-sm font-medium text-dusk hover:text-ink">
            Registry
          </Link>
          <Link href="/demo" className="text-sm font-medium text-dusk hover:text-ink">
            Live demo
          </Link>
        </nav>
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
      aria-pressed={active}
      className={`flex-1 rounded-full px-4 py-2 text-sm font-semibold transition ${
        active
          ? "bg-zombie-dark text-white"
          : "border border-zombie-light text-dusk hover:bg-zombie-wash"
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

function TextAreaField({
  label,
  value,
  onChange,
  required = false,
  error = null,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  required?: boolean;
  error?: string | null;
  placeholder?: string;
}) {
  const errorId = useId();
  return (
    <label className="mt-4 block first:mt-0">
      <span className="text-sm font-medium">{label}</span>
      <textarea
        value={value}
        required={required}
        onChange={(e) => onChange(e.target.value)}
        rows={6}
        spellCheck={false}
        placeholder={placeholder}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? errorId : undefined}
        className="mt-1 w-full resize-y rounded-lg border border-zombie-light bg-bone px-3 py-2 font-mono text-xs outline-none focus:border-zombie-dark"
      />
      {error && (
        <span id={errorId} role="alert" className="mt-1 block text-xs text-rot">
          {error}
        </span>
      )}
    </label>
  );
}

function ScanningOverlay({ source }: { source: Source }) {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-40 flex flex-col items-center justify-center gap-4 bg-bone/80 backdrop-blur"
    >
      <ZombieMascot size={120} />
      <p className="font-display text-xl font-bold">Reading your {source.toUpperCase()} account…</p>
      <p className="text-sm text-dusk">List and get calls only — this changes nothing.</p>
    </div>
  );
}
