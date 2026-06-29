#!/usr/bin/env python3
"""
archive_pin.py — pin each genesis source pre-image to an INDEPENDENT public archive
so a third party can verify a published content-hash even if the live source mutates/404s.
Per depr-22 (legal-edges): Wayback "Save Page Now" + Software Heritage "Save Code Now"
hold the pre-image under THEIR OWN legal basis; async + throttled + robots-respecting;
public content only; NO IPFS for expressive bytes. Stores pointers only, never rehosted bytes.

Reads the genesis source_manifest (github_repos) from data/snapshots/<date>/provenance.json,
writes data/snapshots/<date>/archive-pointers.json. Stdlib only.
"""
import json, time, sys, urllib.request, urllib.error, pathlib

SNAP = pathlib.Path(__file__).resolve().parent.parent / "data" / "snapshots" / "2026-06-27"
UA = "EvidaxisArchivePin/1.0 (+https://evidaxis.org; genesis pre-image preservation)"

def _req(url, method="GET", timeout=45):
    r = urllib.request.Request(url, method=method, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.geturl(), resp.read(2000).decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, url, str(e)
    except Exception as e:
        return None, url, f"{type(e).__name__}: {e}"

def wayback(repo_url):
    # Save Page Now: GET https://web.archive.org/save/<url>  (≈15/min/IP)
    st, final, _ = _req("https://web.archive.org/save/" + repo_url, timeout=60)
    if st in (200, 301, 302) and "web.archive.org/web/" in final:
        return {"status": "ok", "archived_url": final}
    # fall back to the latest existing snapshot via the availability API
    st2, _, body = _req("https://archive.org/wayback/available?url=" + repo_url)
    if st2 == 200:
        try:
            snap = json.loads(body).get("archived_snapshots", {}).get("closest", {})
            if snap.get("available"):
                return {"status": "existing", "archived_url": snap.get("url")}
        except Exception:
            pass
    return {"status": "failed", "http": st}

def swh(repo_url):
    # Save Code Now: POST https://archive.softwareheritage.org/api/1/origin/save/git/url/<url>/  (≈120/hr anon)
    api = "https://archive.softwareheritage.org/api/1/origin/save/git/url/" + repo_url + "/"
    st, _, body = _req(api, method="POST", timeout=45)
    if st in (200, 201):
        try:
            j = json.loads(body)
            return {"status": "ok", "save_request_status": j.get("save_request_status"),
                    "save_task_status": j.get("save_task_status"), "origin_url": j.get("origin_url")}
        except Exception:
            return {"status": "ok", "raw": body[:200]}
    return {"status": "failed", "http": st}

def main():
    prov = json.loads((SNAP / "provenance.json").read_text())
    repos = prov["source_manifest"]["github_repos"]
    out = {"generated_for_snapshot": prov.get("snapshot_id"),
           "policy": "Wayback Save-Page-Now + Software Heritage Save-Code-Now; async, throttled, public-content-only; pointers held under each archive's own legal basis; NO IPFS for expressive bytes (depr-22).",
           "repos": {}}
    for i, repo in enumerate(repos):
        url = "https://github.com/" + repo
        print(f"[{i+1}/{len(repos)}] {repo}", flush=True)
        wb = wayback(url); print(f"   wayback: {wb.get('status')}", flush=True)
        time.sleep(5)                      # Wayback ≈15/min → conservative
        sw = swh(url); print(f"   swh: {sw.get('status')}", flush=True)
        time.sleep(6)                      # SWH ≈120/hr anon → conservative
        out["repos"][repo] = {"source_url": url, "wayback": wb, "software_heritage": sw}
    (SNAP / "archive-pointers.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    ok_wb = sum(1 for r in out["repos"].values() if r["wayback"]["status"] in ("ok", "existing"))
    ok_sw = sum(1 for r in out["repos"].values() if r["software_heritage"]["status"] == "ok")
    print(f"\nDONE: wayback {ok_wb}/{len(repos)} · swh {ok_sw}/{len(repos)} → {SNAP/'archive-pointers.json'}")

if __name__ == "__main__":
    main()
