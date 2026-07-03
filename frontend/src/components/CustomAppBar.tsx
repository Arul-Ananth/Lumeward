import { AppBar, Toolbar, Typography, Container, Tabs, Tab, Button, Box, Chip } from '@mui/material';
import { SmartToy as BotIcon, Psychology as BrainIcon, Newspaper as NewsIcon } from '@mui/icons-material';

import { useAuth } from '../hooks/useAuth';

interface CustomAppBarProps {
    tabIndex: number;
    setTabIndex: (index: number) => void;
}

export default function CustomAppBar({ tabIndex, setTabIndex }: CustomAppBarProps) {
    const { status, logout } = useAuth();
    const trustedLan = status?.trusted_lan_mode;

    return (
        <AppBar position="static" color="transparent" elevation={0} sx={{ borderBottom: '1px solid', borderColor: 'divider' }}>
            <Container maxWidth="lg">
                <Toolbar disableGutters>
                    <BotIcon sx={{ mr: 1, color: 'primary.main' }} />
                    <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
                        Newsroom Agent
                    </Typography>

                    <Tabs value={tabIndex} onChange={(_e, val) => setTabIndex(val)} textColor="primary" indicatorColor="primary">
                        <Tab icon={<NewsIcon />} label="News" />
                        <Tab icon={<BrainIcon />} label="Memory" />
                    </Tabs>

                    <Box sx={{ ml: 2, display: 'flex', gap: 1 }}>
                        <Chip
                            label={trustedLan ? 'Trusted LAN' : status?.provider || 'Interactive Auth'}
                            color="primary"
                            variant="outlined"
                        />
                        {!trustedLan && (
                            <Button color="inherit" onClick={() => void logout()}>
                                Sign out
                            </Button>
                        )}
                    </Box>
                </Toolbar>
            </Container>
        </AppBar>
    );
}
