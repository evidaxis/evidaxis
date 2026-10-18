#!/usr/bin/env python3
"""Open model families: OpenAlex citations of technical reports, and GitHub commit
activity of the family's organization repositories in one Evidaxis snapshot.

    python3 build.py --fetch     # write raw/ from arXiv and OpenAlex (network)
    python3 build.py --offline   # rebuild the CSV files and chart.svg from raw/

Standard library only. --offline does not open a network connection.
Data and outputs: CC0-1.0.
"""
from __future__ import annotations

import argparse
import csv
import difflib
import html
import json
import os
import re
import statistics
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
SNAPSHOT = REPO / "data/snapshots/2026-10-17/snapshot.json"
OWNERS = REPO / "etl/owner_types.json"
RAW = HERE / "raw"
YEARS = (2023, 2024, 2025, 2026)

# "technical report" must begin by this 0-based word, after the family name,
# so a derivative title that merely contains both phrases is not counted.
TECHNICAL_WORD_MAX = 6
RETRIES = 3  # one dropped connection should not turn a report into "not found"
ARXIV_PAUSE_S = 3  # export.arxiv.org asks for 3 seconds between requests
OPENALEX_SELECT = ",".join([
    "id", "display_name", "publication_year", "doi", "ids",
    "cited_by_count", "counts_by_year", "locations",
])
# publication_date is a day. counts_by_year has no month, so 2026 cannot be
# matched to the same span of 2025. type distinguishes a journal article.
WORK_SELECT = OPENALEX_SELECT + ",publication_date,type"
# Title repair omits locations and every author field. per-page=8 is the
# existing title-search page size.
TITLE_SEARCH_SELECT = "id,display_name,doi,ids,publication_year,cited_by_count,counts_by_year"
# Citation totals in commit e88cf7fbc0, before the 2026-10-18 link correction.
FIRST_VERSION_CITES = {
    "Qwen": (1, 131, 251, 325),
    "DeepSeek": (0, 25, 539, 1046),
    "Llama": (1205, 3296, 2239, 376),
    "Gemma": (0, 108, 274, 129),
    "OLMo": (0, 16, 32, 23),
    "GLM": (85, 168, 188, 21),
    "Kimi": (0, 0, 12, 8),
    "InternLM": (0, 3, 22, 4),
    "Mistral": (8, 127, 184, 143),
    "Phi": (23, 119, 175, 74),
}
FIRST_VERSION_DENOM_2025 = 3916

# Canonical generation reports: the family's own write-ups, including papers
# whose title does not contain the words "technical report".
# Title search adds later reports whose title leads with the family name.
FAMILIES = [
    {
        "family": "Qwen",
        "stems": ("qwen",),
        "orgs": ("qwenlm", "qwenaudio"),
        "name_re": None,
        "canonical": ("2309.16609", "2407.10671", "2412.15115", "2505.09388"),
        "arxiv_query": 'ti:"technical report" AND (ti:Qwen OR ti:Qwen2 OR ti:Qwen3)',
    },
    {
        "family": "DeepSeek",
        "stems": ("deepseek",),
        "orgs": ("deepseek-ai",),
        "name_re": None,
        "canonical": ("2401.02954", "2405.04434", "2412.19437", "2501.12948"),
        "arxiv_query": 'ti:"technical report" AND (ti:DeepSeek OR ti:DeepSeek-V2 OR ti:DeepSeek-V3 OR ti:DeepSeek-R1)',
    },
    {
        "family": "Llama",
        "stems": ("llama",),
        "orgs": ("meta-llama",),
        "name_re": None,
        "canonical": ("2302.13971", "2307.09288", "2407.21783"),
        "arxiv_query": 'ti:"technical report" AND (ti:Llama OR ti:LLaMA)',
    },
    {
        "family": "Gemma",
        "stems": ("gemma",),
        "orgs": ("google", "google-deepmind", "google-research"),
        "name_re": r"gemma",
        "canonical": ("2403.08295", "2408.00118", "2503.19786"),
        "arxiv_query": 'ti:"technical report" AND ti:Gemma',
    },
    {
        "family": "OLMo",
        "stems": ("olmo",),
        "orgs": ("allenai",),
        "name_re": r"(^|[^A-Za-z])olmo([^A-Za-z]|$)",
        "canonical": ("2402.00838", "2501.00656"),
        "arxiv_query": 'ti:"technical report" AND (ti:OLMo OR ti:"OLMo 2")',
    },
    {
        "family": "GLM",
        "stems": ("glm", "chatglm"),
        "orgs": ("zai-org", "thudm"),
        "name_re": r"(^|[^A-Za-z])glm([^A-Za-z]|$)",
        "canonical": ("2210.02414", "2406.12793"),
        "arxiv_query": 'ti:"technical report" AND (ti:GLM OR ti:ChatGLM OR ti:GLM-4)',
    },
    {
        "family": "Kimi",
        "stems": ("kimi",),
        "orgs": ("moonshotai",),
        "name_re": r"kimi",
        "canonical": ("2501.12599", "2504.07491"),
        "arxiv_query": 'ti:"technical report" AND ti:Kimi',
    },
    {
        "family": "InternLM",
        "stems": ("internlm",),
        "orgs": ("internlm",),
        "name_re": None,
        "canonical": ("2403.17297",),
        "arxiv_query": 'ti:"technical report" AND (ti:InternLM OR ti:InternLM2)',
    },
    {
        "family": "Mistral",
        "stems": ("mistral", "mixtral"),
        "orgs": ("mistralai",),
        "name_re": None,
        "canonical": ("2310.06825", "2401.04088"),
        "arxiv_query": 'ti:"technical report" AND (ti:Mistral OR ti:Mixtral)',
    },
    {
        "family": "Phi",
        "stems": ("phi",),
        "orgs": ("microsoft",),
        "name_re": r"^phi",
        "canonical": ("2306.11644", "2309.05463", "2404.14219", "2412.08905"),
        "arxiv_query": 'ti:"technical report" AND (ti:Phi-1 OR ti:Phi-2 OR ti:Phi-3 OR ti:Phi-4 OR ti:"phi-1.5")',
    },
]

ATOM_NS = {
    "a": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}

# The Atom author element is a person's name. The open repo does not store it.
_AUTHOR_ELEMENT = re.compile(
    r"[ \t]*<(?:[A-Za-z_][\w.-]*:)?author(?:\s[^>]*)?>.*?</(?:[A-Za-z_][\w.-]*:)?author>[ \t]*\n?",
    re.DOTALL,
)
_AUTHOR_EMPTY = re.compile(
    r"[ \t]*<(?:[A-Za-z_][\w.-]*:)?author(?:\s[^>]*)?/>[ \t]*\n?",
)


def strip_arxiv_authors(xml_bytes: bytes) -> bytes:
    text = xml_bytes.decode("utf-8")
    text = _AUTHOR_ELEMENT.sub("", text)
    text = _AUTHOR_EMPTY.sub("", text)
    return text.encode("utf-8")


def norm_title(s: str) -> str:
    s = (s or "").casefold().replace("–", " ").replace("—", " ")
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return " ".join(s.split())


def title_ratio(a: str, b: str) -> float:
    na, nb = norm_title(a), norm_title(b)
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def base_arxiv(arxiv_id: str) -> str:
    return re.sub(r"v\d+$", "", arxiv_id.strip())


def num(value) -> str:
    if value is None:
        return "not_found"
    if isinstance(value, float):
        text = f"{value:.4f}".rstrip("0").rstrip(".")
        return text if text not in ("", "-0") else "0"
    return str(value)


def technical_report_lead(title: str, stems: tuple[str, ...]) -> bool:
    words = norm_title(title).split()
    if not words or not any(words[0].startswith(stem) for stem in stems):
        return False
    for i in range(len(words) - 1):
        if words[i] == "technical" and words[i + 1] == "report":
            return i <= TECHNICAL_WORD_MAX
    return False


def year_counts(work: dict) -> dict[int, int]:
    # OpenAlex lists a year only when that year has citations. A missing year is 0.
    out = {year: 0 for year in YEARS}
    for row in work.get("counts_by_year") or []:
        year = row.get("year")
        if year in out:
            out[year] = int(row.get("cited_by_count") or 0)
    return out


def parse_feed(xml_bytes: bytes) -> tuple[str, list[dict]]:
    root = ET.fromstring(xml_bytes)
    total = root.findtext("opensearch:totalResults", default="", namespaces=ATOM_NS) or ""
    entries = []
    for entry in root.findall("a:entry", ATOM_NS):
        id_text = entry.findtext("a:id", default="", namespaces=ATOM_NS) or ""
        if "/abs/" not in id_text:
            continue
        versioned = id_text.split("/abs/")[-1]
        title = " ".join((entry.findtext("a:title", default="", namespaces=ATOM_NS) or "").split())
        journal_doi = (entry.findtext("arxiv:doi", default="", namespaces=ATOM_NS) or "").strip()
        published = entry.findtext("a:published", default="", namespaces=ATOM_NS) or ""
        published_year = int(published[:4]) if len(published) >= 4 and published[:4].isdigit() else None
        entries.append({
            "arxiv_id": base_arxiv(versioned),
            "version": versioned,
            "title": title,
            "journal_doi": journal_doi,
            "published_year": published_year,
        })
    return total, entries


def http_json(url: str) -> dict:
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    if "api.openalex.org" in url and key and "api_key=" not in url:
        url += ("&" if "?" in url else "?") + "api_key=" + urllib.parse.quote(key)
    request = urllib.request.Request(url, headers={
        "User-Agent": "evidaxis-research",
        "Accept": "application/json",
    })
    last_error = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return json.load(response)
        except urllib.error.HTTPError as error:
            body = error.read().decode("utf-8", "replace")
            if error.code == 404:
                return {"http_status": 404, "results": [], "body": body[:500]}
            last_error = f"HTTP {error.code}: {body[:300]}"
        except Exception as error:
            last_error = str(error)
        time.sleep(2 * (attempt + 1))
    return {"http_status": 0, "results": [], "error": last_error}


def http_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "evidaxis-research"})
    last_error = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                return response.read()
        except Exception as error:
            last_error = error
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"GET failed: {url.split('?')[0]}: {last_error}")


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.casefold()).strip("-")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def fetch() -> None:
    if not os.environ.get("OPENALEX_API_KEY", "").strip():
        raise SystemExit("OPENALEX_API_KEY is not set")
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "arxiv").mkdir(exist_ok=True)
    (RAW / "openalex").mkdir(exist_ok=True)
    pulled = time.strftime("%Y-%m-%d", time.gmtime())
    canonical_ids = []
    for family in FAMILIES:
        canonical_ids.extend(family["canonical"])
    id_url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
        "id_list": ",".join(canonical_ids),
        "max_results": str(len(canonical_ids)),
    })
    (RAW / "arxiv" / "canonical-ids.xml").write_bytes(strip_arxiv_authors(http_bytes(id_url)))
    time.sleep(ARXIV_PAUSE_S)
    for family in FAMILIES:
        query_url = "https://export.arxiv.org/api/query?" + urllib.parse.urlencode({
            "search_query": family["arxiv_query"],
            "start": 0,
            "max_results": 50,
            "sortBy": "submittedDate",
            "sortOrder": "ascending",
        })
        (RAW / "arxiv" / f"title-{slug(family['family'])}.xml").write_bytes(
            strip_arxiv_authors(http_bytes(query_url))
        )
        time.sleep(ARXIV_PAUSE_S)

    catalog = load_arxiv_catalog()
    for arxiv_id, entry in sorted(catalog.items()):
        doi_url = (
            "https://api.openalex.org/works?filter=doi:"
            + urllib.parse.quote(f"https://doi.org/10.48550/arxiv.{arxiv_id}")
            + f"&per-page=5&select={OPENALEX_SELECT}"
        )
        write_json(RAW / "openalex" / f"doi-{arxiv_id}.json", http_json(doi_url))
        title = entry["title"][:160]
        title_url = (
            "https://api.openalex.org/works?filter=title.search:"
            + urllib.parse.quote(title)
            + f"&per-page=8&select={OPENALEX_SELECT}"
        )
        write_json(RAW / "openalex" / f"title-{arxiv_id}.json", http_json(title_url))
    fetch_work_links(catalog, pulled)
    fetch_contaminated_titles(catalog)
    write_json(RAW / "manifest.json", {
        "openalex_pull_date": pulled,
        "arxiv_pull_date": pulled,
        "snapshot_path": "data/snapshots/2026-10-17/snapshot.json",
        "reports": len(catalog),
        "work_doi_endpoint": "https://api.openalex.org/works/doi:10.48550/arXiv.{id}",
    })
    print(f"fetched {len(catalog)} arXiv ids on {pulled}")


def fetch_work_links(catalog: dict[str, dict], pulled: str | None = None) -> None:
    """Store the DOI-path work, an exact-title search, and a journal-DOI work."""
    if not os.environ.get("OPENALEX_API_KEY", "").strip():
        raise SystemExit("OPENALEX_API_KEY is not set")
    (RAW / "openalex").mkdir(parents=True, exist_ok=True)
    for arxiv_id, entry in sorted(catalog.items()):
        doi_url = (
            "https://api.openalex.org/works/doi:10.48550/arXiv."
            + arxiv_id
            + f"?select={WORK_SELECT}"
        )
        write_json(RAW / "openalex" / f"bydoi-{arxiv_id}.json", http_json(doi_url))
        title = entry.get("title") or ""
        if title:
            # per-page=8 is the existing title-search page size.
            phrase = 'display_name.search:"' + title.replace('"', "") + '"'
            title_url = (
                "https://api.openalex.org/works?filter="
                + urllib.parse.quote(phrase, safe="")
                + f"&per-page=8&select={WORK_SELECT}"
            )
            write_json(RAW / "openalex" / f"sametitle-{arxiv_id}.json", http_json(title_url))
        journal = norm_doi(entry.get("journal_doi") or "")
        if journal and journal != arxiv_doi(arxiv_id):
            vor_url = (
                "https://api.openalex.org/works/doi:"
                + journal
                + f"?select={WORK_SELECT}"
            )
            write_json(RAW / "openalex" / f"vordoi-{arxiv_id}.json", http_json(vor_url))
    manifest_path = RAW / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    else:
        manifest = {}
    manifest["work_doi_endpoint"] = "https://api.openalex.org/works/doi:10.48550/arXiv.{id}"
    if pulled:
        manifest["openalex_pull_date"] = pulled
    write_json(manifest_path, manifest)
    print(f"stored DOI-path works for {len(catalog)} reports")


def load_arxiv_catalog() -> dict[str, dict]:
    catalog: dict[str, dict] = {}
    canonical_ids = {arxiv_id for family in FAMILIES for arxiv_id in family["canonical"]}
    _, canonical_entries = parse_feed((RAW / "arxiv" / "canonical-ids.xml").read_bytes())
    by_id = {entry["arxiv_id"]: entry for entry in canonical_entries}
    for family in FAMILIES:
        for arxiv_id in family["canonical"]:
            entry = by_id.get(arxiv_id)
            if entry is None:
                catalog[arxiv_id] = {
                    "arxiv_id": arxiv_id,
                    "title": "",
                    "journal_doi": "",
                    "published_year": None,
                    "families": [family["family"]],
                    "roles": ["canonical"],
                    "arxiv_status": "not_found",
                }
                continue
            catalog.setdefault(arxiv_id, {**entry, "families": [], "roles": [], "arxiv_status": "found"})
            catalog[arxiv_id]["journal_doi"] = catalog[arxiv_id].get("journal_doi") or entry.get("journal_doi") or ""
            if not catalog[arxiv_id].get("published_year"):
                catalog[arxiv_id]["published_year"] = entry.get("published_year")
            catalog[arxiv_id]["families"].append(family["family"])
            if "canonical" not in catalog[arxiv_id]["roles"]:
                catalog[arxiv_id]["roles"].append("canonical")
        total, entries = parse_feed((RAW / "arxiv" / f"title-{slug(family['family'])}.xml").read_bytes())
        for entry in entries:
            if entry["title"].casefold() == "error":
                continue
            arxiv_id = entry["arxiv_id"]
            lead = technical_report_lead(entry["title"], family["stems"])
            if not lead:
                role = "title_search_excluded"
            elif arxiv_id in canonical_ids:
                role = "canonical"
            else:
                role = "title_search"
            catalog.setdefault(arxiv_id, {**entry, "families": [], "roles": [], "arxiv_status": "found", "title_search_total": total})
            if family["family"] not in catalog[arxiv_id]["families"]:
                catalog[arxiv_id]["families"].append(family["family"])
            if role not in catalog[arxiv_id]["roles"]:
                catalog[arxiv_id]["roles"].append(role)
            catalog[arxiv_id]["title"] = catalog[arxiv_id]["title"] or entry["title"]
            catalog[arxiv_id]["journal_doi"] = catalog[arxiv_id].get("journal_doi") or entry.get("journal_doi") or ""
            if not catalog[arxiv_id].get("published_year"):
                catalog[arxiv_id]["published_year"] = entry.get("published_year")
            catalog[arxiv_id]["title_search_total"] = total
    return catalog


def norm_doi(doi: str) -> str:
    text = (doi or "").strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/"):
        if text.startswith(prefix):
            text = text[len(prefix):]
    return text.rstrip("/")


def arxiv_doi(arxiv_id: str) -> str:
    return f"10.48550/arxiv.{arxiv_id.lower()}"


def is_zenodo(doi: str) -> bool:
    return norm_doi(doi).startswith("10.5281/zenodo.")


def identity_dois(work: dict) -> list[str]:
    seen = []
    values = [work.get("doi") or ""]
    for loc in work.get("locations") or []:
        values.append(loc.get("doi") or "")
    for value in values:
        key = norm_doi(value)
        if not key or is_zenodo(key) or key in seen:
            continue
        seen.append(key)
    return seen


def extra_dois(work: dict, arxiv_id: str, journal_doi: str) -> list[str]:
    """Other publisher DOIs on a work that also carries this arXiv DOI.

    A separate proceedings work, whose own DOI is not this arXiv DOI, is not
    a contaminated merge. Zenodo deposits are ignored.
    """
    found = identity_dois(work)
    own = arxiv_doi(arxiv_id)
    if own not in found:
        return []
    allowed = {own}
    journal = norm_doi(journal_doi)
    if journal:
        allowed.add(journal)
    return [doi for doi in found if doi not in allowed]


def load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_single_work(path: Path) -> dict | None:
    payload = load_json(path)
    if not payload or payload.get("http_status") not in (None, 200):
        return None
    if payload.get("id") and payload.get("display_name") is not None:
        return payload
    return None


def titles_match(work: dict, arxiv_title: str) -> bool:
    if not arxiv_title:
        return False
    return norm_title(work.get("display_name") or "") == norm_title(arxiv_title)


# A full-string arXiv id. A DOI, including 10.48550/arxiv.<id>, is not an arXiv id.
_ARXIV_ID_EXACT = re.compile(
    r"^(?:https?://arxiv\.org/(?:abs|pdf)/|pmh:oai:arxiv\.org:|arxiv:)?(\d{4}\.\d{4,5})(?:v\d+)?$",
    re.IGNORECASE,
)


def arxiv_id_exact(work: dict, arxiv_id: str) -> bool:
    """True when ids or locations carry this arXiv id exactly."""
    values = []
    ids = work.get("ids") or {}
    if isinstance(ids, dict):
        for key, value in ids.items():
            if str(key).casefold() == "doi" or value is None:
                continue
            values.append(str(value))
    for loc in work.get("locations") or []:
        if not isinstance(loc, dict):
            continue
        for key in ("id", "landing_page_url", "pdf_url"):
            if loc.get(key):
                values.append(str(loc[key]))
    for value in values:
        match = _ARXIV_ID_EXACT.match(value.strip())
        if match and match.group(1) == arxiv_id:
            return True
    return False


def same_title_works(arxiv_id: str, arxiv_title: str) -> list[dict]:
    payload = load_json(RAW / "openalex" / f"sametitle-{arxiv_id}.json")
    if not payload:
        return []
    works = []
    for work in payload.get("results") or []:
        if not work.get("id"):
            continue
        if titles_match(work, arxiv_title):
            works.append(work)
    return works


def title_search_hits(
    arxiv_id: str, arxiv_title: str, published_year: int | None,
) -> tuple[list[dict], list[int]]:
    """Exact normalized title and the arXiv publication year, from titlesearch-*.json.

    The second list is publication years of title matches that are a different year.
    """
    payload = load_json(RAW / "openalex" / f"titlesearch-{arxiv_id}.json")
    if not payload or published_year is None:
        return [], []
    hits = []
    other_years = []
    for work in payload.get("results") or []:
        if not work.get("id") or not titles_match(work, arxiv_title):
            continue
        year = work.get("publication_year")
        if year == published_year:
            hits.append(work)
        elif year is not None:
            other_years.append(int(year))
    return hits, other_years


def work_is_countable(work: dict, arxiv_id: str, arxiv_title: str, journal_doi: str) -> bool:
    """Keep a count only when the normalized title matches.

    An arXiv id in ids or locations does not keep a different title. That is
    the Llama 2 merge: the location names 2307.09288 and the title is another
    paper. A DOI match is not identity. Extra publisher DOIs still reject.
    """
    if extra_dois(work, arxiv_id, journal_doi):
        return False
    if titles_match(work, arxiv_title):
        return True
    return False


def _strip_people(value):
    if isinstance(value, dict):
        for key in list(value.keys()):
            if "author" in key.casefold():
                del value[key]
            else:
                _strip_people(value[key])
    elif isinstance(value, list):
        for item in value:
            _strip_people(item)


def fetch_contaminated_titles(catalog: dict[str, dict]) -> int:
    """Store title.search responses for reports the DOI link does not keep."""
    if not os.environ.get("OPENALEX_API_KEY", "").strip():
        raise SystemExit("OPENALEX_API_KEY is not set")
    (RAW / "openalex").mkdir(parents=True, exist_ok=True)
    stored = 0
    for arxiv_id, entry in sorted(catalog.items()):
        if entry.get("arxiv_status") == "not_found" or not entry.get("title"):
            continue
        _work, _ratio, status, _why = resolve_report(
            arxiv_id,
            entry["title"],
            entry.get("journal_doi") or "",
            entry.get("published_year"),
            recover=False,
        )
        if status != "contaminated":
            continue
        title = entry["title"]
        # per-page=8 is the existing title-search page size.
        url = (
            "https://api.openalex.org/works?filter="
            + urllib.parse.quote("title.search:" + title, safe="")
            + f"&per-page=8&select={TITLE_SEARCH_SELECT}"
        )
        payload = http_json(url)
        _strip_people(payload)
        write_json(RAW / "openalex" / f"titlesearch-{arxiv_id}.json", payload)
        stored += 1
        print(f"title search {arxiv_id} results {len(payload.get('results') or [])}")
    return stored


def resolve_report(
    arxiv_id: str,
    arxiv_title: str,
    journal_doi: str,
    published_year: int | None = None,
    recover: bool = True,
) -> tuple[dict | None, float, str, str]:
    # The old 0.55 title-ratio gate is gone: a close title accepted the wrong OpenAlex work.
    """Link via GET /works/doi:10.48550/arXiv.<id>.

    A work is counted only when its title matches the arXiv title after
    normalization. An arXiv id in ids or locations, or a matching DOI, does
    not count a different title: that work is contaminated. A title search
    may replace it when the title and the year both match.
    """
    bydoi = load_single_work(RAW / "openalex" / f"bydoi-{arxiv_id}.json")
    vor = load_single_work(RAW / "openalex" / f"vordoi-{arxiv_id}.json")
    contaminated = []
    if bydoi is not None:
        contaminated = extra_dois(bydoi, arxiv_id, journal_doi)
    title_conflict = []
    for work in (bydoi, vor):
        if work is None or not arxiv_title or titles_match(work, arxiv_title):
            continue
        if work is vor and norm_doi(vor.get("doi") or "") != norm_doi(journal_doi):
            continue
        title_conflict.append(work)
    candidates = []
    seen = set()

    def add(work: dict | None) -> None:
        if work is None or not work.get("id") or work["id"] in seen:
            return
        if not work_is_countable(work, arxiv_id, arxiv_title, journal_doi):
            return
        # A zero-citation same-title stub is not a measured zero when the
        # arXiv-DOI work was merged with unrelated DOIs.
        cites = int(work.get("cited_by_count") or 0)
        own = norm_doi(work.get("doi") or "") == arxiv_doi(arxiv_id)
        if contaminated and cites == 0 and titles_match(work, arxiv_title) and not own:
            return
        seen.add(work["id"])
        candidates.append(work)

    if bydoi is not None and not contaminated:
        add(bydoi)
    if vor is not None and norm_doi(vor.get("doi") or "") == norm_doi(journal_doi):
        add(vor)
    # A same-title record with 0 citations is not a second version when a
    # counted work is already in hand. "Mistral-7B" normalizes to "Mistral 7B".
    counted = any(int(work.get("cited_by_count") or 0) > 0 for work in candidates)
    for work in same_title_works(arxiv_id, arxiv_title):
        if counted and int(work.get("cited_by_count") or 0) == 0:
            continue
        add(work)
    best_ratio = 0.0
    pool = [work for work in (bydoi, vor) if work] + same_title_works(arxiv_id, arxiv_title)
    for work in pool:
        best_ratio = max(best_ratio, title_ratio(work.get("display_name") or "", arxiv_title))
    if not candidates:
        if title_conflict or contaminated:
            return _contaminated_or_recovered(
                arxiv_id, arxiv_title, published_year, contaminated, title_conflict, best_ratio, recover,
            )
        if not arxiv_title:
            return None, 0.0, "not_found", "The arXiv API did not return this id."
        return None, best_ratio, "not_found", (
            f"No OpenAlex work at doi:10.48550/arXiv.{arxiv_id}, and no same-title work with a usable count."
        )
    work = max(
        candidates,
        key=lambda item: (
            int(item.get("cited_by_count") or 0),
            titles_match(item, arxiv_title),
            arxiv_id_exact(item, arxiv_id),
            item.get("id") or "",
        ),
    )
    ratio = title_ratio(work.get("display_name") or "", arxiv_title)
    why = ""
    if len(candidates) > 1:
        why = (
            "Preprint and version of record are separate OpenAlex works. "
            "The higher cited_by_count is kept and the two are not added."
        )
    elif contaminated:
        why = (
            "The arXiv-DOI work also carries an unrelated DOI, so that work is not used. "
            "The kept work is the version of record."
        )
    return work, ratio, "linked", why


def _contaminated_or_recovered(
    arxiv_id: str,
    arxiv_title: str,
    published_year: int | None,
    contaminated: list[str],
    title_conflict: list[dict],
    best_ratio: float,
    recover: bool,
) -> tuple[dict | None, float, str, str]:
    parts = []
    if title_conflict:
        names = [work.get("display_name") or "a different title" for work in title_conflict]
        shown = " and ".join(f"«{name}»" for name in names)
        id_note = ""
        if any(arxiv_id_exact(work, arxiv_id) for work in title_conflict):
            id_note = " Ids or locations name this arXiv id. That does not make the work this report."
        verb = "The title does not match." if len(names) == 1 else "Neither title matches."
        parts.append(
            f"OpenAlex tied this arXiv id to {shown}. {verb}{id_note} That count is not used."
        )
    if contaminated:
        listed = ", ".join(contaminated)
        parts.append(
            f"OpenAlex merges doi:10.48550/arXiv.{arxiv_id} with unrelated DOI(s): {listed}."
        )
    if not recover:
        parts.append("The count is not used.")
        return None, best_ratio or 0.0, "contaminated", " ".join(parts)
    hits, other_years = title_search_hits(arxiv_id, arxiv_title, published_year)
    if hits:
        work = max(hits, key=lambda item: (int(item.get("cited_by_count") or 0), item.get("id") or ""))
        parts.append(
            f"Title search kept the work with this title and publication year {published_year}."
        )
        if len(hits) > 1:
            parts.append("The higher cited_by_count is kept and the matches are not added.")
        return work, 1.0, "linked", " ".join(parts)
    if published_year is None:
        parts.append("Title search could not check the year, because the arXiv record has no publication date.")
    elif other_years:
        listed = ", ".join(str(year) for year in sorted(set(other_years)))
        parts.append(
            f"Title search found this title in {listed}, not in {published_year}. That work is not used."
        )
    else:
        parts.append(
            f"Title search found no OpenAlex work with this title and publication year {published_year}."
        )
    parts.append("The report stays out of the sum.")
    return None, best_ratio or 0.0, "contaminated", " ".join(parts)


def measured_role(roles: list[str]) -> str | None:
    if "canonical" in roles:
        return "canonical"
    if "title_search" in roles:
        return "title_search"
    if "title_search_excluded" in roles:
        return "title_search_excluded"
    return None


def family_of_report(entry: dict) -> str | None:
    # A report is counted once, for the first family in the fixed list that claims it.
    order = [family["family"] for family in FAMILIES]
    claimed = [name for name in order if name in entry["families"]]
    return claimed[0] if claimed else None


def build_reports(catalog: dict[str, dict]) -> list[dict]:
    rows = []
    for arxiv_id, entry in sorted(catalog.items()):
        role = measured_role(entry["roles"])
        if role is None:
            continue
        family = family_of_report(entry)
        if family is None:
            continue
        work, ratio, status, why = (None, 0.0, "not_found", "The arXiv API did not return this id.")
        if entry.get("arxiv_status") != "not_found" and entry.get("title"):
            work, ratio, status, why = resolve_report(
                arxiv_id,
                entry["title"],
                entry.get("journal_doi") or "",
                entry.get("published_year"),
            )
        elif entry.get("arxiv_status") == "not_found":
            status = "not_found"
        years = {year: "not_found" for year in YEARS}
        openalex_id = ""
        openalex_title = ""
        openalex_doi = ""
        cited = "not_found"
        if work is not None:
            counts = year_counts(work)
            years = {year: counts[year] for year in YEARS}
            openalex_id = work.get("id") or ""
            openalex_title = work.get("display_name") or ""
            openalex_doi = work.get("doi") or ""
            cited = int(work.get("cited_by_count") or 0)
        in_sum = "yes" if status == "linked" and role in ("canonical", "title_search") else "no"
        if role == "title_search_excluded":
            why = (
                "Title search hit, but the family name is not the first word, "
                'or "technical report" starts after word six. Not in the sum.'
            )
        rows.append({
            "family": family,
            "role": role,
            "arxiv_id": arxiv_id,
            "arxiv_title": entry.get("title") or "not_found",
            "in_sum": in_sum,
            "link_status": status,
            "why": why,
            "title_ratio": num(round(ratio, 4)) if entry.get("title") else "not_found",
            "openalex_id": openalex_id or "not_found",
            "openalex_title": openalex_title or "not_found",
            "openalex_doi": openalex_doi or "not_found",
            "cited_by_count": cited,
            **{f"cites_{year}": years[year] for year in YEARS},
        })
    rows.sort(key=lambda row: (row["family"], row["role"], row["arxiv_id"]))
    return rows


def load_repos() -> list[dict]:
    snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    owners = json.loads(OWNERS.read_text(encoding="utf-8"))["repos"]
    owners_lower = {key.casefold(): value for key, value in owners.items()}
    snapshot_date = snapshot["snapshot_date"]
    rows = []
    seen = set()
    for entity in snapshot["entities"]:
        repo = entity.get("github_repo") or ""
        if "/" not in repo or repo.casefold() in seen:
            continue
        owner = owners.get(repo) or owners_lower.get(repo.casefold()) or {}
        owner_type = owner.get("owner_type") or "not_found"
        org, name = repo.split("/", 1)
        velocity = (entity.get("axes") or {}).get("github_commit_velocity") or {}
        for family in FAMILIES:
            if org.casefold() not in family["orgs"]:
                continue
            if family["name_re"] and not re.search(family["name_re"], name, re.IGNORECASE):
                continue
            if owner_type != "Organization":
                rows.append({
                    "family": family["family"],
                    "github_repo": repo if owner_type == "Organization" else "",
                    "owner_type": owner_type,
                    "included": "no",
                    "recent_weekly_commits": "not_found",
                    "slope": "not_found",
                    "stars_not_scored": "not_found",
                    "snapshot_date": snapshot_date,
                    "reason": "not_an_organization" if owner_type != "not_found" else "owner_type_not_found",
                })
                continue
            seen.add(repo.casefold())
            recent = velocity.get("recent_weekly_commits")
            slope = velocity.get("slope")
            stars = velocity.get("stars_not_scored")
            rows.append({
                "family": family["family"],
                "github_repo": repo,
                "owner_type": "Organization",
                "included": "yes",
                "recent_weekly_commits": num(recent) if recent is not None else "not_found",
                "slope": num(slope) if slope is not None else "not_found",
                "stars_not_scored": num(stars) if stars is not None else "not_found",
                "snapshot_date": snapshot_date,
                "reason": "",
            })
    rows.sort(key=lambda row: (row["family"], row["included"], row["github_repo"]))
    return rows, snapshot_date


def median_of(values: list[float]) -> float | None:
    if not values:
        return None
    return float(statistics.median(values))


def build_families(reports: list[dict], repos: list[dict], snapshot_date: str, pull_date: str) -> list[dict]:
    rows = []
    for family in FAMILIES:
        name = family["family"]
        mine_all = [row for row in reports if row["family"] == name]
        mine = [row for row in mine_all if row["role"] in ("canonical", "title_search")]
        excluded = [row for row in mine_all if row["role"] == "title_search_excluded"]
        linked = [row for row in mine if row["in_sum"] == "yes"]
        sums = {}
        for year in YEARS:
            if not linked:
                sums[year] = None
            else:
                sums[year] = sum(int(row[f"cites_{year}"]) for row in linked)
        own_repos = [row for row in repos if row["family"] == name and row["included"] == "yes"]
        recent_values = [float(row["recent_weekly_commits"]) for row in own_repos if row["recent_weekly_commits"] != "not_found"]
        slope_values = [float(row["slope"]) for row in own_repos if row["slope"] != "not_found"]
        zero = sum(1 for value in recent_values if value == 0.0)
        ratio_25 = None
        ratio_26 = None
        if sums[2024] not in (None, 0) and sums[2025] is not None:
            ratio_25 = sums[2025] / sums[2024]
        if sums[2025] not in (None, 0) and sums[2026] is not None:
            ratio_26 = sums[2026] / sums[2025]
        rows.append({
            "family": name,
            "reports_found": len(mine),
            "reports_linked": len(linked),
            "reports_not_linked": len(mine) - len(linked),
            "canonical_reports": sum(1 for row in mine if row["role"] == "canonical"),
            "title_search_reports": sum(1 for row in mine if row["role"] == "title_search"),
            "title_search_excluded": len(excluded),
            **{f"cites_{year}": num(sums[year]) for year in YEARS},
            "cites_2025_over_2024": num(ratio_25) if ratio_25 is not None else "not_found",
            "cites_2026_over_2025": num(ratio_26) if ratio_26 is not None else "not_found",
            "repos_matched_org": len([row for row in repos if row["family"] == name]),
            "repos_included": len(own_repos),
            "repos_with_weekly": len(recent_values),
            "repos_weekly_not_found": len(own_repos) - len(recent_values),
            "repos_zero_weekly": zero if recent_values else "not_found",
            "sum_recent_weekly_commits": num(round(sum(recent_values), 4)) if recent_values else "not_found",
            "median_recent_weekly_commits": num(median_of(recent_values)) if recent_values else "not_found",
            "median_slope_26w": num(median_of(slope_values)) if slope_values else "not_found",
            "snapshot_date": snapshot_date,
            "openalex_pull_date": pull_date,
        })
    denominators = {}
    for year in YEARS:
        denominators[year] = sum(
            int(row[f"cites_{year}"]) for row in rows if row[f"cites_{year}"] != "not_found"
        )
    for row in rows:
        for year in YEARS:
            cites = row[f"cites_{year}"]
            denom = denominators[year]
            if cites == "not_found" or denom == 0:
                row[f"share_{year}"] = "not_found"
            else:
                row[f"share_{year}"] = num(int(cites) / denom)
            row[f"denominator_{year}"] = num(denom) if denom or cites != "not_found" else "not_found"
    return rows


def as_int(value) -> int | None:
    if value == "not_found" or value is None:
        return None
    return int(value)


def citation_finding(families: list[dict]) -> dict:
    """Qwen versus Llama on complete years only. 2026 has no monthly split."""
    by_name = {row["family"]: row for row in families}
    qwen = by_name["Qwen"]
    llama = by_name["Llama"]
    complete_years = (2023, 2024, 2025)
    first_year = None
    compared = []
    for year in complete_years:
        qwen_cites = as_int(qwen[f"cites_{year}"])
        llama_cites = as_int(llama[f"cites_{year}"])
        denominator = as_int(qwen[f"denominator_{year}"])
        compared.append({
            "year": year,
            "qwen": qwen_cites,
            "llama": llama_cites,
            "denominator": denominator,
            "qwen_share": qwen[f"share_{year}"],
            "llama_share": llama[f"share_{year}"],
        })
        if first_year is None and qwen_cites is not None and llama_cites is not None and qwen_cites > llama_cites:
            first_year = year
    qwen_2026 = as_int(qwen["cites_2026"])
    llama_2026 = as_int(llama["cites_2026"])
    partial_2026_qwen_ahead = (
        qwen_2026 is not None and llama_2026 is not None and qwen_2026 > llama_2026
    )
    return {
        "letter_finding": first_year is not None,
        "qwen_exceeds_llama_year": first_year,
        "complete_years": compared,
        "partial_2026_qwen_ahead": partial_2026_qwen_ahead,
        "partial_2026_used": False,
    }


def share_percent(value: str) -> str:
    if value == "not_found":
        return "not found"
    return f"{float(value) * 100:.1f}%"


def llama_outside_sum(reports: list[dict]) -> list[dict]:
    return [
        row for row in reports
        if row["family"] == "Llama"
        and row["role"] in ("canonical", "title_search")
        and row["in_sum"] == "no"
    ]


def llama_report_name(row: dict) -> str:
    names = {
        "2302.13971": "Llama",
        "2307.09288": "Llama 2",
        "2407.21783": "Llama 3",
    }
    return names.get(row["arxiv_id"], row["arxiv_id"])


def finding_sentence(families: list[dict], pull_date: str, reports: list[dict]) -> str:
    found = citation_finding(families)
    pull = pull_date
    # The manifest date is YYYY-MM-DD. Say it as a calendar date in the sentence.
    year, month, day = pull.split("-")
    months = {
        "01": "January", "02": "February", "03": "March", "04": "April",
        "05": "May", "06": "June", "07": "July", "08": "August",
        "09": "September", "10": "October", "11": "November", "12": "December",
    }
    spoken = f"{int(day)} {months[month]} {year}"
    bits = []
    for row in found["complete_years"]:
        bits.append(
            f"{row['year']}: Qwen {row['qwen']} and Llama {row['llama']}, "
            f"denominator {row['denominator']}"
        )
    detail = "; ".join(bits)
    if found["letter_finding"]:
        year_hit = found["qwen_exceeds_llama_year"]
        hit = next(row for row in found["complete_years"] if row["year"] == year_hit)
        return (
            f"On the OpenAlex pull of {spoken}, citations of Qwen's linked technical reports "
            f"first exceeded Llama's in {year_hit}: {hit['qwen']} versus {hit['llama']}, "
            f"denominator {hit['denominator']} (that year's sum of citations of the linked "
            f"reports of all 10 families). 2026 is incomplete and is not the basis of this sentence."
        )
    # No crossover: say what the counts do show. A partial-year count can only
    # grow, so a partial 2026 count above a full 2025 count holds.
    # "Llama's lead is understated" stays only when every excluded Llama report
    # is outside the sum and adding it cannot reduce Llama's count.
    last = found["complete_years"][-1]
    rows = {row["family"]: row for row in families}
    outside = llama_outside_sum(reports)
    llama_ahead = int(last["llama"]) > int(last["qwen"])
    understated = bool(outside) and llama_ahead and all(row["in_sum"] == "no" for row in outside)
    lead = (
        f"Downloads and citations rank these families differently. The ATOM Report shows "
        f"Qwen passing Llama on Hugging Face downloads in September 2025. On the OpenAlex pull "
        f"of {spoken}, Llama's linked technical reports still drew {int(last['llama']):,} citations "
        f"in {last['year']} against Qwen's {int(last['qwen']):,}, of {int(last['denominator']):,} for "
        f"all ten families"
    )
    if understated:
        labels = [llama_report_name(row) for row in outside]
        if len(labels) == 1:
            excluded = f"{labels[0]} is excluded"
        else:
            excluded = ", ".join(labels[:-1]) + " and " + labels[-1] + " are excluded"
        lead += f"; {excluded} (see below), so Llama's lead is understated."
    else:
        lead += "."
    lines = [lead]
    deep = rows.get("DeepSeek")
    if deep and str(deep.get("cites_2026", "")).isdigit() and str(deep.get("cites_2025", "")).isdigit() \
            and int(deep["cites_2026"]) > int(deep["cites_2025"]):
        lines.append(
            f"DeepSeek's reports have drawn {int(deep['cites_2026']):,} citations in 2026 to date, "
            f"already more than their full {last['year']} ({int(deep['cites_2025']):,}).")
    lines.append("Partial-year counts can only grow; 2026 is not otherwise compared.")
    return " ".join(lines)


def svg_chart(families: list[dict], pull_date: str) -> str:
    # Three complete years. 2026 is omitted: counts_by_year has no month.
    width, height = 920, 560
    left, top, row_h, gap = 110, 108, 22, 18
    colors = {2023: "#b7c3ce", 2024: "#6ea0e0", 2025: "#2a78d6"}
    shares = []
    for row in families:
        for year in (2023, 2024, 2025):
            if row[f"share_{year}"] != "not_found":
                shares.append(float(row[f"share_{year}"]))
    scale = max(shares or [0.1]) * 1.15
    plot_w = 460
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'font-family="Inter, Helvetica, Arial, sans-serif">',
        f'<rect width="{width}" height="{height}" fill="#fcfcfb"/>',
        '<text x="24" y="32" font-size="16" font-weight="600" fill="#0b0b0b">'
        'Share of citations to linked technical reports</text>',
        f'<text x="24" y="54" font-size="13" fill="#52514e">Ten families, OpenAlex pull {pull_date}. '
        'Each bar is that family divided by the ten-family sum.</text>',
        '<text x="24" y="74" font-size="13" fill="#52514e">'
        '2026 is not drawn. OpenAlex has no monthly counts, so the year is incomplete.</text>',
    ]
    legend_x = left
    for year in (2023, 2024, 2025):
        parts.append(f'<rect x="{legend_x}" y="84" width="14" height="10" fill="{colors[year]}"/>')
        parts.append(
            f'<text x="{legend_x + 18}" y="93" font-size="12" fill="#52514e">{year}</text>'
        )
        legend_x += 70
    for index, row in enumerate(families):
        y = top + index * (row_h + gap)
        parts.append(
            f'<text x="{left - 12}" y="{y + 16}" font-size="14" text-anchor="end" fill="#0b0b0b">'
            f'{html.escape(row["family"])}</text>'
        )
        for slot, year in enumerate((2023, 2024, 2025)):
            bar_y = y + slot * 7
            parts.append(
                f'<rect x="{left}" y="{bar_y}" width="{plot_w}" height="6" fill="#ecebe8"/>'
            )
            if row[f"share_{year}"] == "not_found":
                continue
            share = float(row[f"share_{year}"])
            bar_w = max(1.0, plot_w * share / scale)
            parts.append(
                f'<rect x="{left}" y="{bar_y}" width="{bar_w:.1f}" height="6" fill="{colors[year]}"/>'
            )
        label = " · ".join(share_percent(row[f"share_{year}"]) for year in (2023, 2024, 2025))
        parts.append(
            f'<text x="{left + plot_w + 12}" y="{y + 16}" font-size="12" fill="#0b0b0b">'
            f'{html.escape(label)}</text>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def correction_section(families: list[dict]) -> str:
    by_name = {row["family"]: row for row in families}
    changed = []
    for name, old in FIRST_VERSION_CITES.items():
        row = by_name[name]
        new = tuple(int(row[f"cites_{year}"]) for year in YEARS)
        if new != old:
            old_text = "/".join(str(value) for value in old)
            new_text = "/".join(str(value) for value in new)
            changed.append(f"{name} citations 2023/2024/2025/2026 were {old_text} and are now {new_text}.")
    denom = int(by_name["Qwen"]["denominator_2025"])
    lines = [
        "The first version, commit e88cf7fbc0, linked Llama 2 (arXiv 2307.09288) by DOI to an OpenAlex work about an ICU simulation.",
        "That work's title is not the Llama 2 report. Its citations were still counted, including 808 in 2025.",
        f"Llama's 2025 total in that version was 2,239, against Qwen's 251, of {FIRST_VERSION_DENOM_2025:,} for all ten families.",
        "A matching DOI is not identity. A work is now counted only when its title matches the arXiv title after normalization.",
        "An arXiv id in ids or locations does not keep a different title. That status is `contaminated`, and the count is not used.",
        "Each contaminated report was searched on OpenAlex by title. A hit is kept only when the title and the publication year both match.",
    ]
    if changed:
        lines.extend(changed)
    else:
        lines.append("No family citation total changed.")
    if denom != FIRST_VERSION_DENOM_2025:
        lines.append(
            f"The 2025 denominator was {FIRST_VERSION_DENOM_2025:,} and is now {denom:,}. "
            "Shares moved with that denominator."
        )
    return "\n".join(lines)


def render_readme(families: list[dict], reports: list[dict], pull_date: str, snapshot_date: str) -> str:
    sentence = finding_sentence(families, pull_date, reports)
    header = (
        "| Family | Reports in the sum | 2023 | 2024 | 2025 | 2026 partial | "
        "Share 2023 | Share 2024 | Share 2025 | Org repos | Median commits/week | Sum of commits/week |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|\n"
    )
    lines = []
    for row in families:
        repos = row["repos_included"] if row["repos_included"] else "not found"
        median = row["median_recent_weekly_commits"]
        total = row["sum_recent_weekly_commits"]
        if row["repos_included"] == 0:
            repos = "not found"
            median = "not found"
            total = "not found"
        lines.append(
            f"| {row['family']} | {row['reports_linked']} of {row['reports_found']} | "
            f"{row['cites_2023']} | {row['cites_2024']} | {row['cites_2025']} | {row['cites_2026']} | "
            f"{share_percent(row['share_2023'])} | {share_percent(row['share_2024'])} | "
            f"{share_percent(row['share_2025'])} | {repos} | {median} | {total} |"
        )
    noted = [
        row for row in reports
        if row["in_sum"] == "yes" and (row.get("why") or "").strip()
    ]
    left_out = [
        row for row in reports
        if row["in_sum"] == "no" and row["role"] in ("canonical", "title_search")
    ]
    left_lines = []
    for row in left_out:
        left_lines.append(f"- `{row['arxiv_id']}` ({row['family']}, {row['arxiv_title']}). {row['why']}")
    if not left_lines:
        left_lines.append("- None. Every canonical report and every title-search report is in the sum.")
    note_lines = [
        f"- `{row['arxiv_id']}` ({row['family']}). {row['why']}" for row in noted
    ]
    if not note_lines:
        note_lines.append("- None.")
    excluded = sum(1 for row in reports if row["role"] == "title_search_excluded")
    denom_2025 = families[0]["denominator_2025"] if families else "not_found"
    deepseek = next(row for row in families if row["family"] == "DeepSeek")
    deepseek_sum = deepseek["sum_recent_weekly_commits"]
    deepseek_repos = deepseek["repos_included"]
    body = f"""# Technical reports and repository activity of ten open model families

*Evidaxis research note · OpenAlex pull {pull_date} · snapshot {snapshot_date} · data and code CC0-1.0*

{sentence}

![Share of citations to linked technical reports, 2023–2025](chart.svg)

{header}{chr(10).join(lines)}

A zero in a citation column is a measured zero on a linked report. `not found` is a gap.
The share is that family's citations divided by `denominator_{{year}}` in `families.csv`.
For 2025 the denominator is {denom_2025}. Share columns for 2026 are in the CSV and are not used above.

## What was counted

Ten families named in the ATOM Report's regional list (Section 2.2) and kept as this
package's set: Qwen, DeepSeek, Llama, Gemma, OLMo, GLM, Kimi, InternLM, Mistral, and Phi.
ATOM measures model weights on Hugging Face. This note measures citations of the families'
technical reports, and commit activity of organization repositories in one Evidaxis snapshot.

**Reports.** Each family has a fixed list of generation reports (arXiv ids in `build.py`)
plus every arXiv hit whose title leads with the family name and says "technical report"
within the first six words. Derivative titles that only contain the name later, such as
Lawyer LLaMA and the FoundationAI Llama reports, stay in `reports.csv` as
`title_search_excluded` and are not in the sums. {excluded} titles are excluded that way.
Qwen-Image is arXiv `2508.02324`, from the Qwen title search.

**OpenAlex link.** Each report is looked up at `https://api.openalex.org/works/doi:10.48550/arXiv.<id>`.
A count is kept only when the title matches the arXiv title after normalization (case, punctuation, and spaces).
A matching DOI is not enough. An arXiv id in `ids` or `locations` does not keep a work whose title is a different paper. That work is `contaminated`, and the count is not used.
A contaminated report is searched with `https://api.openalex.org/works?filter=title.search:<title>`.
A hit is kept only when the normalized title and the publication year both match. Otherwise the report stays out of the sum.
When a preprint and a version of record both match and are separate OpenAlex works, the higher `cited_by_count` is kept and the two are not added.
A work that carries the arXiv DOI together with any other publisher DOI is a contaminated merge: its count is not used, and a same-title work with 0 citations is not entered as zero.
The journal DOI named on the arXiv record is checked as a version of record and is kept only when the title matches.
On a linked work, OpenAlex omits a year that has no citations. Those years are 0 in the sum.
`counts_by_year` has a year and a count. It has no month. 2026 is therefore not compared with the same months of 2025.

**Reports outside the sum.** Every canonical or title-search report that is not in the sum has a `why` cell in `reports.csv`.

{chr(10).join(left_lines)}

Rows that stay in the sum, with a note:

{chr(10).join(note_lines)}

**Repositories.** From `data/snapshots/2026-10-17/snapshot.json`, organization owners only
(`etl/owner_types.json`). The owner login must be the lab: `QwenLM`, `QwenAudio`,
`deepseek-ai`, `meta-llama`, `InternLM`, `mistralai`. Gemma, OLMo, GLM, Kimi, and Phi use
the company login and a name test (`gemma`, `olmo`, `glm`, `kimi`, `phi`). Personal
accounts are not listed. `recent_weekly_commits` is the mean of the last 12 weeks of
GitHub `commit_activity` on the default branch. The slope is the log-slope of the last
26 weeks. A median of 0 can sit next to a large sum: DeepSeek's {deepseek_repos} repositories sum to
{deepseek_sum} commits/week.

## Limits

- OpenAlex's citation graph is the source. Counts were not scaled to any other index.
- 2026 runs through the pull on {pull_date} and is not a finished year.
- The archive is the Evidaxis registry of code systems, not a full list of each lab's
  repositories. Llama's only match is `meta-llama/prompt-ops`.
- Default branch only. Work on other branches is outside this snapshot.
- The old DOI filter responses remain in `raw/openalex/doi-*.json` and `title-*.json`.
  The sums read `bydoi-*.json`, `sametitle-*.json`, `vordoi-*.json`, and `titlesearch-*.json`.

## Correction 2026-10-18

{correction_section(families)}

## Reproduce

```
python3 build.py --offline
```

`--offline` reads `raw/` and the snapshot. It does not use the network. It rewrites
`reports.csv`, `repos.csv`, `families.csv`, `chart.svg`, and this README.

`build.py --fetch` writes `raw/` from the arXiv API and OpenAlex. It needs
`OPENALEX_API_KEY` in the environment. Three tries are used so one dropped connection
does not turn a report into `not_found`. arXiv asks for 3 seconds between requests.

Standard library only.

## Cite

Evidaxis (2026). *Technical reports and repository activity of ten open model families.*
Research note, OpenAlex pull {pull_date}, snapshot {snapshot_date}.
https://github.com/evidaxis/evidaxis/tree/main/research/2026-10-open-model-families

Questions and corrections: hello@evidaxis.org
"""
    return body


def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def offline() -> None:
    manifest = json.loads((RAW / "manifest.json").read_text(encoding="utf-8"))
    catalog = load_arxiv_catalog()
    reports = build_reports(catalog)
    repos, snapshot_date = load_repos()
    families = build_families(reports, repos, snapshot_date, manifest["openalex_pull_date"])
    missing_why = [
        row["arxiv_id"] for row in reports
        if row["in_sum"] == "no" and not (row.get("why") or "").strip()
    ]
    if missing_why:
        raise SystemExit("reports outside the sum without why: " + ", ".join(missing_why))
    mismatched = [
        row["arxiv_id"] for row in reports
        if row["link_status"] == "linked"
        and norm_title(row["arxiv_title"]) != norm_title(row["openalex_title"])
    ]
    if mismatched:
        raise SystemExit("linked work title mismatch: " + ", ".join(mismatched))
    write_csv(HERE / "reports.csv", reports)
    write_csv(HERE / "repos.csv", repos)
    write_csv(HERE / "families.csv", families)
    (HERE / "chart.svg").write_text(
        svg_chart(families, manifest["openalex_pull_date"]),
        encoding="utf-8",
    )
    (HERE / "README.md").write_text(
        render_readme(families, reports, manifest["openalex_pull_date"], snapshot_date),
        encoding="utf-8",
    )
    bits = citation_finding(families)
    print(json.dumps(bits, ensure_ascii=False, indent=2))
    for row in families:
        print(
            f"{row['family']:10} reports {row['reports_linked']}/{row['reports_found']} "
            f"cites {row['cites_2023']}/{row['cites_2024']}/{row['cites_2025']}/{row['cites_2026']} "
            f"repos {row['repos_included']} median {row['median_recent_weekly_commits']} "
            f"sum {row['sum_recent_weekly_commits']} slope {row['median_slope_26w']}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    if args.fetch:
        fetch()
    if args.offline or not args.fetch:
        offline()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
