// Writers run beside the event they attest. A skipped retry emits nothing;
// only another receipt can overwrite a failed publication context.
import { appendFileSync } from 'node:fs';
import { expectedSnapshot } from './deploy-receipt.mjs';
import { execFileSync, spawnSync } from 'node:child_process';
import { pathToFileURL } from 'node:url';
import { githubJson, snapshotCommit } from './release-record.mjs';
import { RELEASE_CONTEXTS } from './weekly-release.mjs';

const STEP_NAMES = {
  secrets: 'Require Vercel secrets',
  node: 'Set up Node',
  build: 'Build the static site from the committed tree',
  deploy: 'Deploy prebuilt dist to Vercel production',
  receipt: 'Verify prod serves the snapshot this tree holds',
  hf: 'Mirror the dated snapshot to HF and verify public contents',
};

export function stageResult(stage, steps) {
  const ids = stage === 'deployed' ? ['secrets', 'node', 'build', 'deploy', 'receipt'] : ['hf'];
  const receipt = ids.at(-1);
  if (steps[receipt]?.outcome === 'success') return { state: 'success', description: STEP_NAMES[receipt] };
  const failure = ids.find(id => ['failure', 'cancelled'].includes(steps[id]?.outcome));
  return failure ? { state: 'failure', description: STEP_NAMES[failure] } : null;
}

export async function writeReleaseStatus({ sha, date, stage, state, description }, post = githubJson, env = process.env) {
  if (env.MODE === 'rehearsal') throw new Error('Rehearsal cannot write release statuses');
  if (!/^[a-f0-9]{40}$/.test(sha) || !/^\d{4}-\d{2}-\d{2}$/.test(date) ||
      !RELEASE_CONTEXTS.includes(stage) || !['success', 'failure'].includes(state) ||
      typeof description !== 'string' || !description.trim() || description.length > 140 ||
      (stage === 'captured' && (state !== 'success' || description !== date))) {
    throw new Error('Invalid release status write');
  }
  await post(`statuses/${sha}`, { context: `evidaxis/release-${stage}`, state, description,
    target_url: `https://github.com/${env.GITHUB_REPOSITORY}/actions/runs/${env.GITHUB_RUN_ID}` });
}

export async function releaseTarget(date, get = githubJson) {
  date = expectedSnapshot(date).snapshot_date;
  // A later main commit must not move the receipt away from the deployed tree.
  const ref = execFileSync('git', ['rev-parse', 'HEAD'], { encoding: 'utf8' }).trim();
  const sha = await snapshotCommit(date, get, ref);
  if (!sha) throw new Error('Snapshot commit missing');
  return { date, sha };
}

export async function mirrorSnapshot(date, { target = releaseTarget, run = spawnSync, write = writeReleaseStatus } = {}) {
  const release = await target(date);
  const result = run('python3', ['scripts/hf_upload_snapshot.py', '--date', date], { stdio: 'inherit' });
  await write({ ...release, stage: 'hf', state: result.status === 0 ? 'success' : 'failure',
    description: STEP_NAMES.hf });
  if (result.status !== 0) throw new Error('HF publication failed');
}

async function main() {
  const [command, argument] = process.argv.slice(2);
  // Guard before any subprocess as well as at the API write boundary.
  if (process.env.MODE === 'rehearsal') throw new Error('Rehearsal cannot publish');
  if (command === 'prepare' || command === 'capture') {
    const release = await releaseTarget(argument);
    if (process.env.GITHUB_OUTPUT) appendFileSync(process.env.GITHUB_OUTPUT, `date=${release.date}\nsha=${release.sha}\n`);
    if (command === 'capture') await writeReleaseStatus({ ...release, stage: 'captured', state: 'success', description: release.date });
  } else if (command === 'record' && ['deployed', 'hf'].includes(argument)) {
    const result = stageResult(argument, JSON.parse(process.env.RELEASE_STEPS));
    if (result) await writeReleaseStatus({ sha: process.env.RELEASE_SHA, date: process.env.RELEASE_DATE, stage: argument, ...result });
  } else if (command === 'hf') {
    await mirrorSnapshot(argument);
  } else {
    throw new Error('Use prepare [date], capture date, record deployed|hf, or hf date');
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
