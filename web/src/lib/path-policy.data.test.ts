import { expect, it } from 'vitest';
import { copyFileSync, mkdirSync, mkdtempSync, rmSync, symlinkSync } from 'node:fs';
import { join } from 'node:path';
import { tmpdir } from 'node:os';
import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

it.each(['data', 'etl'])('rejects a default %s symlink to fixtures with both env overrides unset', dir => {
  const root = mkdtempSync(join(tmpdir(), 'evx-production-path-'));
  try {
    const lib = join(root, 'web/src/lib');
    const fixture = join(root, 'web/test-fixtures/frozen', dir);
    mkdirSync(lib, { recursive: true });
    mkdirSync(fixture, { recursive: true });
    copyFileSync(new URL('./path-policy.mjs', import.meta.url), join(lib, 'path-policy.mjs'));
    symlinkSync(fixture, join(root, dir));
    const env = { ...process.env };
    delete env.EVIDAXIS_DATA_DIR;
    delete env.EVIDAXIS_ETL_DIR;
    const run = spawnSync(process.execPath, ['--input-type=module', '-e',
      `import { assertProductionPaths } from ${JSON.stringify(pathToFileURL(join(lib, 'path-policy.mjs')).href)}; assertProductionPaths();`], { env, encoding: 'utf8' });
    expect(run.status).not.toBe(0);
    expect(run.stderr).toContain(`Production fixture guard: EVIDAXIS_${dir.toUpperCase()}_DIR`);
  } finally { rmSync(root, { recursive: true, force: true }); }
});
