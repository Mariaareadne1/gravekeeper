import type { Finding, ScanResult, ScanSummary, Source } from "./types";

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
      const body = await resp.json();
      detail = body.detail || detail;
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
  credentials?: Record<string, string>;
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

export async function getFindings(scanId: string, zombiesOnly = false): Promise<Finding[]> {
  const q = zombiesOnly ? "?zombies_only=true" : "";
  return handle<Finding[]>(await fetch(`${API_BASE}/scan/${scanId}/findings${q}`));
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

// A relative "214 days ago" helper for last-activity columns.
export function relativeDays(iso: string | null): { text: string; days: number | null } {
  if (!iso) return { text: "never used", days: null };
  const then = new Date(iso).getTime();
  const days = Math.floor((Date.now() - then) / 86_400_000);
  if (days <= 0) return { text: "today", days: 0 };
  if (days === 1) return { text: "yesterday", days: 1 };
  if (days < 60) return { text: `${days} days ago`, days };
  return { text: `${days} days ago`, days };
}
