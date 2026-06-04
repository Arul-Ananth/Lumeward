import { createContext } from 'react';

import type { AuthContextValue } from '../features/auth/types';

export const AuthContext = createContext<AuthContextValue | undefined>(undefined);
