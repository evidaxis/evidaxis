import { describe, expect, it } from 'vitest';
import { LIST_PAGE_SIZE, pageCount, pageItems, pagePath } from './pagination';

describe('large-list pagination', () => {
  it('leaves lists at or below 250 untouched', () => {
    const rows = Array.from({ length: 250 }, (_, index) => index);
    expect(pageCount(rows.length)).toBe(1);
    expect(pageItems(rows, 1)).toBe(rows);
  });

  it('uses 200-row pages only above the threshold', () => {
    const rows = Array.from({ length: 401 }, (_, index) => index);
    expect(pageCount(rows.length)).toBe(3);
    expect(pageItems(rows, 1)).toHaveLength(LIST_PAGE_SIZE);
    expect(pageItems(rows, 2)).toEqual(rows.slice(200, 400));
    expect(pageItems(rows, 3)).toEqual([400]);
    expect(() => pageItems(rows, 4)).toThrow('invalid page');
  });

  it('keeps page one at the base URL', () => {
    expect(pagePath('/coverage/', 1)).toBe('/coverage/');
    expect(pagePath('/coverage/', 2)).toBe('/coverage/page/2/');
  });
});
