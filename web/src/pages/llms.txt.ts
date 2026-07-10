import type { APIRoute } from 'astro';
import { snapshot, SNAP_DATE, entities } from '../lib/data';
import { cohortLabel, COHORT_ORDER } from '../lib/cohorts';
import { claimUrn } from '../lib/claim_urn';

type SnapFlags = { provisional?: boolean; spine_complete?: boolean };

function cohortIdx(key: string): number {
  const i = COHORT_ORDER.indexOf(key);
  return i < 0 ? 999 : i;
}

function byCohortThenAlpha<T extends { cohort: string; name: string }>(list: T[]): T[] {
  return [...list].sort((a, b) => {
    const c = cohortIdx(a.cohort) - cohortIdx(b.cohort);
    if (c !== 0) return c;
    return a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });
  });
}

function entityLine(e: (typeof entities)[number]): string {
  const mom = e.momentum != null ? e.momentum.toFixed(1) : 'n/a';
  const urn = claimUrn(e.entity_id, snapshot.methodology_version, snapshot.snapshot_date);
  return `- [${e.name}](https://evidaxis.org/e/${e.entity_id}/): momentum ${mom}, status ${e.status}, cohort ${cohortLabel(e.cohort)}. Cite-as: ${urn}. JSON: https://evidaxis.org/e/${e.entity_id}.json`;
}

export const GET: APIRoute = () => {
  const flags = snapshot as typeof snapshot & SnapFlags;
  const c = snapshot.counts;
  const provisional = flags.provisional === true;
  const spineComplete = flags.spine_complete === true;

  const rising = byCohortThenAlpha(entities.filter((e) => e.status === 'rising'));
  const watch = byCohortThenAlpha(entities.filter((e) => e.status === 'watch'));
  const catalog = byCohortThenAlpha(entities);

  const risingSection = rising.length === 0
    ? 'None. Two independent axes must converge; none this period.'
    : rising.map(entityLine).join('\n');

  const watchSection = watch.length === 0
    ? 'None this period.'
    : watch.map(entityLine).join('\n');

  // Group catalog by cohort (canonical order), alphabetical already applied.
  const byCohort = new Map<string, typeof entities>();
  for (const e of catalog) {
    const list = byCohort.get(e.cohort) ?? [];
    list.push(e);
    byCohort.set(e.cohort, list);
  }
  const catalogSections: string[] = [];
  const cohortKeys = [
    ...COHORT_ORDER.filter((k) => byCohort.has(k)),
    ...[...byCohort.keys()].filter((k) => !COHORT_ORDER.includes(k)).sort(),
  ];
  for (const key of cohortKeys) {
    const list = byCohort.get(key)!;
    catalogSections.push(`### ${cohortLabel(key)}\n${list.map(entityLine).join('\n')}`);
  }

  const cohortList = Object.keys(snapshot.cohorts)
    .sort()
    .map((cKey) => `  - https://evidaxis.org/ai/cohorts/${cKey}/`)
    .join('\n');

  const txt = `# Evidaxis

> Evidaxis is an independent data observatory that measures open-source and research-native AI
> systems and scores them by "momentum", the rate of change of their public signals, on a
> transparent, versioned public methodology. A system is recognized as rising only when two
> independent axes converge. All measurements are released to the public domain under CC0. The
> site is fully static; every page has a stable canonical URL and machine-readable JSON-LD, and
> every system and snapshot has a downloadable JSON representation. Lists are ordered by cohort,
> then alphabetically; momentum is a measurement, not a placement. Readers sort for themselves.

## Status (snapshot ${snapshot.period})

- rising: ${c.rising}
- watch: ${c.watch}
- axis2_present: ${c.axis2_present}
- provisional: ${provisional}
- spine_complete: ${spineComplete}

## Rising this period

${risingSection}

## Watch list

${watchSection}

## Catalog (by cohort, alphabetical within cohort)

Snapshot ${snapshot.period}. Grouped by cohort; alphabetical inside each cohort. Momentum value, claim-URN, and JSON twin per system.

${catalogSections.join('\n\n')}

## Key resources

- [Methodology (current)](https://evidaxis.org/methodology/current/): how momentum scores and the convergence gate are computed. Versioned. Cite the version you used.
- [Methodology v1](https://evidaxis.org/methodology/v1/): the frozen v1 definition.
- [Methodology version registry (JSON)](https://evidaxis.org/methodology-registry.json): machine-readable registry of methodology versions.
- [Latest snapshot](https://evidaxis.org/snapshots/${SNAP_DATE}/): the most recent complete measurement snapshot (period ${snapshot.period}), with full JSON download.
- [Coverage atlas](https://evidaxis.org/coverage/): every cohort tracked, and the gaps not yet measured.

## Data license

All Evidaxis data is released under CC0 1.0 (public domain). Reuse, redistribute, and cite freely.
Attribution to Evidaxis is appreciated but not required.

Cite: 10.5281/zenodo.21076012 (https://doi.org/10.5281/zenodo.21076012) is the genesis seed deposit (m1, 19 systems) citation handle for the Evidaxis genesis snapshot bundle.

## How to cite a system

Each measured system has a canonical record at https://evidaxis.org/e/{entity_id}/ (carries the full
record and JSON-LD) and a machine-readable record at https://evidaxis.org/e/{entity_id}.json. Cite the
record plus the snapshot period, e.g. "Evidaxis momentum for {System}, snapshot ${snapshot.period}
(https://evidaxis.org/e/{entity_id})".

Durable (format-independent) canonical reference: urn:evidaxis:claim:{entity_id}:{methodology_version}:{snapshot_date}
(e.g. urn:evidaxis:claim:{entity_id}:${snapshot.methodology_version}:${snapshot.snapshot_date}). This claim-URN names the
assertion Evidaxis makes about a system under a methodology at an epoch; it is stable across changes in how the
record is delivered (HTTP today, other protocols later) and today resolves at https://evidaxis.org/e/{entity_id}/.
It is emitted per system as JSON-LD identifier and an HTML rel="cite-as" link. Prefer it for long-lived citations.

## Machine-readable access (no API needed)

Evidaxis is static; the data IS the files:
- Per-system JSON: https://evidaxis.org/e/{entity_id}.json
- Per-snapshot JSON: https://evidaxis.org/snapshots/${SNAP_DATE}/snapshot.json
- Methodology version registry (JSON): https://evidaxis.org/methodology-registry.json
- Cohorts (canonical):
${cohortList}
These URLs are stable and safe to fetch and cache.

## Integrity

git is the only source of truth; every input is hash-pinned and the raw provenance is published, so every
score is checkable against its hash-pinned inputs. The genesis snapshot bundle is frozen and hash-verified.
Methodology is versioned. Positive-only (no "worst" list). Systems are scored, never people. Nobody is
ranked last; lists are not ordered as winners.
`;
  return new Response(txt, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
