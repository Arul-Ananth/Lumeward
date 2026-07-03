import * as React from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Link from '@mui/material/Link';
import { useNavigate } from 'react-router-dom';

import AuthSplitLayout from '../../../components/AuthSplitLayout';
import { useAuth } from '../../../hooks/useAuth';
import AuthFormScaffold, { AuthTextField } from '../components/AuthFormScaffold';

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
            <AuthFormScaffold
                alternateHref="/signup"
                alternatePrompt="Don't have an account?"
                alternateText="Sign up"
                formError={formError}
                onSubmit={handleSubmit}
                socialAction="Sign in"
                submitText="Sign in"
                title="Sign in"
            >
                <AuthTextField error={Boolean(emailError)} helperText={emailError} id="email" label="Email" type="email" placeholder="you@domain.com" autoComplete="email" autoFocus value={email} onChange={(event) => setEmail(event.target.value)} />
                <AuthTextField error={Boolean(passwordError)} helperText={passwordError} id="password" label="Password" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} />
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <FormControlLabel control={<Checkbox value="remember" color="primary" />} label="Remember me" />
                    <Link component="button" type="button" onClick={() => setOpen(true)} variant="body2">
                        Forgot password?
                    </Link>
                </Box>
            </AuthFormScaffold>
            <ForgotPassword open={open} handleClose={() => setOpen(false)} />
        </AuthSplitLayout>
    );
}
