import { useRef, useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import {
    Typography, Container, Paper, TextField, Button,
    Card, CardContent, Chip, IconButton, Box, CircularProgress, Alert, Snackbar,
    Divider, Grid
} from '@mui/material';
import {
    Send as SendIcon,
    ThumbUp as ThumbUpIcon,
    ThumbDown as ThumbDownIcon,
    Refresh as RefreshIcon,
    UploadFile as UploadFileIcon,
} from '@mui/icons-material';

import { api } from '../services/api';
import type { FeedCard, MemoryRecord, NewsletterResponse, Workspace } from '../services/api';
import CustomAppBar from '../components/CustomAppBar';
import WorkspacePanel from '../features/workspaces/WorkspacePanel';
import { getWorkspaceId, setWorkspaceId } from '../features/auth/storage';
import { useAuth } from '../hooks/useAuth';

const Dashboard = () => {
    const { status } = useAuth();
    const [topic, setTopic] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<NewsletterResponse | null>(null);
    const [tabIndex, setTabIndex] = useState(0);
    const [memories, setMemories] = useState<MemoryRecord[]>([]);
    const [snackbarOpen, setSnackbarOpen] = useState(false);
    const [snackbarMsg, setSnackbarMsg] = useState('');
    const [errorMsg, setErrorMsg] = useState('');
    const [uploading, setUploading] = useState(false);
    const [uploadStatus, setUploadStatus] = useState('');
    const [uploadError, setUploadError] = useState('');
    const fileInputRef = useRef<HTMLInputElement | null>(null);
    const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
    const [workspaceId, selectWorkspace] = useState<number | null>(null);
    const [feed, setFeed] = useState<FeedCard[]>([]);
    const [workspacesLoaded, setWorkspacesLoaded] = useState(false);
    const interactive = status?.auth_mode === 'interactive';
    const workspace = workspaces.find((item) => item.id === workspaceId) ?? null;

    useEffect(() => {
        if (!interactive) return;
        void api.listWorkspaces().then((items) => {
            setWorkspaces(items);
            const stored = getWorkspaceId();
            const selected = items.some((item) => item.id === stored) ? stored : items[0]?.id ?? null;
            selectWorkspace(selected);
            setWorkspaceId(selected);
        }).finally(() => setWorkspacesLoaded(true));
    }, [interactive]);

    const changeWorkspace = (id: number) => {
        selectWorkspace(id);
        setWorkspaceId(id);
        setResult(null);
        setFeed([]);
    };

    const addWorkspace = (created: Workspace) => {
        setWorkspaces((items) => [...items, created]);
        changeWorkspace(created.id);
    };

    const handleGenerate = async () => {
        if (!topic) return;
        setLoading(true);
        setResult(null);
        setErrorMsg('');

        try {
            const data = await api.generateBriefing(topic);
            setResult(data);
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            console.error(error);
            setErrorMsg(message || "Connection failed. Please check backend terminal for errors.");
        } finally {
            setLoading(false);
        }
    };

    const sendFeedback = async (sentiment: 'positive' | 'negative', text: string) => {
        if (!result) return;
        try {
            await api.sendFeedback(result.topic, text, sentiment);
            setSnackbarMsg(`Feedback Sent: ${sentiment.toUpperCase()}`);
            setSnackbarOpen(true);
        } catch (error) {
            console.error(error);
            setSnackbarMsg("Failed to send feedback");
            setSnackbarOpen(true);
        }
    };

    const fetchProfile = async () => {
        try {
            const mems = await api.getProfile();
            setMemories(mems);
        } catch (error) {
            console.error(error);
        }
    };

    const handleUploadClick = () => {
        fileInputRef.current?.click();
    };

    const handleFolderZipUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
        const file = event.target.files?.[0];
        event.target.value = '';
        if (!file) return;
        setUploadStatus('');
        setUploadError('');
        if (!file.name.toLowerCase().endsWith('.zip')) {
            setUploadError('Select a .zip archive.');
            return;
        }

        setUploading(true);
        try {
            const response = await api.uploadFolderZip(file);
            setUploadStatus(
                `${response.files_ingested} indexed, ${response.files_skipped} skipped, ${response.files_failed} failed.`,
            );
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Folder upload failed.';
            setUploadError(message);
        } finally {
            setUploading(false);
        }
    };

    useEffect(() => {
        if (tabIndex === 1) fetchProfile();
    }, [tabIndex]);

    return (
        // FIX: MinHeight set to 100dvh to fill screen on mobile and desktop
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>
            <CustomAppBar
                tabIndex={tabIndex}
                setTabIndex={setTabIndex}
                workspaces={workspaces}
                workspaceId={workspaceId}
                onWorkspaceChange={changeWorkspace}
            />

            {/* FIX: flexGrow: 1 pushes the bottom of the container to the bottom of the viewport */}
            <Container maxWidth={false} component="main" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
                {interactive && workspacesLoaded && !workspace ? (
                    <WorkspacePanel workspace={null} onWorkspaceCreated={addWorkspace} />
                ) : tabIndex === 0 ? (
                    <Grid container spacing={3}>
                        <Grid size={{ xs: 12, md: 4 }}>
                            <Paper sx={{ p: 3, borderRadius: 2 }}>
                                <Typography variant="h6" gutterBottom>Request Briefing</Typography>
                                <TextField
                                    fullWidth
                                    label="Topic (e.g., AI Agents)"
                                    value={topic}
                                    onChange={(e) => setTopic(e.target.value)}
                                    margin="normal"
                                    disabled={loading}
                                />
                                <Button
                                    fullWidth
                                    variant="contained"
                                    size="large"
                                    onClick={handleGenerate}
                                    disabled={loading || !topic || (interactive && !workspace)}
                                    startIcon={loading ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
                                    sx={{ mt: 2 }}
                                >
                                    {loading ? 'Agents Working...' : 'Generate Report'}
                                </Button>

                                {errorMsg && (
                                    <Box sx={{ mt: 2 }}>
                                        <Alert severity="error">{errorMsg}</Alert>
                                    </Box>
                                )}
                            </Paper>

                            {interactive && workspace && (
                                <WorkspacePanel workspace={workspace} onWorkspaceCreated={addWorkspace} />
                            )}

                            <Paper sx={{ p: 3, borderRadius: 2, mt: 3 }}>
                                <Typography variant="h6" gutterBottom>Upload Folder</Typography>
                                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                                    Upload a zipped folder to your private server memory.
                                </Typography>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".zip,application/zip"
                                    hidden
                                    onChange={handleFolderZipUpload}
                                />
                                <Button
                                    fullWidth
                                    variant="outlined"
                                    onClick={handleUploadClick}
                                    disabled={uploading}
                                    startIcon={uploading ? <CircularProgress size={20} /> : <UploadFileIcon />}
                                >
                                    {uploading ? 'Indexing...' : 'Upload .zip'}
                                </Button>
                                {uploadStatus && (
                                    <Alert severity="success" sx={{ mt: 2 }}>
                                        {uploadStatus}
                                    </Alert>
                                )}
                                {uploadError && (
                                    <Alert severity="error" sx={{ mt: 2 }}>
                                        {uploadError}
                                    </Alert>
                                )}
                            </Paper>
                        </Grid>

                        <Grid size={{ xs: 12, md: 8 }}>
                            {interactive && workspace && (
                                <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
                                    <Button startIcon={<RefreshIcon />} onClick={() => void api.getFeed().then(setFeed).catch((error) => {
                                        setErrorMsg(error instanceof Error ? error.message : 'Unable to load feed.');
                                    })}>Refresh team feed</Button>
                                </Box>
                            )}
                            {result ? (
                                <Paper sx={{ p: 4, borderRadius: 2 }}>
                                    <Typography variant="h5" gutterBottom>{result.topic}</Typography>
                                    <Divider sx={{ my: 2 }} />
                                    <div className="prose">
                                        <ReactMarkdown>{result.content}</ReactMarkdown>
                                    </div>
                                    <Box sx={{ mt: 4, display: 'flex', gap: 1 }}>
                                        <IconButton color="success" onClick={() => sendFeedback('positive', 'Great!')}>
                                            <ThumbUpIcon />
                                        </IconButton>
                                        <IconButton color="error" onClick={() => sendFeedback('negative', 'Bad.')}>
                                            <ThumbDownIcon />
                                        </IconButton>
                                    </Box>
                                </Paper>
                            ) : feed.length > 0 ? (
                                <Grid container spacing={2}>
                                    {feed.map((item) => (
                                        <Grid size={{ xs: 12, md: 6 }} key={item.id}>
                                            <Card variant="outlined">
                                                <CardContent>
                                                    <Typography variant="h6">{item.title}</Typography>
                                                    <Typography variant="body2" color="text.secondary">
                                                        {item.bullets.join(' ')}
                                                    </Typography>
                                                    <Box sx={{ mt: 1 }}>{item.topics.map((tag) => <Chip key={tag} label={tag} size="small" sx={{ mr: 0.5 }} />)}</Box>
                                                </CardContent>
                                            </Card>
                                        </Grid>
                                    ))}
                                </Grid>
                            ) : (
                                <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed grey', borderRadius: 2 }}>
                                    <Typography color="text.secondary">Request a briefing or refresh the selected workspace feed.</Typography>
                                </Box>
                            )}
                        </Grid>
                    </Grid>
                ) : (
                    <Box>
                        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                            <Typography variant="h5">Agent Memory</Typography>
                            <Button startIcon={<RefreshIcon />} onClick={fetchProfile}>Refresh</Button>
                        </Box>
                        <Grid container spacing={3}>
                            {memories.length > 0 ? (
                                memories.map((mem) => (
                                    <Grid size={{ xs: 12, sm: 6, md: 4 }} key={mem.id}>
                                        <Card variant="outlined">
                                            <CardContent>
                                                <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                                                    <Chip
                                                        label={mem.metadata.sentiment || 'info'}
                                                        color={mem.metadata.sentiment === 'positive' ? 'success' : 'error'}
                                                        size="small"
                                                    />
                                                    <Typography variant="caption" color="text.secondary">
                                                        {mem.metadata.topic}
                                                    </Typography>
                                                </Box>
                                                <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic' }}>
                                                    "{mem.document}"
                                                </Typography>
                                            </CardContent>
                                        </Card>
                                    </Grid>
                                ))
                            ) : (
                                <Grid size={12}>
                                    <Typography align="center" color="text.secondary" sx={{ py: 4 }}>
                                        No memories yet. Use the newsfeed to train the system.
                                    </Typography>
                                </Grid>
                            )}
                        </Grid>
                    </Box>
                )}
            </Container>
            <Snackbar open={snackbarOpen} autoHideDuration={4000} onClose={() => setSnackbarOpen(false)} message={snackbarMsg} />
        </Box>
    );
};

export default Dashboard;

