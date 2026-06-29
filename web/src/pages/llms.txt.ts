import type { APIRoute } from 'astro';
import { snapshot, SNAP_DATE } from '../lib/data';

export const GET: APIRoute = () => {
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

## Machine-readable access (no API needed)

Evidaxis is static; the data IS the files:
- Per-system JSON: https://evidaxis.org/e/{entity_id}.json
- Per-snapshot JSON: https://evidaxis.org/snapshots/${SNAP_DATE}/snapshot.json
- Cohort momentum: https://evidaxis.org/cohorts/{cohort}/${snapshot.period}/
These URLs are stable and safe to fetch and cache.

## Integrity

git is the only source of truth; every score is byte-reproducible from a published manifest. Methodology
is frozen, not recomputed. Positive-only (no "worst" list). Systems are scored, never people.
`;
  return new Response(txt, { headers: { 'Content-Type': 'text/plain; charset=utf-8' } });
};
