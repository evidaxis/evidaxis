import { getViteConfig } from 'astro/config';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { assertUnitPath } from './src/lib/path-policy.mjs';

const fixture = fileURLToPath(new URL('./test-fixtures/2026-10-17/', import.meta.url));
const env = {
  EVIDAXIS_UNIT_TEST: '1',
  EVIDAXIS_DATA_DIR: resolve(fixture, 'data'),
  EVIDAXIS_ETL_DIR: resolve(fixture, 'etl'),
};
Object.assign(process.env, env);

// Astro's renderer tests the actual B component without a browser or listener.
export default getViteConfig({
  plugins: [{
    name: 'hermetic-unit-imports',
    enforce: 'pre',
    resolveId(id, importer) {
      // JSON imports bypass the test worker's fs mocks; stop them in Vite too.
      if (id.startsWith('/') || (id.startsWith('.') && importer)) {
        assertUnitPath(resolve(importer ? dirname(importer) : '.', id.split('?')[0]));
      }
      return null;
    },
    load(id) {
      // Also check resolved IDs after Vite aliases have been applied.
      if (id.startsWith('/')) assertUnitPath(id.split('?')[0]);
      return null;
    },
  }],
  server: { hmr: false },
  test: {
    env,
    environment: 'node',
    include: ['src/**/*.test.ts'],
    exclude: ['src/**/*.data.test.ts'],
    setupFiles: ['./test/unit-setup.ts'],
    // Keep the existing timeout for Astro rendering on shared CI runners.
    testTimeout: 60_000,
  },
}, { configFile: false, integrations: [] });
