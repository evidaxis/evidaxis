import { getViteConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';

// This suite always checks the real archive, even if the caller has preview env.
const env = {
  EVIDAXIS_UNIT_TEST: '0',
  EVIDAXIS_DATA_DIR: fileURLToPath(new URL('../data/', import.meta.url)),
  EVIDAXIS_ETL_DIR: fileURLToPath(new URL('../etl/', import.meta.url)),
};
Object.assign(process.env, env);

export default getViteConfig({
  server: { hmr: false },
  test: {
    env,
    environment: 'node',
    include: ['src/**/*.data.test.ts'],
    // Census tests walk every archived system; retain the existing CI timeout.
    testTimeout: 60_000,
  },
}, { configFile: false, integrations: [] });
