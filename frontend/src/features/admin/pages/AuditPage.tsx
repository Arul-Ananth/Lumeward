import { useCallback, useEffect, useState } from "react";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemText from "@mui/material/ListItemText";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { adminApi } from "../api";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
} from "../components";
import type { AuditEvent } from "../types";
export default function AuditPage() {
  const [items, setItems] = useState<AuditEvent[]>([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      setItems((await adminApi.audit(filter.trim(), signal)).items);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to load audit activity.",
      );
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [filter]);
  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 250);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load]);
  const summary = (event: AuditEvent) =>
    Object.keys(event.summary).length
      ? Object.entries(event.summary)
          .map(([key, value]) => `${key}: ${String(value)}`)
          .join(", ")
      : event.action;
  return (
    <>
      <PageHeader
        title="Audit"
        description="Review privileged changes made in your organization."
      />
      <TextField
        label="Filter by action"
        value={filter}
        onChange={(e) => setFilter(e.target.value)}
        fullWidth
        sx={{ mb: 3 }}
      />
      {error && <ErrorState message={error} retry={() => void load()} />}
      {loading ? (
        <LoadingState />
      ) : items.length ? (
        <Card variant="outlined">
          <CardContent sx={{ p: 0 }}>
            <List>
              {items.map((event) => (
                <ListItem key={event.id} divider>
                  <ListItemText
                    primary={summary(event)}
                    secondary={`${event.actor_name || "System"} · ${event.action} · ${new Date(event.created_at).toLocaleString()}`}
                  />
                </ListItem>
              ))}
            </List>
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          title="No matching activity"
          description={
            filter
              ? "Try a broader action filter."
              : "Privileged organization changes will appear here."
          }
        />
      )}
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: "block", mt: 2 }}
      >
        Audit records do not include passwords, tokens, or secrets.
      </Typography>
    </>
  );
}
