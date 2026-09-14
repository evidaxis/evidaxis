import { join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

export const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
// A preview must switch all archive readers together, including history and custody.
export const DATA_DIR = resolve(process.env.EVIDAXIS_DATA_DIR ?? join(REPO_ROOT, 'data'));
export const dataPath = (...parts: string[]) => join(DATA_DIR, ...parts);
export const repoDataPath = (repoRoot: string, ...parts: string[]) =>
  repoRoot === REPO_ROOT ? dataPath(...parts) : join(repoRoot, 'data', ...parts);
