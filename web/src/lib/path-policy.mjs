import { readlinkSync, realpathSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

export const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
export const FIXTURE_ROOT = join(REPO_ROOT, 'web', 'test-fixtures');
// Keep native references: the unit guard also protects public realpath/readlink.
const nativeRealpath = realpathSync;
const nativeReadlink = readlinkSync;

// Resolve existing ancestors too: a missing file inside a symlink is still inside
// its target. Lexical checks also work when the live directories are hidden.
function canonical(path) {
  try { return nativeRealpath(path); } catch (error) {
    if (!['ENOENT', 'ENOTDIR'].includes(error.code)) throw error;
    const parent = dirname(path);
    // A dangling link can target live data while that directory is hidden.
    let target;
    try { target = nativeReadlink(path); } catch (linkError) {
      if (!['ENOENT', 'ENOTDIR', 'EINVAL'].includes(linkError.code)) throw linkError;
    }
    if (target) return canonical(resolve(parent, target));
    return parent === path ? path : join(canonical(parent), relative(parent, path));
  }
}

function within(path, root) {
  const rel = relative(root, path);
  return rel === '' || (rel !== '..' && !rel.startsWith(`..${sep}`) && !rel.startsWith(sep));
}

export function isInside(path, root) {
  const absolute = resolve(path instanceof URL ? fileURLToPath(path) : String(path));
  return within(absolute, resolve(root)) || within(canonical(absolute), canonical(resolve(root)));
}

export function assertUnitPath(path) {
  if (process.env.EVIDAXIS_UNIT_TEST === '1'
    && ['data', 'etl'].some(dir => isInside(path, join(REPO_ROOT, dir)))) {
    throw new Error(`Hermetic unit test: live data/ or etl/ access forbidden: ${path}`);
  }
  return path;
}

export function assertProductionPaths() {
  for (const key of ['EVIDAXIS_DATA_DIR', 'EVIDAXIS_ETL_DIR']) {
    const path = process.env[key] || join(REPO_ROOT, key === 'EVIDAXIS_DATA_DIR' ? 'data' : 'etl');
    if (isInside(path, FIXTURE_ROOT)) {
      throw new Error(`Production fixture guard: ${key} points inside web/test-fixtures/`);
    }
  }
}
