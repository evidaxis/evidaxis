// Small structural reader for generated HTML; scripts stay opaque so markup
// inside analytics strings cannot become a false card, link or measurement.
export const decode = text => text.replace(/&(#x[\da-f]+|#\d+|amp|lt|gt|quot|apos|nbsp);/gi, (all, key) => {
  if (key[0] === '#') return String.fromCodePoint(key[1].toLowerCase() === 'x' ? parseInt(key.slice(2), 16) : +key.slice(1));
  return { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ' }[key.toLowerCase()] ?? all;
});
export function parseHTML(html) {
  const root = { tag: 'root', attrs: {}, children: [] }, stack = [root];
  const tokens = /<!--[\s\S]*?-->|<![^>]*>|<(script|style)\b([^>]*)>([\s\S]*?)<\/\1\s*>|<\/?[a-z][^>]*>|[^<]+/gi;
  const attrs = raw => Object.fromEntries([...raw.matchAll(/([^\s=/>]+)(?:\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s>]+)))?/g)].map(m => [m[1].toLowerCase(), decode(m[2] ?? m[3] ?? m[4] ?? '')]));
  for (const match of html.matchAll(tokens)) {
    const token = match[0];
    if (token.startsWith('<!')) continue;
    if (match[1]) { stack.at(-1).children.push({ tag: match[1].toLowerCase(), attrs: attrs(match[2]), children: [match[3]] }); continue; }
    if (token.startsWith('</')) {
      const tag = token.slice(2, -1).trim().toLowerCase(), i = stack.findLastIndex(n => n.tag === tag);
      if (i > 0) stack.length = i;
    } else if (token[0] === '<') {
      const parts = token.match(/^<([^\s/>]+)([\s\S]*?)\/?\s*>$/);
      if (!parts) continue;
      const node = { tag: parts[1].toLowerCase(), attrs: attrs(parts[2]), children: [] };
      stack.at(-1).children.push(node);
      if (!/^(area|base|br|col|embed|hr|img|input|link|meta|param|source|track|wbr)$/.test(node.tag) && !token.endsWith('/>')) stack.push(node);
    } else stack.at(-1).children.push(decode(token));
  }
  return root;
}
export const hasClass = (node, name) => (node.attrs.class ?? '').split(/\s+/).includes(name);
export function elements(node, predicate) {
  if (typeof node === 'string') return [];
  return [...(predicate(node) ? [node] : []), ...node.children.flatMap(child => elements(child, predicate))];
}
export function plainText(node, omit = () => false) {
  if (typeof node === 'string') return node;
  if (omit(node)) return '';
  return node.children.map(child => plainText(child, omit)).join(' ');
}
export const cardArticle = tree => elements(tree, n => 'data-card-b' in n.attrs)[0];
