"""Tests for collectors/openalex_resolve.py — offline (injected fetch)."""
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "collectors"))
import openalex_resolve as oar


def _work(wid, title, year=2023, cites=100):
    return {"id": f"https://openalex.org/{wid}", "title": title,
            "publication_year": year, "cited_by_count": cites}


def test_scoring_picks_canonical_paper():
    """vLLM-like fixture: the PagedAttention paper must outrank noise."""
    entity = {"entity_id": "e_TEST", "name": "vLLM", "github_repo": "vllm-project/vllm"}

    def fake_fetch(url):
        return {"results": [
            _work("W111", "unrelated survey of ml serving", 2020, 10),
            _work("W4387321091",
                  "efficient memory management for large language model serving: vllm and pagedattention",
                  2023, 1095),
            _work("W222", "vllm", 2013, 999),  # pre-2015 -> zero
        ]}

    cands = oar.get_candidates(entity, fake_fetch, "", "")
    assert cands[0]["work_id"] == "W4387321091"
    assert cands[0]["score"] > 0.3
    assert next(c for c in cands if c["work_id"] == "W222")["score"] == 0.0


def test_empty_results_path():
    entity = {"entity_id": "e_TEST", "name": "Ghost", "github_repo": "g/g"}
    assert oar.get_candidates(entity, lambda url: {}, "", "") == []
    assert oar.get_candidates({"entity_id": "e_X"}, lambda url: {}, "", "") == []


def test_merge_allowlist_into_seeds():
    seeds = {"verticals": {"v1": {"entities": [
        {"github_repo": "vllm-project/vllm", "name": "vLLM", "openalex_work_ids": []},
        {"github_repo": "other/repo", "name": "Other", "openalex_work_ids": []},
        {"github_repo": "keep/asis", "name": "Keep", "openalex_work_ids": ["W9"]},
    ]}}}
    id_map = {"vllm-project/vllm": "e_VLLM", "other/repo": "e_OTHER", "keep/asis": "e_KEEP"}
    allowlist = {
        "e_VLLM": {"work_ids": ["W4387321091"], "status": "linked"},
        "e_OTHER": {"work_ids": ["W111"], "status": "absent"},  # not linked -> skip
    }
    changed, _notes = oar.merge_allowlist_into_seeds(seeds, allowlist, id_map)
    ents = seeds["verticals"]["v1"]["entities"]
    assert changed == 1
    assert ents[0]["openalex_work_ids"] == ["W4387321091"]
    assert ents[1]["openalex_work_ids"] == []      # absent status untouched
    assert ents[2]["openalex_work_ids"] == ["W9"]  # unrelated entity untouched


def test_merge_is_idempotent():
    seeds = {"verticals": {"v1": {"entities": [
        {"github_repo": "a/b", "name": "A", "openalex_work_ids": ["W1"]}]}}}
    allowlist = {"e_A": {"work_ids": ["W1"], "status": "linked"}}
    changed, _ = oar.merge_allowlist_into_seeds(seeds, allowlist, {"a/b": "e_A"})
    assert changed == 0


def test_candidates_file_shape():
    """The per-entity record carries the fields the verification step consumes."""
    entity = {"entity_id": "e_T", "name": "T", "github_repo": "t/t"}
    cands = oar.get_candidates(entity, lambda url: {"results": [_work("W5", "t")]}, "", "")
    rec = {"entity_id": entity["entity_id"], "github_repo": entity["github_repo"],
           "display_name": entity["name"], "candidates": cands}
    parsed = json.loads(json.dumps(rec))
    assert set(parsed) == {"entity_id", "github_repo", "display_name", "candidates"}
    assert set(parsed["candidates"][0]) == {"work_id", "title", "year",
                                            "cited_by_count", "score", "reason"}
