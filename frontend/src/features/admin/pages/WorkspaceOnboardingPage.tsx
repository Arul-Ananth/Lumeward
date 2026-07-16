import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import { ErrorState, LoadingState } from "../components";
export default function WorkspaceOnboardingPage() {
  const { bootstrap, loading, error, refresh } = useAdmin();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState("");
  if (loading) return <LoadingState label="Preparing your organization…" />;
  if (error || !bootstrap)
    return (
      <Container sx={{ py: 6 }}>
        <ErrorState
          message={error || "Organization unavailable."}
          retry={() => void refresh()}
        />
      </Container>
    );
  if (!bootstrap.onboarding_required && bootstrap.workspaces.length)
    return <Navigate to="/admin/overview" replace />;
  const submit = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setFormError("");
    try {
      await adminApi.createWorkspace(name.trim());
      await refresh();
      navigate("/admin/overview", { replace: true });
    } catch (reason) {
      setFormError(
        reason instanceof Error
          ? reason.message
          : "Unable to create workspace.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <Box
      sx={{ minHeight: "100dvh", display: "grid", placeItems: "center", p: 2 }}
    >
      <Container maxWidth="sm">
        <Card variant="outlined">
          <CardContent sx={{ p: { xs: 3, sm: 5 } }}>
            <Typography color="primary.main" fontWeight={700}>
              Lumeward
            </Typography>
            <Typography component="h1" variant="h4" sx={{ mt: 2 }}>
              Create your first workspace
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1, mb: 3 }}>
              Workspaces keep members and shared knowledge organized inside{" "}
              {bootstrap.organization.name}.
            </Typography>
            <Stack component="form" spacing={2} onSubmit={submit}>
              <TextField
                autoFocus
                required
                label="Workspace name"
                placeholder="For example, Research"
                value={name}
                onChange={(e) => setName(e.target.value)}
                helperText="You can create more workspaces later."
              />
              {formError && <Alert severity="error">{formError}</Alert>}
              <Button
                type="submit"
                variant="contained"
                size="large"
                disabled={busy || !name.trim()}
              >
                {busy ? "Creating…" : "Create workspace"}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
