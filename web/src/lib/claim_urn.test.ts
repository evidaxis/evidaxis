import { describe, expect, it } from 'vitest';
import { ClaimUrnError, claimUrn, claimUrnForEntity, parseClaimUrn } from './claim_urn';

const ACC = 'EVX:SYS:Y92940K5ESN7';
const LEGACY = 'e_H6PPP8CA9RR'; // the form live snapshots actually carry

describe('claim_urn (TS mirror of collectors/claim_urn.py)', () => {
  it('builds + parses a legacy live entity id round-trip', () => {
    const urn = claimUrn(LEGACY, 'm2', '2026-w27');
    expect(urn).toBe('urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-w27');
    expect(parseClaimUrn(urn)).toEqual({ accession_id: LEGACY, methodology_version: 'm2', epoch: '2026-w27' });
  });

  it('builds + parses an EVX accession round-trip (accession carries two colons)', () => {
    const urn = claimUrn(ACC, 'm1', '2026-06-27');
    expect(parseClaimUrn(urn)).toEqual({ accession_id: ACC, methodology_version: 'm1', epoch: '2026-06-27' });
    const got = parseClaimUrn('urn:evidaxis:claim:EVX:ACC:0123456789AB:m10:2027-w01');
    expect(got.accession_id).toBe('EVX:ACC:0123456789AB');
    expect(got.methodology_version).toBe('m10');
    expect(got.epoch).toBe('2027-w01');
  });

  it('rejects a non-URN, bad method, colon-in-epoch, and person-looking accession', () => {
    expect(() => parseClaimUrn('https://evidaxis.org/e/e_H6PPP8CA9RR/')).toThrow(ClaimUrnError);
    expect(() => claimUrn(ACC, 'v2', '2026-w26')).toThrow(ClaimUrnError);
    expect(() => claimUrn(ACC, 'm1', '2026-06-27T10:00:00')).toThrow(ClaimUrnError);
    expect(() => claimUrn('github:torvalds', 'm1', '2026-w26')).toThrow(ClaimUrnError);
    expect(() => claimUrn('e_ILLEGALOCHAR', 'm2', '2026-w27')).toThrow(ClaimUrnError); // I/L/O not base32
  });

  it('claimUrnForEntity uses entity_id + snapshot method + period', () => {
    const e: any = { entity_id: LEGACY };
    const snap: any = { methodology_version: 'm2', period: '2026-w27' };
    expect(claimUrnForEntity(e, snap)).toBe('urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-w27');
  });
});
