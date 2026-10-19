import { createHash } from 'node:crypto';
import type { OwnerEntry, OwnerTypes } from './person_free';

/** Publish drop records and opaque repository ids, never a personal account address.
 * The archive hash describes the original bytes, not this public projection.
 * A missing registry row is published as gh:unclassified so one cache gap cannot stop a weekly build.
 */
const TOP_LEVEL = [
  'v', 'snapshot_date', 'checked_at', 'seeded', 'in_snapshot',
  'drop_fraction', 'max_drop_fraction', 'note',
] as const;

type SlugMaps = { field: Map<string, string>; userText: Map<string, string> };
const INDEXES = new WeakMap<object, SlugMaps>();

function publicRef(entry: OwnerEntry | undefined): string {
  if (!entry || !Number.isSafeInteger(entry.repo_id) || entry.repo_id <= 0) return 'gh:unclassified';
  return `gh:${entry.repo_id}`;
}

function putSlug(map: Map<string, { ref: string; rank: number }>, slug: string, ref: string, rank: number) {
  if (!/^[^/]+\/[^/]+$/.test(slug)) return;
  const key = slug.toLowerCase();
  const prev = map.get(key);
  if (!prev || rank > prev.rank) map.set(key, { ref, rank });
}

function repoMaps(registry: OwnerTypes): SlugMaps {
  if (registry && typeof registry === 'object') {
    const cached = INDEXES.get(registry);
    if (cached) return cached;
  }
  const fieldRank = new Map<string, { ref: string; rank: number }>();
  const userRank = new Map<string, { ref: string; rank: number }>();
  const repos = registry?.repos ?? {};
  for (const [key, entry] of Object.entries(repos)) {
    const ref = publicRef(entry);
    // A registry key outranks another row's full_name when the strings collide.
    putSlug(fieldRank, key, ref, 2);
    if (typeof entry?.full_name === 'string') putSlug(fieldRank, entry.full_name, ref, 1);
    if (entry?.owner_type === 'User') {
      putSlug(userRank, key, ref, 2);
      if (typeof entry.full_name === 'string') putSlug(userRank, entry.full_name, ref, 1);
    }
  }
  const flatten = (map: Map<string, { ref: string; rank: number }>) =>
    new Map([...map].map(([slug, value]) => [slug, value.ref]));
  const built = { field: flatten(fieldRank), userText: flatten(userRank) };
  if (registry && typeof registry === 'object') INDEXES.set(registry, built);
  return built;
}

function lookupSlug(userText: Map<string, string>, slug: string): string | undefined {
  let key = slug.toLowerCase();
  const direct = userText.get(key);
  if (direct) return direct;
  // The address token can swallow a trailing ".git" or a sentence period.
  if (key.endsWith('.git')) key = key.slice(0, -4);
  key = key.replace(/\.+$/, '');
  return userText.get(key);
}

function scrubUserText(text: string, userText: Map<string, string>): string {
  if (!text || !userText.size) return text;
  // Owner/repo, with or without a github.com URL prefix. Only User-type registry rows match.
  const address = /(?<![A-Za-z0-9_.-])(?:https?:\/\/(?:www\.)?github\.com\/)?([A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100})(?:\.git)?(?![A-Za-z0-9._-])/gi;
  return text.replace(address, (match, slug: string) => lookupSlug(userText, slug) ?? match);
}

function repoRef(name: unknown, field: Map<string, string>): string {
  if (typeof name !== 'string') return 'gh:unclassified';
  return field.get(name.toLowerCase()) ?? 'gh:unclassified';
}

function projectEntry(row: unknown, maps: SlugMaps): Record<string, unknown> {
  if (!row || typeof row !== 'object' || Array.isArray(row)) return {};
  const source = row as Record<string, unknown>;
  const out: Record<string, unknown> = {};
  if ('entity_id' in source) out.entity_id = source.entity_id;
  if ('previously_tracked' in source) out.previously_tracked = source.previously_tracked;
  if ('reason' in source) {
    out.reason = typeof source.reason === 'string' ? scrubUserText(source.reason, maps.userText) : source.reason;
  }
  if ('github_repo' in source) out.repo_ref = repoRef(source.github_repo, maps.field);
  return out;
}

export function publicDropped(raw: Buffer, registry: OwnerTypes) {
  const parsed = JSON.parse(raw.toString('utf8'));
  const source = parsed && typeof parsed === 'object' && !Array.isArray(parsed) ? parsed as Record<string, unknown> : {};
  const maps = repoMaps(registry);
  const projected: Record<string, unknown> = {
    projection: 'person_free_dropped_1',
    archive_sha256: createHash('sha256').update(raw).digest('hex'),
  };
  for (const key of TOP_LEVEL) {
    if (!Object.prototype.hasOwnProperty.call(source, key)) continue;
    const value = source[key];
    projected[key] = key === 'note' && typeof value === 'string' ? scrubUserText(value, maps.userText) : value;
  }
  projected.dropped = (Array.isArray(source.dropped) ? source.dropped : []).map((row) => projectEntry(row, maps));
  return projected;
}
