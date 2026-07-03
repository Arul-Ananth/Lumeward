import * as React from 'react';
import { useNavigate } from 'react-router-dom';

import AuthSplitLayout from '../../../components/AuthSplitLayout';
import { useAuth } from '../../../hooks/useAuth';
import AuthFormScaffold, { AuthTextField } from '../components/AuthFormScaffold';

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
            <AuthFormScaffold
                alternateHref="/signin"
                alternatePrompt="Already have an account?"
                alternateText="Sign in"
                formError={formError}
                onSubmit={handleSubmit}
                socialAction="Sign up"
                submitText="Create account"
                title="Sign up"
            >
                <AuthTextField error={Boolean(nameError)} helperText={nameError} id="name" label="Name" value={name} onChange={(event) => setName(event.target.value)} />
                <AuthTextField error={Boolean(emailError)} helperText={emailError} id="email" label="Email" type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
                <AuthTextField error={Boolean(passwordError)} helperText={passwordError} id="password" label="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </AuthFormScaffold>
        </AuthSplitLayout>
    );
}
