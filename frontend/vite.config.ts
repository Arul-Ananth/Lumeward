import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    build: {
        rollupOptions: {
            output: {
                manualChunks(id) {
                    if (id.includes('node_modules')) {
                        if (id.includes('@mui/icons-material')) {
                            return 'icons';
                        }
                        if (id.includes('@mui/material') || id.includes('@emotion/react') || id.includes('@emotion/styled')) {
                            return 'mui-vendor';
                        }
                        if (id.includes('react-markdown')) {
                            return 'markdown';
                        }
                        if (id.includes('react-dom') || id.includes('react-router-dom') || /node_modules[\\/](react|scheduler)[\\/]/.test(id)) {
                            return 'react-vendor';
                        }
                    }
                },
            },
        },
    },
    server: {
        port: 5173,
        strictPort: true,
        watch: {
            ignored: ['**/lumeward.db', '**/lumeward.db-journal', '**/qdrant_data/**'],
        },
    },
});
