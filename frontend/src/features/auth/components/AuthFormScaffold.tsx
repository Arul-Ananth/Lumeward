import type { FormEvent, ReactNode } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
import FormLabel from '@mui/material/FormLabel';
import Link from '@mui/material/Link';
import TextField, { type TextFieldProps } from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { Link as RouterLink } from 'react-router-dom';

import AuthCard from './AuthCard';
import { SitemarkIcon } from './AuthIcons';
import SocialAuthButtons from './SocialAuthButtons';

interface AuthFormScaffoldProps {
    alternateHref: string;
    alternatePrompt: string;
    alternateText: string;
    children: ReactNode;
    formError?: string;
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
    socialAction: 'Sign in' | 'Sign up';
    submitText: string;
    title: string;
}

export default function AuthFormScaffold({
    alternateHref,
    alternatePrompt,
    alternateText,
    children,
    formError,
    onSubmit,
    socialAction,
    submitText,
    title,
}: AuthFormScaffoldProps) {
    return (
        <AuthCard variant="outlined">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <SitemarkIcon />
                <Typography variant="overline" sx={{ letterSpacing: '0.2em' }}>
                    Newsroom Agent
                </Typography>
            </Box>
            <Typography component="h1" variant="h4" sx={{ width: '100%', fontSize: 'clamp(2rem, 10vw, 2.15rem)' }}>
                {title}
            </Typography>
            <Box component="form" onSubmit={onSubmit} noValidate sx={{ display: 'flex', flexDirection: 'column', width: '100%', gap: 2 }}>
                {children}
                {formError && <Alert severity="error">{formError}</Alert>}
                <Button type="submit" fullWidth variant="contained">
                    {submitText}
                </Button>
            </Box>
            <Divider>or</Divider>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                <SocialAuthButtons action={socialAction} />
                <Typography sx={{ textAlign: 'center' }}>
                    {alternatePrompt}{' '}
                    <Link component={RouterLink} to={alternateHref} variant="body2">
                        {alternateText}
                    </Link>
                </Typography>
            </Box>
        </AuthCard>
    );
}

export function AuthTextField({ id, label, ...props }: TextFieldProps & { id: string; label: string }) {
    return (
        <FormControl>
            <FormLabel htmlFor={id}>{label}</FormLabel>
            <TextField id={id} required fullWidth {...props} />
        </FormControl>
    );
}
