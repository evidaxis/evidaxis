import { readFileSync } from 'node:fs';
import { pathToFileURL } from 'node:url';

export function verifyReceipt(expected, body) {
  const actual = JSON.parse(body);
  for (const field of ['snapshot_date', 'methodology_version']) {
    if (typeof expected[field] !== 'string' || !expected[field] || actual?.[field] !== expected[field]) {
      throw new Error(`publication receipt mismatch: ${field}`);
    }
  }
  return { snapshot_date: actual.snapshot_date, methodology_version: actual.methodology_version };
}

export function expectedSnapshot(date) {
  date ||= JSON.parse(readFileSync('data/latest.json', 'utf8')).snapshot_date;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date)) throw new Error('Invalid receipt date');
  const expected = JSON.parse(readFileSync(`data/snapshots/${date}/snapshot.json`, 'utf8'));
  if (expected.snapshot_date !== date) throw new Error('Receipt date mismatch');
  return expected;
}

async function main() {
  const expected = expectedSnapshot(process.env.RELEASE_DATE);
  const url = `https://evidaxis.org/snapshots/${expected.snapshot_date}/snapshot.json`;
  // Preserve the existing twelve observations and fifteen-second propagation interval.
  for (let attempt = 1; attempt <= 12; attempt++) {
    try {
      const response = await fetch(url, { headers: { 'cache-control': 'no-cache' } });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      verifyReceipt(expected, await response.text());
      for (const path of ['/coverage/power/', '/feed.atom']) {
        const extra = await fetch(`https://evidaxis.org${path}`, { headers: { 'cache-control': 'no-cache' } });
        if (!extra.ok) throw new Error(`${path}: HTTP ${extra.status}`);
        await extra.arrayBuffer();
      }
      console.log(`Site receipt: ${expected.snapshot_date} ${expected.methodology_version}`);
      return;
    } catch {
      console.log(`receipt attempt ${attempt}: content not yet verified`);
      await new Promise(resolve => setTimeout(resolve, 15000));
    }
  }
  throw new Error('production content receipt failed');
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch(error => { console.error(error.message); process.exitCode = 1; });
}
