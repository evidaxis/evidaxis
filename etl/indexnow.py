#!/usr/bin/env python3
"""
IndexNow ping — notify Bing / Yandex / Seznam (and, downstream, ChatGPT Search via Bing)
of changed URLs on each snapshot. Reads the live sitemap, POSTs the URL list to IndexNow.
Run after each deploy. Cheapest fast-index path for a new domain.
"""
import json, re, sys, urllib.request

HOST = "evidaxis.org"
KEY = "be23b52b58b549cfa47bac03cb09819c"
KEY_LOCATION = f"https://{HOST}/{KEY}.txt"
SITEMAP = f"https://{HOST}/sitemap-0.xml"


def fetch(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "evidaxis-indexnow/1"}), timeout=30).read().decode()


def main():
    xml = fetch(SITEMAP)
    urls = re.findall(r"<loc>([^<]+)</loc>", xml)
    if not urls:
        print("no URLs in sitemap"); return
    payload = json.dumps({"host": HOST, "key": KEY, "keyLocation": KEY_LOCATION, "urlList": urls}).encode()
    req = urllib.request.Request("https://api.indexnow.org/indexnow", data=payload,
                                 headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"IndexNow: HTTP {r.status} · submitted {len(urls)} URLs (200/202 = accepted)")
    except urllib.error.HTTPError as e:
        print(f"IndexNow: HTTP {e.code} · {len(urls)} URLs · {e.reason}")


if __name__ == "__main__":
    main()
