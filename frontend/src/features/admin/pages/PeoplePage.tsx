import { useCallback, useEffect, useRef, useState } from "react";
import Button from "@mui/material/Button";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";

import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import { EmptyState, ErrorState, LoadingState, PageHeader, StatusMessage } from "../components";
import { InvitationList, InviteDialog, MemberAccessCard } from "../people/PeopleComponents";
import type { Invitation, Member } from "../types";

export default function PeoplePage() {
  const { bootstrap, workspaceId } = useAdmin();
  const [members, setMembers] = useState<Member[]>([]);
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [invitationLinks, setInvitationLinks] = useState<Record<number, string>>({});
  const [search, setSearch] = useState("");
  const [inviteOpen, setInviteOpen] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const requestSequence = useRef(0);
  const canManageOrganization = bootstrap?.organization_role === "organization_admin";

  const load = useCallback(async () => {
    const request = ++requestSequence.current;
    setLoading(true);
    setError("");
    try {
      const memberPage = await adminApi.members(search, canManageOrganization ? null : workspaceId);
      if (request !== requestSequence.current) return;
      setMembers(memberPage.items);
      if (canManageOrganization) {
        const invitationPage = await adminApi.invitations();
        if (request !== requestSequence.current) return;
        setInvitations(invitationPage.items);
      }
      else setInvitations([]);
    } catch (reason) {
      if (request !== requestSequence.current) return;
      setError(reason instanceof Error ? reason.message : "Unable to load people.");
    } finally {
      if (request === requestSequence.current) setLoading(false);
    }
  }, [search, workspaceId, canManageOrganization]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250);
    return () => window.clearTimeout(timer);
  }, [load]);

  const resend = async (id: number) => {
    setError("");
    try {
      const invitation = await adminApi.resendInvitation(id);
      if (invitation.invitation_url) setInvitationLinks((links) => ({ ...links, [id]: invitation.invitation_url as string }));
      setMessage("Invitation resent. Copy the new link before leaving this page.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to resend invitation.");
    }
  };
  const revoke = async (id: number) => {
    setError("");
    try {
      await adminApi.revokeInvitation(id);
      setMessage("Invitation revoked.");
      await load();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to revoke invitation.");
    }
  };
  const copy = async (url: string) => {
    try {
      await navigator.clipboard.writeText(url);
      setMessage("Invitation link copied.");
    } catch {
      setError("Your browser blocked clipboard access. Copy the link from the address shown after resending.");
    }
  };

  return (
    <>
      <PageHeader
        title="People"
        description="Manage organization roles and workspace access."
        action={canManageOrganization ? <Button variant="contained" onClick={() => setInviteOpen(true)}>Invite person</Button> : undefined}
      />
      {message && <StatusMessage>{message}</StatusMessage>}
      {error && <ErrorState message={error} retry={() => void load()} />}
      <TextField label="Search people" value={search} onChange={(event) => setSearch(event.target.value)} fullWidth sx={{ mb: 3 }} />
      {loading ? <LoadingState /> : members.length ? (
        <Stack spacing={2}>
          {members.map((member) => (
            <MemberAccessCard
              key={member.user_id}
              member={member}
              canManageOrganization={canManageOrganization}
              saved={(text) => {
                setMessage(text);
                void load();
              }}
            />
          ))}
        </Stack>
      ) : <EmptyState title="No members found" description={search ? "Try a different search." : "No members are assigned to this workspace."} />}
      {canManageOrganization && <>
        <Typography variant="h5" sx={{ mt: 5, mb: 2 }}>Pending invitations</Typography>
        <InvitationList invitations={invitations} links={invitationLinks} onCopy={(url) => void copy(url)} onResend={(id) => void resend(id)} onRevoke={(id) => void revoke(id)} />
        <InviteDialog open={inviteOpen} onClose={() => setInviteOpen(false)} onCreated={(invitation) => {
          setInviteOpen(false);
          if (invitation.invitation_url) setInvitationLinks((links) => ({ ...links, [invitation.id]: invitation.invitation_url as string }));
          setMessage(
            invitation.delivery_error
              ? "Invitation created, but email delivery failed. Copy its link below."
              : "Invitation created. Copy its link before leaving this page.",
          );
          void load();
        }} />
      </>}
    </>
  );
}
