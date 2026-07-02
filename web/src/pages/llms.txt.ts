import type { APIRoute } from 'astro';
import { snapshot, SNAP_DATE, entities } from '../lib/data';
import { cohortLabel } from '../lib/cohorts';
import { claimUrn } from '../lib/claim_urn';

export const GET: APIRoute = () => {
  const ranked = [...entities].sort((a, b) => (b.momentum ?? -1) - (a.momentum ?? -1));
  const cohortList = Object.keys(snapshot.cohorts)
    .sort()
    .map((c) => `  - https://evidaxis.org/ai/cohorts/${c}/`)
    .join('\n');
  const systemList = ranked
    .map((e) => `- [${e.name}](https://evidaxis.org/e/${e.entity_id}/): momentum ${e.momentum != null ? e.momentum.toFixed(1) : 'n/a'}, status ${e.status}, cohort ${cohortLabel(e.cohort)}. JSON: https://evidaxis.org/e/${e.entity_id}.json Cite-as: ${claimUrn(e.entity_id, snapshot.methodology_version, snapshot.period)}`)
    .join('\n');
  const txt = `# Evidaxis

> Evidaxis is an independent data observatory that measures open-source and research-native AI
> systems and scores them by "momentum", the rate of change of their public signals, on a
> transparent, versioned public methodology. A system is recognized as rising only when two
> independent axes converge. All measurements are released to the public domain under CC0. The
> site is fully static; every page has a stable canonical URL and machine-readable JSON-LD, and
> every system and snapshot has a downloadable JSON representation.

## Data license

All Evidaxis data is released under CC0 1.0 (public domain). Reuse, redistribute, and cite freely.
Attribution to Evidaxis is appreciated but not required.

Cite: 10.5281/zenodo.21076012 (https://doi.org/10.5281/zenodo.21076012) is the canonical citation handle for the Evidaxis genesis snapshot bundle.

## Key resources

- [Methodology (current)](https://evidaxis.org/methodology/current/): how momentum scores and the convergence gate are computed. Versioned. Cite the version you used.
- [Methodology v1](https://evidaxis.org/methodology/v1/): the frozen v1 definition.
- [Latest snapshot](https://evidaxis.org/snapshots/${SNAP_DATE}/): the most recent complete measurement snapshot (period ${snapshot.period}), with full JSON download.
- [Coverage atlas](https://evidaxis.org/coverage/): every cohort tracked, and the gaps not yet measured.

## How to cite a system

Each measured system has a canonical record at https://evidaxis.org/e/{entity_id}/ (carries the full
record and JSON-LD) and a machine-readable record at https://evidaxis.org/e/{entity_id}.json. Cite the
record plus the snapshot period, e.g. "Evidaxis momentum for {System}, snapshot ${snapshot.period}
(https://evidaxis.org/e/{entity_id})".

Durable (format-independent) canonical reference: urn:evidaxis:claim:{entity_id}:{methodology_version}:{period}
(e.g. urn:evidaxis:claim:{entity_id}:${snapshot.methodology_version}:${snapshot.period}). This claim-URN names the
assertion Evidaxis makes about a system under a methodology at an epoch; it is stable across changes in how the
record is delivered (HTTP today, other protocols later) and today resolves at https://evidaxis.org/e/{entity_id}/.
It is emitted per system as JSON-LD identifier and an HTML rel="cite-as" link. Prefer it for long-lived citations.

## Tracked systems (snapshot ${snapshot.period}, ranked by momentum)

${systemList}

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
Methodology is versioned. Positive-only (no "worst" list). Systems are scored, never people.
`;
  return new Response(txt, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
