import assignment from '../../data/canary-assignment.json' with { type: 'json' };

export const CROCKFORD = '0123456789ABCDEFGHJKMNPQRSTVWXYZ';
export const HEADLINE_EXPERIMENT = new Set(assignment.pairs.flatMap(p => [p.control, p.treatment]));
export function isTemplateB(entityId, url = `/e/${entityId}/`) {
  const ordinal = CROCKFORD.indexOf(entityId.at(-1));
  if (ordinal < 0) throw new Error(`Invalid Crockford entity id: ${entityId}`);
  const canonical = new URL(url, 'https://evidaxis.org');
  canonical.pathname = canonical.pathname.replace(/\/?$/, '/');
  return ordinal % 2 === 0 && !HEADLINE_EXPERIMENT.has(canonical.href)
    && !HEADLINE_EXPERIMENT.has(`https://evidaxis.org/e/${entityId}/`);
}

// The HTML, sitemap and post-build audit consume the same serialized evidence.
export function isIndexable(record) {
  if (record.display?.template !== 'B') {
    if (isTemplateB(record.entity.entity_id, record.canonical)) return false;
    return record.measurement_state?.history_sufficiency?.state === 'sufficient';
  }
  const measured = (record.readings ?? []).filter(r => r.entity_id === record.entity.entity_id
    && r.source && r.date && (Number.isFinite(r.value)
      || (Array.isArray(r.value) && r.value.length > 0 && r.value.every(Number.isFinite))));
  const primary = new Set(['commits', 'commit_series', 'citations', 'citation_series', 'dependents', 'dependents_series', 'stars']);
  const keys = new Set(measured.filter(r => primary.has(r.key)).map(r => r.key));
  const comparison = record.display.answer_comparison;
  if (record.display.niche_assigned === false) {
    return keys.size >= 2 && comparison === null && !/\bniche median\b/i.test(record.display.answer);
  }
  return keys.size >= 2 && /\bmedian\b/i.test(record.display.answer)
    && measured.some(r => r.key === comparison?.key && Number.isFinite(r.value)
      && Number.isFinite(comparison?.median) && comparison.n > 0
      && record.display.answer.includes(String(comparison.rendered_value)));
}
