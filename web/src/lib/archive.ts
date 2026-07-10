import { existsSync, readFileSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import type { Entity, Snapshot } from './data';

const REPO_ROOT = fileURLToPath(new URL('../../../', import.meta.url));
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
  recordStatus: 'current' | 'superseded';
};

function readJson(path: string): any {
  return JSON.parse(readFileSync(path, 'utf8'));
}

/** Absolute path to a frozen snapshot artifact (read-only archive layer). */
export function snapshotArtifactPath(date: string, name: string, repoRoot = REPO_ROOT): string {
  return join(repoRoot, 'data', 'snapshots', date, name);
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

/** Enumerate immutable snapshot payloads. Exported with a root argument for tests. */
export function enumerateSnapshots(repoRoot = REPO_ROOT): Snapshot[] {
  const snapshotsDir = join(repoRoot, 'data', 'snapshots');
  return readdirSync(snapshotsDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && DATE_RE.test(entry.name))
    .map((entry) => {
      const snap = readJson(join(snapshotsDir, entry.name, 'snapshot.json')) as Snapshot;
      if (snap.snapshot_date !== entry.name) {
        throw new Error(`snapshot date mismatch: directory ${entry.name}, payload ${snap.snapshot_date}`);
      }
      return snap;
    })
    .sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date));
}

export function buildEntityUniverse(allSnapshots: Snapshot[], latestDate: string): ArchivedEntity[] {
  const byId = new Map<string, ArchivedEntity>();
  for (const snap of [...allSnapshots].sort((a, b) => a.snapshot_date.localeCompare(b.snapshot_date))) {
    for (const entity of snap.entities) {
      const existing = byId.get(entity.entity_id);
      byId.set(entity.entity_id, {
        entity,
        snapshot: snap,
        firstSeenSnapshot: existing?.firstSeenSnapshot ?? snap.snapshot_date,
        lastSeenSnapshot: snap.snapshot_date,
        recordStatus: 'superseded',
      });
    }
  }
  for (const record of byId.values()) {
    record.recordStatus = record.lastSeenSnapshot === latestDate ? 'current' : 'superseded';
  }
  return [...byId.values()].sort((a, b) => a.entity.entity_id.localeCompare(b.entity.entity_id));
}

export const snapshots = enumerateSnapshots();
const latestPointer = readJson(join(REPO_ROOT, 'data', 'latest.json')) as { snapshot_date: string };
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
