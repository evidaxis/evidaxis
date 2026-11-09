"""Shared fictional vectors, plus publication behavior independent of the classifier."""
import json
import re
import subprocess
from pathlib import Path

import pytest
from scripts import person_free as pf
from scripts import hf_upload_snapshot as hf

ROOT = Path(__file__).resolve().parents[1]
VECTORS = json.loads((ROOT / "tests/fixtures/person-free-conformance.json").read_text())["cases"]


@pytest.mark.parametrize("case", VECTORS, ids=lambda case: case["id"])
def test_conformance(case):
    original = json.dumps(case)
    c = pf.classify_registry(case["registry"], case.get("accounts", {}), case.get("floor", []))
    assert {"handles": sorted(c.handles), "stalePaths": sorted(c.stale_paths),
            "publicRepos": sorted(c.public_repos)} == case["expected"]
    index = pf.build_handle_index(c.handles, case.get("templateWords", []))
    for probe in case.get("probes", []):
        assert sorted(set(pf.handle_hits(pf.lenient_decoded(probe["text"]), index))) == probe["hits"]
    if p := case.get("projection"):
        assert pf.safe_homepage(p["homepage"], p["repo"], case["registry"][p["repo"]], c, index) == p["expectedHomepage"]
    assert json.dumps(case) == original


@pytest.mark.parametrize("case", [c for c in VECTORS if "projection" in c], ids=lambda c: c["id"])
def test_hf_projection_experiments(case, tmp_path, monkeypatch):
    (tmp_path / "etl").mkdir()
    (tmp_path / "web/src/data").mkdir(parents=True)
    (tmp_path / "etl/owner_types.json").write_text(json.dumps({"repos": case["registry"]}))
    (tmp_path / "web/src/data/person-free-handles.json").write_text(json.dumps(case.get("floor", [])))
    monkeypatch.setattr(hf, "REPO", tmp_path)
    p = case["projection"]
    result = hf.project_person_free({"entities": [{"entity_id": "e_DRILL", "github_repo": p["repo"], "homepage": p["homepage"]}]})
    assert result["entities"][0].get("homepage") == p["expectedHomepage"]
    stage = tmp_path / "stage"
    stage.mkdir()
    (stage / "snapshot.json").write_text(json.dumps(result))
    assert hf._person_free_hits(stage) == []


def test_diagnostic_is_salted_and_does_not_print_identifiers():
    index = pf.build_handle_index(["zz-drill-secret"])
    line = pf.diagnostic("zz-drill-secret/page.json", "f", "zz-drill-secret", index)
    assert "zz-drill-secret" not in line
    assert re.fullmatch(r"\[path:[0-9a-f]{8}\]: rule=f hash=[0-9a-f]{8}", line)
    assert line == pf.diagnostic("zz-drill-secret/page.json", "f", "zz-drill-secret", index)
    script = "from scripts.person_free import diagnostic; print(diagnostic('page.json', 'f', 'zz-drill-secret'))"
    outputs = [subprocess.check_output([str(ROOT / '.venv/bin/python'), '-c', script], cwd=ROOT) for _ in range(2)]
    assert outputs[0] != outputs[1]
    line = pf.diagnostic("zz-drill-lab/given/page.json", "d", "zz-drill-lab/given", index)
    assert re.fullmatch(r"\[path:[0-9a-f]{8}\]: rule=d hash=[0-9a-f]{8}", line)


def test_exact_short_field_values_are_masked_even_when_present_in_source():
    index = pf.build_handle_index(['f', '78', 'system'], ['f', '78', 'system'])
    assert pf.reveals_handle(' F ', index)
    assert pf.reveals_handle('78', index)
    assert not pf.reveals_handle('System', index)


def test_hf_masks_stale_paths_in_free_text_and_diagnostics(tmp_path, monkeypatch):
    case = VECTORS[0]
    (tmp_path / 'etl').mkdir()
    (tmp_path / 'web/src/data').mkdir(parents=True)
    (tmp_path / 'etl/owner_types.json').write_text(json.dumps({'repos': case['registry']}))
    (tmp_path / 'web/src/data/person-free-handles.json').write_text('[]')
    monkeypatch.setattr(hf, 'REPO', tmp_path)
    path = 'zz-drill-lab/given'
    entity = {'entity_id': 'e_DRILL', 'github_repo': path, 'description': path, 'deps': {'package': path}}
    projected = hf.project_person_free({'entities': [entity]})['entities'][0]
    assert projected['description'] is None
    assert projected['deps']['package'] == 'package not shown'
    stage = tmp_path / 'stage'
    leak = stage / path / 'page.json'
    leak.parent.mkdir(parents=True)
    leak.write_text(json.dumps({'url': path}))
    hits = hf._person_free_hits(stage)
    assert len(hits) == 1
    assert re.fullmatch(r"\[path:[0-9a-f]{8}\]: rule=d hash=[0-9a-f]{8}", hits[0])


def test_template_vocabulary_matches_javascript():
    script = "import {templateWords} from './web/src/lib/personFree.mjs'; console.log(JSON.stringify([...templateWords()].sort()))"
    actual = json.loads(subprocess.check_output(['node', '--input-type=module', '-e', script], cwd=ROOT))
    assert sorted(pf.template_words()) == actual
    assert not pf.handle_hits('System /system/tool', pf.build_handle_index(['system']))
    assert pf.handle_hits('github.com/system/tool', pf.build_handle_index(['system'])) == ['system']
