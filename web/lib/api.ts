import type {
  Finding,
  LifecycleState,
  RegistryEntry,
  RegistryUpdate,
  ScanResult,
  ScanSummary,
  Source,
} from "./types";

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function handle<T>(resp: Response): Promise<T> {
  if (!resp.ok) {
    let detail = resp.statusText;
    try {
      const body: unknown = await resp.json();
      if (typeof body === "object" && body && "detail" in body) {
        const { detail: bodyDetail } = body as { detail?: unknown };
        if (typeof bodyDetail === "string" && bodyDetail) detail = bodyDetail;
      }
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(resp.status, detail);
  }
  return resp.json() as Promise<T>;
}

export interface ScanRequest {
  connector?: Source;
  synthetic?: boolean;
  // Credential dict shape varies per connector; GCP nests a service-account
  // JSON object, so this is not restricted to string values.
  credentials?: Record<string, unknown>;
  environment_label?: string;
  persist?: boolean;
}

export async function runScan(req: ScanRequest): Promise<ScanSummary> {
  const resp = await fetch(`${API_BASE}/scan`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(req),
  });
  return handle<ScanSummary>(resp);
}

export async function getScan(scanId: string): Promise<ScanResult> {
  return handle<ScanResult>(await fetch(`${API_BASE}/scan/${scanId}`));
}

export async function setReview(
  scanId: string,
  agentId: string,
  reviewState: "review" | "keep" | null
): Promise<Finding> {
  const resp = await fetch(
    `${API_BASE}/scan/${scanId}/review?agent_id=${encodeURIComponent(agentId)}`,
    {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ review_state: reviewState }),
    }
  );
  return handle<Finding>(resp);
}

export function exportUrl(scanId: string, format: "json" | "csv"): string {
  return `${API_BASE}/scan/${scanId}/export?format=${format}`;
}

// --- Lifecycle registry ------------------------------------------------------

// The durable identity of a registry entry: the connector plus its native id.
// NOTE: the caller passes the agent_id, which is itself already source-prefixed
// (e.g. "aws:user:..."), so the durable key intentionally double-prefixes the
// source ("aws:aws:user:..."). This matches the backend's
// `identity_key_for(record.source, agent_id)` join — do NOT "fix" one side in
// isolation or registry lookups will silently miss.
export function identityKeyFor(source: Source, id: string): string {
  return `${source}:${id}`;
}

export interface RegistryFilters {
  lifecycle_state?: LifecycleState;
  source?: Source;
}

export async function listRegistry(filters?: RegistryFilters): Promise<RegistryEntry[]> {
  const params = new URLSearchParams();
  if (filters?.lifecycle_state) params.set("lifecycle_state", filters.lifecycle_state);
  if (filters?.source) params.set("source", filters.source);
  const query = params.toString();
  return handle<RegistryEntry[]>(
    await fetch(`${API_BASE}/registry${query ? `?${query}` : ""}`)
  );
}

// Look up a single entry. A 404 means "no entry yet" — return null rather than
// throwing so callers can treat an unregistered identity as an empty form.
export async function getRegistryEntry(identityKey: string): Promise<RegistryEntry | null> {
  const resp = await fetch(
    `${API_BASE}/registry/lookup?identity_key=${encodeURIComponent(identityKey)}`
  );
  if (resp.status === 404) return null;
  return handle<RegistryEntry>(resp);
}

export async function upsertRegistryEntry(
  identityKey: string,
  update: RegistryUpdate
): Promise<RegistryEntry> {
  const resp = await fetch(
    `${API_BASE}/registry?identity_key=${encodeURIComponent(identityKey)}`,
    {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(update),
    }
  );
  return handle<RegistryEntry>(resp);
}

// A relative "214 days ago" helper for last-activity columns.
export function relativeDays(iso: string | null): { text: string; days: number | null } {
  if (!iso) return { text: "never used", days: null };
  const then = new Date(iso).getTime();
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return { text: "today", days: 0 };
  if (days === 1) return { text: "yesterday", days: 1 };
  return { text: `${days} days ago`, days };
}
