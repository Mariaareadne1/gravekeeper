import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AgentRecord, Finding, ScanResult } from "@/lib/types";
import ResultsDashboard from "../ResultsDashboard";

// Keep the real ApiError / helpers and only stub the network writes.
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, setReview: vi.fn(), upsertRegistryEntry: vi.fn() };
});

import { ApiError, setReview } from "@/lib/api";

const setReviewMock = vi.mocked(setReview);

const record: AgentRecord = {
  id: "agent-1",
  source: "aws",
  type: "service_account",
  display_name: "orphaned-deploy-bot",
  created_at: "2020-01-01T00:00:00Z",
  last_activity_at: null,
  owner: null,
  owner_status: "none",
  scopes: ["s3:*"],
  raw_metadata: {},
};

function makeScan(overrides: Partial<Finding> = {}): ScanResult {
  const finding: Finding = {
    agent_id: "agent-1",
    is_zombie_candidate: true,
    confidence: 0.9,
    reasons: ["NO_ACTIVITY_90D", "NO_OWNER"],
    recommended_action: "retire",
    review_state: null,
    registry: null,
    ...overrides,
  };
  return {
    scan_id: "scan-1",
    started_at: "2024-01-01T00:00:00Z",
    finished_at: "2024-01-01T00:01:00Z",
    environment_label: "Sample environment",
    source: "aws",
    total_identities: 1,
    zombie_candidates: 1,
    findings: [finding],
    records: [record],
  };
}

beforeEach(() => {
  setReviewMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("ResultsDashboard", () => {
  it("renders the findings table with a summary and a zombie row", () => {
    render(<ResultsDashboard initial={makeScan()} />);

    expect(screen.getByRole("heading", { name: /look abandoned/i })).toBeInTheDocument();
    expect(screen.getByRole("table")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /view details for orphaned-deploy-bot/i })
    ).toBeInTheDocument();
  });

  it("opens the detail drawer on Enter and closes it on Escape", async () => {
    const user = userEvent.setup();
    render(<ResultsDashboard initial={makeScan()} />);

    const row = screen.getByRole("button", { name: /view details for orphaned-deploy-bot/i });
    row.focus();
    await user.keyboard("{Enter}");

    expect(await screen.findByRole("dialog")).toBeInTheDocument();

    await user.keyboard("{Escape}");
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  });

  it("opens the detail drawer when Space is pressed on a row", async () => {
    const user = userEvent.setup();
    render(<ResultsDashboard initial={makeScan()} />);

    const row = screen.getByRole("button", { name: /view details for orphaned-deploy-bot/i });
    row.focus();
    await user.keyboard("[Space]");

    expect(await screen.findByRole("dialog")).toBeInTheDocument();
  });

  it("reverts the optimistic mark and shows a role=alert when the review write fails", async () => {
    const user = userEvent.setup();
    // Starts as "keep" so we can prove the failed "review" mark rolls back to it.
    setReviewMock.mockRejectedValueOnce(new ApiError(500, "backend unavailable"));
    render(<ResultsDashboard initial={makeScan({ review_state: "keep" })} />);

    const row = screen.getByRole("button", { name: /view details for orphaned-deploy-bot/i });
    row.focus();
    await user.keyboard("{Enter}");
    await screen.findByRole("dialog");

    await user.click(screen.getByRole("button", { name: /mark for review/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("backend unavailable");
    // Optimistic change reverted: the row badge is back to "keep", not "review".
    expect(screen.getByText("keep")).toBeInTheDocument();
    expect(screen.queryByText("review")).not.toBeInTheDocument();
  });
});
