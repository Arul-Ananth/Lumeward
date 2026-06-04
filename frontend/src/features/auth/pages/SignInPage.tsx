import * as React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import Link from '@mui/material/Link';
import MuiCard from '@mui/material/Card';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { styled } from '@mui/material/styles';
import { Link as RouterLink, useNavigate } from 'react-router-dom';

import AuthSplitLayout from '../../../components/AuthSplitLayout';
import { socialLogin } from '../api';
import { useAuth } from '../../../hooks/useAuth';

function GoogleIcon() {
    return (
        <Box component="svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.26-.19-.58z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
        </Box>
    );
}

function FacebookIcon() {
    return (
        <Box component="svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="#1877F2">
            <path d="M24 12.073c0-6.627-5.373-12-12-12s-12 5.373-12 12c0 5.99 4.388 10.954 10.125 11.854v-8.385H7.078v-3.47h3.047V9.43c0-3.007 1.792-4.669 4.533-4.669 1.312 0 2.686.235 2.686.235v2.953H15.83c-1.491 0-1.956.925-1.956 1.874v2.25h3.328l-.532 3.47h-2.796v8.385C19.612 23.027 24 18.062 24 12.073z" />
        </Box>
    );
}

function AppleIcon() {
    return (
        <Box component="svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M17.05 20.28c-.98.95-2.05.8-3.08.35-1.09-.46-2.09-.48-3.24 0-1.44.62-2.2.44-3.06-.35C2.79 15.25 3.51 7.59 9.05 7.31c1.35.07 2.29.74 3.08.74 1.18 0 2.45-1.02 3.9-1.02 1.29.05 2.52.55 3.22 1.4-2.92 1.63-2.34 5.72.64 7.02-.54 1.7-1.3 3.42-2.84 4.83zm-2.9-15.06c1.15-1.41 1-3.03.96-3.72-1.24.11-2.8.92-3.69 1.94-.97 1.12-1.23 2.91-1.07 3.59 1.41.13 2.76-.66 3.8-1.81z" />
        </Box>
    );
}

function SitemarkIcon() {
    return (
        <Box component="svg" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <rect x="2" y="2" width="20" height="20" rx="4" />
        </Box>
    );
}

function ForgotPassword({ open, handleClose }: { open: boolean; handleClose: () => void }) {
    return (
        <Dialog open={open} onClose={handleClose}>
            <DialogTitle>Reset password</DialogTitle>
            <DialogContent>
                <DialogContentText>
                    Password reset is not implemented yet.
                </DialogContentText>
            </DialogContent>
            <DialogActions>
                <Button onClick={handleClose}>Close</Button>
            </DialogActions>
        </Dialog>
    );
}

const Card = styled(MuiCard)(({ theme }) => ({
    display: 'flex',
    flexDirection: 'column',
    width: '100%',
    padding: theme.spacing(4.5),
    gap: theme.spacing(2),
    border: `1px solid ${theme.palette.divider}`,
    background: theme.palette.background.paper,
    color: theme.palette.text.primary,
    boxShadow: theme.shadows[6],
}));

export default function SignInPage() {
    const navigate = useNavigate();
    const { login } = useAuth();
    const [email, setEmail] = React.useState('');
    const [password, setPassword] = React.useState('');
    const [emailError, setEmailError] = React.useState('');
    const [passwordError, setPasswordError] = React.useState('');
    const [formError, setFormError] = React.useState('');
    const [open, setOpen] = React.useState(false);

    const validateInputs = () => {
        let valid = true;
        if (!email || !/\S+@\S+\.\S+/.test(email)) {
            setEmailError('Please enter a valid email address.');
            valid = false;
        } else {
            setEmailError('');
        }
        if (!password) {
            setPasswordError('Password is required.');
            valid = false;
        } else {
            setPasswordError('');
        }
        return valid;
    };

    const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setFormError('');
        if (!validateInputs()) {
            return;
        }

        try {
            await login(email, password);
            navigate('/');
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            setFormError(`Sign in failed: ${message}`);
        }
    };

    return (
        <AuthSplitLayout
            heroTitle="Secure access for every deployment mode."
            heroBody="Trusted LAN can bypass sign-in, but interactive deployments keep a dedicated auth surface that can evolve without rewriting the app shell."
            heroTags={['Trusted LAN', 'Interactive auth', 'Provider-ready architecture']}
        >
            <Card variant="outlined">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SitemarkIcon />
                    <Typography variant="overline" sx={{ letterSpacing: '0.2em' }}>
                        Newsroom Agent
                    </Typography>
                </Box>
                <Typography component="h1" variant="h4" sx={{ width: '100%', fontSize: 'clamp(2rem, 10vw, 2.15rem)' }}>
                    Sign in
                </Typography>
                <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 2 }}>
                    <FormControl>
                        <FormLabel htmlFor="email">Email</FormLabel>
                        <TextField
                            error={Boolean(emailError)}
                            helperText={emailError}
                            id="email"
                            type="email"
                            placeholder="you@domain.com"
                            autoComplete="email"
                            autoFocus
                            required
                            fullWidth
                            value={email}
                            onChange={(event) => setEmail(event.target.value)}
                        />
                    </FormControl>
                    <FormControl>
                        <FormLabel htmlFor="password">Password</FormLabel>
                        <TextField
                            error={Boolean(passwordError)}
                            helperText={passwordError}
                            type="password"
                            id="password"
                            autoComplete="current-password"
                            required
                            fullWidth
                            value={password}
                            onChange={(event) => setPassword(event.target.value)}
                        />
                    </FormControl>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <FormControlLabel control={<Checkbox value="remember" color="primary" />} label="Remember me" />
                        <Link component="button" type="button" onClick={() => setOpen(true)} variant="body2">
                            Forgot password?
                        </Link>
                    </Box>
                    {formError && <Alert severity="error">{formError}</Alert>}
                    <Button type="submit" fullWidth variant="contained">
                        Sign in
                    </Button>
                </Box>
                <Divider>or</Divider>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <Button fullWidth variant="outlined" onClick={() => socialLogin('google')} startIcon={<GoogleIcon />}>
                        Sign in with Google
                    </Button>
                    <Button fullWidth variant="outlined" onClick={() => socialLogin('facebook')} startIcon={<FacebookIcon />}>
                        Sign in with Facebook
                    </Button>
                    <Button fullWidth variant="outlined" onClick={() => socialLogin('apple')} startIcon={<AppleIcon />}>
                        Sign in with Apple
                    </Button>
                    <Typography sx={{ textAlign: 'center' }}>
                        Don&apos;t have an account?{' '}
                        <Link component={RouterLink} to="/signup" variant="body2">
                            Sign up
                        </Link>
                    </Typography>
                </Box>
            </Card>
            <ForgotPassword open={open} handleClose={() => setOpen(false)} />
        </AuthSplitLayout>
    );
}
