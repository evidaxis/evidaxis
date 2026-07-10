/** claim-URN  -  the format-independent canonical reference (see CLAIM-URN.md).
 *  TS mirror of collectors/claim_urn.py: the grammar is a LOCKED external
 *  contract, so keep it byte-identical to the Python reference implementation.
 *  A claim-URN names "what Evidaxis asserts about system X, under methodology M,
 *  at epoch T"  -  it is per-ENTITY (a claim is an assertion about a system), never
 *  minted for aggregate snapshots (those keep their DOI / snapshot-id identity). */
import type { Entity, Snapshot } from './data';

const PREFIX = 'urn:evidaxis:claim';

// Crockford base32 body (never I L O U); two accession forms: EVX:TYPE:BODY | e_BODY.
const ACCESSION_RE = /^(?:EVX:[A-Z]{2,4}:[0-9A-HJKMNP-TV-Z]{11,40}|e_[0-9A-HJKMNP-TV-Z]{11,40})$/;
const METHOD_RE = /^m[0-9]+$/;
const EPOCH_RE = /^\d{4}-(?:w\d{2}|\d{2}-\d{2})$/;

export class ClaimUrnError extends Error {}

function validate(accession: string, method: string, epoch: string): void {
  if (!ACCESSION_RE.test(accession)) throw new ClaimUrnError(`bad accession_id: ${accession}`);
  if (!METHOD_RE.test(method)) throw new ClaimUrnError(`bad methodology_version: ${method} (want m<N>)`);
  if (!EPOCH_RE.test(epoch)) throw new ClaimUrnError(`bad epoch: ${epoch} (want YYYY-Www or YYYY-MM-DD, colon-free)`);
}

/** Construct a claim-URN, validating each field against the locked grammar. */
export function claimUrn(accession: string, method: string, epoch: string): string {
  validate(accession, method, epoch);
  return `${PREFIX}:${accession}:${method}:${epoch}`;
}

/** Parse a claim-URN. Last two colon tokens = method + epoch (colon-free by
 *  grammar); the rest rejoins as the accession. Throws ClaimUrnError on garbage. */
export function parseClaimUrn(urn: string): { accession_id: string; methodology_version: string; epoch: string } {
  if (typeof urn !== 'string' || !urn.startsWith(PREFIX + ':')) throw new ClaimUrnError(`not a claim-URN: ${urn}`);
  const parts = urn.slice(PREFIX.length + 1).split(':');
  if (parts.length < 3) throw new ClaimUrnError(`too few segments in ${urn}: want accession+method+epoch`);
  const epoch = parts[parts.length - 1];
  const method = parts[parts.length - 2];
  const accession = parts.slice(0, -2).join(':');
  validate(accession, method, epoch);
  return { accession_id: accession, methodology_version: method, epoch };
}

/** The durable citation for a single system's measurement at this snapshot.
 *  Epoch is snapshot_date (YYYY-MM-DD), not ISO-week period: two snapshots in the
 *  same week can hold different payloads, and a week-epoch URN would be ambiguous
 *  (see data/observations/ERRATA.md, 2026-07-10). Grammar still accepts YYYY-Www
 *  so historically minted URNs remain parseable. */
export const claimUrnForEntity = (e: Entity, snap: Snapshot): string =>
  claimUrn(e.entity_id, snap.methodology_version, snap.snapshot_date);
