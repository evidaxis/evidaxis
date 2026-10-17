import { spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';

export function transportFailure(text) {
  return /\b(ECONNRESET|ETIMEDOUT|ECONNREFUSED|EAI_AGAIN|ENOTFOUND|UND_ERR_CONNECT_TIMEOUT)\b|fetch failed|socket hang up|network (?:error|timeout)|HTTP (?:502|503|504)\b/i.test(text);
}

export function deploy(run = spawnSync) {
  // One transport retry is allowed; configuration and build failures stop immediately.
  for (let attempt = 1; attempt <= 2; attempt++) {
    const result = run('npx', ['--yes', 'vercel@48.2.9', 'deploy', '--prod', '--yes', '--archive=tgz', '--token', process.env.VERCEL_TOKEN],
      { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    // CLI output includes private deployment hostnames; neither stream belongs in public logs.
    if (result.status === 0) {
      console.log('Vercel deployment completed; checking the public content next.');
      return;
    }
    if (attempt === 1 && transportFailure(`${result.stdout || ''}\n${result.stderr || ''}\n${result.error?.code || ''}`)) {
      console.log('Vercel transport failed; retrying once.');
      continue;
    }
    throw new Error(`Vercel deployment failed (attempt ${attempt}, exit ${result.status ?? 'unavailable'}); CLI output withheld.`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try { deploy(); } catch (error) { console.error(error.message); process.exitCode = 1; }
}
