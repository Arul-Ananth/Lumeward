import {
    useCallback,
    useEffect,
    useMemo,
    useState,
    type ReactNode,
} from 'react';

import { AuthContext } from '../context/AuthContext';
import { ApiError } from '../services/http';
import { getAuthStatus, login as loginRequest, logout as logoutRequest, signup as signupRequest } from '../features/auth/api';
import { clearSessionToken, getSessionToken, setSessionToken } from '../features/auth/storage';
import { buildOfflineAuthStatus, type AuthContextValue, type AuthStatusResponse, type SignupResponse } from '../features/auth/types';

function normalizeAuthBootstrapError(error: unknown): AuthStatusResponse {
    if (error instanceof ApiError && error.status === 0) {
        return buildOfflineAuthStatus(error.message);
    }
    if (error instanceof Error) {
        return buildOfflineAuthStatus(error.message);
    }
    return buildOfflineAuthStatus('Unable to determine backend auth status.');
}

export function AuthProvider({ children }: { children: ReactNode }) {
    const [loading, setLoading] = useState(true);
    const [status, setStatus] = useState<AuthStatusResponse | null>(null);

    const loadStatus = useCallback(async () => {
        try {
            const nextStatus = await getAuthStatus();
            if (!nextStatus.authenticated && getSessionToken()) {
                clearSessionToken();
            }
            return nextStatus;
        } catch (error) {
            clearSessionToken();
            return normalizeAuthBootstrapError(error);
        }
    }, []);

    const refreshStatus = useCallback(async () => {
        setStatus(await loadStatus());
    }, [loadStatus]);

    useEffect(() => {
        let active = true;
        (async () => {
            const nextStatus = await loadStatus();
            if (active) {
                setStatus(nextStatus);
                setLoading(false);
            }
        })();
        return () => {
            active = false;
        };
    }, [loadStatus]);

    const login = useCallback(async (email: string, password: string) => {
        const nextStatus = await loginRequest(email, password);
        if (nextStatus.session_token) {
            setSessionToken(nextStatus.session_token);
        } else {
            clearSessionToken();
        }
        const refreshed = await loadStatus();
        setStatus(refreshed);
        return refreshed;
    }, [loadStatus]);

    const signup = useCallback(async (fullName: string, email: string, password: string): Promise<SignupResponse> => {
        return signupRequest(fullName, email, password);
    }, []);

    const logout = useCallback(async () => {
        try {
            await logoutRequest();
        } finally {
            clearSessionToken();
            setStatus(await loadStatus());
        }
    }, [loadStatus]);

    const value = useMemo<AuthContextValue>(
        () => ({
            loading,
            status,
            refreshStatus,
            login,
            signup,
            logout,
        }),
        [loading, status, refreshStatus, login, signup, logout],
    );

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
