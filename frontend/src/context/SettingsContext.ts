import { createContext } from 'react';

export interface SettingsContextType {
    apiKey: string;
    setApiKey: (key: string) => void;
    serperKey: string;
    setSerperKey: (key: string) => void;
}

export const SettingsContext = createContext<SettingsContextType | undefined>(undefined);
