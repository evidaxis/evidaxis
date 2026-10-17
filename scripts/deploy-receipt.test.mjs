import test from 'node:test';
import assert from 'node:assert/strict';
import { verifyReceipt } from './deploy-receipt.mjs';
import { deploy, transportFailure } from './vercel-deploy.mjs';

const expected = { snapshot_date: '2026-10-24', methodology_version: 'm5' };

test('receipt accepts the dated public projection', () => {
  assert.deepEqual(verifyReceipt(expected, JSON.stringify({ ...expected, entities: [] })), expected);
});

test('receipt rejects stale date, wrong methodology, missing fields and HTML with HTTP 200', () => {
  for (const body of [JSON.stringify({ ...expected, snapshot_date: '2026-10-17' }),
    JSON.stringify({ ...expected, methodology_version: 'm4' }), '{}', 'null', '<html>old site</html>']) {
    assert.throws(() => verifyReceipt(expected, body));
  }
  assert.throws(() => verifyReceipt({}, '{}'));
});

test('deployment retries transport once and keeps both CLI streams private', () => {
  const logs = [];
  const oldLog = console.log;
  console.log = line => logs.push(line);
  try {
    let calls = 0;
    deploy((command, args, options) => {
      assert.equal(command, 'npx');
      assert.ok(args.includes('vercel@64.5.0'));
      assert.deepEqual(options.stdio, ['ignore', 'pipe', 'pipe']);
      calls++;
      return calls === 1 ? { status: 1, stderr: 'ECONNRESET secret-preview.vercel.app' }
        : { status: 0, stdout: 'https://secret-preview.vercel.app' };
    });
    assert.equal(calls, 2);
    assert.ok(logs.every(line => !line.includes('vercel.app')));
  } finally { console.log = oldLog; }
});

test('deployment fails configuration immediately and stops after the second transport failure', () => {
  for (const [error, count] of [['Invalid token', 1], ['ETIMEDOUT', 2]]) {
    let calls = 0;
    assert.throws(() => deploy(() => { calls++; return { status: 1, stderr: error }; }), /deployment failed/);
    assert.equal(calls, count);
  }
  assert.equal(transportFailure('EAI_AGAIN'), true);
  assert.equal(transportFailure('build failed'), false);
});
