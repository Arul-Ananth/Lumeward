import Box from '@mui/material/Box';
import Button from '@mui/material/Button';

import { socialLogin } from '../api';
import { AppleIcon, FacebookIcon, GoogleIcon } from './AuthIcons';

type SocialAuthButtonsProps = {
    action: 'Sign in' | 'Sign up';
};

export default function SocialAuthButtons({ action }: SocialAuthButtonsProps) {
    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Button fullWidth variant="outlined" onClick={() => socialLogin('google')} startIcon={<GoogleIcon />}>
                {action} with Google
            </Button>
            <Button fullWidth variant="outlined" onClick={() => socialLogin('facebook')} startIcon={<FacebookIcon />}>
                {action} with Facebook
            </Button>
            <Button fullWidth variant="outlined" onClick={() => socialLogin('apple')} startIcon={<AppleIcon />}>
                {action} with Apple
            </Button>
        </Box>
    );
}
