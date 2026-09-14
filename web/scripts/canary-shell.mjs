import { createHash } from 'node:crypto';

// Byte-pinned control shell from the pre-canary render. Task 1 intentionally
// changes descriptions, typed status bodies, JSON-LD, and component CSS; this
// shell selects the remaining byte-stable title, identity, navigation,
// breadcrumb, receipt, and citation regions. Treatment-marker checks below
// cover the intentionally excluded body regions.
export const controlShellPatterns = [
  /<title>[\s\S]*?<\/title>/,
  /<link rel="canonical"[^>]*>/,
  /<meta property="og:title"[^>]*>/,
  /<meta property="og:url"[^>]*>/,
  /<link rel="alternate" type="application\/json"[^>]*>/,
  /<link rel="cite-as"[^>]*>/,
  /<nav class="nav">[\s\S]*?<\/nav>/,
  /<nav class="crumb mono"[\s\S]*?<\/nav>/,
  /<div class="receipt mono"[\s\S]*?<\/div>/,
  /<p class="cite mono muted"[\s\S]*?<\/p>/,
  /<p class="cite-urn mono muted"[\s\S]*?<\/p>/,
];
// Weekly snapshot motion legitimately rewrites date-bearing shell tokens on
// control and treatment alike: the receipt's snapshot id and period, the nav
// snapshot link, and the claim-URN date in cite-as and the citation footer.
// The 2026-08-22 snapshot proved the unmasked pin fails closed on ordinary
// data motion (publication stalled >31 h on 24 false positives). Masking pins
// every remaining byte - methodology version included, so a methodology bump
// still demands a conscious baseline regeneration.
export const maskWeeklyTokens = (shell) => shell
  .replace(/(snapshot <b[^>]*>)[0-9a-f]+(<\/b>)/g, '$1SNAPSHOT_ID$2')
  .replace(/\b\d{4}-\d{2}-\d{2}\b/g, 'DATE')
  .replace(/\b\d{4}-w\d{2}\b/g, 'PERIOD');
export const controlShellHash = (html) => createHash('sha256')
  .update(maskWeeklyTokens(controlShellPatterns.map((pattern) => html.match(pattern)?.[0] ?? 'MISSING').join('\n')))
  .digest('hex');
