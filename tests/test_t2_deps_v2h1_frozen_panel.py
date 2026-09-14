"""The v2h.1 collector must capture the FROZEN panel of
AXIS3-DEPS-V2H1-SUPERSESSION-2026-07-21 (component 5) whatever the pin map grows
to: post-freeze pins once entered both the rows and the panel-wide self-name
exclusion (governance/ERRATUM-2026-09-14-v2h1-collector-panel-drift.md)."""
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "collectors"))

import t2_deps_v2h1_collect as collect

# sha256 over sorted "entity_id|SYS/name" lines of the panel as frozen at aaeefa43.
# Content, not size: a swapped package would keep 90/628 and still break the record.
FROZEN_PANEL_SHA256 = "b276051518138b84959e10ec3713fb3b804d758e0d8be05f7948bacbb6305063"


def _panel_sha(entity_pkgs):
    blob = "\n".join(f"{eid}|{sys_}/{name}" for eid in sorted(entity_pkgs)
                     for sys_, name in sorted(entity_pkgs[eid]))
    return hashlib.sha256(blob.encode()).hexdigest()


def test_panel_is_the_frozen_panel_despite_later_pins():
    entity_pkgs, manifest_sha = collect.load_panel()
    assert manifest_sha.startswith("026eaa45377a")
    assert len(entity_pkgs) == 90
    assert sum(len(pkgs) for pkgs in entity_pkgs.values()) == 628
    assert _panel_sha(entity_pkgs) == FROZEN_PANEL_SHA256


def test_post_freeze_and_undated_pins_are_not_admitted(tmp_path, monkeypatch):
    pins = json.loads(collect.LEGACY_PINS.read_text())
    id_map = json.loads((collect.REPO / "etl/id_map.json").read_text())
    spare = [repo for repo in id_map if repo not in pins["pins"]][:2]
    assert len(spare) == 2
    pins["pins"][spare[0]] = {"system": "pypi", "package": "late-pin",
                              "pinned_at": "2099-01-01T00:00:00Z"}
    pins["pins"][spare[1]] = {"system": "pypi", "package": "undated-pin"}
    path = tmp_path / "deps_id_map.json"
    path.write_text(json.dumps(pins))
    monkeypatch.setattr(collect, "LEGACY_PINS", path)

    entity_pkgs, _ = collect.load_panel()

    names = {name for pkgs in entity_pkgs.values() for _, name in pkgs}
    assert "late-pin" not in names
    assert "undated-pin" not in names
    assert len(entity_pkgs) == 90
