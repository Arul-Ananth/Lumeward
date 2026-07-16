import { useEffect, useState } from "react";
import { Navigate, useNavigate, useParams } from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Chip from "@mui/material/Chip";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import { useAuth } from "../../../hooks/useAuth";
import { setSessionToken } from "../../auth/storage";
import { adminApi } from "../api";
import { ErrorState, LoadingState } from "../components";
import type { InvitationPreview } from "../types";
export default function InvitationPage() {
  const { token = "" } = useParams();
  const navigate = useNavigate();
  const { status, login, logout, refreshStatus } = useAuth();
  const [preview, setPreview] = useState<InvitationPreview | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    void adminApi
      .invitation(token, controller.signal)
      .then(setPreview)
      .catch((reason) =>
        setError(
          reason instanceof Error ? reason.message : "Invitation unavailable.",
        ),
      )
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [token]);
  if (!token) return <Navigate to="/" replace />;
  if (loading) return <LoadingState label="Checking invitation…" />;
  const accept = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!preview) return;
    setBusy(true);
    setError("");
    try {
      if (preview.existing_user && !status?.authenticated)
        await login(preview.email, password);
      const response = await adminApi.acceptInvitation(
        token,
        preview.existing_user ? {} : { full_name: name.trim(), password },
      );
      if (response.session_token) setSessionToken(response.session_token);
      await refreshStatus();
      navigate("/", { replace: true });
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to accept invitation.",
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
            {error && !preview ? (
              <ErrorState message={error} />
            ) : (
              preview && (
                <>
                  <Typography component="h1" variant="h4" sx={{ mt: 2 }}>
                    Join {preview.organization_name}
                  </Typography>
                  <Typography color="text.secondary" sx={{ mt: 1 }}>
                    You were invited as{" "}
                    {preview.organization_role === "organization_admin"
                      ? "an organization administrator"
                      : "a member"}{" "}
                    using {preview.email}.
                  </Typography>
                  <Stack direction="row" gap={1} flexWrap="wrap" sx={{ my: 2 }}>
                    {preview.workspace_assignments.map((assignment) => (
                      <Chip
                        key={assignment.workspace_id}
                        label={`${assignment.workspace_name || `Workspace ${assignment.workspace_id}`} · ${assignment.role === "workspace_admin" ? "Admin" : "Member"}`}
                      />
                    ))}
                  </Stack>
                  {preview.status !== "pending" ? (
                    <Alert severity="warning">
                      This invitation is {preview.status}.
                    </Alert>
                  ) : (
                    <Stack component="form" spacing={2} onSubmit={accept}>
                      {preview.existing_user && status?.authenticated ? (
                        <Alert severity="info" action={<Button color="inherit" onClick={() => void logout()}>Switch account</Button>}>
                          Continue with the currently signed-in account. If it is not {preview.email}, switch accounts first.
                        </Alert>
                      ) : preview.existing_user ? (
                        <>
                          <Typography>
                            Sign in with the invited email to continue.
                          </Typography>
                          <TextField
                            value={preview.email}
                            label="Email"
                            slotProps={{ input: { readOnly: true } }}
                          />
                          <TextField
                            required
                            type="password"
                            label="Password"
                            autoComplete="current-password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                          />
                        </>
                      ) : (
                        <>
                          <TextField
                            autoFocus
                            required
                            label="Your name"
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                          />
                          <TextField
                            value={preview.email}
                            label="Email"
                            slotProps={{ input: { readOnly: true } }}
                          />
                          <TextField
                            required
                            type="password"
                            label="Create password"
                            autoComplete="new-password"
                            helperText="Use at least 8 characters."
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                          />
                        </>
                      )}
                      {error && <Alert severity="error">{error}</Alert>}
                      <Button
                        type="submit"
                        variant="contained"
                        disabled={
                          busy ||
                          (preview.existing_user && status?.authenticated ? false : !password) ||
                          (!preview.existing_user &&
                            (password.length < 8 || !name.trim()))
                        }
                      >
                        {busy
                          ? "Joining…"
                          : `Join ${preview.organization_name}`}
                      </Button>
                    </Stack>
                  )}
                </>
              )
            )}
          </CardContent>
        </Card>
      </Container>
    </Box>
  );
}
