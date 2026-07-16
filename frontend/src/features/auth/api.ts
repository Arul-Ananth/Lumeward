import type { AuthStatusResponse, OrganizationSignupResponse, SignupResponse } from './types';
import { apiRequest } from '../../services/http';

export async function getAuthStatus(): Promise<AuthStatusResponse> {
    return apiRequest<AuthStatusResponse>('/auth/status');
}

export async function signup(fullName: string, email: string, password: string): Promise<SignupResponse> {
    return apiRequest<SignupResponse>('/auth/signup', {
        method: 'POST',
        body: {
            full_name: fullName,
            email,
            password,
        },
        includeAuth: false,
    });
}

export async function signupOrganization(fullName: string, email: string, password: string, organizationName: string): Promise<OrganizationSignupResponse> {
    return apiRequest<OrganizationSignupResponse>('/auth/organization-signup', {
        method: 'POST',
        body: { full_name: fullName, email, password, organization_name: organizationName },
        includeAuth: false,
    });
}

export async function login(email: string, password: string): Promise<AuthStatusResponse> {
    return apiRequest<AuthStatusResponse>('/auth/login', {
        method: 'POST',
        body: { email, password },
        includeAuth: false,
    });
}

export async function logout(): Promise<void> {
    await apiRequest<{ message: string }>('/auth/logout', {
        method: 'POST',
    });
}
