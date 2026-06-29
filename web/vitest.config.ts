import { defineConfig } from 'vitest/config';

// Minimal Vitest config for the pure lib layer (charts.ts, derived.ts).
// Node environment: these modules are DOM-free by design.
export default defineConfig({
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
});
