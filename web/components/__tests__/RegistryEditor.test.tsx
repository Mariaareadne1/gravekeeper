import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { RegistryEntry } from "@/lib/types";
import RegistryEditor from "../RegistryEditor";

// Keep the real ApiError (RegistryEditor branches on `instanceof ApiError`) and
// only replace the network call.
vi.mock("@/lib/api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/api")>();
  return { ...actual, upsertRegistryEntry: vi.fn() };
});

import { ApiError, upsertRegistryEntry } from "@/lib/api";

const upsertMock = vi.mocked(upsertRegistryEntry);

function makeEntry(overrides: Partial<RegistryEntry> = {}): RegistryEntry {
  return {
    identity_key: "aws:role-abc",
    source: "aws",
    identity_id: "role-abc",
    assigned_owner: "platform-team@acme.com",
    owner_status_override: null,
    lifecycle_state: "under_review",
    note: "watch this one",
    updated_by: null,
    updated_at: new Date().toISOString(),
    history: [],
    ...overrides,
  };
}

beforeEach(() => {
  upsertMock.mockReset();
});

afterEach(() => {
  cleanup();
});

describe("RegistryEditor", () => {
  it("renders owner, lifecycle, and note fields from the entry", () => {
    render(
      <RegistryEditor identityKey="aws:role-abc" entry={makeEntry()} onSaved={vi.fn()} />
    );

    expect(screen.getByRole("textbox", { name: "Assigned owner" })).toHaveValue(
      "platform-team@acme.com"
    );
    expect(screen.getByRole("combobox", { name: "Lifecycle state" })).toHaveValue(
      "under_review"
    );
    expect(screen.getByRole("textbox", { name: "Note" })).toHaveValue("watch this one");
  });

  it("saves with the right identity key + payload and calls onSaved", async () => {
    const user = userEvent.setup();
    const saved = makeEntry({ lifecycle_state: "retired" });
    upsertMock.mockResolvedValueOnce(saved);
    const onSaved = vi.fn();

    render(<RegistryEditor identityKey="aws:role-abc" entry={null} onSaved={onSaved} />);

    await user.type(
      screen.getByRole("textbox", { name: "Assigned owner" }),
      "new-owner@acme.com"
    );
    await user.selectOptions(
      screen.getByRole("combobox", { name: "Lifecycle state" }),
      "retired"
    );
    await user.type(screen.getByRole("textbox", { name: "Note" }), "decommissioned");
    await user.click(screen.getByRole("button", { name: /save to registry/i }));

    await waitFor(() => {
      expect(upsertMock).toHaveBeenCalledWith("aws:role-abc", {
        lifecycle_state: "retired",
        assigned_owner: "new-owner@acme.com",
        note: "decommissioned",
      });
    });
    expect(onSaved).toHaveBeenCalledWith(saved);
  });

  it("surfaces a role=alert error and does not call onSaved when the save is rejected", async () => {
    const user = userEvent.setup();
    upsertMock.mockRejectedValueOnce(new ApiError(500, "registry write failed"));
    const onSaved = vi.fn();

    render(<RegistryEditor identityKey="aws:role-abc" entry={makeEntry()} onSaved={onSaved} />);

    await user.click(screen.getByRole("button", { name: /save to registry/i }));

    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("registry write failed");
    expect(onSaved).not.toHaveBeenCalled();
  });
});
