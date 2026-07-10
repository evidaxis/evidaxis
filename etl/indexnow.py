#!/usr/bin/env python3
"""
IndexNow ping — notify Bing / Yandex / Seznam (and, downstream, ChatGPT Search via Bing)
of changed URLs on each snapshot. Reads the live sitemap-index, walks every child
sitemap, POSTs the URL list (+ /llms.txt) to IndexNow. Run after each deploy.
Cheapest fast-index path for a new domain.
"""
import json
import re
import urllib.request

HOST = "evidaxis.org"
KEY = "be23b52b58b549cfa47bac03cb09819c"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
# Prefer the sitemap index so multi-shard deploys are covered; never hardcode sitemap-0.
SITEMAP_INDEX = f"https://{HOST}/sitemap-index.xml"
# Back-compat alias used by older call sites / tests.
SITEMAP = SITEMAP_INDEX
LLMS_TXT = f"https://{HOST}/llms.txt"


def fetch(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "evidaxis-indexnow/1"}),
        timeout=30,
    ).read().decode()


def extract_locs(xml: str) -> list[str]:
    """Pull every <loc>…</loc> value from a sitemap or sitemap-index document."""
    return re.findall(r"<loc>([^<]+)</loc>", xml)


def is_sitemap_index(xml: str) -> bool:
    """True when the document is a sitemap index (lists child sitemaps), not a urlset."""
    return "sitemapindex" in xml.lower()


def collect_urls_from_sitemaps(index_xml: str, child_xml_by_url: dict[str, str]) -> list[str]:
    """Pure offline parser: expand a sitemap-index (or bare urlset) into page URLs.

    `child_xml_by_url` maps each child-sitemap URL (from the index <loc>s) to its
    XML body. When `index_xml` is already a urlset, children are ignored.
    """
    if is_sitemap_index(index_xml):
        urls: list[str] = []
        for child_url in extract_locs(index_xml):
            child_xml = child_xml_by_url.get(child_url, "")
            urls.extend(extract_locs(child_xml))
        return urls
    return extract_locs(index_xml)


def collect_url_list(fetch_fn=None) -> list[str]:
    """Fetch sitemap-index (or fallback urlset), walk children, append /llms.txt.

    `fetch_fn` defaults to module-level `fetch` at call time (so tests can
    monkeypatch indexnow.fetch without fighting a bound default argument).
    """
    get = fetch_fn if fetch_fn is not None else fetch
    index_xml = get(SITEMAP_INDEX)
    if is_sitemap_index(index_xml):
        child_urls = extract_locs(index_xml)
        child_xml_by_url = {u: get(u) for u in child_urls}
        urls = collect_urls_from_sitemaps(index_xml, child_xml_by_url)
    else:
        # Live deploy may expose a single urlset at the index URL; treat as pages.
        urls = collect_urls_from_sitemaps(index_xml, {})
    if LLMS_TXT not in urls:
        urls.append(LLMS_TXT)
    return urls


def main():
    urls = list(dict.fromkeys(collect_url_list()))  # dedup, keep order (review nit 2026-07-10)
    if not urls:
        print("no URLs in sitemap")
        return
    payload = json.dumps(
        {"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}
    ).encode()
    req = urllib.request.Request(
        "https://api.indexnow.org/indexnow",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: HTTP {r.status} · submitted {len(urls)} URLs (200/202 = accepted)")
    except urllib.error.HTTPError as e:
        print(f"IndexNow: HTTP {e.code} · {len(urls)} URLs · {e.reason}")


if __name__ == "__main__":
    main()
