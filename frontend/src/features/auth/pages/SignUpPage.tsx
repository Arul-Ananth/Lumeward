import * as React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
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

export default function SignUpPage() {
    const navigate = useNavigate();
    const { signup } = useAuth();
    const [name, setName] = React.useState('');
    const [email, setEmail] = React.useState('');
    const [password, setPassword] = React.useState('');
    const [nameError, setNameError] = React.useState('');
    const [emailError, setEmailError] = React.useState('');
    const [passwordError, setPasswordError] = React.useState('');
    const [formError, setFormError] = React.useState('');

    const validateInputs = () => {
        let valid = true;
        if (!name.trim()) {
            setNameError('Name is required.');
            valid = false;
        } else {
            setNameError('');
        }
        if (!email || !/\S+@\S+\.\S+/.test(email)) {
            setEmailError('Please enter a valid email address.');
            valid = false;
        } else {
            setEmailError('');
        }
        if (!password || password.length < 6) {
            setPasswordError('Password must be at least 6 characters long.');
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
            await signup(name, email, password);
            navigate('/signin');
        } catch (error) {
            const message = error instanceof Error ? error.message : 'Unknown error';
            setFormError(`Signup failed: ${message}`);
        }
    };

    return (
        <AuthSplitLayout
            heroTitle="Identity that can evolve without a rewrite."
            heroBody="This auth surface stays separate from the dashboard so future session, token, SSO, or external provider support can plug in cleanly."
            heroTags={['Interactive auth', 'Provider-neutral', 'Security-preserving']}
        >
            <AuthCard variant="outlined">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <SitemarkIcon />
                    <Typography variant="overline" sx={{ letterSpacing: '0.2em' }}>
                        Newsroom Agent
                    </Typography>
                </Box>
                <Typography component="h1" variant="h4" sx={{ width: '100%', fontSize: 'clamp(2rem, 10vw, 2.15rem)' }}>
                    Sign up
                </Typography>
                <Box component="form" onSubmit={handleSubmit} noValidate sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 2 }}>
                    <FormControl>
                        <FormLabel htmlFor="name">Name</FormLabel>
                        <TextField error={Boolean(nameError)} helperText={nameError} id="name" required fullWidth value={name} onChange={(event) => setName(event.target.value)} />
                    </FormControl>
                    <FormControl>
                        <FormLabel htmlFor="email">Email</FormLabel>
                        <TextField error={Boolean(emailError)} helperText={emailError} id="email" type="email" required fullWidth value={email} onChange={(event) => setEmail(event.target.value)} />
                    </FormControl>
                    <FormControl>
                        <FormLabel htmlFor="password">Password</FormLabel>
                        <TextField error={Boolean(passwordError)} helperText={passwordError} id="password" type="password" required fullWidth value={password} onChange={(event) => setPassword(event.target.value)} />
                    </FormControl>
                    {formError && <Alert severity="error">{formError}</Alert>}
                    <Button type="submit" fullWidth variant="contained">
                        Create account
                    </Button>
                </Box>
                <Divider>or</Divider>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                    <SocialAuthButtons action="Sign up" />
                    <Typography sx={{ textAlign: 'center' }}>
                        Already have an account?{' '}
                        <Link component={RouterLink} to="/signin" variant="body2">
                            Sign in
                        </Link>
                    </Typography>
                </Box>
            </AuthCard>
        </AuthSplitLayout>
    );
}
