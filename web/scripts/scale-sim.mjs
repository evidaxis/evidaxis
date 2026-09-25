#!/usr/bin/env node
import { createHash } from 'node:crypto';
import {
  cpSync,
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs';
import { tmpdir } from 'node:os';
import { basename, dirname, join, relative, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const WEB_ROOT = resolve(new URL('..', import.meta.url).pathname);
const REPO_ROOT = resolve(WEB_ROOT, '..');
const SOURCE_DATA = join(REPO_ROOT, 'data');
const REPORT = join(WEB_ROOT, 'scale-sim-report.md');
const SOURCE_DATE = '2026-09-19';
const SIM_DATE = '2026-09-26';
const SYNTHETIC_COUNT = 5_705;
const CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
const label = (process.argv[2] ?? 'current').toLowerCase().replace(/[^a-z0-9_-]+/g, '-');

const readJson = (path) => JSON.parse(readFileSync(path, 'utf8'));
const jsonBytes = (value) => `${JSON.stringify(value, null, 2)}\n`;
const sha256 = (bytes) => createHash('sha256').update(bytes).digest('hex');
const formatBytes = (bytes) => {
  const units = ['B', 'KB', 'MB', 'GB'];
  let value = bytes, unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value.toFixed(unit === 0 ? 0 : 2)} ${units[unit]}`;
};

function crockford(value) {
  let n = BigInt(value), out = '';
  do {
    out = CROCKFORD[Number(n % 32n)] + out;
    n /= 32n;
  } while (n > 0n);
  return out.padStart(11, '0').slice(-11);
}

function syntheticSeries(index) {
  const base = 2 + (index % 13);
  return Array.from({ length: 52 }, (_, week) =>
    base + Math.floor(week / 9) + ((index * 7 + week * 5) % 8));
}

function syntheticEntity(index, id, series) {
  const recent = series.slice(-12).reduce((sum, value) => sum + value, 0) / 12;
  const suffix = String(index + 1).padStart(4, '0');
  return {
    entity_id: id,
    name: `Sim Engine ${suffix}`,
    slug: `sim-engine-${suffix}`,
    entity_type: 'repo',
    homepage: null,
    // A classified organization repository keeps the publication projection
    // active without changing the real owner registry during this temp-only run.
    github_repo: 'tensorflow/tensorflow',
    openalex_work_ids: [],
    industry: 'unassigned',
    sub_niche: 'unassigned-v1',
    cohort: 'unassigned-v1',
    axes: {
      github_commit_velocity: {
        slope: 0.004 + (index % 17) / 1000,
        cohort_z: ((index % 9) - 4) / 2,
        recent_weekly_commits: recent,
        stars_not_scored: 25 + (index * 37) % 8000,
      },
      openalex_citation_momentum: {
        status: 'absent', slope: null, cohort_z: null, total_citations: 0,
        by_year: null, proxy: null,
      },
      deps_direct_dependents_momentum: {
        status: 'out_of_panel', slope: null, theil_sen: null, cohort_z: null,
        latest: null, points: null, points_reconstructable: null,
        as_of_partition: null, unstable: null, rising_vote: false,
      },
    },
    momentum: 50 + (index % 41) / 10,
    percentile: 50,
    confidence: 'low',
    axes_present: ['github_commit_velocity'],
    convergent_axes: [],
    rising: false,
    status: 'single-axis',
    incumbent: false,
    note: 'Synthetic scale simulation fixture.',
  };
}

function walkFiles(root) {
  const files = [];
  const walk = (dir) => {
    for (const entry of readdirSync(dir, { withFileTypes: true })) {
      const path = join(dir, entry.name);
      if (entry.isDirectory()) walk(path);
      else if (entry.isFile()) files.push(path);
    }
  };
  walk(root);
  return files;
}

function replaceSection(document, sectionLabel, body) {
  const start = `<!-- scale-sim:${sectionLabel}:start -->`;
  const end = `<!-- scale-sim:${sectionLabel}:end -->`;
  const section = `${start}\n${body.trim()}\n${end}`;
  const pattern = new RegExp(`${start.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\s\\S]*?${end.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`);
  return pattern.test(document) ? document.replace(pattern, section) : `${document.trimEnd()}\n\n${section}\n`;
}

const tempRoot = mkdtempSync(join(tmpdir(), 'evidaxis-scale-sim-'));
const tempData = join(tempRoot, 'data');
const tempDist = join(tempRoot, 'dist');
const archivePath = join(tempRoot, 'dist.tgz');

try {
  console.log(`Copying ${SOURCE_DATA} to ${tempData}`);
  cpSync(SOURCE_DATA, tempData, { recursive: true });

  const sourceDir = join(tempData, 'snapshots', SOURCE_DATE);
  const targetDir = join(tempData, 'snapshots', SIM_DATE);
  mkdirSync(targetDir, { recursive: true });
  const snapshot = readJson(join(sourceDir, 'snapshot.json'));
  const provenance = readJson(join(sourceDir, 'provenance.json'));
  const existingIds = new Set(snapshot.entities.map((entity) => entity.entity_id));
  const synthetic = [];
  let candidate = 1_000_000_000_000n;
  while (synthetic.length < SYNTHETIC_COUNT) {
    const id = `e_${crockford(candidate)}`;
    candidate += 1n;
    if (existingIds.has(id)) continue;
    const series = syntheticSeries(synthetic.length);
    synthetic.push(syntheticEntity(synthetic.length, id, series));
    provenance.github_weekly_raw[id] = series;
  }

  snapshot.snapshot_date = SIM_DATE;
  snapshot.period = '2026-w39';
  snapshot.captured_at = '2026-09-26T06:17:00+00:00';
  snapshot.snapshot_id = sha256(synthetic.map((entity) => entity.entity_id).join('\n')).slice(0, 12);
  snapshot.entities.push(...synthetic);
  snapshot.counts.entities = snapshot.entities.length;
  snapshot.counts['single-axis'] = (snapshot.counts['single-axis'] ?? 0) + SYNTHETIC_COUNT;

  provenance.snapshot_id = snapshot.snapshot_id;
  provenance.captured_at = snapshot.captured_at;
  const snapshotText = jsonBytes(snapshot);
  provenance.manifest_hash = sha256(snapshotText);
  const provenanceText = jsonBytes(provenance);
  const manifest = {
    ...readJson(join(sourceDir, 'manifest.json')),
    snapshot_id: snapshot.snapshot_id,
    snapshot_date: SIM_DATE,
    period: snapshot.period,
    manifest_hash: provenance.manifest_hash,
  };
  const manifestText = jsonBytes(manifest);
  const dropped = {
    v: 'dropped_1', snapshot_date: SIM_DATE, checked_at: snapshot.captured_at,
    seeded: snapshot.entities.length, in_snapshot: snapshot.entities.length,
    drop_fraction: 0, dropped: [], note: 'Synthetic scale simulation.', max_drop_fraction: 0.15,
  };
  const droppedText = jsonBytes(dropped);
  const artifacts = new Map([
    ['snapshot.json', snapshotText],
    ['manifest.json', manifestText],
    ['provenance.json', provenanceText],
    ['dropped.json', droppedText],
  ]);
  for (const [name, contents] of artifacts) writeFileSync(join(targetDir, name), contents);
  writeFileSync(join(targetDir, 'SHA256SUMS'), [...artifacts]
    .map(([name, contents]) => `${sha256(contents)}  ${name}\n`).join(''));
  writeFileSync(join(tempData, 'latest.json'), jsonBytes({
    snapshot_date: SIM_DATE,
    period: snapshot.period,
    snapshot_id: snapshot.snapshot_id,
    methodology_version: snapshot.methodology_version,
  }));

  const started = process.hrtime.bigint();
  const build = spawnSync('npm', ['run', 'build', '--', '--silent'], {
    cwd: WEB_ROOT,
    env: { ...process.env, EVIDAXIS_DATA_DIR: tempData, EVIDAXIS_DIST: tempDist },
    stdio: 'inherit',
  });
  const wallSeconds = Number(process.hrtime.bigint() - started) / 1e9;
  if (build.status !== 0) throw new Error(`scale build failed with exit ${build.status ?? 'unknown'}`);

  const tar = spawnSync('tar', ['-czf', archivePath, '-C', tempDist, '.'], { stdio: 'inherit' });
  if (tar.status !== 0) throw new Error(`tgz creation failed with exit ${tar.status ?? 'unknown'}`);

  const rows = walkFiles(tempDist).map((path) => ({
    path: relative(tempDist, path),
    bytes: statSync(path).size,
  }));
  const totalBytes = rows.reduce((sum, row) => sum + row.bytes, 0);
  const tgzBytes = statSync(archivePath).size;
  const largest = [...rows].sort((a, b) => b.bytes - a.bytes).slice(0, 25);
  const oversized = rows.filter((row) => row.path.endsWith('.html') && row.bytes > 1024 * 1024)
    .sort((a, b) => b.bytes - a.bytes);
  const feedJsonItems = readJson(join(tempDist, 'feed.json')).items.length;
  const feedAtomEntries = (readFileSync(join(tempDist, 'feed.atom'), 'utf8').match(/<entry>/g) ?? []).length;
  const pageChecks = [
    ['cohort', 'ai/cohorts/unassigned-v1/page/2/index.html', '/ai/cohorts/unassigned-v1/page/2/'],
    ['coverage', 'coverage/page/2/index.html', '/coverage/page/2/'],
    ['snapshot', `snapshots/${SIM_DATE}/page/2/index.html`, `/snapshots/${SIM_DATE}/page/2/`],
  ].map(([name, file, path]) => {
    const html = readFileSync(join(tempDist, file), 'utf8');
    return {
      name, path,
      selfCanonical: html.includes(`<link rel="canonical" href="https://evidaxis.org${path}">`),
      linked: html.includes('rel="prev"') && html.includes('rel="next"') && html.includes('aria-label="Pages"'),
    };
  });
  const sitemap = rows.filter((row) => /^sitemap.*\.xml$/.test(row.path))
    .map((row) => readFileSync(join(tempDist, row.path), 'utf8')).join('\n');
  for (const check of pageChecks) check.inSitemap = sitemap.includes(`https://evidaxis.org${check.path}`);
  if (feedJsonItems !== 100 || feedAtomEntries !== 100) throw new Error(`site feed cap failed: JSON ${feedJsonItems}, Atom ${feedAtomEntries}`);
  if (pageChecks.some((check) => !check.selfCanonical || !check.linked || !check.inSitemap)) {
    throw new Error(`pagination acceptance failed: ${JSON.stringify(pageChecks)}`);
  }
  const folders = new Map();
  for (const row of rows) {
    const folder = row.path.includes('/') ? row.path.split('/')[0] : '(root)';
    const value = folders.get(folder) ?? { files: 0, bytes: 0 };
    value.files += 1; value.bytes += row.bytes; folders.set(folder, value);
  }

  const reportBody = `## ${label.toUpperCase()} fixes\n\n` +
    `- Synthetic snapshot: ${SIM_DATE}, ${snapshot.entities.length.toLocaleString('en-US')} systems (${SYNTHETIC_COUNT.toLocaleString('en-US')} added)\n` +
    `- Build wall time: ${wallSeconds.toFixed(2)} s\n` +
    `- File count: ${rows.length.toLocaleString('en-US')}\n` +
    `- Total bytes: ${totalBytes.toLocaleString('en-US')} (${formatBytes(totalBytes)})\n` +
    `- tgz bytes: ${tgzBytes.toLocaleString('en-US')} (${formatBytes(tgzBytes)})\n` +
    `- HTML pages above 1 MB: ${oversized.length}\n\n` +
    `### Scale acceptance checks\n\n` +
    `- Root JSON Feed items: ${feedJsonItems}; root Atom entries: ${feedAtomEntries}.\n` +
    `- Page 2 self-canonical, linked with Previous / Next and page list, and present in sitemap: ${pageChecks.map((check) => check.name).join(', ')}.\n\n` +
    `### 25 largest files\n\n| File | Bytes | Size |\n|---|---:|---:|\n` +
    largest.map((row) => `| \`${row.path}\` | ${row.bytes.toLocaleString('en-US')} | ${formatBytes(row.bytes)} |`).join('\n') +
    `\n\n### HTML pages above 1 MB\n\n` +
    (oversized.length ? oversized.map((row) => `- \`${row.path}\`: ${row.bytes.toLocaleString('en-US')} bytes (${formatBytes(row.bytes)})`).join('\n') : '- None.') +
    `\n\n### Per-folder totals\n\n| Folder | Files | Bytes | Size |\n|---|---:|---:|---:|\n` +
    [...folders].sort((a, b) => b[1].bytes - a[1].bytes)
      .map(([folder, value]) => `| \`${folder}\` | ${value.files.toLocaleString('en-US')} | ${value.bytes.toLocaleString('en-US')} | ${formatBytes(value.bytes)} |`).join('\n');

  const header = '# Evidaxis scale simulation report\n\nGenerated by `node scripts/scale-sim.mjs <label>` against a temp-only synthetic snapshot.\n';
  let report = existsSync(REPORT) ? readFileSync(REPORT, 'utf8') : header;
  if (!report.startsWith('# Evidaxis scale simulation report')) report = header;
  report = replaceSection(report, label, reportBody);
  writeFileSync(REPORT, report);
  console.log(`Scale report (${label}): ${REPORT}`);
  console.log(`Build ${wallSeconds.toFixed(2)} s; ${rows.length} files; ${formatBytes(totalBytes)} total; ${formatBytes(tgzBytes)} tgz; ${oversized.length} HTML > 1 MB`);
} finally {
  rmSync(tempRoot, { recursive: true, force: true });
}
