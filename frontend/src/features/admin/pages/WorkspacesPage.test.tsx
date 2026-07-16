import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAdmin } from "../AdminContext";
import { adminApi } from "../api";
import WorkspacesPage from "./WorkspacesPage";

vi.mock("../AdminContext", () => ({ useAdmin: vi.fn() }));
vi.mock("../api", () => ({
  adminApi: {
    workspaces: vi.fn(),
    createWorkspace: vi.fn(),
    renameWorkspace: vi.fn(),
  },
}));

describe("WorkspacesPage async states", () => {
  beforeEach(() => {
    vi.mocked(useAdmin).mockReturnValue({
      refresh: vi.fn(),
    } as unknown as ReturnType<typeof useAdmin>);
  });

  it("shows a recoverable error and retries the failed request", async () => {
    const user = userEvent.setup();
    vi.mocked(adminApi.workspaces)
      .mockRejectedValueOnce(new Error("Organization service unavailable"))
      .mockResolvedValueOnce([]);

    render(<WorkspacesPage />);

    expect(screen.getByRole("progressbar")).toBeInTheDocument();
    expect(
      await screen.findByText("Organization service unavailable"),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Retry" }));

    await waitFor(() => expect(adminApi.workspaces).toHaveBeenCalledTimes(2));
    await waitFor(() =>
      expect(
        screen.queryByText("Organization service unavailable"),
      ).not.toBeInTheDocument(),
    );
  });
});
