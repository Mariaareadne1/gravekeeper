"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { AgentRecord, Finding, ReasonCode, RegistryEntry, ScanResult } from "@/lib/types";
import { LIFECYCLE_LABELS, REASON_LABELS } from "@/lib/types";
import { ApiError, exportUrl, identityKeyFor, relativeDays, setReview } from "@/lib/api";
import RegistryEditor from "./RegistryEditor";
import ZombieMascot from "./ZombieMascot";

type Filter = "all" | "zombies" | "healthy";

interface Row {
  finding: Finding;
  record: AgentRecord;
}

export default function ResultsDashboard({ initial }: { initial: ScanResult }) {
  const [scan, setScan] = useState<ScanResult>(initial);
  const [filter, setFilter] = useState<Filter>("zombies");
  const [openId, setOpenId] = useState<string | null>(null);
  const [markError, setMarkError] = useState<string | null>(null);
  // Main content wrapper — made inert while the drawer is open. The filter
  // group holds the fallback focus target for when a trigger row is gone.
  const contentRef = useRef<HTMLDivElement>(null);
  const filterGroupRef = useRef<HTMLDivElement>(null);

  // Stable identity so the drawer's mount-scoped focus/inert effect doesn't
  // re-run (and steal focus) on every parent re-render.
  const focusFallback = useCallback(() => {
    filterGroupRef.current?.querySelector<HTMLButtonElement>("button")?.focus();
  }, []);

  const rows: Row[] = useMemo(() => {
    const byId = new Map(scan.records.map((r) => [r.id, r]));
    return scan.findings
      .map((finding) => ({ finding, record: byId.get(finding.agent_id)! }))
      .filter((r) => r.record)
      .sort((a, b) => b.finding.confidence - a.finding.confidence);
  }, [scan]);

  const visible = rows.filter((r) => {
    if (filter === "zombies") return r.finding.is_zombie_candidate;
    if (filter === "healthy") return !r.finding.is_zombie_candidate;
    return true;
  });

  const healthy = scan.total_identities - scan.zombie_candidates;

  async function mark(agentId: string, state: "review" | "keep" | null) {
    setMarkError(null);
    // Snapshot only THIS finding's review_state for rollback, so a failure
    // reverts just this mark and never clobbers a concurrent update elsewhere.
    const previousState =
      scan.findings.find((f) => f.agent_id === agentId)?.review_state ?? null;
    setScan((s) => ({
      ...s,
      findings: s.findings.map((f) =>
        f.agent_id === agentId ? { ...f, review_state: state } : f
      ),
    }));
    try {
      const updated = await setReview(scan.scan_id, agentId, state);
      setScan((s) => ({
        ...s,
        findings: s.findings.map((f) => (f.agent_id === agentId ? updated : f)),
      }));
    } catch (err) {
      // Revert only this finding's review_state and surface the failure.
      setScan((s) => ({
        ...s,
        findings: s.findings.map((f) =>
          f.agent_id === agentId ? { ...f, review_state: previousState } : f
        ),
      }));
      setMarkError(
        err instanceof ApiError
          ? `Couldn't save your mark: ${err.message}`
          : "Couldn't save your mark. Check your connection and try again."
      );
    }
  }

  // Fold a saved registry entry back into the finding so the row badge and the
  // drawer stay in sync without a re-scan.
  function onRegistrySaved(agentId: string, registry: RegistryEntry) {
    setScan((s) => ({
      ...s,
      findings: s.findings.map((f) =>
        f.agent_id === agentId ? { ...f, registry } : f
      ),
    }));
  }

  function openDetails(agentId: string) {
    setMarkError(null);
    setOpenId(agentId);
  }

  function closeDrawer() {
    setMarkError(null);
    setOpenId(null);
  }

  const openRow = openId ? rows.find((r) => r.finding.agent_id === openId) : null;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div ref={contentRef}>
        <SummaryBar
          scanId={scan.scan_id}
          label={scan.environment_label}
          zombies={scan.zombie_candidates}
          healthy={healthy}
          total={scan.total_identities}
        />

        <div
          ref={filterGroupRef}
          role="group"
          aria-label="Filter results"
          className="mt-6 flex flex-wrap items-center gap-2"
        >
        <FilterTab active={filter === "zombies"} onClick={() => setFilter("zombies")}>
          Zombies ({scan.zombie_candidates})
        </FilterTab>
        <FilterTab active={filter === "healthy"} onClick={() => setFilter("healthy")}>
          Healthy ({healthy})
        </FilterTab>
        <FilterTab active={filter === "all"} onClick={() => setFilter("all")}>
          All ({scan.total_identities})
        </FilterTab>
      </div>

      {visible.length === 0 ? (
        <EmptyState filter={filter} />
      ) : (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-zombie-light/50 bg-surface">
          <table className="w-full min-w-[720px] text-left text-sm">
            <thead className="border-b border-zombie-light/50 text-xs uppercase tracking-wide text-dusk">
              <tr>
                <th className="px-4 py-3">Identity</th>
                <th className="px-4 py-3">Last active</th>
                <th className="px-4 py-3">Owner</th>
                <th className="px-4 py-3">Why</th>
                <th className="px-4 py-3 text-right">Confidence</th>
              </tr>
            </thead>
            <tbody>
              {visible.map(({ finding, record }) => (
                <tr
                  key={finding.agent_id}
                  className="relative border-b border-zombie-light/25 last:border-0 hover:bg-zombie-wash/40"
                >
                  <td className="px-4 py-3">
                    {/* Real button overlaying the whole row: keyboard-operable
                        natively, keeps the full-row-click feel. Table cells
                        below carry only non-interactive display content. */}
                    <button
                      type="button"
                      onClick={() => openDetails(finding.agent_id)}
                      aria-label={`View details for ${record.display_name}`}
                      className="absolute inset-0 z-10 h-full w-full cursor-pointer rounded-none focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-zombie-dark"
                    />
                    <div className="flex items-center gap-2 font-medium">
                      <SourceBadge source={record.source} />
                      {record.display_name}
                      {finding.review_state && <ReviewTag state={finding.review_state} />}
                      {finding.registry &&
                        finding.registry.lifecycle_state !== "active" && (
                          <Chip tone="gray">
                            {LIFECYCLE_LABELS[finding.registry.lifecycle_state]}
                          </Chip>
                        )}
                    </div>
                    <div className="text-xs text-dusk">{record.type.replace(/_/g, " ")}</div>
                  </td>
                  <td className="px-4 py-3">
                    <LastActive iso={record.last_activity_at} />
                  </td>
                  <td className="px-4 py-3">
                    <OwnerChip owner={record.owner} status={record.owner_status} />
                  </td>
                  <td className="px-4 py-3 text-xs text-dusk">
                    {finding.reasons.length
                      ? REASON_LABELS[finding.reasons[0] as ReasonCode]
                      : "looks healthy"}
                    {finding.reasons.length > 1 && (
                      <span className="text-dusk"> +{finding.reasons.length - 1}</span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <ConfidenceBar value={finding.confidence} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      </div>

      {openRow && (
        <DetailDrawer
          row={openRow}
          error={markError}
          contentRef={contentRef}
          onClose={closeDrawer}
          onFallbackFocus={focusFallback}
          onMark={mark}
          onRegistrySaved={onRegistrySaved}
        />
      )}
    </div>
  );
}

function SummaryBar({
  scanId,
  label,
  zombies,
  healthy,
  total,
}: {
  scanId: string;
  label: string;
  zombies: number;
  healthy: number;
  total: number;
}) {
  return (
    <div className="rounded-2xl border border-zombie-light/50 bg-surface p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="text-sm text-dusk">{label}</div>
        <div className="flex gap-2">
          <a
            href={exportUrl(scanId, "csv")}
            className="rounded-full border border-zombie-light px-3 py-1 text-xs font-semibold text-dusk hover:bg-zombie-wash"
          >
            Export CSV
          </a>
          <a
            href={exportUrl(scanId, "json")}
            className="rounded-full border border-zombie-light px-3 py-1 text-xs font-semibold text-dusk hover:bg-zombie-wash"
          >
            Export JSON
          </a>
        </div>
      </div>
      <h1 className="mt-1 font-display text-3xl font-bold sm:text-4xl">
        {zombies > 0 ? (
          <>
            <span className="text-rot">{zombies} agents</span> look abandoned.
          </>
        ) : (
          <>Nothing looks abandoned here.</>
        )}
      </h1>
      <div className="mt-4 flex flex-wrap gap-6 text-sm">
        <Stat n={total} label="identities found" />
        <Stat n={zombies} label="zombie candidates" tone="rot" />
        <Stat n={healthy} label="look healthy" tone="zombie" />
      </div>
    </div>
  );
}

function Stat({ n, label, tone }: { n: number; label: string; tone?: "rot" | "zombie" }) {
  const color = tone === "rot" ? "text-rot" : tone === "zombie" ? "text-zombie-light" : "text-ink";
  return (
    <div>
      <span className={`font-display text-2xl font-bold ${color}`}>{n}</span>{" "}
      <span className="text-dusk">{label}</span>
    </div>
  );
}

function FilterTab({
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
      className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
        active
          ? "bg-zombie-dark text-white"
          : "border border-zombie-light text-dusk hover:bg-zombie-wash"
      }`}
    >
      {children}
    </button>
  );
}

function SourceBadge({ source }: { source: string }) {
  return (
    <span className="rounded bg-zombie-wash px-1.5 py-0.5 text-[10px] font-bold uppercase text-ink">
      {source}
    </span>
  );
}

function LastActive({ iso }: { iso: string | null }) {
  const { text, days } = relativeDays(iso);
  const stale = days === null || days >= 90;
  return <span className={stale ? "text-rot" : "text-dusk"}>{text}</span>;
}

function OwnerChip({ owner, status }: { owner: string | null; status: string }) {
  if (status === "disabled")
    return <Chip tone="rot">{owner ? `${owner} · left` : "owner left"}</Chip>;
  if (status === "missing") return <Chip tone="rot">owner missing</Chip>;
  if (status === "none" || !owner) return <Chip tone="gray">no owner</Chip>;
  if (status === "unknown") return <Chip tone="gray">{owner} · unverified</Chip>;
  return <Chip tone="zombie">{owner}</Chip>;
}

function Chip({ tone, children }: { tone: "rot" | "gray" | "zombie"; children: React.ReactNode }) {
  const styles =
    tone === "rot"
      ? "bg-rot/10 text-rot"
      : tone === "zombie"
        ? "bg-zombie-wash text-ink"
        : "bg-surface-light text-dusk";
  return (
    <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${styles}`}>{children}</span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const strong = value >= 0.5;
  return (
    <div className="ml-auto flex w-28 items-center gap-2">
      <div className="h-1.5 flex-1 rounded-full bg-zombie-wash">
        <div
          className={`h-full rounded-full ${strong ? "bg-rot" : "bg-zombie"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-9 text-right text-xs tabular-nums text-dusk">{pct}%</span>
    </div>
  );
}

function ReviewTag({ state }: { state: string }) {
  return (
    <span className="rounded-full bg-zombie-wash px-2 py-0.5 text-[10px] font-semibold uppercase text-zombie-light">
      {state}
    </span>
  );
}

function EmptyState({ filter }: { filter: Filter }) {
  return (
    <div className="mt-4 flex flex-col items-center gap-4 rounded-2xl border border-dashed border-zombie-light bg-surface py-16 text-center">
      <ZombieMascot size={90} />
      <p className="text-dusk">
        {filter === "zombies"
          ? "No zombie candidates in this view. That's a good sign."
          : "Nothing to show here."}
      </p>
    </div>
  );
}

const FOCUSABLE_SELECTOR =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

function DetailDrawer({
  row,
  error,
  contentRef,
  onClose,
  onFallbackFocus,
  onMark,
  onRegistrySaved,
}: {
  row: Row;
  error: string | null;
  contentRef: React.RefObject<HTMLElement>;
  onClose: () => void;
  onFallbackFocus: () => void;
  onMark: (agentId: string, state: "review" | "keep" | null) => void;
  onRegistrySaved: (agentId: string, registry: RegistryEntry) => void;
}) {
  const { finding, record } = row;
  const asideRef = useRef<HTMLElement>(null);

  // Move focus into the drawer on open, restore it to the trigger on close,
  // keep Tab focus trapped inside, and make the page behind inert so screen
  // readers in browse mode can't wander out of the modal.
  useEffect(() => {
    const trigger = document.activeElement as HTMLElement | null;
    const content = contentRef.current;
    // `inert` blocks focus + pointer + SR browse mode; aria-hidden is the
    // fallback for engines that don't yet honor inert.
    content?.setAttribute("inert", "");
    content?.setAttribute("aria-hidden", "true");
    asideRef.current?.focus();
    return () => {
      content?.removeAttribute("inert");
      content?.removeAttribute("aria-hidden");
      // Restore focus to the trigger, but only if it's still in the document —
      // a re-render (e.g. a failed mark reverting a row) can detach it.
      if (trigger && document.body.contains(trigger)) {
        trigger.focus();
      } else {
        onFallbackFocus();
      }
    };
  }, [contentRef, onFallbackFocus]);

  function handleKeyDown(e: React.KeyboardEvent<HTMLElement>) {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
      return;
    }
    if (e.key !== "Tab") return;
    const aside = asideRef.current;
    if (!aside) return;
    const focusable = Array.from(
      aside.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
    );
    if (focusable.length === 0) {
      e.preventDefault();
      aside.focus();
      return;
    }
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    const active = document.activeElement;
    if (e.shiftKey && (active === first || active === aside)) {
      e.preventDefault();
      last.focus();
    } else if (!e.shiftKey && active === last) {
      e.preventDefault();
      first.focus();
    }
  }

  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div
        className="absolute inset-0 bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={asideRef}
        role="dialog"
        aria-modal="true"
        aria-label={`Details for ${record.display_name}`}
        tabIndex={-1}
        onKeyDown={handleKeyDown}
        className="relative z-10 h-full w-full max-w-md overflow-y-auto bg-surface p-6 shadow-2xl"
      >
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <SourceBadge source={record.source} />
              <h2 className="font-display text-xl font-bold">{record.display_name}</h2>
            </div>
            <p className="mt-1 text-sm text-dusk">{record.type.replace(/_/g, " ")}</p>
          </div>
          <button
            onClick={onClose}
            className="inline-flex min-h-[44px] min-w-[44px] items-center justify-center rounded-full text-2xl text-dusk hover:text-ink"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="mt-5 rounded-xl border border-zombie-light/50 bg-surface-light p-4">
          <div className="flex items-center justify-between">
            <span className="text-sm font-semibold">Zombie confidence</span>
            <span className="font-display text-lg font-bold text-rot">
              {Math.round(finding.confidence * 100)}%
            </span>
          </div>
          <p className="mt-1 text-xs text-dusk">
            Recommended: <span className="font-semibold">{finding.recommended_action}</span>. This
            is an inference from signals — you make the call.
          </p>
        </div>

        <section className="mt-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-dusk">Why</h3>
          <ul className="mt-2 space-y-2">
            {finding.reasons.length === 0 && (
              <li className="text-sm text-dusk">No zombie signals — this one looks healthy.</li>
            )}
            {finding.reasons.map((r) => (
              <li key={r} className="flex gap-2 text-sm">
                <span className="mt-1.5 h-2 w-2 flex-none rounded-full bg-rot" />
                {REASON_LABELS[r]}
              </li>
            ))}
          </ul>
        </section>

        <section className="mt-5 space-y-2 text-sm">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-dusk">Details</h3>
          <DetailRow k="Last activity" v={relativeDays(record.last_activity_at).text} />
          <DetailRow
            k="Owner"
            v={record.owner ? `${record.owner} (${record.owner_status})` : "none on record"}
          />
          <DetailRow k="Created" v={record.created_at ? relativeDays(record.created_at).text : "—"} />
          <DetailRow k="Permissions" v={record.scopes.join(", ") || "—"} />
        </section>

        <div className="mt-6 flex gap-3">
          <button
            onClick={() => onMark(finding.agent_id, "review")}
            className="flex-1 rounded-full bg-zombie-dark px-4 py-2 text-sm font-semibold text-white hover:brightness-95"
          >
            Mark for review
          </button>
          <button
            onClick={() => onMark(finding.agent_id, "keep")}
            className="flex-1 rounded-full border border-zombie-light px-4 py-2 text-sm font-semibold text-zombie-light hover:bg-zombie-wash"
          >
            Mark as keep
          </button>
        </div>
        {error && (
          <div
            role="alert"
            className="mt-3 rounded-lg bg-rot/10 px-3 py-2 text-sm text-rot"
          >
            {error}
          </div>
        )}
        <p className="mt-3 text-center text-xs text-dusk">
          Marking is a note to yourself. GraveKeeper never revokes or deletes anything.
        </p>

        <section className="mt-6 border-t border-zombie-light/50 pt-5">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-dusk">
            Lifecycle registry
          </h3>
          <p className="mt-1 text-xs text-dusk">
            The mark above is scan-local. The registry below is durable — its owner,
            lifecycle state, and note persist across every future scan.
          </p>
          <div className="mt-4">
            <RegistryEditor
              key={identityKeyFor(record.source, finding.agent_id)}
              identityKey={identityKeyFor(record.source, finding.agent_id)}
              entry={finding.registry ?? null}
              onSaved={(entry) => onRegistrySaved(finding.agent_id, entry)}
            />
          </div>
        </section>
      </aside>
    </div>
  );
}

function DetailRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-zombie-light/25 py-1.5 last:border-0">
      <span className="text-dusk">{k}</span>
      <span className="text-right font-medium">{v}</span>
    </div>
  );
}
