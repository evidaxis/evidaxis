import { getViteConfig } from 'astro/config';

// Astro's renderer tests the actual B component without a browser or listener.
export default getViteConfig({
  server: {
    hmr: false,
    // A worktree may symlink node_modules outside the project root. Vite then
    // refuses those real paths unless the sandbox is open.
    fs: { strict: false },
  },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
}, { configFile: false, integrations: [] });
