import { createHash } from 'node:crypto';

// Maps exist only during generation. No source-to-surrogate dictionary is saved.
export function fixtureAnonymizer(documents, registry, accounts, formerOwners = []) {
  const digest = value => createHash('sha256').update(value.toLowerCase()).digest('hex').slice(0, 16);
  const synthetic = (kind, value) => `fixture-${kind}-${digest(value)}`;
  const projectOwners = new Set(Object.keys(accounts).map(owner => owner.toLowerCase()));
  const owners = new Map(formerOwners.map(owner => [owner.toLowerCase(), synthetic('user', owner)]));
  for (const [repo, entry] of Object.entries(registry.repos)) {
    if (entry.owner_type !== 'User' || projectOwners.has(entry.full_name.split('/')[0].toLowerCase())) continue;
    for (const path of [repo, entry.full_name]) {
      const owner = path.split('/')[0].toLowerCase();
      owners.set(owner, synthetic('user', owner));
    }
  }
  const replacements = new Map();
  const personalRepo = value => typeof value === 'string' && owners.has(value.split('/')[0].toLowerCase());
  const personalRecord = value => {
    const entry = registry.repos[value];
    return entry ? entry.owner_type === 'User' && !projectOwners.has(entry.full_name.split('/')[0].toLowerCase()) : personalRepo(value);
  };
  for (const [repo, entry] of Object.entries(registry.repos)) {
    for (const path of [repo, entry.full_name]) if (personalRepo(path)) {
      replacements.set(path.toLowerCase(), `${owners.get(path.split('/')[0].toLowerCase())}/${synthetic('repo', path)}`);
    }
  }
  const personalIds = new Set();
  function walk(value, visit, personal = false) {
    if (!value || typeof value !== 'object') return;
    const own = personal || personalRecord(value.github_repo) || personalIds.has(value.entity_id);
    visit(value, own);
    for (const [key, child] of Object.entries(value)) walk(child, visit, own || personalRecord(key));
  }
  for (const doc of documents) walk(doc, value => {
    if (value.entity_id && personalRecord(value.github_repo)) personalIds.add(value.entity_id);
  });
  for (const doc of documents) walk(doc, (value, personal) => {
    if (!personal) return;
    if (typeof value.homepage === 'string' && value.homepage && !/github\.com\//i.test(value.homepage)) {
      replacements.set(value.homepage.toLowerCase(), `https://${synthetic('home', value.homepage)}.invalid/`);
    }
    if (typeof value.package === 'string' && value.package) {
      replacements.set(value.package.toLowerCase(), owners.get(value.package.toLowerCase()) ?? synthetic('package', value.package));
    }
  });
  // Distinctive handles also occur in titles, notes and provenance. Short handles
  // are replaced only as exact values or in account contexts, not ordinary prose.
  for (const [owner, replacement] of owners) if (owner.length >= 4 && !/^\d+$/.test(owner)) replacements.set(owner, replacement);
  const escaped = text => text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  for (const [source, replacement] of [...replacements]) {
    replacements.set(encodeURIComponent(source).toLowerCase(), encodeURIComponent(replacement));
  }
  const pattern = new RegExp(`(?<![a-z0-9_-])(?:${[...replacements.keys()].sort((a, b) => b.length - a.length || a.localeCompare(b, 'en')).map(escaped).join('|')})(?![a-z0-9_-])`, 'gi');
  function text(value) {
    const exact = replacements.get(value.toLowerCase()) ?? owners.get(value.toLowerCase());
    if (exact) return exact;
    return value.replace(pattern, match => replacements.get(match.toLowerCase()))
      .replace(/((?:github\.com|githubusercontent\.com|api\.github\.com\/repos)\/)([a-z0-9-]+)/gi,
        (_, prefix, owner) => prefix + (owners.get(owner.toLowerCase()) ?? owner))
      .replace(/([a-z0-9-]+)(\.github\.io)/gi, (_, owner, suffix) => (owners.get(owner.toLowerCase()) ?? owner) + suffix)
      .replace(/@([a-z0-9-]+)/gi, (_, owner) => '@' + (owners.get(owner.toLowerCase()) ?? owner));
  }
  function anonymize(value) {
    if (typeof value === 'string') return text(value);
    if (Array.isArray(value)) return value.map(anonymize);
    if (!value || typeof value !== 'object') return value;
    return Object.fromEntries(Object.entries(value).map(([key, child]) => [
      // Schema keys are not account identities; repository keys are locators.
      key.includes('/') ? text(key) : key, anonymize(child),
    ]));
  }
  return anonymize;
}
