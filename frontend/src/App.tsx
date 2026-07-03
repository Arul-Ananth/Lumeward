import { lazy, Suspense } from 'react';
import { BrowserRouter as Router, Navigate, Route, Routes } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { getApiBaseUrl } from './services/http';
import { useAuth } from './hooks/useAuth';
import { AuthProvider } from './providers/AuthProvider';
import AppTheme from './theme/AppTheme';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const SignInPage = lazy(() => import('./features/auth/pages/SignInPage'));
const SignUpPage = lazy(() => import('./features/auth/pages/SignUpPage'));

function LoadingScreen() {
  return (
    <Box sx={{ minHeight: '100dvh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <CircularProgress />
    </Box>
  );
}

function BackendUnavailableScreen({ message }: { message: string }) {
  return (
    <Container maxWidth="sm" sx={{ minHeight: '100dvh', display: 'flex', alignItems: 'center' }}>
      <Stack spacing={2} sx={{ width: '100%' }}>
        <Typography variant="h4">Backend unavailable</Typography>
        <Alert severity="error">{message}</Alert>
        <Typography variant="body2" color="text.secondary">
          The frontend is configured to call {getApiBaseUrl()}. Start the Lumeward server there or update `VITE_API_BASE_URL`.
        </Typography>
        <Box component="pre" sx={{ m: 0, p: 2, borderRadius: 1, bgcolor: 'background.paper', border: '1px solid', borderColor: 'divider', overflowX: 'auto' }}>
{`.\\venv_win\\Scripts\\python.exe backend\\main.py --mode server`}
        </Box>
      </Stack>
    </Container>
  );
}

function AppRoutes() {
  const { loading, status } = useAuth();

  if (loading || !status) {
    return <LoadingScreen />;
  }

  if (status.auth_mode === 'offline') {
    return <BackendUnavailableScreen message={status.message} />;
  }

  const interactiveMode = status.auth_mode === 'interactive';
  const needsLogin = interactiveMode && !status.authenticated;

  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/" element={needsLogin ? <Navigate to="/signin" replace /> : <Dashboard />} />
        <Route
          path="/signin"
          element={interactiveMode && status.authenticated ? <Navigate to="/" replace /> : status.trusted_lan_mode ? <Navigate to="/" replace /> : <SignInPage />}
        />
        <Route
          path="/signup"
          element={interactiveMode && status.authenticated ? <Navigate to="/" replace /> : status.trusted_lan_mode ? <Navigate to="/" replace /> : <SignUpPage />}
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </Suspense>
  );
}

export default function App() {
  return (
    <AppTheme>
      <AuthProvider>
        <Router>
          <AppRoutes />
        </Router>
      </AuthProvider>
    </AppTheme>
  );
}
