import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { useAdmin } from "../AdminContext";
import { adminApi } from "../api";
import WorkspaceOnboardingPage from "./WorkspaceOnboardingPage";

vi.mock("../AdminContext", () => ({ useAdmin: vi.fn() }));
vi.mock("../api", () => ({ adminApi: { createWorkspace: vi.fn() } }));

const refresh = vi.fn();
const bootstrap = {
  organization: { id: 1, name: "Acme Research", slug: "acme-research" },
  organization_role: "organization_admin" as const,
  workspaces: [],
  permissions: ["workspaces.manage"],
  onboarding_required: true,
};

describe("WorkspaceOnboardingPage", () => {
  beforeEach(() => {
    refresh.mockResolvedValue(undefined);
    vi.mocked(adminApi.createWorkspace).mockResolvedValue({
      id: 4,
      name: "Research",
    } as never);
    vi.mocked(useAdmin).mockReturnValue({
      bootstrap,
      loading: false,
      error: "",
      workspaceId: null,
      selectWorkspace: vi.fn(),
      refresh,
    });
  });

  function renderRoutes() {
    return render(
      <MemoryRouter initialEntries={["/onboarding/workspace"]}>
        <Routes>
          <Route
            path="/onboarding/workspace"
            element={<WorkspaceOnboardingPage />}
          />
          <Route path="/admin/overview" element={<h1>Admin overview</h1>} />
        </Routes>
      </MemoryRouter>,
    );
  }

  it("requires and creates the first workspace before entering administration", async () => {
    renderRoutes();

    expect(
      screen.getByRole("heading", { name: "Create your first workspace" }),
    ).toBeInTheDocument();
    fireEvent.change(
      screen.getByRole("textbox", { name: /Workspace name/ }),
      { target: { value: "Research" } },
    );
    fireEvent.click(screen.getByRole("button", { name: "Create workspace" }));

    expect(adminApi.createWorkspace).toHaveBeenCalledWith("Research");
    await waitFor(() => expect(refresh).toHaveBeenCalledOnce());
    expect(
      await screen.findByRole("heading", { name: "Admin overview" }),
    ).toBeInTheDocument();
  });

  it("redirects administrators who already completed onboarding", async () => {
    vi.mocked(useAdmin).mockReturnValue({
      bootstrap: {
        ...bootstrap,
        onboarding_required: false,
        workspaces: [
          {
            id: 4,
            organization_id: 1,
            name: "Research",
            slug: "research",
            role: "workspace_admin",
            member_count: 1,
          },
        ],
      },
      loading: false,
      error: "",
      workspaceId: 4,
      selectWorkspace: vi.fn(),
      refresh,
    });
    renderRoutes();

    expect(
      await screen.findByRole("heading", { name: "Admin overview" }),
    ).toBeInTheDocument();
  });
});
