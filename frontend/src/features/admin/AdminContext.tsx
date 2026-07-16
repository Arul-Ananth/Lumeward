/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { getWorkspaceId, setWorkspaceId } from "../auth/storage";
import { adminApi } from "./api";
import type { AdminBootstrap } from "./types";

interface AdminContextValue {
  bootstrap: AdminBootstrap | null;
  loading: boolean;
  error: string;
  workspaceId: number | null;
  selectWorkspace: (id: number) => void;
  refresh: () => Promise<void>;
}
const AdminContext = createContext<AdminContextValue | null>(null);

export function AdminProvider({ children }: { children: ReactNode }) {
  const [bootstrap, setBootstrap] = useState<AdminBootstrap | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [workspaceId, setSelected] = useState<number | null>(getWorkspaceId());
  const load = useCallback(async (signal?: AbortSignal) => {
    setError("");
    try {
      const next = await adminApi.bootstrap(signal);
      setBootstrap(next);
      const stored = getWorkspaceId();
      const selected = next.workspaces.some((item) => item.id === stored)
        ? stored
        : (next.workspaces[0]?.id ?? null);
      setSelected(selected);
      setWorkspaceId(selected);
    } catch (reason) {
      if (reason instanceof DOMException && reason.name === "AbortError")
        return;
      setError(
        reason instanceof Error
          ? reason.message
          : "Unable to load organization.",
      );
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);
  const selectWorkspace = useCallback((id: number) => {
    setSelected(id);
    setWorkspaceId(id);
  }, []);
  const refresh = useCallback(async () => {
    setLoading(true);
    await load();
  }, [load]);
  const value = useMemo(
    () => ({
      bootstrap,
      loading,
      error,
      workspaceId,
      selectWorkspace,
      refresh,
    }),
    [bootstrap, loading, error, workspaceId, selectWorkspace, refresh],
  );
  return (
    <AdminContext.Provider value={value}>{children}</AdminContext.Provider>
  );
}

export function useAdmin() {
  const value = useContext(AdminContext);
  if (!value) throw new Error("useAdmin must be used inside AdminProvider.");
  return value;
}
