import { useCallback, useEffect, useRef, useState } from "react";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Card from "@mui/material/Card";
import CardContent from "@mui/material/CardContent";
import Checkbox from "@mui/material/Checkbox";
import Chip from "@mui/material/Chip";
import FormControlLabel from "@mui/material/FormControlLabel";
import FormControl from "@mui/material/FormControl";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Grid from "@mui/material/Grid";
import Stack from "@mui/material/Stack";
import TextField from "@mui/material/TextField";
import Typography from "@mui/material/Typography";
import UploadFileOutlined from "@mui/icons-material/UploadFileOutlined";
import { adminApi } from "../api";
import { useAdmin } from "../AdminContext";
import {
  EmptyState,
  ErrorState,
  LoadingState,
  PageHeader,
  StatusMessage,
} from "../components";
import type { AdminTag, SharedContextItem } from "../types";

type TagPolicy = "neutral" | "prioritize" | "block";

function TagPolicyRow({ tag, workspaceId, onSaved }: { tag: AdminTag; workspaceId: number; onSaved: () => void }) {
  const initial: TagPolicy = tag.blocked ? "block" : (tag.priority ?? 0) > 0 ? "prioritize" : "neutral";
  const [policy, setPolicy] = useState<TagPolicy>(initial);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const save = async () => {
    setSaving(true);
    setError("");
    try {
      await adminApi.setTagPolicy(workspaceId, tag.id, {
        priority: policy === "prioritize" ? 1 : 0,
        blocked: policy === "block",
      });
      onSaved();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to update policy.");
    } finally {
      setSaving(false);
    }
  };
  return (
    <Box>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1} alignItems={{ sm: "center" }}>
        <Typography sx={{ flexGrow: 1 }}>{tag.display_name}</Typography>
        <FormControl size="small" sx={{ minWidth: 140 }}>
          <InputLabel id={`tag-policy-${tag.id}`}>Policy</InputLabel>
          <Select labelId={`tag-policy-${tag.id}`} label="Policy" value={policy} onChange={(event) => setPolicy(event.target.value as TagPolicy)}>
            <MenuItem value="neutral">Neutral</MenuItem>
            <MenuItem value="prioritize">Prioritize</MenuItem>
            <MenuItem value="block">Block</MenuItem>
          </Select>
        </FormControl>
        <Button onClick={() => void save()} disabled={saving}>{saving ? "Saving…" : "Save"}</Button>
      </Stack>
      {error && <Typography variant="caption" color="error">{error}</Typography>}
    </Box>
  );
}

export default function ContextPage() {
  const { workspaceId, bootstrap } = useAdmin();
  const [items, setItems] = useState<SharedContextItem[]>([]);
  const [tags, setTags] = useState<AdminTag[]>([]);
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [tagIds, setTagIds] = useState<number[]>([]);
  const [tagName, setTagName] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);
  const workspace = bootstrap?.workspaces.find(
    (item) => item.id === workspaceId,
  );
  const canCreateTags = bootstrap?.permissions.includes("tags.manage") ?? false;
  const load = useCallback(async (signal?: AbortSignal) => {
    if (!workspaceId) {
      setLoading(false);
      return;
    }
    setLoading(true);
    setError("");
    try {
      const [context, nextTags] = await Promise.all([
        adminApi.context(workspaceId, signal),
        adminApi.tags(workspaceId, signal),
      ]);
      setItems(context.items);
      setTags(nextTags);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError") return;
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to load shared context.",
      );
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, [workspaceId]);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  const share = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!workspaceId) return;
    setBusy(true);
    setError("");
    try {
      const result = await adminApi.shareContext(
        workspaceId,
        text.trim(),
        title.trim(),
        tagIds,
      );
      setMessage(
        `${result.chunks_indexed} context chunks shared with ${workspace?.name}.`,
      );
      setTitle("");
      setText("");
      setTagIds([]);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to share context.",
      );
    } finally {
      setBusy(false);
    }
  };
  const upload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !workspaceId) return;
    if (!file.name.toLowerCase().endsWith(".zip")) {
      setError("Choose a .zip archive.");
      return;
    }
    setBusy(true);
    setError("");
    try {
      const result = await adminApi.uploadContext(workspaceId, file);
      setMessage(result.message || `${result.files_ingested} files shared.`);
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to upload archive.",
      );
    } finally {
      setBusy(false);
    }
  };
  const createTag = async () => {
    if (!tagName.trim()) return;
    setBusy(true);
    try {
      await adminApi.createTag(tagName.trim());
      setTagName("");
      setMessage("Tag created.");
      await load();
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "Unable to create tag.",
      );
    } finally {
      setBusy(false);
    }
  };
  if (!workspaceId)
    return (
      <>
        <PageHeader
          title="Shared context"
          description="Knowledge visible to members of a workspace."
        />
        <EmptyState
          title="Create a workspace first"
          description="Shared context must belong to a workspace."
        />
      </>
    );
  return (
    <>
      <PageHeader
        title="Shared context"
        description={`Knowledge shared with ${workspace?.name ?? "the selected workspace"}. Private uploads remain in your personal workspace.`}
      />
      {message && <StatusMessage>{message}</StatusMessage>}
      {error && <ErrorState message={error} retry={() => void load()} />}
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, lg: 5 }}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6">Share text</Typography>
              <Box component="form" onSubmit={share}>
                <Stack spacing={2} sx={{ mt: 2 }}>
                  <TextField
                    required
                    label="Title"
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                  <TextField
                    required
                    multiline
                    minRows={6}
                    label="Context"
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                  />
                  <Box>
                    <Typography variant="subtitle2">Tags</Typography>
                    {tags.map((tag) => (
                      <FormControlLabel
                        key={tag.id}
                        control={
                          <Checkbox
                            checked={tagIds.includes(tag.id)}
                            onChange={(_, checked) =>
                              setTagIds((ids) =>
                                checked
                                  ? [...ids, tag.id]
                                  : ids.filter((id) => id !== tag.id),
                              )
                            }
                          />
                        }
                        label={tag.display_name}
                      />
                    ))}
                  </Box>
                  <Button
                    type="submit"
                    variant="contained"
                    disabled={busy || !title.trim() || !text.trim()}
                  >
                    {busy ? "Sharing…" : "Share with workspace"}
                  </Button>
                </Stack>
              </Box>
              <Box sx={{ mt: 4 }}>
                <Typography variant="h6">Upload archive</Typography>
                <Typography variant="body2" color="text.secondary">
                  ZIP contents are indexed into this workspace’s shared context.
                </Typography>
                <input
                  hidden
                  ref={fileRef}
                  type="file"
                  accept=".zip,application/zip"
                  onChange={upload}
                />
                <Button
                  startIcon={<UploadFileOutlined />}
                  onClick={() => fileRef.current?.click()}
                  disabled={busy}
                  sx={{ mt: 1 }}
                >
                  Choose ZIP
                </Button>
              </Box>
            </CardContent>
          </Card>
          <Card variant="outlined" sx={{ mt: 2 }}>
            <CardContent>
              <Typography variant="h6">Organization tags</Typography>
              {canCreateTags && <Stack direction="row" spacing={1} sx={{ mt: 2 }}>
                <TextField
                  size="small"
                  label="New tag"
                  value={tagName}
                  onChange={(e) => setTagName(e.target.value)}
                />
                <Button
                  onClick={() => void createTag()}
                  disabled={busy || !tagName.trim()}
                >
                  Add
                </Button>
              </Stack>}
              <Stack spacing={1} sx={{ mt: 2 }}>
                {tags.map((tag) => <TagPolicyRow key={tag.id} tag={tag} workspaceId={workspaceId} onSaved={() => { setMessage("Workspace tag policy updated."); void load(); }} />)}
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 7 }}>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Indexed context
          </Typography>
          {loading ? (
            <LoadingState />
          ) : items.length ? (
            <Stack spacing={2}>
              {items.map((item) => (
                <Card variant="outlined" key={item.id}>
                  <CardContent>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      gap={2}
                    >
                      <Box>
                        <Typography fontWeight={600}>{item.title}</Typography>
                        <Typography variant="body2" color="text.secondary">
                          {item.source || "Shared text"}
                          {item.created_at
                            ? ` · ${new Date(item.created_at).toLocaleString()}`
                            : ""}
                        </Typography>
                        {item.preview && <Typography variant="body2" sx={{ mt: 1 }}>{item.preview}</Typography>}
                      </Box>
                      {item.status && <Chip size="small" label={item.status} />}
                    </Stack>
                    {item.tags?.map((tag) => (
                      <Chip
                        key={tag}
                        size="small"
                        label={tag}
                        sx={{ mt: 1, mr: 0.5 }}
                      />
                    ))}
                  </CardContent>
                </Card>
              ))}
            </Stack>
          ) : (
            <EmptyState
              title="No shared context"
              description="Share text or upload a ZIP to make knowledge available to this workspace."
            />
          )}
        </Grid>
      </Grid>
    </>
  );
}
