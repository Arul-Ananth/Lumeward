import { apiRequest } from "../../services/http";
import type {
  AdminBootstrap,
  AdminTag,
  AdminWorkspace,
  AuditEvent,
  Invitation,
  InvitationPreview,
  Member,
  Organization,
  OrganizationRole,
  Overview,
  Page,
  SharedContextItem,
  WorkspaceAssignment,
} from "./types";

const page = <T>(value: Page<T> | T[]): Page<T> =>
  Array.isArray(value)
    ? { items: value, total: value.length, page: 1, page_size: value.length }
    : value;

interface RawMember extends Omit<Member, "active"> {
  is_active: boolean;
}
interface RawInvitation extends Omit<
  Invitation,
  "invitation_url" | "delivery_error"
> {
  invite_url?: string;
  email_delivery_error?: string | null;
}
interface RawInvitationPreview extends Omit<
  InvitationPreview,
  "organization_name"
> {
  organization: Organization;
}
const member = (item: RawMember): Member => ({
  ...item,
  active: item.is_active,
});
const invitation = (item: RawInvitation): Invitation => ({
  ...item,
  invitation_url: item.invite_url,
  delivery_error: item.email_delivery_error,
});

export const adminApi = {
  bootstrap: (signal?: AbortSignal) =>
    apiRequest<AdminBootstrap>("/admin/bootstrap", { signal }),
  overview: (signal?: AbortSignal) =>
    apiRequest<Overview>("/admin/overview", { signal }),
  organization: (signal?: AbortSignal) =>
    apiRequest<Organization>("/admin/organization", { signal }),
  renameOrganization: (name: string) =>
    apiRequest<Organization>("/admin/organization", {
      method: "PATCH",
      body: { name },
    }),
  workspaces: (signal?: AbortSignal) =>
    apiRequest<AdminWorkspace[]>("/admin/workspaces", { signal }),
  createWorkspace: (name: string) =>
    apiRequest<AdminWorkspace>("/admin/workspaces", {
      method: "POST",
      body: { name },
    }),
  renameWorkspace: (id: number, name: string) =>
    apiRequest<AdminWorkspace>(`/admin/workspaces/${id}`, {
      method: "PATCH",
      body: { name },
    }),
  members: async (
    search = "",
    workspaceId?: number | null,
    signal?: AbortSignal,
  ) => {
    const result = page(
      await apiRequest<Page<RawMember> | RawMember[]>(
        `/admin/members?search=${encodeURIComponent(search)}`,
        {
          signal,
          includeWorkspace: Boolean(workspaceId),
          headers: workspaceId
            ? { "X-Workspace-ID": String(workspaceId) }
            : undefined,
        },
      ),
    );
    return { ...result, items: result.items.map(member) };
  },
  updateMember: async (
    userId: number,
    body: {
      organization_role?: OrganizationRole;
      active?: boolean;
      workspace_assignments?: WorkspaceAssignment[];
    },
    workspaceId?: number | null,
  ) => {
    const { active, ...rest } = body;
    return member(
      await apiRequest<RawMember>(`/admin/members/${userId}`, {
        method: "PUT",
        body: {
          ...rest,
          ...(active === undefined ? {} : { is_active: active }),
        },
        includeWorkspace: Boolean(workspaceId),
        headers: workspaceId
          ? { "X-Workspace-ID": String(workspaceId) }
          : undefined,
      }),
    );
  },
  invitations: async (signal?: AbortSignal) => {
    const result = page(
      await apiRequest<Page<RawInvitation> | RawInvitation[]>(
        "/admin/invitations",
        { signal },
      ),
    );
    return { ...result, items: result.items.map(invitation) };
  },
  invite: (body: {
    email: string;
    organization_role: OrganizationRole;
    workspace_assignments: WorkspaceAssignment[];
  }) =>
    apiRequest<RawInvitation>("/admin/invitations", {
      method: "POST",
      body,
    }).then(invitation),
  resendInvitation: (id: number) =>
    apiRequest<RawInvitation>(`/admin/invitations/${id}/resend`, {
      method: "POST",
    }).then(invitation),
  revokeInvitation: (id: number) =>
    apiRequest<void>(`/admin/invitations/${id}`, { method: "DELETE" }),
  context: async (workspaceId: number, signal?: AbortSignal) =>
    page(
      await apiRequest<Page<SharedContextItem> | SharedContextItem[]>(
        "/admin/context",
        { signal, headers: { "X-Workspace-ID": String(workspaceId) } },
      ),
    ),
  shareContext: (
    workspaceId: number,
    text: string,
    title: string,
    tagIds: number[],
  ) =>
    apiRequest<{ chunks_indexed: number }>("/admin/context", {
      method: "POST",
      body: { text, title, tag_ids: tagIds, source: "web" },
      headers: { "X-Workspace-ID": String(workspaceId) },
    }),
  uploadContext: (workspaceId: number, file: File) => {
    const body = new FormData();
    body.append("file", file);
    return apiRequest<{
      message: string;
      files_ingested: number;
      files_failed: number;
    }>("/admin/context/upload", {
      method: "POST",
      body,
      headers: { "X-Workspace-ID": String(workspaceId) },
    });
  },
  tags: (workspaceId: number, signal?: AbortSignal) =>
    apiRequest<AdminTag[]>("/admin/tags", {
      signal,
      headers: { "X-Workspace-ID": String(workspaceId) },
    }),
  createTag: (displayName: string) =>
    apiRequest<AdminTag>("/admin/tags", {
      method: "POST",
      body: { display_name: displayName },
    }),
  setTagPolicy: (
    workspaceId: number,
    tagId: number,
    body: { priority: number; blocked: boolean },
  ) =>
    apiRequest<void>(`/admin/workspaces/${workspaceId}/tags/${tagId}/policy`, {
      method: "PUT",
      body,
    }),
  audit: async (action = "", signal?: AbortSignal) =>
    page(
      await apiRequest<Page<AuditEvent> | AuditEvent[]>(
        `/admin/audit?action=${encodeURIComponent(action)}`,
        { signal },
      ),
    ),
  invitation: async (token: string, signal?: AbortSignal) => {
    const result = await apiRequest<RawInvitationPreview>(
      `/auth/invitations/${encodeURIComponent(token)}`,
      { includeAuth: false, signal },
    );
    return { ...result, organization_name: result.organization.name };
  },
  acceptInvitation: (
    token: string,
    body: { full_name?: string; password?: string },
  ) =>
    apiRequest<{ session_token?: string }>(
      `/auth/invitations/${encodeURIComponent(token)}/accept`,
      {
        method: "POST",
        body,
      },
    ),
};
