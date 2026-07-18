"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { listRegistry, relativeDays } from "@/lib/api";
import type { RegistryEntry, Source } from "@/lib/types";
import { LIFECYCLE_LABELS } from "@/lib/types";
import RegistryEditor from "@/components/RegistryEditor";
import ZombieMascot from "@/components/ZombieMascot";

export default function RegistryPage() {
  const [entries, setEntries] = useState<RegistryEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [openKey, setOpenKey] = useState<string | null>(null);
  // Guard against StrictMode's double-invoke firing two requests per view.
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    (async () => {
      try {
        setEntries(await listRegistry());
      } catch (e) {
        setError(
          e instanceof Error
            ? e.message
            : "Could not reach the scanner. Is the backend running on port 8000?"
        );
      }
    })();
  }, []);

  // Fold a saved entry back into the list so the table reflects it immediately.
  function onSaved(saved: RegistryEntry) {
    setEntries((prev) =>
      prev
        ? prev.map((e) => (e.identity_key === saved.identity_key ? saved : e))
        : prev
    );
  }

  function toggle(identityKey: string) {
    setOpenKey((k) => (k === identityKey ? null : identityKey));
  }

  return (
    <main className="min-h-screen">
      <TopBar />
      {error ? (
        <ErrorState message={error} />
      ) : !entries ? (
        <LoadingState />
      ) : entries.length === 0 ? (
        <EmptyState />
      ) : (
        <RegistryTable
          entries={entries}
          openKey={openKey}
          onToggle={toggle}
          onSaved={onSaved}
        />
      )}
    </main>
  );
}

function TopBar() {
  return (
    <header className="border-b border-zombie-light/40 bg-surface/85">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <Link href="/" className="flex items-center gap-2 font-display text-lg font-bold">
          <ZombieMascot size={30} animate={false} />
          GraveKeeper
        </Link>
        <Link href="/scan" className="text-sm font-medium text-dusk hover:text-ink">
          Run a scan
        </Link>
      </div>
    </header>
  );
}

function RegistryTable({
  entries,
  openKey,
  onToggle,
  onSaved,
}: {
  entries: RegistryEntry[];
  openKey: string | null;
  onToggle: (identityKey: string) => void;
  onSaved: (entry: RegistryEntry) => void;
}) {
  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="flex items-center gap-3">
        <ZombieMascot size={48} animate={false} />
        <div>
          <h1 className="font-display text-2xl font-bold">Lifecycle registry</h1>
          <p className="text-sm text-dusk">
            Durable owners, states, and notes that persist across every scan.
          </p>
        </div>
      </div>

      <div className="mt-6 overflow-x-auto rounded-2xl border border-zombie-light/50 bg-surface">
        <table className="w-full min-w-[820px] text-left text-sm">
          <thead className="border-b border-zombie-light/50 text-xs uppercase tracking-wide text-dusk">
            <tr>
              <th className="px-4 py-3">Identity</th>
              <th className="px-4 py-3">Source</th>
              <th className="px-4 py-3">Assigned owner</th>
              <th className="px-4 py-3">Lifecycle</th>
              <th className="px-4 py-3">Note</th>
              <th className="px-4 py-3">Updated</th>
            </tr>
          </thead>
          <tbody>
            {entries.map((entry) => {
              const open = openKey === entry.identity_key;
              const panelId = `registry-panel-${entry.identity_key}`;
              return (
                <Fragment key={entry.identity_key}>
                  <tr className="relative border-b border-zombie-light/25 last:border-0 hover:bg-zombie-wash/40">
                    <td className="px-4 py-3 font-medium">
                      {/* Real button overlaying the whole row: keyboard-operable
                          natively, toggles the editor panel below. */}
                      <button
                        type="button"
                        onClick={() => onToggle(entry.identity_key)}
                        aria-expanded={open}
                        aria-controls={panelId}
                        aria-label={`Edit registry entry for ${entry.identity_key}`}
                        className="absolute inset-0 z-10 h-full w-full cursor-pointer rounded-none focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-zombie-dark"
                      />
                      {entry.identity_id}
                    </td>
                    <td className="px-4 py-3">
                      <SourceBadge source={entry.source} />
                    </td>
                    <td className="px-4 py-3 text-dusk">{entry.assigned_owner || "—"}</td>
                    <td className="px-4 py-3">
                      <LifecycleChip state={entry.lifecycle_state} />
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-dusk">
                      {entry.note || "—"}
                    </td>
                    <td className="px-4 py-3 text-dusk">
                      {relativeDays(entry.updated_at).text}
                    </td>
                  </tr>
                  {open && (
                    <tr className="bg-surface-light">
                      <td colSpan={6} className="px-4 py-5">
                        <div id={panelId} className="max-w-lg">
                          <RegistryEditor
                            identityKey={entry.identity_key}
                            entry={entry}
                            onSaved={onSaved}
                            autoFocus
                          />
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function SourceBadge({ source }: { source: Source }) {
  return (
    <span className="rounded bg-zombie-wash px-1.5 py-0.5 text-[10px] font-bold uppercase text-ink">
      {source}
    </span>
  );
}

function LifecycleChip({ state }: { state: RegistryEntry["lifecycle_state"] }) {
  const tone = state === "active" ? "bg-zombie-wash text-zombie-light" : "bg-surface-light text-dusk";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${tone}`}>
      {LIFECYCLE_LABELS[state]}
    </span>
  );
}

function LoadingState() {
  return (
    <div className="flex flex-col items-center gap-4 py-24 text-center">
      <ZombieMascot size={120} />
      <p className="text-dusk">Reading the lifecycle registry…</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="mx-auto max-w-lg px-6 py-24 text-center">
      <ZombieMascot size={100} />
      <h1 className="mt-4 font-display text-2xl font-bold">The registry is empty</h1>
      <p className="mt-2 text-dusk">
        Nothing has been recorded yet. Open a scan and save an owner, state, or note on an
        identity to start the registry.
      </p>
      <p className="mt-4 text-sm text-dusk">
        <Link href="/scan" className="font-semibold text-zombie-light underline">
          Run a scan
        </Link>{" "}
        to get started.
      </p>
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
