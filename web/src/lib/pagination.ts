export const LIST_PAGINATION_THRESHOLD = 250;
export const LIST_PAGE_SIZE = 200;

export function pageCount(itemCount: number): number {
  return itemCount > LIST_PAGINATION_THRESHOLD ? Math.ceil(itemCount / LIST_PAGE_SIZE) : 1;
}

export function pageItems<T>(items: T[], page: number): T[] {
  const total = pageCount(items.length);
  if (!Number.isInteger(page) || page < 1 || page > total) throw new Error(`invalid page ${page} of ${total}`);
  if (total === 1) return items;
  const start = (page - 1) * LIST_PAGE_SIZE;
  return items.slice(start, start + LIST_PAGE_SIZE);
}

export function pagePath(basePath: string, page: number): string {
  const base = basePath.endsWith('/') ? basePath : `${basePath}/`;
  return page === 1 ? base : `${base}page/${page}/`;
}
