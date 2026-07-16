export type OrganizationRole = "organization_admin" | "member";
export type WorkspaceRole = "workspace_admin" | "member";
export type InvitationStatus = "pending" | "accepted" | "revoked" | "expired";

export interface Organization {
  id: number;
  name: string;
  slug: string;
}
export interface AdminWorkspace {
  id: number;
  organization_id: number;
  name: string;
  slug: string;
  role: WorkspaceRole;
  member_count?: number;
  admin_count?: number;
}
export interface AdminBootstrap {
  organization: Organization;
  organization_role: OrganizationRole;
  workspaces: AdminWorkspace[];
  permissions: string[];
  onboarding_required: boolean;
}
export interface WorkspaceAssignment {
  workspace_id: number;
  workspace_name?: string;
  role: WorkspaceRole;
}
export interface Member {
  user_id: number;
  full_name: string;
  email: string;
  organization_role: OrganizationRole;
  active: boolean;
  workspace_assignments: WorkspaceAssignment[];
}
export interface Invitation {
  id: number;
  email: string;
  organization_role: OrganizationRole;
  status: InvitationStatus;
  expires_at: string;
  created_at: string;
  workspace_assignments: WorkspaceAssignment[];
  invitation_url?: string;
  delivery_error?: string | null;
}
export interface AuditEvent {
  id: number;
  action: string;
  actor_name?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  summary: Record<string, unknown>;
  created_at: string;
}
export interface SharedContextItem {
  id: string | number;
  title: string;
    source?: string;
    preview?: string;
  workspace_id: number;
  workspace_name?: string;
  status?: string;
  created_at?: string;
  tags?: string[];
}
export interface AdminTag {
  id: number;
  display_name: string;
  normalized_key?: string;
  priority?: number | null;
  blocked?: boolean | null;
}
export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
export interface Overview {
  member_count: number;
  workspace_count: number;
  pending_invitation_count: number;
  shared_context_count: number;
  recent_audit: AuditEvent[];
}
export interface InvitationPreview {
  email: string;
  organization_name: string;
  organization_role: OrganizationRole;
  expires_at: string;
  status: InvitationStatus;
  existing_user: boolean;
  workspace_assignments: WorkspaceAssignment[];
}
