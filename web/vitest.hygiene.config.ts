import { getViteConfig } from 'astro/config';
import { fileURLToPath } from 'node:url';

// Same live archive as the data suite. These checks are hygiene, not the publication gate.
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
    include: ['src/**/*.hygiene.test.ts'],
    // An empty hygiene suite is a missing check, not a pass.
    passWithNoTests: false,
    // Same bound as the data suite: the checks walk the frozen fixture and the live registry.
    testTimeout: 60_000,
  },
}, { configFile: false, integrations: [] });
