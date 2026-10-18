import { test } from 'node:test';
import assert from 'node:assert/strict';
import { failedStepName, rehearsalAlertText, rehearsalFailureText } from './rehearsal-alert.mjs';

const step = 'Verify the site against this rehearsal candidate';
const runUrl = 'https://github.com/evidaxis/evidaxis/actions/runs/99';

test('the keeper line names the failed step and the run link', () => {
  const text = rehearsalFailureText({ date: '2026-10-17', step, runUrl });
  assert.equal(
    text,
    'Репетиция субботы 2026-10-17 упала на шаге «Verify the site against this rehearsal candidate». ' +
      'Выпуск не задет; до субботы есть время починить. https://github.com/evidaxis/evidaxis/actions/runs/99',
  );
  assert.equal(text.includes(step), true);
  assert.equal(text.includes(runUrl), true);
});

test('the keeper line has no publication address', () => {
  const text = rehearsalAlertText({
    date: '2026-10-17',
    runUrl,
    jobs: { jobs: [{ steps: [{ name: 'Collect snapshot', conclusion: 'success' }, { name: step, conclusion: 'failure' }] }] },
  });
  assert.equal(text.includes(step), true);
  assert.equal(text.includes(runUrl), true);
  for (const host of ['vercel.com', 'huggingface.co', 'evidaxis.org', 'zenodo.org']) {
    assert.equal(text.includes(host), false, host);
  }
});

test('a missing jobs payload still produces a line without a publication address', () => {
  const text = rehearsalAlertText({ date: '2026-10-17', jobs: null, runUrl });
  assert.equal(text.includes('«неизвестен»'), true);
  assert.equal(text.includes(runUrl), true);
  assert.equal(text.includes('huggingface.co'), false);
});

test('the failed step is the first conclusion failure', () => {
  const name = failedStepName({
    jobs: [{ steps: [{ name: 'Collect snapshot', conclusion: 'success' }, { name: step, conclusion: 'failure' }] }],
  });
  assert.equal(name, step);
  assert.equal(failedStepName({ jobs: [] }), '');
});
