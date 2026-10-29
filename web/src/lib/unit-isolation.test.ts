import { afterAll, afterEach, expect, it } from 'vitest';
import fs from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { promisify } from 'node:util';
import { pathToFileURL } from 'node:url';
import { exec, execSync, execFile, execFileSync, fork, spawn, spawnSync } from 'node:child_process';
import { dataPath, REPO_ROOT } from './data-path';

const forbidden = /Hermetic unit test: live data\/ or etl\/ access forbidden/;
const temp = fs.mkdtempSync(join(tmpdir(), 'evx-isolation-'));
afterAll(() => fs.rmSync(temp, { recursive: true, force: true }));
afterEach(() => {
  for (const name of fs.readdirSync(temp)) fs.rmSync(join(temp, name), { recursive: true, force: true });
});

it.each(['copyFileSync', 'cpSync'] as const)('guards the source of fs.%s', name => {
  expect(() => fs[name](join(REPO_ROOT, 'data/latest.json'), join(temp, 'copy.json'))).toThrow(forbidden);
});
it.each(['copyFile', 'cp'] as const)('guards callback and promise fs.%s', async name => {
  const source = join(REPO_ROOT, 'data/latest.json'), dest = join(temp, 'copy.json');
  await expect(async () => promisify(fs[name])(source, dest)).rejects.toThrow(forbidden);
  await expect(async () => fs.promises[name](source, dest)).rejects.toThrow(forbidden);
});
it.each(['lstatSync', 'realpathSync', 'readlinkSync', 'statfsSync'] as const)('guards fs.%s metadata reads', name => {
  expect(() => fs[name](join(REPO_ROOT, 'data'))).toThrow(forbidden);
});
it.each(['lstat', 'realpath', 'readlink', 'statfs', 'stat', 'readdir', 'opendir'] as const)('guards callback and promise fs.%s', async name => {
  const source = join(REPO_ROOT, 'etl');
  await expect(async () => promisify(fs[name] as any)(source)).rejects.toThrow(forbidden);
  await expect(async () => fs.promises[name](source)).rejects.toThrow(forbidden);
});
it('guards realpath.native and promise watchers too', () => {
  expect(() => fs.realpathSync.native(join(REPO_ROOT, 'data'))).toThrow(forbidden);
  expect(() => fs.promises.watch(join(REPO_ROOT, 'etl'))).toThrow(forbidden);
});
it('guards Blob reads and forbids native glob traversal', async () => {
  if (typeof fs.openAsBlob === 'function') {
    await expect(async () => fs.openAsBlob(join(REPO_ROOT, 'data/latest.json'))).rejects.toThrow(forbidden);
  }
  if (typeof fs.globSync === 'function') {
    expect(() => fs.globSync('data/**', { cwd: REPO_ROOT })).toThrow(/fs.glob traversal is forbidden/);
    expect(() => fs.promises.glob('data/**', { cwd: REPO_ROOT })).toThrow(/fs.glob traversal is forbidden/);
  }
});
it('rejects a live symlink encountered below a permitted cp source', async () => {
  const source = join(temp, 'source');
  fs.mkdirSync(source);
  fs.symlinkSync(join(REPO_ROOT, 'data/latest.json'), join(source, 'link'));
  await expect(async () => fs.promises.cp(source, join(temp, 'dest'), { recursive: true, dereference: true })).rejects.toThrow(forbidden);
});
it.each(['watch', 'watchFile'] as const)('guards fs.%s', name => {
  const source = join(REPO_ROOT, 'data/latest.json');
  expect(() => {
    const watcher = fs[name](source, () => {});
    if (name === 'watch') (watcher as fs.FSWatcher).close();
    else fs.unwatchFile(source);
  }).toThrow(forbidden);
});
it('allows fixture copies', async () => {
  await fs.promises.copyFile(dataPath('latest.json'), join(temp, 'copy.json'));
  expect(JSON.parse(fs.readFileSync(join(temp, 'copy.json'), 'utf8')).snapshot_date).toBe('2026-10-17');
});
it('installs the same guard in a child even with an explicit empty environment', () => {
  const run = spawnSync(process.execPath, ['-e', 'require("node:fs").readFileSync(process.argv[1])', join(REPO_ROOT, 'data/latest.json')], {
    encoding: 'utf8', env: {},
  });
  expect(run.status).not.toBe(0);
  expect(run.stderr).toMatch(forbidden);
});
it('lets child scripts read fixtures', () => {
  const run = spawnSync(process.execPath, ['-e', 'process.stdout.write(require("node:fs").readFileSync(process.argv[1]))', dataPath('latest.json')], { encoding: 'utf8' });
  expect(run.status).toBe(0);
  expect(JSON.parse(run.stdout).snapshot_date).toBe('2026-10-17');
});
it('guards live JSON module imports in child scripts', () => {
  const url = pathToFileURL(join(REPO_ROOT, 'data/latest.json')).href;
  const run = spawnSync(process.execPath, ['--input-type=module', '-e',
    `await import(${JSON.stringify(url)}, { with: { type: 'json' } });`], { encoding: 'utf8' });
  expect(run.status).not.toBe(0);
  // With live data hidden, Node rejects the URL during module resolution,
  // before the guarded fs reader runs. Neither case may return the live JSON.
  expect(run.stderr).toMatch(/Hermetic unit test: live data\/ or etl\/ access forbidden|ERR_MODULE_NOT_FOUND/);
});
it('guards grandchildren and rejects preloads that would execute before the guard', () => {
  const script = join(temp, 'preload.cjs');
  fs.writeFileSync(script, `require('node:fs').readFileSync(${JSON.stringify(join(REPO_ROOT, 'etl/owner_types.json'))});`);
  expect(() => spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8', env: { NODE_OPTIONS: `--require=${script}` } })).toThrow(/--require preloads/);
  expect(() => spawnSync(process.execPath, ['--require', script, '-e', ''])).toThrow(/--require preloads/);
  const preloaded = spawnSync(process.execPath, ['-e', ''], { encoding: 'utf8', env: { NODE_OPTIONS: `--import=${script}` } });
  expect(preloaded.status).not.toBe(0);
  expect(preloaded.stderr).toMatch(forbidden);
  const grandchild = spawnSync(process.execPath, ['-e', `const r = require('node:child_process').spawnSync(process.execPath, [${JSON.stringify(script)}], { encoding: 'utf8', env: {} }); process.stderr.write(r.stderr); process.exit(r.status);`], { encoding: 'utf8' });
  expect(grandchild.status).not.toBe(0);
  expect(grandchild.stderr).toMatch(forbidden);
});
it('supports async Node scripts and guards fork and execFile entry points', async () => {
  const source = join(temp, 'read.cjs');
  fs.writeFileSync(source, 'process.stdout.write(require("node:fs").readFileSync(process.argv[2]));');
  const result = await new Promise<string>((resolve, reject) => execFile(process.execPath, [source, dataPath('latest.json')], { encoding: 'utf8' }, (err, stdout) => err ? reject(err) : resolve(stdout)));
  expect(JSON.parse(result).snapshot_date).toBe('2026-10-17');
  expect(() => execFileSync(process.execPath, [source, join(REPO_ROOT, 'etl/owner_types.json')], { stdio: 'pipe' })).toThrow(forbidden);
  for (const launch of [() => spawn(process.execPath, [source, join(REPO_ROOT, 'data/latest.json')]),
    () => fork(source, [join(REPO_ROOT, 'data/latest.json')], { silent: true, execArgv: [] })]) {
    const child = launch();
    let stderr = '';
    child.stderr!.on('data', chunk => { stderr += chunk; });
    const code = await new Promise(resolve => child.on('close', resolve));
    expect(code).not.toBe(0);
    expect(stderr).toMatch(forbidden);
  }
});
it('forbids unguarded shell and non-Node child processes', () => {
  expect(() => exec('echo test')).toThrow(/shell child processes are forbidden/);
  expect(() => execSync('echo test')).toThrow(/shell child processes are forbidden/);
  expect(() => spawnSync('sh', ['-c', 'echo test'])).toThrow(/only guarded Node/);
  expect(() => spawnSync(process.execPath, ['-e', ''], { shell: true })).toThrow(/only guarded Node/);
});
