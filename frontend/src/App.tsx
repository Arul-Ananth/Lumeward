import { lazy, Suspense, type ReactNode } from "react";
import {
  BrowserRouter as Router,
  Navigate,
  Route,
  Routes,
} from "react-router-dom";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import CircularProgress from "@mui/material/CircularProgress";
import Container from "@mui/material/Container";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

import { getApiBaseUrl } from "./services/http";
import { useAuth } from "./hooks/useAuth";
import { AuthProvider } from "./providers/AuthProvider";
import AppTheme from "./theme/AppTheme";
import { AdminProvider, useAdmin } from "./features/admin/AdminContext";

const Dashboard = lazy(() => import("./pages/Dashboard"));
const SignInPage = lazy(() => import("./features/auth/pages/SignInPage"));
const SignUpPage = lazy(() => import("./features/auth/pages/SignUpPage"));
const AdminShell = lazy(() => import("./features/admin/AdminShell"));
const OverviewPage = lazy(() => import("./features/admin/pages/OverviewPage"));
const PeoplePage = lazy(() => import("./features/admin/pages/PeoplePage"));
const WorkspacesPage = lazy(
  () => import("./features/admin/pages/WorkspacesPage"),
);
const ContextPage = lazy(() => import("./features/admin/pages/ContextPage"));
const SettingsPage = lazy(() => import("./features/admin/pages/SettingsPage"));
const AuditPage = lazy(() => import("./features/admin/pages/AuditPage"));
const WorkspaceOnboardingPage = lazy(
  () => import("./features/admin/pages/WorkspaceOnboardingPage"),
);
const InvitationPage = lazy(
  () => import("./features/admin/pages/InvitationPage"),
);

function LoadingScreen() {
  return (
    <Box
      role="status"
      aria-label="Loading Lumeward"
      sx={{
        minHeight: "100dvh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <CircularProgress />
    </Box>
  );
}

function BackendUnavailableScreen({ message }: { message: string }) {
  return (
    <Container
      maxWidth="sm"
      sx={{ minHeight: "100dvh", display: "flex", alignItems: "center" }}
    >
      <Stack spacing={2} sx={{ width: "100%" }}>
        <Typography variant="h4">Backend unavailable</Typography>
        <Alert severity="error">{message}</Alert>
        <Typography variant="body2" color="text.secondary">
          The frontend is configured to call {getApiBaseUrl()}. Start the Lumeward server there or update `VITE_API_BASE_URL`.
        </Typography>
        <Box
          component="pre"
          sx={{
            m: 0,
            p: 2,
            borderRadius: 1,
            bgcolor: "background.paper",
            border: "1px solid",
            borderColor: "divider",
            overflowX: "auto",
          }}
        >
          {`.\\venv_win\\Scripts\\uv.exe run lumeward --mode server`}
        </Box>
      </Stack>
    </Container>
  );
}

function LandingRedirect() {
  const { bootstrap, loading, error } = useAdmin();
  if (loading) return <LoadingScreen />;
  if (error || !bootstrap) return <Navigate to="/workspace" replace />;
  if (bootstrap.onboarding_required)
    return <Navigate to="/onboarding/workspace" replace />;
  const canAdmin =
    bootstrap.organization_role === "organization_admin" ||
    bootstrap.workspaces.some(
      (workspace) => workspace.role === "workspace_admin",
    );
  return (
    <Navigate
      to={
        canAdmin
          ? bootstrap.organization_role === "organization_admin"
            ? "/admin/overview"
            : "/admin/people"
          : "/workspace"
      }
      replace
    />
  );
}

function OrganizationAdminOnly({ children }: { children: ReactNode }) {
  const { bootstrap, loading } = useAdmin();
  if (loading) return <LoadingScreen />;
  return bootstrap?.organization_role === "organization_admin" ? children : <Navigate to="/admin/people" replace />;
}

function AppRoutes() {
  const { loading, status } = useAuth();

  if (loading || !status) {
    return <LoadingScreen />;
  }

  if (status.auth_mode === "offline") {
    return <BackendUnavailableScreen message={status.message} />;
  }

  const interactiveMode = status.auth_mode === "interactive";
  const needsLogin = interactiveMode && !status.authenticated;

  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/invite/:token" element={<InvitationPage />} />
        <Route
          path="/"
          element={
            needsLogin ? (
              <Navigate to="/signin" replace />
            ) : (
              <AdminProvider>
                <LandingRedirect />
              </AdminProvider>
            )
          }
        />
        <Route
          path="/signin"
          element={
            interactiveMode && status.authenticated ? (
              <Navigate to="/" replace />
            ) : status.trusted_lan_mode ? (
              <Navigate to="/" replace />
            ) : (
              <SignInPage />
            )
          }
        />
        <Route
          path="/workspace"
          element={
            needsLogin ? <Navigate to="/signin" replace /> : <Dashboard />
          }
        />
        <Route
          path="/onboarding/workspace"
          element={
            needsLogin ? (
              <Navigate to="/signin" replace />
            ) : (
              <AdminProvider>
                <WorkspaceOnboardingPage />
              </AdminProvider>
            )
          }
        />
        <Route
          path="/admin"
          element={
            needsLogin ? (
              <Navigate to="/signin" replace />
            ) : (
              <AdminProvider>
                <AdminShell />
              </AdminProvider>
            )
          }
        >
          <Route index element={<Navigate to="overview" replace />} />
          <Route path="overview" element={<OrganizationAdminOnly><OverviewPage /></OrganizationAdminOnly>} />
          <Route path="people" element={<PeoplePage />} />
          <Route path="workspaces" element={<OrganizationAdminOnly><WorkspacesPage /></OrganizationAdminOnly>} />
          <Route path="context" element={<ContextPage />} />
          <Route path="settings" element={<OrganizationAdminOnly><SettingsPage /></OrganizationAdminOnly>} />
          <Route path="audit" element={<OrganizationAdminOnly><AuditPage /></OrganizationAdminOnly>} />
        </Route>
        <Route
          path="/signup"
          element={
            interactiveMode && status.authenticated ? (
              <Navigate to="/" replace />
            ) : status.trusted_lan_mode ? (
              <Navigate to="/" replace />
            ) : (
              <SignUpPage />
            )
          }
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
