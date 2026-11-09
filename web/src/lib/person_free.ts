import { FLOOR_HANDLES, buildHandleIndex, classifyRegistry, validOwnerEntry, privacyDiagnostic, revealsHandleText, lenientDecoded, staleSlugHits } from './personFree.mjs';
export type OwnerType = 'Organization' | 'User';

export type OwnerEntry = {
  owner_type: OwnerType;
  repo_id: number;
  full_name: string;
};

export type OwnerTypes = {
  schema_version: 'owner_types_1';
  repos: Record<string, OwnerEntry>;
  // Run-local input: former project owners may have no current registry row.
  projectAccounts?: Record<string, unknown>;
};

type RepositoryEntity = {
  github_repo: string;
  homepage?: string | null;
  [key: string]: unknown;
};

function entryFor(e: RepositoryEntity, registry: OwnerTypes): OwnerEntry {
  const entry = registry?.repos?.[e.github_repo];
  if (!validOwnerEntry(entry)) {
    throw new Error(privacyDiagnostic('registry', 'classification', e.github_repo));
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

const CLASSIFICATIONS = new WeakMap<OwnerTypes, ReturnType<typeof classifyRegistry>>();
export function registryClassification(registry: OwnerTypes) {
  let classified = CLASSIFICATIONS.get(registry);
  if (!classified) {
    classified = classifyRegistry(registry.repos, registry.projectAccounts ?? {}, FLOOR_HANDLES);
    CLASSIFICATIONS.set(registry, classified);
  }
  return classified;
}
const HANDLE_INDEXES = new WeakMap<OwnerTypes, ReturnType<typeof buildHandleIndex>>();
export function userHandleIndex(registry: OwnerTypes) {
  let index = HANDLE_INDEXES.get(registry);
  if (!index) {
    index = buildHandleIndex(registryClassification(registry).handles);
    HANDLE_INDEXES.set(registry, index);
  }
  return index;
}
export const revealsHandle = (text: string | null | undefined, registry: OwnerTypes) => {
  if (!text) return false;
  const c = registryClassification(registry);
  return revealsHandleText(text, userHandleIndex(registry))
    || staleSlugHits(lenientDecoded(text).toLowerCase(), c.stalePaths, c.canonicalPaths).length > 0;
};

function isPublicRepo(e: RepositoryEntity, registry: OwnerTypes) {
  return registryClassification(registry).publicRepos.has(e.github_repo);
}

export const neutralName = (entityId: string) => `System ${entityId}`;
export function publicName(e: { name: string; entity_id: string }, registry: OwnerTypes): string {
  return revealsHandle(e.name, registry) ? neutralName(e.entity_id) : e.name;
}

export function publicRepoLabel(e: RepositoryEntity, registry: OwnerTypes): string {
  const entry = entryFor(e, registry);
  if (isPublicRepo(e, registry) && !revealsHandle(entry.full_name, registry)) return entry.full_name;
  const repoName = entry.full_name.split('/')[1];
  return revealsHandle(repoName, registry) ? 'repository not shown' : repoName;
}

// Dependency labels can embed personal tokens in either published component.
export function publicPackageLabel(system: string, pkg: string, registry: OwnerTypes): string {
  return revealsHandle(system, registry) || revealsHandle(pkg, registry) ? 'package not shown' : `${system}/${pkg}`;
}

export function publicOwnerType(e: RepositoryEntity, registry: OwnerTypes): OwnerType {
  entryFor(e, registry);
  return isPublicRepo(e, registry) ? 'Organization' : 'User';
}

export function publicRepoUrl(e: RepositoryEntity, registry: OwnerTypes): string | null {
  const entry = entryFor(e, registry);
  return isPublicRepo(e, registry) && !revealsHandle(entry.full_name, registry)
    ? `https://github.com/${entry.full_name}` : publicHomepage(e, registry);
}

export function publicHomepage(e: RepositoryEntity, registry: OwnerTypes): string | null {
  const entry = entryFor(e, registry);
  if (!e.homepage) return null;
  try { new URL(e.homepage); } catch { return null; }
  if (isPublicRepo(e, registry) && isGithubUrl(e.homepage)) {
    return revealsHandle(entry.full_name, registry) ? null : `https://github.com/${entry.full_name}`;
  }
  const decoded = lenientDecoded(e.homepage).toLowerCase();
  if (revealsHandle(e.homepage, registry)) return null;
  const index = userHandleIndex(registry);
  const owners = [e.github_repo.split('/')[0], entry.full_name.split('/')[0]].map(s => s.toLowerCase());
  // Rule f's prose exemption does not apply to the known owner's own homepage.
  if (owners.some(owner => index.all.has(owner) && decoded.includes(owner))) return null;
  if (!isPublicRepo(e, registry) && (isGithubUrl(e.homepage) || isGithubUrl(decoded))) return null;
  return e.homepage;
}

// Apply to nested text and packages too: JSON twins must be no wider than cards.
export function publicFields<T>(value: T, registry: OwnerTypes, dependency = false): T {
  if (dependency && typeof value === 'string' && revealsHandle(value, registry)) return 'package not shown' as T;
  if (Array.isArray(value)) return value.map(v => publicFields(v, registry, dependency)) as T;
  if (!value || typeof value !== 'object') return value;
  const out: Record<string, unknown> = {};
  for (const [key, child] of Object.entries(value)) {
    if (typeof child === 'string' && revealsHandle(child, registry)) {
      if (key === 'note') continue;
      if (['proxy', 'description', 'summary'].includes(key)) { out[key] = null; continue; }
      if (key === 'package') { out[key] = 'package not shown'; continue; }
    }
    out[key] = publicFields(child, registry, dependency || key === 'deps');
  }
  return out as T;
}

export function publicEntity<T extends RepositoryEntity>(e: T, registry: OwnerTypes): Record<string, unknown> {
  const entry = entryFor(e, registry);
  e = publicFields(e, registry);
  if ((typeof e.name === 'string' && revealsHandle(e.name, registry)) || (typeof e.slug === 'string' && revealsHandle(e.slug, registry))) {
    e = { ...e, name: neutralName(String(e.entity_id)), slug: String(e.entity_id).toLowerCase() };
  }
  if (isPublicRepo(e, registry) && !revealsHandle(entry.full_name, registry)) {
    return { ...e, homepage: publicHomepage(e, registry), github_repo: entry.full_name };
  }
  const { github_repo: _internalRepo, ...rest } = e;
  return {
    ...rest,
    homepage: publicHomepage(e, registry),
    repository: {
      repo_name: revealsHandle(entry.full_name.split('/')[1], registry) ? null : entry.full_name.split('/')[1],
      owner_type: 'user',
      repo_ref: `gh:${entry.repo_id}`,
    },
  };
}

export function publicSnapshot<T extends { entities: RepositoryEntity[] }>(snapshot: T, registry: OwnerTypes): Record<string, unknown> {
  return { ...snapshot, entities: snapshot.entities.map((e) => publicEntity(e, registry)) };
}
