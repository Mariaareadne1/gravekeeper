"use client";

import { useMemo, useState } from "react";
import type { AgentRecord, Finding, ReasonCode, ScanResult } from "@/lib/types";
import { REASON_LABELS } from "@/lib/types";
import { relativeDays, setReview } from "@/lib/api";
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
    try {
      const updated = await setReview(scan.scan_id, agentId, state);
      setScan((s) => ({
        ...s,
        findings: s.findings.map((f) => (f.agent_id === agentId ? updated : f)),
      }));
    } catch {
      /* best-effort; the dashboard stays usable if the write fails */
    }
  }

  const openRow = openId ? rows.find((r) => r.finding.agent_id === openId) : null;

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <SummaryBar
        label={scan.environment_label}
        zombies={scan.zombie_candidates}
        healthy={healthy}
        total={scan.total_identities}
      />

      <div className="mt-6 flex flex-wrap items-center gap-2">
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
        <div className="mt-4 overflow-x-auto rounded-2xl border border-zombie-light/50 bg-white/70">
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
                  onClick={() => setOpenId(finding.agent_id)}
                  className="cursor-pointer border-b border-zombie-light/25 last:border-0 hover:bg-zombie-wash/40"
                >
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2 font-medium">
                      <SourceBadge source={record.source} />
                      {record.display_name}
                      {finding.review_state && <ReviewTag state={finding.review_state} />}
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

      {openRow && (
        <DetailDrawer row={openRow} onClose={() => setOpenId(null)} onMark={mark} />
      )}
    </div>
  );
}

function SummaryBar({
  label,
  zombies,
  healthy,
  total,
}: {
  label: string;
  zombies: number;
  healthy: number;
  total: number;
}) {
  return (
    <div className="rounded-2xl border border-zombie-light/50 bg-white/70 p-6">
      <div className="text-sm text-dusk">{label}</div>
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
  const color = tone === "rot" ? "text-rot" : tone === "zombie" ? "text-zombie-dark" : "text-ink";
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
      onClick={onClick}
      className={`rounded-full px-4 py-1.5 text-sm font-semibold transition ${
        active
          ? "bg-zombie text-white"
          : "border border-zombie-light text-dusk hover:bg-zombie-wash"
      }`}
    >
      {children}
    </button>
  );
}

function SourceBadge({ source }: { source: string }) {
  return (
    <span className="rounded bg-zombie-wash px-1.5 py-0.5 text-[10px] font-bold uppercase text-zombie-dark">
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
        ? "bg-zombie-wash text-zombie-dark"
        : "bg-dusk/10 text-dusk";
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
    <span className="rounded-full bg-zombie-dark/10 px-2 py-0.5 text-[10px] font-semibold uppercase text-zombie-dark">
      {state}
    </span>
  );
}

function EmptyState({ filter }: { filter: Filter }) {
  return (
    <div className="mt-4 flex flex-col items-center gap-4 rounded-2xl border border-dashed border-zombie-light bg-white/50 py-16 text-center">
      <ZombieMascot size={90} />
      <p className="text-dusk">
        {filter === "zombies"
          ? "No zombie candidates in this view. That's a good sign."
          : "Nothing to show here."}
      </p>
    </div>
  );
}

function DetailDrawer({
  row,
  onClose,
  onMark,
}: {
  row: Row;
  onClose: () => void;
  onMark: (agentId: string, state: "review" | "keep" | null) => void;
}) {
  const { finding, record } = row;
  return (
    <div className="fixed inset-0 z-40 flex justify-end">
      <div
        className="absolute inset-0 bg-ink/30"
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        role="dialog"
        aria-label={`Details for ${record.display_name}`}
        className="relative z-10 h-full w-full max-w-md overflow-y-auto bg-bone p-6 shadow-2xl"
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
            className="rounded-full px-2 text-2xl text-dusk hover:text-ink"
            aria-label="Close"
          >
            ×
          </button>
        </div>

        <div className="mt-5 rounded-xl border border-zombie-light/50 bg-white/70 p-4">
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
            className="flex-1 rounded-full bg-zombie px-4 py-2 text-sm font-semibold text-white hover:bg-zombie-dark"
          >
            Mark for review
          </button>
          <button
            onClick={() => onMark(finding.agent_id, "keep")}
            className="flex-1 rounded-full border border-zombie-dark px-4 py-2 text-sm font-semibold text-zombie-dark hover:bg-zombie-wash"
          >
            Mark as keep
          </button>
        </div>
        <p className="mt-3 text-center text-xs text-dusk">
          Marking is a note to yourself. GraveKeeper never revokes or deletes anything.
        </p>
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
