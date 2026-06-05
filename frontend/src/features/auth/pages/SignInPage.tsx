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
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { Link as RouterLink, useNavigate } from 'react-router-dom';

import AuthSplitLayout from '../../../components/AuthSplitLayout';
import { useAuth } from '../../../hooks/useAuth';
import AuthCard from '../components/AuthCard';
import { SitemarkIcon } from '../components/AuthIcons';
import SocialAuthButtons from '../components/SocialAuthButtons';

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
            <AuthCard variant="outlined">
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
                    <SocialAuthButtons action="Sign in" />
                    <Typography sx={{ textAlign: 'center' }}>
                        Don&apos;t have an account?{' '}
                        <Link component={RouterLink} to="/signup" variant="body2">
                            Sign up
                        </Link>
                    </Typography>
                </Box>
            </AuthCard>
            <ForgotPassword open={open} handleClose={() => setOpen(false)} />
        </AuthSplitLayout>
    );
}
