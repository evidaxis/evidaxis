import { getViteConfig } from 'astro/config';

// Astro's renderer tests the actual B component without a browser or listener.
export default getViteConfig({
  server: { hmr: false },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
}, { configFile: false, integrations: [] });
