export type OwnerType = 'Organization' | 'User';

export type OwnerEntry = {
  owner_type: OwnerType;
  repo_id: number;
  full_name: string;
};

export type OwnerTypes = {
  schema_version: 'owner_types_1';
  repos: Record<string, OwnerEntry>;
};

type RepositoryEntity = {
  github_repo: string;
  homepage?: string | null;
  [key: string]: unknown;
};

function entryFor(e: RepositoryEntity, registry: OwnerTypes): OwnerEntry {
  const entry = registry?.repos?.[e.github_repo];
  if (!entry || !['Organization', 'User'].includes(entry.owner_type)
    || !Number.isInteger(entry.repo_id) || entry.repo_id <= 0
    || typeof entry.full_name !== 'string' || !/^[^/]+\/[^/]+$/.test(entry.full_name)) {
    throw new Error(`repository publication classification is unavailable for ${e.github_repo}`);
  }
  return entry;
}

function isGithubUrl(value: string): boolean {
  try {
    const url = new URL(value);
    return url.hostname.toLowerCase().replace(/^www\./, '') === 'github.com';
  } catch {
    return false;
  }
}

/** Repeatedly percent-decode (bounded) so an encoded handle cannot slip through
 *  the owner check (review 2026-07-10: %67corso bypass). */
function fullyDecoded(value: string): string {
  let out = value;
  for (let i = 0; i < 3; i++) {
    let next;
    try { next = decodeURIComponent(out); } catch { break; }
    if (next === out) break;
    out = next;
  }
  return out.toLowerCase();
}

function safeUserHomepage(homepage: string | null | undefined, owner: string): string | null {
  if (!homepage) return null;
  try { new URL(homepage); } catch { return null; }
  const decoded = fullyDecoded(homepage);
  return isGithubUrl(homepage) || isGithubUrl(decoded) || decoded.includes(owner.toLowerCase())
    ? null
    : homepage;
}

export function publicRepoLabel(e: RepositoryEntity, registry: OwnerTypes): string {
  const entry = entryFor(e, registry);
  return entry.owner_type === 'User' ? entry.full_name.split('/')[1] : entry.full_name;
}

export function publicOwnerType(e: RepositoryEntity, registry: OwnerTypes): OwnerType {
  return entryFor(e, registry).owner_type;
}

export function publicRepoUrl(e: RepositoryEntity, registry: OwnerTypes): string | null {
  const entry = entryFor(e, registry);
  return entry.owner_type === 'Organization'
    ? `https://github.com/${entry.full_name}`
    : safeUserHomepage(e.homepage, entry.full_name.split('/')[0]);
}

export function publicHomepage(e: RepositoryEntity, registry: OwnerTypes): string | null {
  const entry = entryFor(e, registry);
  if (entry.owner_type === 'User') return safeUserHomepage(e.homepage, entry.full_name.split('/')[0]);
  if (e.homepage && isGithubUrl(e.homepage)) return `https://github.com/${entry.full_name}`;
  return e.homepage ?? null;
}

export function publicEntity<T extends RepositoryEntity>(e: T, registry: OwnerTypes): Record<string, unknown> {
  const entry = entryFor(e, registry);
  if (entry.owner_type === 'Organization') {
    return { ...e, homepage: publicHomepage(e, registry), github_repo: entry.full_name };
  }
  const { github_repo: _internalRepo, ...rest } = e;
  return {
    ...rest,
    homepage: safeUserHomepage(e.homepage, entry.full_name.split('/')[0]),
    repository: {
      repo_name: entry.full_name.split('/')[1],
      owner_type: 'user',
      repo_ref: `gh:${entry.repo_id}`,
    },
  };
}

export function publicSnapshot<T extends { entities: RepositoryEntity[] }>(snapshot: T, registry: OwnerTypes): Record<string, unknown> {
  return { ...snapshot, entities: snapshot.entities.map((e) => publicEntity(e, registry)) };
}
