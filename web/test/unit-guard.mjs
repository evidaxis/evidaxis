import fs from 'node:fs';
import children from 'node:child_process';
import { syncBuiltinESMExports } from 'node:module';
import { assertUnitPath } from '../src/lib/path-policy.mjs';

// The same preload runs in Vitest workers and Node descendants. Capture the
// policy's native realpath/readlink before replacing the public fs entry points.
const installed = Symbol.for('evidaxis.unit-guard');
function protect(api, names) {
  for (const name of names) {
    const original = api[name];
    if (typeof original !== 'function' || original[installed]) continue;
    const guarded = (path, ...args) => {
      if (typeof path !== 'number') assertUnitPath(path);
      if (name === 'cp' || name === 'cpSync') {
        // cp can reach live files below an otherwise permitted source directory.
        const options = args[1] && typeof args[1] === 'object' ? args[1] : {};
        const filter = options.filter;
        if (typeof args[1] === 'function') args.splice(1, 0, {});
        args[1] = { ...options, filter(source, destination) {
          assertUnitPath(source);
          return filter ? filter(source, destination) : true;
        } };
      }
      return original(path, ...args);
    };
    Object.defineProperty(guarded, installed, { value: true });
    if (original.native) {
      guarded.native = (path, ...args) => { assertUnitPath(path); return original.native(path, ...args); };
    }
    api[name] = guarded;
  }
}
protect(fs, ['readFileSync', 'readFile', 'readdirSync', 'readdir', 'openSync', 'open',
  'createReadStream', 'openAsBlob', 'existsSync', 'exists', 'statSync', 'stat', 'lstatSync', 'lstat',
  'statfsSync', 'statfs', 'accessSync', 'access', 'opendirSync', 'opendir',
  'readlinkSync', 'readlink', 'realpathSync', 'realpath', 'watch', 'watchFile',
  'copyFileSync', 'copyFile', 'cpSync', 'cp']);
protect(fs.promises, ['readFile', 'readdir', 'open', 'stat', 'lstat', 'statfs', 'access',
  'opendir', 'readlink', 'realpath', 'watch', 'copyFile', 'cp']);
// Native glob expands wildcards/cwd internally, bypassing per-path fs wrappers.
// Tests can enumerate fixture directories through the guarded readdir instead.
for (const api of [fs, fs.promises]) for (const name of ['glob', 'globSync']) {
  if (typeof api[name] === 'function') api[name] = () => {
    throw new Error('Hermetic unit test: fs.glob traversal is forbidden; use guarded readdir');
  };
}

const preload = new URL('./unit-guard.mjs', import.meta.url).href;
const requirePreload = /(?:^|\s)["']?(?:--require(?:\b|=)|-r)/;
function assertPreloads(args, options) {
  // Node executes --require before every --import, regardless of flag order.
  if (args.some(arg => /^--require(?:=|$)|^-r/.test(arg))
    || requirePreload.test((options.env ?? process.env).NODE_OPTIONS ?? '')) {
    throw new Error('Hermetic unit test: --require preloads run before the guard and are forbidden');
  }
}
const childEnv = options => {
  const env = options.env ?? process.env;
  const first = `--import=${preload}`;
  const nodeOptions = env.NODE_OPTIONS ?? '';
  return { ...options, env: { ...env, EVIDAXIS_UNIT_TEST: '1',
    // Environment preloads run before CLI preloads; the guard must run first.
    NODE_OPTIONS: nodeOptions.startsWith(first) ? nodeOptions : `${first} ${nodeOptions}`.trim(),
  } };
};
function assertNode(command, options) {
  if (![process.execPath, 'node'].includes(command) || options.shell) {
    throw new Error('Hermetic unit test: only guarded Node child processes are allowed; use the data suite for shell commands');
  }
}
for (const name of ['spawn', 'spawnSync', 'execFile', 'execFileSync']) {
  const original = children[name];
  if (original[installed]) continue;
  const guarded = (command, ...rest) => {
    const args = Array.isArray(rest[0]) ? rest.shift() : [];
    const options = rest[0] && typeof rest[0] === 'object' ? rest.shift() : {};
    assertNode(command, options);
    assertPreloads(args, options);
    return original(process.execPath, ['--import', preload, ...args], childEnv(options), ...rest);
  };
  Object.defineProperty(guarded, installed, { value: true });
  children[name] = guarded;
}
const fork = children.fork;
if (!fork[installed]) {
  const guarded = (modulePath, ...rest) => {
    const args = Array.isArray(rest[0]) ? rest.shift() : [];
    const options = rest[0] ?? {};
    assertNode(options.execPath ?? process.execPath, options);
    assertPreloads(options.execArgv ?? process.execArgv, options);
    return fork(modulePath, args, childEnv({ ...options,
      execArgv: ['--import', preload, ...(options.execArgv ?? process.execArgv)],
    }));
  };
  Object.defineProperty(guarded, installed, { value: true });
  children.fork = guarded;
}
for (const name of ['exec', 'execSync']) children[name] = () => {
  throw new Error('Hermetic unit test: shell child processes are forbidden; use guarded Node scripts or the data suite');
};
syncBuiltinESMExports();
