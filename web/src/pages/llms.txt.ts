import type { APIRoute } from 'astro';
import { snapshot, SNAP_DATE, entities } from '../lib/data';
import { cohortLabel, COHORT_ORDER } from '../lib/cohorts';
import { claimUrn } from '../lib/claim_urn';
import { measurementPhrases, measurementStateFor } from '../lib/measurement';
import { computePowerFunnel } from '../lib/power';

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
  const phrases = measurementPhrases(measurementStateFor(e, snapshot));
  return `- [${e.name}](https://evidaxis.org/e/${e.entity_id}/): momentum ${mom}, ${phrases.compact.toLowerCase()}, cohort ${cohortLabel(e.cohort)}. Cite-as: ${urn}. JSON: https://evidaxis.org/e/${e.entity_id}.json`;
}

export const GET: APIRoute = () => {
  const flags = snapshot as typeof snapshot & SnapFlags;
  const power = computePowerFunnel(snapshot);
  const provisional = flags.provisional === true;
  const spineComplete = flags.spine_complete === true;

  const rising = byCohortThenAlpha(entities.filter((e) => measurementStateFor(e, snapshot).positive_signal.state === 'published'));
  const catalog = byCohortThenAlpha(entities);

  const risingSection = rising.length === 0
    ? 'Published Rising signals: 0 for this period. Two independent axes must converge for publication.'
    : rising.map(entityLine).join('\n');

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

- rising_published: ${power.rising_published}
- registry_members: ${power.registry_members}
- history_sufficient: ${power.history_sufficient}
- two_axis_measurable: ${power.two_axis_measurable}
- gate_eligible: ${power.gate_eligible}
- provisional: ${provisional}
- spine_complete: ${spineComplete}

## Rising this period

${risingSection}

## Catalog (by cohort, alphabetical within cohort)

Snapshot ${snapshot.period}. Grouped by cohort; alphabetical inside each cohort. Momentum value, claim-URN, and JSON twin per system.

${catalogSections.join('\n\n')}

## Key resources

- [Methodology (current)](https://evidaxis.org/methodology/current/): how momentum scores and the convergence gate are computed. Versioned. Cite the version you used.
- [Methodology v1](https://evidaxis.org/methodology/v1/): the frozen v1 definition.
- [Methodology version registry (JSON)](https://evidaxis.org/methodology-registry.json): machine-readable registry of methodology versions.
- [Latest snapshot](https://evidaxis.org/snapshots/${SNAP_DATE}/): the most recent complete measurement snapshot (period ${snapshot.period}), with full JSON download.
- [Coverage atlas](https://evidaxis.org/coverage/): every cohort tracked, and the gaps not yet measured.
- [Atom feed](https://evidaxis.org/feed.atom): typed weekly observation events and published convergence signals.
- [JSON Feed](https://evidaxis.org/feed.json): the same typed entries in JSON Feed 1.1 format.

## Data license

All Evidaxis data is released under CC0 1.0 (public domain). Reuse, redistribute, and cite freely.
Attribution to Evidaxis is appreciated but not required.

Cite: 10.5281/zenodo.21076012 (https://doi.org/10.5281/zenodo.21076012) is the genesis seed deposit (m1, 19 systems) citation handle for the Evidaxis genesis snapshot bundle.
Latest deposited snapshot version: 10.5281/zenodo.21307528 (2026-07-10, m2, 134 systems).

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
- Typed Atom feed: https://evidaxis.org/feed.atom
- Typed JSON Feed: https://evidaxis.org/feed.json
- Cohorts (canonical):
${cohortList}
These URLs are stable and safe to fetch and cache.

## Integrity

git is the only source of truth; every input is hash-pinned and the raw provenance is published, so every
score is checkable against its hash-pinned inputs. The genesis snapshot bundle is frozen and hash-verified.
Methodology is versioned. Positive-only (no "worst" list). Systems are scored, never people. Nobody is
ranked last; lists are not ordered as winners.

## How to verify

Each snapshot ships a verification bundle of frozen files. For the latest snapshot (${SNAP_DATE}):
- manifest.json: https://evidaxis.org/snapshots/${SNAP_DATE}/manifest.json
- provenance.json: https://evidaxis.org/snapshots/${SNAP_DATE}/provenance.json
- SHA256SUMS: https://evidaxis.org/snapshots/${SNAP_DATE}/SHA256SUMS
- snapshot.json: https://evidaxis.org/snapshots/${SNAP_DATE}/snapshot.json
- dropped.json (when present): https://evidaxis.org/snapshots/${SNAP_DATE}/dropped.json
Download SHA256SUMS and the listed artifacts, then run: sha256sum -c SHA256SUMS
Replace the date segment with any archived date under https://evidaxis.org/snapshots/.
`;
  return new Response(txt, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
