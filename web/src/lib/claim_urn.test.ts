import { describe, expect, it } from 'vitest';
import { ClaimUrnError, claimUrn, claimUrnForEntity, parseClaimUrn } from './claim_urn';

const ACC = 'EVX:SYS:Y92940K5ESN7';
const LEGACY = 'e_H6PPP8CA9RR'; // the form live snapshots actually carry

// 20 shared vectors mirrored in tests/test_claim_urn.py  -  both implementations must agree.
const SHARED_VECTORS: Array<[string, string, string, string]> = [
  [LEGACY, 'm2', '2026-w27', 'urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-w27'],
  [LEGACY, 'm2', '2026-07-03', 'urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-03'],
  [LEGACY, 'm2', '2026-07-04', 'urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-04'],
  [ACC, 'm1', '2026-06-27', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m1:2026-06-27'],
  [ACC, 'm2', '2026-w26', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-w26'],
  [ACC, 'm2', '2026-07-01', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-07-01'],
  [ACC, 'm10', '2027-w01', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m10:2027-w01'],
  [ACC, 'm0', '2025-01-01', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m0:2025-01-01'],
  ['e_0123456789AB', 'm1', '2026-w01', 'urn:evidaxis:claim:e_0123456789AB:m1:2026-w01'],
  ['e_ZZZZZZZZZZZ', 'm2', '2026-12-31', 'urn:evidaxis:claim:e_ZZZZZZZZZZZ:m2:2026-12-31'],
  ['EVX:ACC:0123456789AB', 'm1', '2026-06-27', 'urn:evidaxis:claim:EVX:ACC:0123456789AB:m1:2026-06-27'],
  ['EVX:SYS:ABCDEFGHJKMN', 'm3', '2026-w52', 'urn:evidaxis:claim:EVX:SYS:ABCDEFGHJKMN:m3:2026-w52'],
  ['EVX:TOOL:PQRSTVWXYZ01', 'm2', '2026-07-10', 'urn:evidaxis:claim:EVX:TOOL:PQRSTVWXYZ01:m2:2026-07-10'],
  [LEGACY, 'm1', '2026-w26', 'urn:evidaxis:claim:e_H6PPP8CA9RR:m1:2026-w26'],
  [LEGACY, 'm1', '2026-06-27', 'urn:evidaxis:claim:e_H6PPP8CA9RR:m1:2026-06-27'],
  [ACC, 'm2', '2026-w27', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-w27'],
  [ACC, 'm2', '2026-07-03', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-07-03'],
  [ACC, 'm2', '2026-07-04', 'urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-07-04'],
  ['e_H6PPP8CA9RR0', 'm2', '2030-w01', 'urn:evidaxis:claim:e_H6PPP8CA9RR0:m2:2030-w01'],
  ['EVX:LIB:0A1B2C3D4E5F', 'm99', '2099-12-31', 'urn:evidaxis:claim:EVX:LIB:0A1B2C3D4E5F:m99:2099-12-31'],
];

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

  it('claimUrnForEntity uses entity_id + snapshot method + snapshot_date (not period)', () => {
    const e: any = { entity_id: LEGACY };
    const snap: any = {
      methodology_version: 'm2',
      period: '2026-w27',
      snapshot_date: '2026-07-04',
    };
    expect(claimUrnForEntity(e, snap)).toBe('urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-04');
    // period must NOT be used  -  two dates in the same week must mint different URNs
    const snapEarlier = { ...snap, snapshot_date: '2026-07-03' };
    expect(claimUrnForEntity(e, snapEarlier)).toBe('urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-03');
    expect(claimUrnForEntity(e, snap)).not.toBe(claimUrnForEntity(e, snapEarlier));
  });

  it('accepts date-epoch minting (YYYY-MM-DD) via claimUrn', () => {
    const urn = claimUrn(LEGACY, 'm2', '2026-07-04');
    expect(urn).toBe('urn:evidaxis:claim:e_H6PPP8CA9RR:m2:2026-07-04');
    expect(parseClaimUrn(urn).epoch).toBe('2026-07-04');
  });

  it('agrees with the Python mirror on 20 shared vectors', () => {
    expect(SHARED_VECTORS).toHaveLength(20);
    for (const [accession, method, epoch, want] of SHARED_VECTORS) {
      const got = claimUrn(accession, method, epoch);
      expect(got).toBe(want);
      expect(parseClaimUrn(got)).toEqual({
        accession_id: accession,
        methodology_version: method,
        epoch,
      });
    }
  });
});
