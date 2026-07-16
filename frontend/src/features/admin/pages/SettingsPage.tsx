import { useEffect, useState } from "react";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import {
  ErrorState,
  LoadingState,
  PageHeader,
  StatusMessage,
} from "../components";
import type { Organization } from "../types";
export default function SettingsPage() {
  const { refresh } = useAdmin();
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [name, setName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const item = await adminApi.organization();
      setOrganization(item);
      setName(item.name);
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to load settings.",
      );
    } finally {
      setLoading(false);
    }
  };
  useEffect(() => {
    void load();
  }, []);
  const save = async (event: React.FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const item = await adminApi.renameOrganization(name.trim());
      setOrganization(item);
      setMessage("Organization name updated.");
      await refresh();
    } catch (reason) {
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to update organization.",
      );
    } finally {
      setBusy(false);
    }
  };
  return (
    <>
      <PageHeader
        title="Organization settings"
        description="Manage the organization details shown to your members."
      />
      {message && <StatusMessage>{message}</StatusMessage>}
      {error && <ErrorState message={error} retry={() => void load()} />}
      {loading ? (
        <LoadingState />
      ) : (
        organization && (
          <Card variant="outlined" sx={{ maxWidth: 640 }}>
            <CardContent>
              <Stack component="form" spacing={3} onSubmit={save}>
                <TextField
                  label="Organization name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
                <TextField
                  label="Organization identifier"
                  value={organization.slug}
                  helperText="This stable identifier cannot be changed."
                  slotProps={{ input: { readOnly: true } }}
                />
                <Button
                  type="submit"
                  variant="contained"
                  disabled={
                    busy || !name.trim() || name.trim() === organization.name
                  }
                >
                  {busy ? "Saving…" : "Save changes"}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        )
      )}
    </>
  );
}
