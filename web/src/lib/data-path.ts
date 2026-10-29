import { join, resolve } from 'node:path';
import { REPO_ROOT, assertUnitPath } from './path-policy.mjs';

export { REPO_ROOT, assertUnitPath };
// A preview must switch all archive readers together, including history and custody.
export const DATA_DIR = assertUnitPath(resolve(process.env.EVIDAXIS_DATA_DIR ?? join(REPO_ROOT, 'data')));
export const ETL_DIR = assertUnitPath(resolve(process.env.EVIDAXIS_ETL_DIR ?? join(REPO_ROOT, 'etl')));
export const dataPath = (...parts: string[]) => assertUnitPath(join(DATA_DIR, ...parts));
export const etlPath = (...parts: string[]) => assertUnitPath(join(ETL_DIR, ...parts));
export const repoDataPath = (repoRoot: string, ...parts: string[]) =>
  resolve(repoRoot) === resolve(REPO_ROOT) ? dataPath(...parts) : assertUnitPath(join(repoRoot, 'data', ...parts));
export const repoEtlPath = (repoRoot: string, ...parts: string[]) =>
  resolve(repoRoot) === resolve(REPO_ROOT) ? etlPath(...parts) : assertUnitPath(join(repoRoot, 'etl', ...parts));
