import { useEffect, useState } from 'react';
import { Alert, Box, Button, MenuItem, Paper, Select, Stack, TextField, Typography } from '@mui/material';

import { api, type Tag, type Workspace } from '../../services/api';

const slug = (value: string) => value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');

interface Props {
    workspace: Workspace | null;
    onWorkspaceCreated: (workspace: Workspace) => void;
}

export default function WorkspacePanel({ workspace, onWorkspaceCreated }: Props) {
    const [organizationName, setOrganizationName] = useState('');
    const [workspaceName, setWorkspaceName] = useState('');
    const [memberEmail, setMemberEmail] = useState('');
    const [title, setTitle] = useState('');
    const [text, setText] = useState('');
    const [tagName, setTagName] = useState('');
    const [tags, setTags] = useState<Tag[]>([]);
    const [tagIds, setTagIds] = useState<number[]>([]);
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');

    useEffect(() => {
        setTagIds([]);
        if (workspace) void api.listTags(workspace.id).then(setTags).catch(() => setTags([]));
    }, [workspace]);

    const run = async (action: () => Promise<void>) => {
        setBusy(true);
        setMessage('');
        setError('');
        try {
            await action();
        } catch (reason) {
            setError(reason instanceof Error ? reason.message : 'Request failed.');
        } finally {
            setBusy(false);
        }
    };

    if (!workspace) {
        return (
            <Paper sx={{ p: 3, maxWidth: 560, mx: 'auto' }}>
                <Typography variant="h5" gutterBottom>Set up your enterprise workspace</Typography>
                <Stack spacing={2}>
                    <TextField label="Organization name" value={organizationName} onChange={(e) => setOrganizationName(e.target.value)} />
                    <TextField label="Team workspace name" value={workspaceName} onChange={(e) => setWorkspaceName(e.target.value)} />
                    <Button disabled={busy || !slug(organizationName) || !slug(workspaceName)} variant="contained" onClick={() => void run(async () => {
                        const organization = await api.createOrganization(organizationName, slug(organizationName));
                        onWorkspaceCreated(await api.createWorkspace(organization.id, workspaceName, slug(workspaceName)));
                    })}>Create workspace</Button>
                    {error && <Alert severity="error">{error}</Alert>}
                </Stack>
            </Paper>
        );
    }

    const admin = workspace.organization_role === 'organization_admin';
    return (
        <Paper sx={{ p: 3, borderRadius: 2, mt: 3 }}>
            <Typography variant="h6" gutterBottom>Team context</Typography>
            <Stack spacing={2}>
                <TextField label="Context title" value={title} onChange={(e) => setTitle(e.target.value)} />
                <TextField label="Text shared with this workspace" multiline minRows={3} value={text} onChange={(e) => setText(e.target.value)} />
                {tags.length > 0 && (
                    <Select multiple displayEmpty value={tagIds} onChange={(e) => setTagIds(e.target.value as number[])}>
                        <MenuItem disabled value="">Select tags</MenuItem>
                        {tags.map((tag) => <MenuItem key={tag.id} value={tag.id}>{tag.display_name}</MenuItem>)}
                    </Select>
                )}
                <Button disabled={busy || !title.trim() || !text.trim()} variant="contained" onClick={() => void run(async () => {
                    const result = await api.shareContext(text, title, tagIds);
                    setText('');
                    setTitle('');
                    setMessage(`${result.chunks_indexed} context chunks shared.`);
                })}>Share context</Button>

                {admin && <Box sx={{ display: 'flex', gap: 1 }}>
                    <TextField fullWidth size="small" label="New tag" value={tagName} onChange={(e) => setTagName(e.target.value)} />
                    <Button disabled={busy || !tagName.trim()} onClick={() => void run(async () => {
                        const tag = await api.createTag(workspace.organization_id, tagName);
                        setTags((current) => current.some((item) => item.id === tag.id) ? current : [...current, tag]);
                        setTagName('');
                    })}>Add tag</Button>
                </Box>}

                {tags.map((tag) => (
                    <Box key={tag.id} sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <Typography sx={{ flexGrow: 1 }}>{tag.display_name}</Typography>
                        <Button size="small" onClick={() => void run(async () => {
                            await api.setTagPreference(tag.id, 1, false);
                            setMessage(`${tag.display_name} prioritized for your feed.`);
                        })}>Prefer</Button>
                        <Button size="small" color="warning" onClick={() => void run(async () => {
                            await api.setTagPreference(tag.id, 0, true);
                            setMessage(`${tag.display_name} muted in your feed.`);
                        })}>Mute</Button>
                    </Box>
                ))}

                {admin && <Box sx={{ display: 'flex', gap: 1 }}>
                    <TextField fullWidth size="small" type="email" label="Existing user email" value={memberEmail} onChange={(e) => setMemberEmail(e.target.value)} />
                    <Button disabled={busy || !memberEmail.trim()} onClick={() => void run(async () => {
                        await api.addMember(workspace, memberEmail);
                        setMemberEmail('');
                        setMessage('Member granted organization and workspace access.');
                    })}>Add member</Button>
                </Box>}
                {message && <Alert severity="success">{message}</Alert>}
                {error && <Alert severity="error">{error}</Alert>}
            </Stack>
        </Paper>
    );
}
