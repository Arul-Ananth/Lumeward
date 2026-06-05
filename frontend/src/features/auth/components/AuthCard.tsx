import MuiCard from '@mui/material/Card';
import { styled } from '@mui/material/styles';

const AuthCard = styled(MuiCard)(({ theme }) => ({
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

export default AuthCard;
