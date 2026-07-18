"use client";

import { useEffect, useRef, useState } from "react";
import type { LifecycleState, RegistryEntry, RegistryUpdate } from "@/lib/types";
import { LIFECYCLE_LABELS } from "@/lib/types";
import { ApiError, upsertRegistryEntry } from "@/lib/api";

const LIFECYCLE_STATES: LifecycleState[] = [
  "active",
  "under_review",
  "decommission_requested",
  "retired",
];

function isLifecycleState(value: string): value is LifecycleState {
  return (LIFECYCLE_STATES as string[]).includes(value);
}

type SaveState = "idle" | "saving" | "saved";

// Presentational registry form. Decoupled from AgentRecord so it works both
// inside the scan drawer and on the standalone /registry page.
export default function RegistryEditor({
  identityKey,
  entry,
  onSaved,
  autoFocus = false,
}: {
  identityKey: string;
  entry: RegistryEntry | null;
  onSaved: (entry: RegistryEntry) => void;
  autoFocus?: boolean;
}) {
  const [assignedOwner, setAssignedOwner] = useState(entry?.assigned_owner ?? "");
  const [lifecycleState, setLifecycleState] = useState<LifecycleState>(
    entry?.lifecycle_state ?? "active"
  );
  const [note, setNote] = useState(entry?.note ?? "");
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [error, setError] = useState<string | null>(null);
  const ownerRef = useRef<HTMLInputElement>(null);

  // When mounted in an expanding container (registry accordion), pull focus into
  // the first field so keyboard users land inside the revealed panel.
  useEffect(() => {
    if (autoFocus) ownerRef.current?.focus();
  }, [autoFocus]);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (saveState === "saving") return; // guard against double-submit
    setError(null);
    setSaveState("saving");

    const trimmedOwner = assignedOwner.trim();
    const trimmedNote = note.trim();
    const update: RegistryUpdate = {
      lifecycle_state: lifecycleState,
      // Send the value when present, or an explicit clear flag when emptied.
      ...(trimmedOwner
        ? { assigned_owner: trimmedOwner }
        : { clear_assigned_owner: true }),
      ...(trimmedNote ? { note: trimmedNote } : { clear_note: true }),
    };

    try {
      const updated = await upsertRegistryEntry(identityKey, update);
      onSaved(updated);
      setSaveState("saved");
    } catch (err) {
      setSaveState("idle");
      setError(
        err instanceof ApiError
          ? `Couldn't save the registry entry: ${err.message}`
          : "Couldn't save the registry entry. Check your connection and try again."
      );
    }
  }

  // Any edit clears the saved confirmation so it always reflects the last save.
  function onEdit<T>(setter: (v: T) => void) {
    return (value: T) => {
      if (saveState === "saved") setSaveState("idle");
      setter(value);
    };
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <label className="block">
        <span className="text-sm font-medium">Assigned owner</span>
        <input
          ref={ownerRef}
          type="text"
          value={assignedOwner}
          onChange={(e) => onEdit(setAssignedOwner)(e.target.value)}
          autoComplete="off"
          spellCheck={false}
          placeholder="e.g. platform-team@acme.com"
          className="mt-1 w-full rounded-lg border border-zombie-light bg-bone px-3 py-2 text-sm outline-none focus:border-zombie-dark"
        />
      </label>

      <label className="block">
        <span className="text-sm font-medium">Lifecycle state</span>
        <select
          value={lifecycleState}
          onChange={(e) => {
            const { value } = e.target;
            if (isLifecycleState(value)) onEdit(setLifecycleState)(value);
          }}
          className="mt-1 w-full rounded-lg border border-zombie-light bg-bone px-3 py-2 text-sm outline-none focus:border-zombie-dark"
        >
          {LIFECYCLE_STATES.map((state) => (
            <option key={state} value={state}>
              {LIFECYCLE_LABELS[state]}
            </option>
          ))}
        </select>
      </label>

      <label className="block">
        <span className="text-sm font-medium">Note</span>
        <textarea
          value={note}
          onChange={(e) => onEdit(setNote)(e.target.value)}
          rows={3}
          spellCheck={false}
          placeholder="A durable note about this identity — kept across scans."
          className="mt-1 w-full resize-y rounded-lg border border-zombie-light bg-bone px-3 py-2 text-sm outline-none focus:border-zombie-dark"
        />
      </label>

      {error && (
        <div role="alert" className="rounded-lg bg-rot/10 px-3 py-2 text-sm text-rot">
          {error}
        </div>
      )}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={saveState === "saving"}
          className="rounded-full bg-zombie-dark px-5 py-2 text-sm font-semibold text-white transition hover:brightness-95 disabled:opacity-60"
        >
          {saveState === "saving" ? "Saving…" : "Save to registry"}
        </button>
        {saveState === "saved" && (
          <span role="status" className="text-xs font-medium text-zombie-dark">
            Saved.
          </span>
        )}
      </div>
    </form>
  );
}
