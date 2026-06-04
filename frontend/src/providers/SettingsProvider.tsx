import { useCallback, useMemo, useState, type ReactNode } from 'react';

import { SettingsContext } from '../context/SettingsContext';

function usePersistedSetting(storageKey: string, initialValue = '') {
    const [value, setValue] = useState(() => localStorage.getItem(storageKey) || initialValue);

    const updateValue = useCallback((nextValue: string) => {
        setValue(nextValue);
        localStorage.setItem(storageKey, nextValue);
    }, [storageKey]);

    return [value, updateValue] as const;
}

export function SettingsProvider({ children }: { children: ReactNode }) {
    const [apiKey, setApiKey] = usePersistedSetting('userArgs_apiKey');
    const [serperKey, setSerperKey] = usePersistedSetting('userArgs_serperKey');

    const value = useMemo(
        () => ({
            apiKey,
            setApiKey,
            serperKey,
            setSerperKey,
        }),
        [apiKey, setApiKey, serperKey, setSerperKey],
    );

    return <SettingsContext.Provider value={value}>{children}</SettingsContext.Provider>;
}
