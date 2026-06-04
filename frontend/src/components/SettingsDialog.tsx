import  { useState } from 'react';
import {
    Dialog, DialogTitle, DialogContent, DialogActions,
    TextField, Button, Typography, Box, Divider
} from '@mui/material';
import { useSettings } from '../hooks/useSettings';

interface SettingsDialogProps {
    open: boolean;
    onClose: () => void;
}

export default function SettingsDialog({ open, onClose }: SettingsDialogProps) {
    const { apiKey, setApiKey, serperKey, setSerperKey } = useSettings();
    const [localOpenAI, setLocalOpenAI] = useState(apiKey);
    const [localSerper, setLocalSerper] = useState(serperKey);

    const handleSave = () => {
        setApiKey(localOpenAI);
        setSerperKey(localSerper);
        onClose();
    };

    return (
        <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
            <DialogTitle>Agent Settings</DialogTitle>
            <DialogContent>
                <Box sx={{ mt: 1 }}>
                    <Typography variant="subtitle2" gutterBottom>
                        Search Capability
                    </Typography>
                    <TextField
                        fullWidth
                        label="Serper API Key (Google Search)"
                        variant="outlined"
                        value={localSerper}
                        onChange={(e) => setLocalSerper(e.target.value)}
                        helperText="Required for real-time web search (serper.dev)"
                        sx={{ mb: 3 }}
                    />

                    <Divider sx={{ mb: 2 }} />

                    <Typography variant="subtitle2" gutterBottom>
                        LLM Configuration
                    </Typography>
                    <TextField
                        fullWidth
                        label="OpenAI API Key (Optional)"
                        variant="outlined"
                        value={localOpenAI}
                        onChange={(e) => setLocalOpenAI(e.target.value)}
                        helperText="If empty, uses Local Ollama (Default)"
                        sx={{ mb: 2 }}
                    />
                </Box>
            </DialogContent>
            <DialogActions>
                <Button onClick={onClose}>Cancel</Button>
                <Button onClick={handleSave} variant="contained" color="primary">
                    Save
                </Button>
            </DialogActions>
        </Dialog>
    );
}
