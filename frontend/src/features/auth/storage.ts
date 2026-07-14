const AUTH_SESSION_STORAGE_KEY = 'lumeward_session_token';
const WORKSPACE_STORAGE_KEY = 'lumeward_workspace_id';

export function getSessionToken(): string | null {
    return sessionStorage.getItem(AUTH_SESSION_STORAGE_KEY);
}

export function setSessionToken(token: string): void {
    sessionStorage.setItem(AUTH_SESSION_STORAGE_KEY, token);
}

export function clearSessionToken(): void {
    sessionStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
    sessionStorage.removeItem(WORKSPACE_STORAGE_KEY);
}

export const getWorkspaceId = (): number | null => {
    const value = Number(sessionStorage.getItem(WORKSPACE_STORAGE_KEY));
    return Number.isInteger(value) && value > 0 ? value : null;
};

export const setWorkspaceId = (id: number | null): void => {
    if (id) sessionStorage.setItem(WORKSPACE_STORAGE_KEY, String(id));
    else sessionStorage.removeItem(WORKSPACE_STORAGE_KEY);
};
