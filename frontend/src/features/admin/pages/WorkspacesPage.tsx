import { useEffect, useState } from "react";
import Alert from "@mui/material/Alert";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardActions from "@mui/material/CardActions";
import CardContent from "@mui/material/CardContent";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  StatusMessage,
} from "../components";
import type { AdminWorkspace } from "../types";

function WorkspaceCard({
  workspace,
  saved,
}: {
  workspace: AdminWorkspace;
  saved: () => void;
}) {
  const [name, setName] = useState(workspace.name);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const save = async () => {
    if (!name.trim() || name.trim() === workspace.name) return;
    setBusy(true);
    setError("");
    try {
      await adminApi.renameWorkspace(workspace.id, name.trim());
      saved();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to rename workspace.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <Card variant="outlined">
      <CardContent>
        <TextField
          label="Workspace name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          fullWidth
        />
        <Typography color="text.secondary" variant="body2" sx={{ mt: 2 }}>
          {workspace.member_count ?? 0} members · {workspace.admin_count ?? 0}{" "}
          administrators
        </Typography>
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </CardContent>
      <CardActions>
        <Button
          onClick={() => void save()}
          disabled={busy || !name.trim() || name.trim() === workspace.name}
        >
          {busy ? "Saving…" : "Save name"}
        </Button>
      </CardActions>
    </Card>
  );
}
export default function WorkspacesPage() {
  const { refresh: refreshBootstrap } = useAdmin();
  const [items, setItems] = useState<AdminWorkspace[]>([]);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      setItems(await adminApi.workspaces());
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to load workspaces.",
      );
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const create = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!name.trim()) return;
    setBusy(true);
    setError("");
    try {
      await adminApi.createWorkspace(name.trim());
      setName("");
      setMessage("Workspace created.");
      await Promise.all([load(), refreshBootstrap()]);
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to create workspace.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeader
        title="Workspaces"
        description="Organize members and shared knowledge into focused spaces."
      />
      {message && <StatusMessage>{message}</StatusMessage>}
      {error && <ErrorState message={error} retry={() => void load()} />}
      <Stack
        component="form"
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        onSubmit={create}
        sx={{ mb: 3 }}
      >
        <TextField
          label="New workspace name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <Button
          type="submit"
          variant="contained"
          disabled={busy || !name.trim()}
        >
          {busy ? "Creating…" : "Create workspace"}
        </Button>
      </Stack>
      {loading ? (
        <LoadingState />
      ) : (
        <Grid container spacing={2}>
          {items.map((workspace) => (
            <Grid key={workspace.id} size={{ xs: 12, md: 6 }}>
              <WorkspaceCard
                workspace={workspace}
                saved={() => {
                  setMessage("Workspace renamed.");
                  void Promise.all([load(), refreshBootstrap()]);
                }}
              />
            </Grid>
          ))}
        </Grid>
      )}
    </>
  );
}
