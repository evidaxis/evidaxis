import { getViteConfig } from 'astro/config';

// Astro's renderer tests the actual B component without a browser or listener.
export default getViteConfig({
  server: { hmr: false },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
    // Census tests walk every archived system, and the archive grows weekly.
    // The 5 s default failed on a shared CI runner on 18.10 (6,324 systems);
    // 60 s still catches a hang.
    testTimeout: 60_000,
  },
}, { configFile: false, integrations: [] });
