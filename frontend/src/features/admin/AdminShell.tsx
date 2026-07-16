import { useState } from "react";
import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import AppBar from "@mui/material/AppBar";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Container from "@mui/material/Container";
import Divider from "@mui/material/Divider";
import Drawer from "@mui/material/Drawer";
import IconButton from "@mui/material/IconButton";
import List from "@mui/material/List";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import MenuItem from "@mui/material/MenuItem";
import Select from "@mui/material/Select";
import Toolbar from "@mui/material/Toolbar";
import Tooltip from "@mui/material/Tooltip";
import Typography from "@mui/material/Typography";
import DashboardOutlined from "@mui/icons-material/DashboardOutlined";
import GroupOutlined from "@mui/icons-material/GroupOutlined";
import WorkspacesOutlined from "@mui/icons-material/WorkspacesOutlined";
import FolderSharedOutlined from "@mui/icons-material/FolderSharedOutlined";
import SettingsOutlined from "@mui/icons-material/SettingsOutlined";
import HistoryOutlined from "@mui/icons-material/HistoryOutlined";
import MenuIcon from "@mui/icons-material/Menu";
import ArrowForwardOutlined from "@mui/icons-material/ArrowForwardOutlined";
import { useAuth } from "../../hooks/useAuth";
import { ErrorState, LoadingState } from "./components";
import { useAdmin } from "./AdminContext";

const width = 248;
const links = [
  {
    to: "/admin/overview",
    label: "Overview",
    icon: <DashboardOutlined />,
    organizationOnly: true,
  },
  { to: "/admin/people", label: "People", icon: <GroupOutlined /> },
  {
    to: "/admin/workspaces",
    label: "Workspaces",
    icon: <WorkspacesOutlined />,
    organizationOnly: true,
  },
  {
    to: "/admin/context",
    label: "Shared context",
    icon: <FolderSharedOutlined />,
  },
  {
    to: "/admin/settings",
    label: "Settings",
    icon: <SettingsOutlined />,
    organizationOnly: true,
  },
  {
    to: "/admin/audit",
    label: "Audit",
    icon: <HistoryOutlined />,
    organizationOnly: true,
  },
];

export default function AdminShell() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { bootstrap, loading, error, workspaceId, selectWorkspace, refresh } =
    useAdmin();
  const { logout, status } = useAuth();
  const location = useLocation();
  if (loading) return <LoadingState label="Loading your organization…" />;
  if (error || !bootstrap)
    return (
      <Container sx={{ py: 6 }}>
        <ErrorState
          message={error || "Organization unavailable."}
          retry={() => void refresh()}
        />
      </Container>
    );
  if (bootstrap.onboarding_required)
    return <Navigate to="/onboarding/workspace" replace />;
  const orgAdmin = bootstrap.organization_role === "organization_admin";
  if (
    !orgAdmin &&
    !bootstrap.workspaces.some(
      (workspace) => workspace.role === "workspace_admin",
    )
  )
    return <Navigate to="/workspace" replace />;
  const visibleLinks = links.filter(
    (link) => orgAdmin || !link.organizationOnly,
  );
  const drawer = (
    <Box sx={{ height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar>
        <Typography variant="h6" color="primary.main" sx={{ fontWeight: 700 }}>
          Lumeward
        </Typography>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1 }}>
        {visibleLinks.map((link) => (
          <ListItemButton
            key={link.to}
            component={NavLink}
            to={link.to}
            selected={location.pathname === link.to}
            onClick={() => setMobileOpen(false)}
            sx={{ borderRadius: 1 }}
          >
            <ListItemIcon sx={{ minWidth: 40 }}>{link.icon}</ListItemIcon>
            <ListItemText primary={link.label} />
          </ListItemButton>
        ))}
      </List>
      <Box sx={{ mt: "auto", p: 2 }}>
        <Button
          component={NavLink}
          to="/workspace"
          endIcon={<ArrowForwardOutlined />}
          fullWidth
        >
          Open workspace
        </Button>
      </Box>
    </Box>
  );
  return (
    <Box sx={{ minHeight: "100dvh", bgcolor: "background.default" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          borderBottom: 1,
          borderColor: "divider",
          ml: { md: `${width}px` },
          width: { md: `calc(100% - ${width}px)` },
        }}
      >
        <Toolbar sx={{ gap: 2 }}>
          <IconButton
            aria-label="Open navigation"
            onClick={() => setMobileOpen(true)}
            sx={{ display: { md: "none" } }}
          >
            <MenuIcon />
          </IconButton>
          <Box sx={{ minWidth: 0, flexGrow: 1 }}>
            <Typography noWrap fontWeight={600}>
              {bootstrap.organization.name}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {orgAdmin
                ? "Organization administrator"
                : "Workspace administrator"}
            </Typography>
          </Box>
          {bootstrap.workspaces.length > 0 && (
            <Select
              aria-label="Current workspace"
              size="small"
              value={workspaceId ?? ""}
              onChange={(event) => selectWorkspace(Number(event.target.value))}
              sx={{ maxWidth: { xs: 150, sm: 240 } }}
            >
              {bootstrap.workspaces.map((workspace) => (
                <MenuItem key={workspace.id} value={workspace.id}>
                  {workspace.name}
                </MenuItem>
              ))}
            </Select>
          )}
          {!status?.trusted_lan_mode && (
            <Tooltip title="Sign out">
              <Button color="inherit" onClick={() => void logout()}>
                Sign out
              </Button>
            </Tooltip>
          )}
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          display: { xs: "none", md: "block" },
          "& .MuiDrawer-paper": { width, boxSizing: "border-box" },
        }}
        open
      >
        {drawer}
      </Drawer>
      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        ModalProps={{ keepMounted: true }}
        sx={{
          display: { xs: "block", md: "none" },
          "& .MuiDrawer-paper": { width },
        }}
      >
        {drawer}
      </Drawer>
      <Box component="main" sx={{ ml: { md: `${width}px` }, pt: 11, pb: 6 }}>
        <Container maxWidth="xl">
          <Outlet />
        </Container>
      </Box>
    </Box>
  );
}
