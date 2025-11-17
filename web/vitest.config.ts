import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
    plugins: [react()],
    test: {
        globals: true,
        environment: 'jsdom',
        environmentOptions: {
            jsdom: {
                url: 'http://localhost/',
                localStorage: {},
                sessionStorage: {},
            },
        },
        setupFiles: './src/test/setup.ts',
        css: true,
        threads: {
            singleThread: true,
        },
    },
});
