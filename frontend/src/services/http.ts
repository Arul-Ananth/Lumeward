import { getSessionToken, getWorkspaceId } from '../features/auth/storage';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

export function getApiBaseUrl(): string {
    return API_BASE_URL;
}

export class ApiError extends Error {
    status: number;

    constructor(status: number, message: string) {
        super(message);
        this.status = status;
    }
}

interface ApiRequestOptions {
    method?: string;
    body?: unknown;
    headers?: HeadersInit;
    includeAuth?: boolean;
}

export async function apiRequest<T>(
    path: string,
    { method = 'GET', body, headers, includeAuth = true }: ApiRequestOptions = {},
): Promise<T> {
    const requestHeaders = new Headers(headers || {});
    const token = includeAuth ? getSessionToken() : null;

    const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

    if (body !== undefined && !isFormData && !requestHeaders.has('Content-Type')) {
        requestHeaders.set('Content-Type', 'application/json');
    }
    if (token && !requestHeaders.has('Authorization')) {
        requestHeaders.set('Authorization', `Bearer ${token}`);
    }
    const workspaceId = getWorkspaceId();
    if (workspaceId && !requestHeaders.has('X-Workspace-ID')) {
        requestHeaders.set('X-Workspace-ID', String(workspaceId));
    }

    let response: Response;
    try {
        response = await fetch(`${API_BASE_URL}${path}`, {
            method,
            headers: requestHeaders,
            body: isFormData ? body : body !== undefined ? JSON.stringify(body) : undefined,
        });
    } catch (error) {
        const message = error instanceof Error ? error.message : 'Unknown network error';
        throw new ApiError(0, `Unable to reach backend at ${API_BASE_URL}. ${message}`);
    }

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
        const detail = typeof data?.detail === 'string' ? data.detail : 'Request failed';
        throw new ApiError(response.status, detail);
    }

    return data as T;
}
