import { describe, expect, it } from 'vitest';
import {
  ENTITY_LEXICON_WINDOW,
  entityLexiconAllowed,
  scanEntityLexicon,
} from '../../scripts/entity-lexicon.mjs';

describe('entity discovery lexicon', () => {
  it.each([
    'gate shut',
    'no signal published',
    'Verdict',
    'path to Rising',
    'needs to recover',
  ])('rejects "%s" inside the system-name context window', (term) => {
    const content = `System Delta${' '.repeat(40)}${term}`;
    expect(scanEntityLexicon(content, 'System Delta').map((finding) => finding.term)).toContain(term);
  });

  it('does not reject the same term outside the context window', () => {
    const content = `System Delta${' '.repeat(ENTITY_LEXICON_WINDOW + 1)}gate shut`;
    expect(scanEntityLexicon(content, 'System Delta')).toHaveLength(0);
  });

  it('matches names case-insensitively at complete word boundaries', () => {
    expect(scanEntityLexicon('system delta gate shut', 'System Delta')).toHaveLength(1);
    expect(scanEntityLexicon('System DeltaPro gate shut', 'System Delta')).toHaveLength(0);
    expect(scanEntityLexicon('RAIL gate shut', 'AI')).toHaveLength(0);
    expect(scanEntityLexicon('AI gate shut', 'AI')).toHaveLength(1);
  });

  it('removes HTML tags without letting them split forbidden words', () => {
    expect(scanEntityLexicon('<p>System Delta gate sh<strong>u</strong>t</p>', 'System Delta')
      .map((finding) => finding.term)).toContain('gate shut');
  });

  it('scans parsed JSON string values instead of a raw cross-field window', () => {
    expect(scanEntityLexicon(JSON.stringify({ name: 'System Delta', status: 'gate shut' }), 'System Delta'))
      .toHaveLength(0);
    expect(scanEntityLexicon(JSON.stringify({ title: 'System Delta gate shut' }), 'System Delta'))
      .toHaveLength(1);
  });

  it('does not treat a forbidden word that is the exact system name as a violation', () => {
    expect(scanEntityLexicon('Verdict', 'Verdict')).toHaveLength(0);
    expect(scanEntityLexicon('Watch', 'Watch')).toHaveLength(0);
    expect(scanEntityLexicon('Verdict gate shut', 'Verdict').map((finding) => finding.term))
      .toContain('gate shut');
  });

  it('reliably rejects the same adjacent-word injection on repeated scans', () => {
    const injected = 'System Delta forbidden spacer gate shut';
    expect(scanEntityLexicon(injected, 'System Delta')).toHaveLength(1);
    expect(scanEntityLexicon(injected, 'System Delta')).toHaveLength(1);
  });

  it('keeps the explicit terminology-page allowlist narrow', () => {
    expect(entityLexiconAllowed('methodology/current/index.html')).toBe(true);
    expect(entityLexiconAllowed('glossary/index.html')).toBe(true);
    expect(entityLexiconAllowed('e/e_TEST/index.html')).toBe(false);
  });
});
