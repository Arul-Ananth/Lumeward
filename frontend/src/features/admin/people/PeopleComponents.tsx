import { useState, type FormEvent } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import Dialog from "@mui/material/Dialog";
import DialogActions from "@mui/material/DialogActions";
import DialogContent from "@mui/material/DialogContent";
import DialogTitle from "@mui/material/DialogTitle";
import FormControl from "@mui/material/FormControl";
import FormControlLabel from "@mui/material/FormControlLabel";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Stack from "@mui/material/Stack";
import Switch from "@mui/material/Switch";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import ContentCopyOutlined from "@mui/icons-material/ContentCopyOutlined";

import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import type {
  Invitation,
  Member,
  OrganizationRole,
  WorkspaceAssignment,
  WorkspaceRole,
} from "../types";

export function InviteDialog({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated: (invitation: Invitation) => void;
}) {
  const { bootstrap } = useAdmin();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<OrganizationRole>("member");
  const [workspaceIds, setWorkspaceIds] = useState<number[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await adminApi.invite({
        email: email.trim(),
        organization_role: role,
        workspace_assignments: workspaceIds.map((workspace_id) => ({
          workspace_id,
          role: "member",
        })),
      });
      onCreated(created);
      setEmail("");
      setRole("member");
      setWorkspaceIds([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to create invitation.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onClose={busy ? undefined : onClose} fullWidth maxWidth="sm">
      <Box component="form" onSubmit={submit}>
        <DialogTitle>Invite a person</DialogTitle>
        <DialogContent>
          <Stack spacing={2} sx={{ pt: 1 }}>
            <TextField autoFocus required type="email" label="Email address" value={email} onChange={(event) => setEmail(event.target.value)} />
            <FormControl>
              <InputLabel id="invite-role">Organization role</InputLabel>
              <Select labelId="invite-role" label="Organization role" value={role} onChange={(event) => setRole(event.target.value as OrganizationRole)}>
                <MenuItem value="member">Member</MenuItem>
                <MenuItem value="organization_admin">Organization administrator</MenuItem>
              </Select>
            </FormControl>
            <Box>
              <Typography variant="subtitle2">Workspace access</Typography>
              {bootstrap?.workspaces.map((workspace) => (
                <FormControlLabel
                  key={workspace.id}
                  control={
                    <Checkbox
                      checked={workspaceIds.includes(workspace.id)}
                      onChange={(_, checked) =>
                        setWorkspaceIds((ids) =>
                          checked
                            ? [...ids, workspace.id]
                            : ids.filter((id) => id !== workspace.id),
                        )
                      }
                    />
                  }
                  label={workspace.name}
                />
              ))}
            </Box>
            {error && <Alert severity="error">{error}</Alert>}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={onClose} disabled={busy}>Cancel</Button>
          <Button type="submit" variant="contained" disabled={busy || !email.trim()}>{busy ? "Creating…" : "Create invitation"}</Button>
        </DialogActions>
      </Box>
    </Dialog>
  );
}

export function MemberAccessCard({
  member,
  canManageOrganization,
  saved,
}: {
  member: Member;
  canManageOrganization: boolean;
  saved: (message: string) => void;
}) {
  const { bootstrap, workspaceId } = useAdmin();
  const [role, setRole] = useState(member.organization_role);
  const [active, setActive] = useState(member.active);
  const [assignments, setAssignments] = useState(member.workspace_assignments);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const visibleWorkspaces = bootstrap?.workspaces.filter((workspace) => canManageOrganization || workspace.id === workspaceId) ?? [];

  const toggleWorkspace = (id: number, checked: boolean) => setAssignments((current) =>
    checked ? [...current, { workspace_id: id, role: "member" }] : current.filter((item) => item.workspace_id !== id),
  );
  const changeWorkspaceRole = (id: number, nextRole: WorkspaceRole) => setAssignments((current) =>
    current.map((item) => item.workspace_id === id ? { ...item, role: nextRole } : item),
  );
  const save = async () => {
    setBusy(true);
    setError("");
    try {
      const body: { organization_role?: OrganizationRole; active?: boolean; workspace_assignments: WorkspaceAssignment[] } = canManageOrganization
        ? { organization_role: role, active, workspace_assignments: assignments }
        : { workspace_assignments: assignments.filter((item) => item.workspace_id === workspaceId) };
      await adminApi.updateMember(member.user_id, body, canManageOrganization ? null : workspaceId);
      saved(`${member.full_name || member.email} updated.`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update member.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack direction="row" justifyContent="space-between" gap={2}>
          <Box><Typography variant="h6">{member.full_name || member.email}</Typography><Typography color="text.secondary">{member.email}</Typography></Box>
          <Chip label={active ? "Active" : "Inactive"} color={active ? "success" : "default"} size="small" />
        </Stack>
        <Stack spacing={2} sx={{ mt: 3 }}>
          <FormControl size="small" disabled={!canManageOrganization}>
            <InputLabel id={`role-${member.user_id}`}>Organization role</InputLabel>
            <Select labelId={`role-${member.user_id}`} label="Organization role" value={role} onChange={(event) => setRole(event.target.value as OrganizationRole)}>
              <MenuItem value="member">Member</MenuItem><MenuItem value="organization_admin">Organization administrator</MenuItem>
            </Select>
          </FormControl>
          {canManageOrganization && <FormControlLabel control={<Switch checked={active} onChange={(_, value) => setActive(value)} />} label="Active organization access" />}
          <Box>
            <Typography variant="subtitle2">Workspace assignments</Typography>
            {visibleWorkspaces.map((workspace) => {
              const assignment = assignments.find((item) => item.workspace_id === workspace.id);
              return (
                <Stack key={workspace.id} direction="row" alignItems="center" justifyContent="space-between">
                  <FormControlLabel control={<Checkbox checked={Boolean(assignment)} onChange={(_, checked) => toggleWorkspace(workspace.id, checked)} />} label={workspace.name} />
                  {assignment && (
                    <Select
                      size="small"
                      aria-label={`${workspace.name} role`}
                      value={assignment.role}
                      onChange={(event) =>
                        changeWorkspaceRole(
                          workspace.id,
                          event.target.value as WorkspaceRole,
                        )
                      }
                    >
                      <MenuItem value="member">Member</MenuItem>
                      <MenuItem value="workspace_admin">
                        Workspace admin
                      </MenuItem>
                    </Select>
                  )}
                </Stack>
              );
            })}
          </Box>
          {error && <Alert severity="error">{error}</Alert>}
        </Stack>
      </CardContent>
      <CardActions><Button onClick={() => void save()} disabled={busy}>{busy ? "Saving…" : "Save access"}</Button></CardActions>
    </Card>
  );
}

export function InvitationList({
  invitations,
  links,
  onCopy,
  onResend,
  onRevoke,
}: {
  invitations: Invitation[];
  links: Record<number, string>;
  onCopy: (url: string) => void;
  onResend: (id: number) => void;
  onRevoke: (id: number) => void;
}) {
  const pending = invitations.filter((item) => item.status === "pending");
  if (!pending.length) return <Typography color="text.secondary">No pending invitations.</Typography>;
  return (
    <Stack spacing={1}>
      {pending.map((item) => {
        const url = links[item.id] || item.invitation_url;
        return (
          <Card variant="outlined" key={item.id}>
            <CardContent>
              <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={2}>
                <Box>
                  <Typography fontWeight={600}>{item.email}</Typography>
                  <Typography variant="body2" color="text.secondary">Expires {new Date(item.expires_at).toLocaleString()}</Typography>
                  {item.delivery_error && <Alert severity="warning" sx={{ mt: 1 }}>Email delivery failed. Copy and share the invitation link.</Alert>}
                </Box>
                <Stack direction="row" flexWrap="wrap">
                  <Button startIcon={<ContentCopyOutlined />} disabled={!url} onClick={() => url && onCopy(url)}>Copy link</Button>
                  <Button onClick={() => onResend(item.id)}>Resend</Button>
                  <Button color="error" onClick={() => onRevoke(item.id)}>Revoke</Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
}
