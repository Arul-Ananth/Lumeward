import { fireEvent, render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuth } from '../../../hooks/useAuth';
import SignUpPage from './SignUpPage';

vi.mock('../../../hooks/useAuth', () => ({ useAuth: vi.fn() }));
vi.mock('../../../components/AuthSplitLayout', () => ({
    default: ({ children }: { children: React.ReactNode }) => <main>{children}</main>,
}));

const signupOrganization = vi.fn();

describe('SignUpPage', () => {
    beforeEach(() => {
        signupOrganization.mockResolvedValue({});
        vi.mocked(useAuth).mockReturnValue({ signupOrganization } as unknown as ReturnType<typeof useAuth>);
    });

    it('creates an organization and routes the administrator to workspace onboarding', async () => {
        render(
            <MemoryRouter initialEntries={['/signup']}>
                <Routes>
                    <Route path="/signup" element={<SignUpPage />} />
                    <Route path="/onboarding/workspace" element={<h1>Workspace onboarding</h1>} />
                </Routes>
            </MemoryRouter>,
        );

        fireEvent.change(screen.getByRole('textbox', { name: /Organization name/ }), { target: { value: 'Acme Research' } });
        fireEvent.change(screen.getByRole('textbox', { name: /^Name/ }), { target: { value: 'Ada Admin' } });
        fireEvent.change(screen.getByRole('textbox', { name: /Email/ }), { target: { value: 'ada@example.com' } });
        fireEvent.change(screen.getByLabelText(/Password/), { target: { value: 'secret123' } });
        fireEvent.click(screen.getByRole('button', { name: 'Create organization' }));

        expect(signupOrganization).toHaveBeenCalledWith(
            'Ada Admin',
            'ada@example.com',
            'secret123',
            'Acme Research',
        );
        expect(await screen.findByRole('heading', { name: 'Workspace onboarding' })).toBeInTheDocument();
    });

    it('announces validation errors without submitting', async () => {
        render(<MemoryRouter><SignUpPage /></MemoryRouter>);

        fireEvent.click(screen.getByRole('button', { name: 'Create organization' }));

        expect(signupOrganization).not.toHaveBeenCalled();
        expect(screen.getByText('Organization name is required.')).toBeInTheDocument();
        expect(screen.getByText('Please enter a valid email address.')).toBeInTheDocument();
        expect(screen.getByText('Password must be at least 8 characters long.')).toBeInTheDocument();
    });
});
