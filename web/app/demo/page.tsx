"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { getScan, runScan } from "@/lib/api";
import type { ScanResult } from "@/lib/types";
import ResultsDashboard from "@/components/ResultsDashboard";
import ZombieMascot from "@/components/ZombieMascot";

export default function DemoPage() {
  const [scan, setScan] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  // Run the scan exactly once, even under React StrictMode's double-invoke in
  // dev — otherwise we'd fire two concurrent scans per page view.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        const summary = await runScan({ synthetic: true });
        const full = await getScan(summary.scan_id);
        setScan(full);
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : "Could not reach the scanner. Is the backend running on port 8000?"
        );
      }
    })();
  }, []);

  return (
    <main className="min-h-screen">
      <DemoBanner />
      {error ? (
        <ErrorState message={error} />
      ) : scan ? (
        <ResultsDashboard initial={scan} />
      ) : (
        <LoadingState />
      )}
    </main>
  );
}

function DemoBanner() {
  return (
    <div className="border-b border-zombie-light/50 bg-zombie-wash">
      <div className="mx-auto flex max-w-6xl flex-col items-start justify-between gap-3 px-6 py-3 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <Link href="/" className="flex items-center gap-2 font-display font-bold">
            <ZombieMascot size={28} animate={false} />
            GraveKeeper
          </Link>
          <span className="text-sm text-dusk">
            Sample environment — see how it works, no login or credentials.
          </span>
        </div>
        <Link
          href="/scan"
          className="rounded-full bg-zombie px-4 py-1.5 text-sm font-semibold text-white hover:bg-zombie-dark"
        >
          Scan your own accounts
        </Link>
      </div>
    </div>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <ZombieMascot size={120} />
      <p className="text-dusk">Scanning the sample environment…</p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="mx-auto max-w-lg px-6 py-24 text-center">
      <ZombieMascot size={100} />
      <h1 className="mt-4 font-display text-2xl font-bold">The scanner is asleep</h1>
      <p className="mt-2 text-dusk">{message}</p>
      <p className="mt-4 text-sm text-dusk">
        Start it with{" "}
        <code className="rounded bg-zombie-wash px-1.5 py-0.5">
          uvicorn gravekeeper.main:app
        </code>{" "}
        in the <code className="rounded bg-zombie-wash px-1.5 py-0.5">scanner</code> folder.
      </p>
    </div>
  );
}
