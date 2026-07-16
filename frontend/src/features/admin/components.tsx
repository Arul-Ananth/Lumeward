import type { ReactNode } from "react";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import CircularProgress from "@mui/material/CircularProgress";
import Paper from "@mui/material/Paper";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";

export function PageHeader({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        gap: 2,
        alignItems: { xs: "flex-start", sm: "center" },
        flexDirection: { xs: "column", sm: "row" },
        mb: 3,
      }}
    >
      <Box>
        <Typography component="h1" variant="h4">
          {title}
        </Typography>
        <Typography color="text.secondary">{description}</Typography>
      </Box>
      {action}
    </Box>
  );
}
export function LoadingState({ label = "Loading…" }: { label?: string }) {
  return (
    <Stack role="status" alignItems="center" spacing={1} sx={{ py: 8 }}>
      <CircularProgress size={28} />
      <Typography>{label}</Typography>
    </Stack>
  );
}
export function ErrorState({
  message,
  retry,
}: {
  message: string;
  retry?: () => void;
}) {
  return (
    <Alert
      severity="error"
      action={
        retry ? (
          <Button color="inherit" onClick={retry}>
            Retry
          </Button>
        ) : undefined
      }
    >
      {message}
    </Alert>
  );
}
export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <Paper variant="outlined" sx={{ p: 4, textAlign: "center" }}>
      <Typography variant="h6">{title}</Typography>
      <Typography color="text.secondary" sx={{ mt: 1, mb: action ? 2 : 0 }}>
        {description}
      </Typography>
      {action}
    </Paper>
  );
}
export function StatusMessage({ children }: { children: ReactNode }) {
  return (
    <Alert severity="success" role="status" sx={{ mb: 2 }}>
      {children}
    </Alert>
  );
}
