import { useCallback, useEffect, useState } from "react";
import Box from "@mui/material/Box";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import Typography from "@mui/material/Typography";
import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import { ErrorState, LoadingState, PageHeader } from "../components";
import type { AuditEvent } from "../types";

export default function OverviewPage() {
  const { bootstrap } = useAdmin();
  const [counts, setCounts] = useState({
    members: 0,
    invitations: 0,
    context: 0,
  });
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const overview = await adminApi.overview();
      setCounts({
        members: overview.member_count,
        invitations: overview.pending_invitation_count,
        context: overview.shared_context_count,
      });
      setEvents(overview.recent_audit);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to load overview.",
      );
    } finally {
      setLoading(false);
    }
  }, []);
  useEffect(() => {
    void load();
  }, [load]);
  if (loading) return <LoadingState label="Loading overview…" />;
  return (
    <>
      <PageHeader
        title="Overview"
        description={`A snapshot of ${bootstrap?.organization.name ?? "your organization"}.`}
      />
      {error && <ErrorState message={error} retry={() => void load()} />}
      <Grid container spacing={2} sx={{ my: 1 }}>
        {[
          ["Members", counts.members],
          ["Workspaces", bootstrap?.workspaces.length ?? 0],
          ["Pending invitations", counts.invitations],
          ["Shared context", counts.context],
        ].map(([label, value]) => (
          <Grid key={String(label)} size={{ xs: 12, sm: 6, lg: 3 }}>
            <Card variant="outlined">
              <CardContent>
                <Typography color="text.secondary">{label}</Typography>
                <Typography variant="h3">{value}</Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
      <Box sx={{ mt: 4 }}>
        <Typography variant="h6">Recent administration activity</Typography>
        {events.length ? (
          <List>
            {events.map((event) => (
              <ListItem key={event.id} divider>
                <ListItemText
                  primary={
                    Object.keys(event.summary).length
                      ? Object.entries(event.summary)
                          .map(([key, value]) => `${key}: ${String(value)}`)
                          .join(", ")
                      : event.action
                  }
                  secondary={`${event.actor_name || "System"} · ${new Date(event.created_at).toLocaleString()}`}
                />
              </ListItem>
            ))}
          </List>
        ) : (
          <Typography color="text.secondary" sx={{ py: 3 }}>
            No administration activity yet.
          </Typography>
        )}
      </Box>
    </>
  );
}
