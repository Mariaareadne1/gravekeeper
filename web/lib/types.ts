// Mirrors the backend pydantic models (scanner/gravekeeper/models.py).

export type Source = "aws" | "github" | "gcp" | "azure" | "synthetic";

export type IdentityType =
  | "service_account"
  | "api_key"
  | "oauth_app"
  | "automation"
  | "agent";

export type OwnerStatus = "active" | "disabled" | "missing" | "unknown" | "none";

export type ReasonCode =
  | "NO_ACTIVITY_90D"
  | "OWNER_DISABLED"
  | "OWNER_MISSING"
  | "NO_OWNER"
  | "OVERPRIVILEGED"
  | "NEVER_USED_BUT_OLD";

export type RecommendedAction = "keep" | "review" | "retire";

export interface AgentRecord {
  id: string;
  source: Source;
  type: IdentityType;
  display_name: string;
  created_at: string | null;
  last_activity_at: string | null;
  owner: string | null;
  owner_status: OwnerStatus;
  scopes: string[];
  raw_metadata: Record<string, unknown>;
}

export interface Finding {
  agent_id: string;
  is_zombie_candidate: boolean;
  confidence: number;
  reasons: ReasonCode[];
  recommended_action: RecommendedAction;
  review_state: string | null;
}

export interface ScanResult {
  scan_id: string;
  started_at: string;
  finished_at: string | null;
  environment_label: string;
  source: Source;
  total_identities: number;
  zombie_candidates: number;
  findings: Finding[];
  records: AgentRecord[];
}

export interface ScanSummary {
  scan_id: string;
  source: string;
  environment_label: string;
  total_identities: number;
  zombie_candidates: number;
}

// Plain-language labels for reason codes, shown in the UI.
export const REASON_LABELS: Record<ReasonCode, string> = {
  NO_ACTIVITY_90D: "No activity in 90+ days",
  OWNER_DISABLED: "Owner account is disabled (they left)",
  OWNER_MISSING: "Recorded owner no longer exists",
  NO_OWNER: "No owner on record",
  OVERPRIVILEGED: "Broad permissions it doesn't use",
  NEVER_USED_BUT_OLD: "Created long ago, never used",
};
