import { describe, expect, it } from 'vitest';
import {
  ENTITY_LEXICON_WINDOW,
  entityLexiconAllowed,
  normalizeLexiconSurface,
  scanEntityLexicon,
  scanEntityPageWide,
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

  // Saturday 2026-11-07: the November census admitted "watch-skill"; the guard
  // read the system's own name as our language and blocked the whole release.
  // The class is "a third-party name contains a guarded word", not one word.
  const GUARDED_WORD_SAMPLES = [
    'no signal published', 'verdict', 'path to rising', 'decelerating', 'not rising', 'gate shut',
    'below gate', 'needs to recover', 'declining', 'slowdown', 'losing momentum', 'falling behind',
    'watch', 'tracked', 'single-axis', 'calibration',
  ];

  it.each(GUARDED_WORD_SAMPLES.flatMap((word) => [`${word}-skill`, `my ${word} kit`, `${word}`]))(
    'does not read the system name "%s" as entity-adjacent or verdict language',
    (name) => {
      // Shape of the built page (e/e_740X7BVD9MZ, 2026-11-07): blocks are space-separated.
      const html = `<h1>${name}</h1> <p>Others / ${name} ${name} repo · <a href="/e/x/">${name}</a> holds a score.</p>`;
      const json = JSON.stringify({ entity: { name }, title: `${name} weekly reading` });
      expect(scanEntityLexicon(html, name)).toHaveLength(0);
      expect(scanEntityLexicon(json, name)).toHaveLength(0);
      expect(scanEntityPageWide(html, [name])).toHaveLength(0);
      expect(scanEntityPageWide(json, [name])).toHaveLength(0);
    },
  );

  it('still rejects a guarded word written next to a name that contains it, once', () => {
    expect(scanEntityLexicon('We watch watch-skill closely.', 'watch-skill').map((f) => f.term))
      .toEqual(['watch']);
    expect(scanEntityPageWide('verdict-ai: the verdict is in.', ['verdict-ai']).map((f) => f.term))
      .toEqual(['verdict']);
  });

  it('still rejects our phrase when the system name is only one word of it', () => {
    // A name may equal part of a guarded phrase; only a term wholly inside the name is the name.
    expect(scanEntityLexicon('Momentum is losing momentum.', 'Momentum').map((f) => f.term))
      .toEqual(['losing momentum']);
    expect(scanEntityLexicon('Rising is not rising.', 'Rising').map((f) => f.term))
      .toEqual(['not rising']);
    expect(scanEntityPageWide('Behind ships. Behind is falling behind.', ['Behind']).map((f) => f.term))
      .toEqual(['falling behind']);
  });

  it('does not exempt a name that exists only after separate HTML blocks are flattened', () => {
    // Codex review 2026-11-08: "Our verdict</p> <p>AI ..." must not read as the name "verdict AI".
    const html = '<h1>verdict AI</h1> <p>Our verdict</p> <p>AI measurements follow.</p>';
    expect(scanEntityLexicon(html, 'verdict AI').map((f) => f.term)).toContain('verdict');
    expect(scanEntityPageWide(html, ['verdict AI']).map((f) => f.term)).toEqual(['verdict']);
    // Inline tags inside one block still form the name.
    expect(scanEntityPageWide('<p><a href="/e/x/">verdict <strong>AI</strong></a> ships.</p>', ['verdict AI']))
      .toHaveLength(0);
    // Codex review round 2: every non-inline element is a boundary, known or not.
    for (const tag of ['fieldset', 'menu', 'dialog', 'legend', 'option', 'x-card', 'x_card-box', 'span.card-box']) {
      const split = `<h1>verdict AI</h1> <${tag}>Our verdict</${tag}> <${tag}>AI measurements follow.</${tag}>`;
      expect(scanEntityLexicon(split, 'verdict AI').map((f) => f.term)).toContain('verdict');
      expect(scanEntityPageWide(split, ['verdict AI']).map((f) => f.term)).toEqual(['verdict']);
    }
  });

  it('never lets an inserted block mark complete a name (Codex review round 4)', () => {
    expect(scanEntityPageWide('<p>Our verdict</p> <p>AI results.</p>', ['verdict \ue000AI']).map((f) => f.term))
      .toEqual(['verdict']);
    expect(scanEntityLexicon('<h1>Example</h1><!-- <div> -->verdict', 'Example').map((f) => f.term))
      .toEqual(['verdict']);
  });

  it('keeps a literal U+241E in the text: it is neither a block mark nor removed', () => {
    // Codex review round 2: a literal mark character must not shift name spans or vanish.
    expect(scanEntityPageWide(JSON.stringify({ text: `${'\u241e'.repeat(8)}verdict Example` }), ['Example'])
      .map((f) => f.term)).toEqual(['verdict']);
    expect(scanEntityPageWide(`<p>Example verdict\u241eAI</p>`, ['Example']).map((f) => f.term))
      .toEqual(['verdict']);
    expect(scanEntityLexicon(`<p>Example verdict\u241eAI</p>`, 'Example').map((f) => f.term))
      .toEqual(['verdict']);
  });

  it('keeps the plain lexicon surface byte-identical to the pre-2026-11-08 normalizer', () => {
    // Block marks only steer name spans; the text the guards read must not change.
    const before = (content: string) => (!/<[a-z!/][\s\S]*>/i.test(content) ? content : content
      .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, '')
      .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, '')
      .replace(/<[^>]+>/g, '')
      .replace(/&nbsp;|&#160;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&quot;|&#34;/gi, '"')
      .replace(/&#39;|&apos;/gi, "'")
      .replace(/&lt;/gi, '<')
      .replace(/&gt;/gi, '>')
      .replace(/\s+/g, ' ')
      .trim());
    for (const html of [
      '<h1>verdict AI</h1> <p>Our verdict</p> <p>AI measurements follow.</p>',
      '<div><p>a</p></div><p>b</p>',
      '  <p> a </p>  <p> b </p>  ',
      '<p>a&nbsp;</p>&nbsp;<p>&nbsp;b</p>',
      '<p>gate sh<strong>u</strong>t</p><br/><li>x</li><li>y</li>',
      '<head><title>T</title><style>p{}</style></head><body><script>var a=1</script><p>z</p></body>',
      '<section>\n\t<h2>Sources</h2>\n<ul><li><a href="/e/x/">watch-skill</a></li></ul></section>',
      '<p>keep \u241e literal</p><fieldset>\ue000 and \ue001</fieldset><x-card>c</x-card><!-- note --><img src="a">',
      '<h1>Example</h1><!-- <div> -->verdict',
      'plain text without tags',
    ]) {
      expect(normalizeLexiconSurface(html)).toBe(before(html));
    }
  });

  it('does not let the window edge cut a second mention of the name into a guarded word', () => {
    const spacer = ' '.repeat(ENTITY_LEXICON_WINDOW - 'watch'.length);
    // The window around the first mention ends inside "watch-skill" of the second one.
    expect(scanEntityLexicon(`watch-skill${spacer}watch-skill`, 'watch-skill')).toHaveLength(0);
  });

  it('keeps the page-wide scan unchanged when no identifiers are given', () => {
    expect(scanEntityPageWide('verdict-ai ships weekly.')).toHaveLength(1);
  });

  it('keeps the explicit terminology-page allowlist narrow', () => {
    expect(entityLexiconAllowed('methodology/current/index.html')).toBe(true);
    expect(entityLexiconAllowed('glossary/index.html')).toBe(true);
    expect(entityLexiconAllowed('e/e_TEST/index.html')).toBe(false);
  });
});
