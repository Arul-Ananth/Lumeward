import { useContext } from 'react';

import { AuthContext } from '../context/AuthContext';
import type { AuthContextValue } from '../features/auth/types';

export function useAuth(): AuthContextValue {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
