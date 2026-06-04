import { useState, useEffect } from 'react';
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
} from '@mui/icons-material';

import { api } from '../services/api';
import type { MemoryRecord, NewsletterResponse } from '../services/api';
import CustomAppBar from '../components/CustomAppBar';

import { useSettings } from '../hooks/useSettings';

const Dashboard = () => {
    const { apiKey, serperKey } = useSettings();
    const [topic, setTopic] = useState('');
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState<NewsletterResponse | null>(null);
    const [tabIndex, setTabIndex] = useState(0);
    const [memories, setMemories] = useState<MemoryRecord[]>([]);
    const [snackbarOpen, setSnackbarOpen] = useState(false);
    const [snackbarMsg, setSnackbarMsg] = useState('');
    const [errorMsg, setErrorMsg] = useState('');
    const [credits, setCredits] = useState<number | string | null>(null);

    const handleGenerate = async () => {
        if (!topic) return;
        setLoading(true);
        setResult(null);
        setErrorMsg('');

        try {
            const data = await api.generateBriefing(topic, {
                serper: serperKey,
                openai: apiKey
            });
            setResult(data);
            if (data.bill) {
                setCredits(data.bill.remaining);
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            console.error(error);
            if (message.includes("Credits")) {
                setErrorMsg(message);
            } else {
                setErrorMsg("Connection failed. Please check backend terminal for errors.");
            }
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

    useEffect(() => {
        if (tabIndex === 1) fetchProfile();
    }, [tabIndex]);

    return (
        // FIX: MinHeight set to 100dvh to fill screen on mobile and desktop
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh' }}>
            <CustomAppBar tabIndex={tabIndex} setTabIndex={setTabIndex} />

            {/* FIX: flexGrow: 1 pushes the bottom of the container to the bottom of the viewport */}
            <Container maxWidth={false} component="main" sx={{ mt: 4, mb: 4, flexGrow: 1 }}>
                {credits !== null && (
                    <Box sx={{ mb: 2, display: 'flex', justifyContent: 'flex-end' }}>
                        <Chip label={`Credits Remaining: ${credits}`} color="primary" variant="outlined" />
                    </Box>
                )}

                {tabIndex === 0 ? (
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
                                    disabled={loading || !topic}
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
                        </Grid>

                        <Grid size={{ xs: 12, md: 8 }}>
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
                            ) : (
                                <Box sx={{ height: 400, display: 'flex', alignItems: 'center', justifyContent: 'center', border: '1px dashed grey', borderRadius: 2 }}>
                                    <Typography color="text.secondary">Enter a topic to start.</Typography>
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

