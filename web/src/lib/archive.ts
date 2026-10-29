import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { REPO_ROOT, dataPath, repoDataPath, repoEtlPath, assertUnitPath } from './data-path';
import type { Entity, Snapshot } from './data';
import { applyProjectAccounts } from './personFree.mjs';
import { neutralName, revealsHandle, type OwnerTypes } from './person_free';

const DATE_RE = /^\d{4}-\d{2}-\d{2}$/;

/** Frozen verification-bundle artifact names under data/snapshots/{date}/. */
export const SNAPSHOT_VERIFICATION_ARTIFACTS = [
  'manifest.json',
  'provenance.json',
  'SHA256SUMS',
  'dropped.json',
] as const;
export type SnapshotVerificationArtifact = (typeof SNAPSHOT_VERIFICATION_ARTIFACTS)[number];

export type ArchivedEntity = {
  entity: Entity;
  snapshot: Snapshot;
  firstSeenSnapshot: string;
  lastSeenSnapshot: string;
  latestSnapshot: string;
  recordStatus: RecordStatus;
};

export type RecordStatus = 'measured' | 'observation_skipped' | 'departure_confirmed' | 'absence_unexplained';
type Departure = { entity_id?: string; github_repo?: string; reason: string; date: string };
export type ObservationEvidence = { declaredGaps: Set<string>; departures: Departure[] };

export function observationEvidence(date: string, repoRoot = REPO_ROOT): ObservationEvidence {
  const dropped = readSnapshotArtifactRaw(date, 'dropped.json', repoRoot);
  const declaredGaps = new Set<string>((dropped ? JSON.parse(dropped.toString('utf8')).dropped ?? [] : [])
    // Every dropped.json row is a seeded system the collector produced no record
    // for; older files (2026-07) name the cause "202-exhaustion" instead.
    .filter((row: any) => typeof row.reason === 'string'
      && /\bdeclared gap\b|\bno record\b|\b202\b/i.test(row.reason))
    .map((row: any) => row.entity_id));
  const dir = repoDataPath(repoRoot, 'observations');
  const departures: Departure[] = [];
  // A confirmed retirement remains evidence in later weeks, until a new
  // measurement supersedes it. Never consult observations after the cutoff.
  for (const day of existsSync(dir) ? readdirSync(dir).filter(d => DATE_RE.test(d) && d <= date).sort() : []) {
    for (const name of ['seed-departures.json', 'departed.json']) {
      const path = join(dir, day, name);
      if (!existsSync(path)) continue;
      const body = readJson(path);
      for (const row of Array.isArray(body) ? body : body.departures ?? body.departed ?? []) {
        if (['gone', 'repo_id_changed'].includes(row.reason)) departures.push({ ...row, date: day });
      }
    }
  }
  return { declaredGaps, departures };
}

export function observationStatus(entity: Entity, lastMeasured: string | null, latestDate: string, evidence: ObservationEvidence): RecordStatus {
  if (lastMeasured === latestDate) return 'measured';
  if (evidence.declaredGaps.has(entity.entity_id)) return 'observation_skipped';
  if (evidence.departures.some(row => row.date >= (lastMeasured ?? '')
    && (row.entity_id === entity.entity_id || (row.github_repo && row.github_repo.toLowerCase() === entity.github_repo?.toLowerCase())))) return 'departure_confirmed';
  return 'absence_unexplained';
}

export function recordAvailability(record: ArchivedEntity) {
  const date = record.lastSeenSnapshot;
  const message = record.recordStatus === 'measured' ? `Measured in snapshot ${date}.`
    : record.recordStatus === 'observation_skipped'
      ? `Not measured in this snapshot: the weekly collection produced no record for this system (a declared gap). Last measured ${date}. The next attempt is the next weekly snapshot.`
      : record.recordStatus === 'departure_confirmed'
        ? `Preserved historical record; record status: superseded; last measured ${date}.`
        : `Not in the latest snapshot; last measured ${date}.`;
  return { state: record.recordStatus, latest_snapshot: record.latestSnapshot, last_measured: date, message };
}

function readJson(path: string): any {
  return JSON.parse(readFileSync(assertUnitPath(path), 'utf8'));
}

/** Absolute path to a frozen snapshot artifact (read-only archive layer). */
export function snapshotArtifactPath(date: string, name: string, repoRoot = REPO_ROOT): string {
  return repoDataPath(repoRoot, 'snapshots', date, name);
}

/** True when the frozen artifact exists on disk for that snapshot date. */
export function hasSnapshotArtifact(date: string, name: string, repoRoot = REPO_ROOT): boolean {
  return existsSync(snapshotArtifactPath(date, name, repoRoot));
}

/**
 * Raw frozen bytes for a snapshot verification artifact. Pass-through only  - 
 * no rewrite, no re-serialize. Returns null when the file is absent (e.g.
 * dropped.json is optional on genesis).
 */
export function readSnapshotArtifactRaw(date: string, name: string, repoRoot = REPO_ROOT): Buffer | null {
  const path = snapshotArtifactPath(date, name, repoRoot);
  try {
    return readFileSync(path);
  } catch {
    return null;
  }
}

function projectAccountMap(repoRoot: string): Record<string, unknown> {
  const path = repoEtlPath(repoRoot, 'project_accounts.json');
  if (!existsSync(path)) return {};
  const accounts = readJson(path)?.accounts;
  if (!accounts || typeof accounts !== 'object' || Array.isArray(accounts)) return {};
  return accounts;
}

/** Enumerate immutable snapshot payloads. Exported with a root argument for tests. */
export function enumerateSnapshots(repoRoot = REPO_ROOT): Snapshot[] {
  const snapshotsDir = repoDataPath(repoRoot, 'snapshots');
  const registry = readJson(repoEtlPath(repoRoot, 'owner_types.json')) as OwnerTypes;
  applyProjectAccounts(registry.repos, projectAccountMap(repoRoot));
  return readdirSync(snapshotsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && DATE_RE.test(entry.name))
    .map((entry) => {
      const snap = readJson(join(snapshotsDir, entry.name, 'snapshot.json')) as Snapshot;
      if (snap.snapshot_date !== entry.name) {
        throw new Error(`snapshot date mismatch: directory ${entry.name}, payload ${snap.snapshot_date}`);
      }
      // Public projection at load: a name or slug that is a person's GitHub handle never
      // reaches a page, feed, badge or JSON twin (person_free.ts). Archive files stay canonical.
      snap.entities = snap.entities.map((e) => revealsHandle(e.name, registry) || revealsHandle(e.slug, registry)
        ? { ...e, name: neutralName(e.entity_id), slug: e.entity_id.toLowerCase() } : e);
      return snap;
    })
    .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date));
}

export function buildEntityUniverse(allSnapshots: Snapshot[], latestDate: string, evidence = observationEvidence(latestDate)): ArchivedEntity[] {
  const byId = new Map<string, ArchivedEntity>();
  for (const snap of [...allSnapshots].sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))) {
    if (snap.snapshot_date > latestDate) continue;
    for (const entity of snap.entities) {
      const existing = byId.get(entity.entity_id);
      byId.set(entity.entity_id, {
        entity,
        snapshot: snap,
        firstSeenSnapshot: existing?.firstSeenSnapshot ?? snap.snapshot_date,
        lastSeenSnapshot: snap.snapshot_date,
        latestSnapshot: latestDate,
        recordStatus: 'absence_unexplained',
      });
    }
  }
  for (const record of byId.values()) {
    record.recordStatus = observationStatus(record.entity, record.lastSeenSnapshot, latestDate, evidence);
  }
  return [...byId.values()].sort((a, b) => a.entity.entity_id.localeCompare(b.entity.entity_id));
}

export const snapshots = enumerateSnapshots();
const latestPointer = readJson(dataPath('latest.json')) as { snapshot_date: string };
const resolvedLatest = snapshots.find((snap) => snap.snapshot_date === latestPointer.snapshot_date);
if (!resolvedLatest) {
  throw new Error(`data/latest.json points to missing snapshot ${latestPointer.snapshot_date}`);
}
export const latest: Snapshot = resolvedLatest;

export const snapshotByDate = new Map(snapshots.map((snap) => [snap.snapshot_date, snap]));
export const entityUniverse = buildEntityUniverse(snapshots, latest.snapshot_date);
export const archiveEntityById = new Map(entityUniverse.map((record) => [record.entity.entity_id, record]));

export function manifestForSnapshot(date: string): any | null {
  try {
    return readJson(snapshotArtifactPath(date, 'manifest.json'));
  } catch {
    return null;
  }
}

export function provenanceForSnapshot(date: string): any | null {
  try {
    return readJson(snapshotArtifactPath(date, 'provenance.json'));
  } catch {
    return null;
  }
}

/** Required verification files every snapshot ships (dropped.json optional). */
export function verificationBundleForSnapshot(date: string, repoRoot = REPO_ROOT): {
  required: { name: SnapshotVerificationArtifact; present: boolean }[];
  optional: { name: 'dropped.json'; present: boolean };
} {
  return {
    required: (['manifest.json', 'provenance.json', 'SHA256SUMS'] as const).map((name) => ({
      name,
      present: hasSnapshotArtifact(date, name, repoRoot),
    })),
    optional: { name: 'dropped.json', present: hasSnapshotArtifact(date, 'dropped.json', repoRoot) },
  };
}
