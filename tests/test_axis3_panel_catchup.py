"""Catchup panel: old partitions stay put, 2026-10-19 unions the manifest, a missing verdict stops."""
import json
import os

import pytest

from collectors import axis3_m4_identity as ident
from collectors import axis3_panel_catchup as catchup
from collectors import t2_deps_v2h1_collect as collect


def test_root_manifest_parser_and_linkage_rule():
    assert catchup.parse_root_manifest("pyproject.toml", '[project]\nname = "Foo_Bar"\n') == ("pypi", "foo-bar")
    assert catchup.parse_root_manifest("pyproject.toml", '[tool.poetry]\nname = "Only_Poetry"\n') == ("pypi", "only-poetry")
    assert catchup.parse_root_manifest("setup.py", 'setup(\n    name="Foo_Bar",\n)\n') == ("pypi", "foo-bar")
    assert catchup.parse_root_manifest("package.json", '{"name": "@o/p"}') == ("npm", "@o/p")
    assert catchup.parse_root_manifest("package.json", '{"name": "@o/p", "private": true}') is None
    assert catchup.parse_root_manifest("Cargo.toml", '[package]\nname = "demo"\n') == ("cargo", "demo")
    assert catchup.parse_root_manifest("go.mod", "module github.com/o/demo\n") == ("go", "github.com/o/demo")
    assert catchup.parse_root_manifest("go.mod", "module localname\n") is None
    assert catchup.parse_root_manifest(
        "pyproject.toml", '[project] # x\nname = "Foo_Bar"\n') == ("pypi", "foo-bar")
    assert catchup.parse_root_manifest(
        "pyproject.toml", '[tool.poetry] # x\nname = "Only_Poetry"\n') == ("pypi", "only-poetry")
    assert catchup.parse_root_manifest(
        "pyproject.toml", '[project] # x\nname = "Foo_Bar"\n[\n') == ("pypi", "foo-bar")
    assert catchup.parse_root_manifest(
        "Cargo.toml", '[package] # x\nname = "demo"\n') == ("cargo", "demo")
    assert catchup.parse_root_manifest(
        "Cargo.toml", '[package] # x\nname = "demo"\n[\n') == ("cargo", "demo")
    assert catchup.parse_root_manifest(
        "setup.py", 'setup(name="demo", version="1.0")\n') == ("pypi", "demo")
    assert catchup.parse_root_manifest("setup.py", "setup(name=pkg)\n") is None
    aliases = {"acme/demo", "acme/demo-old"}
    verified, _ = catchup.linkage_verdict(aliases, {"relatedProjects": [
        {"relationType": "SOURCE_REPO", "projectKey": {"id": "github.com/Acme/Demo"}}]})
    other, _ = catchup.linkage_verdict(aliases, {"relatedProjects": [
        {"relationType": "SOURCE_REPO", "projectKey": {"id": "github.com/other/demo"}}]})
    none, _ = catchup.linkage_verdict(aliases, {"links": [{"url": "https://example.com"}]})
    both, reason = catchup.linkage_verdict(aliases, {"relatedProjects": [
        {"relationType": "SOURCE_REPO", "projectKey": {"id": "github.com/acme/demo"}},
        {"relationType": "SOURCE_REPO", "projectKey": {"id": "github.com/other/demo"}}]})
    failed, why = catchup.linkage_verdict(aliases, None, error="deps.dev package request failed")
    assert verified == "verified" and other == "other_repo" and none == "no_link"
    assert both == "not_admitted" and reason
    assert failed == "not_admitted" and why == "deps.dev package request failed"


def test_same_name_and_existing_panel_are_refused():
    rows = [
        {"entity_id": "e1", "system": "pypi", "package": "same", "manifest_path": "pyproject.toml", "verdict": "no_link"},
        {"entity_id": "e2", "system": "pypi", "package": "same", "manifest_path": "setup.py", "verdict": "no_link"},
        {"entity_id": "e3", "system": "npm", "package": "taken", "manifest_path": "package.json", "verdict": "verified"},
        {"entity_id": "e4", "system": "pypi", "package": "solo", "manifest_path": "pyproject.toml", "verdict": "verified"},
    ]
    decided = catchup.decide_rows(rows, {("NPM", "taken")})
    by_entity = {row["entity_id"]: row for row in decided}
    assert by_entity["e1"]["verdict"] == "not_admitted"
    assert by_entity["e2"]["verdict"] == "not_admitted"
    assert by_entity["e3"]["verdict"] == "not_admitted"
    assert by_entity["e3"]["reason"] == "already in the m4 panel"
    assert by_entity["e4"]["verdict"] == "verified"


def test_partition_2026_10_12_is_the_previous_panel_and_hash():
    pkgs, sha, names = collect.panel_for_partition("2026-10-12")
    base, base_sha = ident.load_panel_m4()
    manifest_sha = collect.load_panel()[1]
    assert pkgs == base
    assert sha == base_sha == ident.m4_mapping_sha(manifest_sha)
    assert sha == ident.m4_mapping_sha(manifest_sha, "2026-10-12")
    assert names == ident.self_names_v2h1()
    assert collect.build_query(pkgs, "2026-10-12", names) == collect.build_query(
        base, "2026-10-12", ident.self_names_v2h1())


def _install(monkeypatch, tmp_path, manifest, audit):
    manifest_path = tmp_path / "expansion-manifest-2026-10-19.json"
    audit_path = tmp_path / "linkage-audit-2026-10-19.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    audit_path.write_text(json.dumps(audit), encoding="utf-8")
    monkeypatch.setattr(ident, "CATCHUP_MANIFEST", manifest_path)
    monkeypatch.setattr(ident, "CATCHUP_AUDIT", audit_path)


def test_partition_2026_10_19_unions_the_manifest_and_changes_only_that_hash(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, {
        "complete": True,
        "systems_viewed": 1,
        "repos": {"acme/demo": {"entity_id": "e_CATCH", "declared_packages": [
            {"system": "pypi", "package": "kept-pkg", "manifest_path": "pyproject.toml", "depsdev_exists": True},
            {"system": "npm", "package": "other-pkg", "manifest_path": "package.json", "depsdev_exists": True},
            {"system": "pypi", "package": "missing-pkg", "manifest_path": "setup.py", "depsdev_exists": False},
        ]}},
    }, {"packages": [
        {"entity_id": "e_CATCH", "system": "pypi", "package": "kept-pkg", "manifest_path": "pyproject.toml", "verdict": "verified"},
        {"entity_id": "e_CATCH", "system": "npm", "package": "other-pkg", "manifest_path": "package.json", "verdict": "other_repo"},
        {"entity_id": "e_CATCH", "system": "pypi", "package": "quiet-pkg", "manifest_path": "pyproject.toml", "verdict": "no_link"},
    ]})
    before, before_sha, before_names = collect.panel_for_partition("2026-10-12")
    after, after_sha, after_names = collect.panel_for_partition("2026-10-19")
    assert before_sha != after_sha
    assert after_sha == ident.m4_mapping_sha(collect.load_panel()[1], "2026-10-19")
    assert before_names == after_names == ident.self_names_v2h1()
    for eid, pkgs in before.items():
        assert pkgs <= after[eid]
    assert after["e_CATCH"] == {("PYPI", "kept-pkg")}
    case = collect.build_query(after, "2026-10-19", after_names).split("ELSE NULL END", 1)[0]
    assert "kept-pkg" in case and "other-pkg" not in case


def test_package_without_a_verdict_fails_loudly(monkeypatch, tmp_path):
    _install(monkeypatch, tmp_path, {
        "complete": True,
        "systems_viewed": 1,
        "repos": {"acme/demo": {"entity_id": "e_CATCH", "declared_packages": [
            {"system": "pypi", "package": "ghost", "manifest_path": "pyproject.toml", "depsdev_exists": True},
        ]}},
    }, {"packages": []})
    with pytest.raises(ValueError, match="no audit verdict"):
        ident.load_panel_m4("2026-10-19")
    with pytest.raises(ValueError, match="no audit verdict"):
        collect.panel_for_partition("2026-10-19")
    # The same hole must not affect the partition that is still on the previous panel.
    collect.panel_for_partition("2026-10-12")


def test_assemble_refuses_a_package_without_a_verdict():
    records = [{"entity_id": "e_gap", "repo": "acme/gap", "packages": [{
        "entity_id": "e_gap", "repo": "acme/gap", "system": "pypi", "package": "ghost",
        "manifest_path": "pyproject.toml", "published": True, "verdict": None,
    }]}]
    with pytest.raises(ValueError, match="no audit verdict"):
        catchup.assemble(records, set())


def test_loader_refuses_a_manifest_that_is_not_complete(monkeypatch, tmp_path):
    audit = {"packages": [
        {"entity_id": "e_CATCH", "system": "pypi", "package": "kept-pkg",
         "manifest_path": "pyproject.toml", "verdict": "verified"},
    ]}
    manifest = {"repos": {"acme/demo": {"entity_id": "e_CATCH", "declared_packages": [
        {"system": "pypi", "package": "kept-pkg", "manifest_path": "pyproject.toml", "depsdev_exists": True},
    ]}}}
    _install(monkeypatch, tmp_path, manifest, audit)
    with pytest.raises(ValueError, match="not complete"):
        ident.load_panel_m4("2026-10-19")
    manifest["complete"] = False
    manifest["systems_viewed"] = 1
    _install(monkeypatch, tmp_path, manifest, audit)
    with pytest.raises(ValueError, match="not complete"):
        ident.load_panel_m4("2026-10-19")
    ident.load_panel_m4("2026-10-12")


def test_missing_catchup_files_stop_only_the_new_partition(monkeypatch, tmp_path):
    monkeypatch.setattr(ident, "CATCHUP_MANIFEST", tmp_path / "no-manifest.json")
    monkeypatch.setattr(ident, "CATCHUP_AUDIT", tmp_path / "no-audit.json")
    ident.load_panel_m4("2026-10-12")
    with pytest.raises(ValueError, match="missing"):
        ident.load_panel_m4("2026-10-19")


def test_cache_dir_follows_env_and_stays_outside_the_repo(monkeypatch, tmp_path):
    monkeypatch.setenv("EVX_GH_CACHE_DIR", str(tmp_path))
    assert catchup.cache_dir() == tmp_path.resolve()
    monkeypatch.setenv("EVX_GH_CACHE_DIR", str(ident.REPO / "data"))
    with pytest.raises(RuntimeError, match="outside"):
        catchup.cache_dir()


def test_cli_rejects_the_wrong_partition_and_a_partial_record(monkeypatch, tmp_path):
    def boom(**_kwargs):
        raise AssertionError("a partial record must not scan")

    monkeypatch.setattr(catchup, "execute", boom)
    assert catchup.main(["--partition", "2026-10-19", "--out", str(tmp_path),
                         "--limit", "2", "--write-record"]) == 2
    monkeypatch.undo()
    assert catchup.main(["--partition", "2026-10-12", "--out", str(tmp_path)]) == 2


def _listing(name: str) -> bytes:
    return json.dumps([{"name": name, "type": "file"}]).encode()


def _version(system: str, name: str, repo: str | None) -> bytes:
    projects = []
    if repo:
        projects.append({"relationType": "SOURCE_REPO", "projectKey": {"id": f"github.com/{repo}"}})
    return json.dumps({
        "versionKey": {"system": system, "name": name, "version": "1.0.0"},
        "relatedProjects": projects,
        "links": [] if repo else [{"url": "https://example.com/about"}],
    }).encode()


def _package_doc(system: str, name: str) -> bytes:
    return json.dumps({
        "packageKey": {"system": system, "name": name},
        "versions": [{"isDefault": True, "versionKey": {"system": system, "name": name, "version": "1.0.0"}}],
    }).encode()


_FIXTURE_REPOS = [
    ("e_keep", "acme/keep", "pyproject.toml", '[project]\nname = "evx-catchup-fixture-kept"\n', "PYPI", "evx-catchup-fixture-kept", "acme/keep"),
    ("e_other", "acme/other", "package.json", '{"name": "evx-catchup-fixture-foreign"}', "NPM", "evx-catchup-fixture-foreign", "elsewhere/lib"),
    ("e_none", "acme/none", "Cargo.toml", '[package]\nname = "evx-catchup-fixture-nolink"\n', "CARGO", "evx-catchup-fixture-nolink", None),
    ("e_miss", "acme/miss", "setup.py", 'setup(name="evx-catchup-fixture-missing")\n', "PYPI", "evx-catchup-fixture-missing", "missing"),
    ("e_mod", "acme/mod", "go.mod", "module github.com/acme/mod\n", "GO", "github.com/acme/mod", None),
    ("e_priv", "acme/priv", "package.json", '{"name": "hidden", "private": true}', "NPM", "hidden", None),
    ("e_dup_a", "acme/dup-a", "pyproject.toml", '[project]\nname = "evx-catchup-fixture-dup"\n', "PYPI", "evx-catchup-fixture-dup", None),
    ("e_dup_b", "acme/dup-b", "pyproject.toml", '[project]\nname = "evx-catchup-fixture-dup"\n', "PYPI", "evx-catchup-fixture-dup", None),
]


def _fake_http(calls: list):
    by_repo = {row[1]: row for row in _FIXTURE_REPOS}

    def get(url, headers, _pacer):
        calls.append(url)
        assert "dependents" not in url.casefold()
        assert "Authorization" not in headers
        if url.startswith("https://api.github.com/repos/") and url.endswith("/contents/"):
            repo = url.removeprefix("https://api.github.com/repos/").removesuffix("/contents/")
            if repo == "acme/gone":
                return 404, url, b"not found"
            return 200, url, _listing(by_repo[repo][2])
        if url.startswith("https://raw.githubusercontent.com/"):
            parts = url.removeprefix("https://raw.githubusercontent.com/").split("/")
            repo = f"{parts[0]}/{parts[1]}"
            filename = "/".join(parts[3:])
            row = by_repo[repo]
            assert filename == row[2]
            return 200, url, row[3].encode()
        if url.startswith("https://api.deps.dev/v3/systems/"):
            rest = url.removeprefix("https://api.deps.dev/v3/systems/")
            system, _packages, tail = rest.split("/", 2)
            name, _sep, version = tail.partition("/versions/")
            from urllib.parse import unquote
            name = unquote(name)
            if name == "evx-catchup-fixture-missing":
                return 404, url, b"{}"
            owner = next(row for row in _FIXTURE_REPOS if row[4] == system and row[5] == name)
            if version:
                return 200, url, _version(system, name, owner[6])
            return 200, url, _package_doc(system, name)
        raise AssertionError(url)

    return get


def test_fixture_scan_writes_a_verdict_for_every_package_and_extends_only_the_new_partition(
        monkeypatch, tmp_path):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    calls = []
    monkeypatch.setattr(catchup, "_http_get", _fake_http(calls))
    out = tmp_path / "out"
    cache = tmp_path / "cache"
    repos = [(row[0], row[1]) for row in _FIXTURE_REPOS] + [("e_gone", "acme/gone")]
    before, before_sha, before_names = collect.panel_for_partition("2026-10-12")
    code = catchup.execute(
        "2026-10-19", out, repos=repos, cache=cache, token="", taken=set(),
        write_record=True, record_file=tmp_path / "record.md")
    assert code == 0
    manifest = json.loads((out / "expansion-manifest-2026-10-19.json").read_text(encoding="utf-8"))
    audit = json.loads((out / "linkage-audit-2026-10-19.json").read_text(encoding="utf-8"))
    assert manifest["complete"] is True
    assert manifest["systems_viewed"] == len(repos)
    sidecar = (out / "expansion-manifest-2026-10-19.json.sha256").read_text(encoding="utf-8")
    digest = sidecar.split()[0]
    assert digest in sidecar
    body = (out / "expansion-manifest-2026-10-19.json").read_bytes()
    import hashlib
    assert hashlib.sha256(body).hexdigest() == digest
    verdicts = {}
    for row in audit["packages"]:
        assert row["verdict"] in {"verified", "no_link", "other_repo", "not_admitted"}
        verdicts[(row["entity_id"], row["system"].upper(), row["package"])] = row["verdict"]
    published = []
    for info in manifest["repos"].values():
        for pkg in info["declared_packages"]:
            if pkg.get("depsdev_exists"):
                published.append((info["entity_id"], pkg["system"].upper(), pkg["package"]))
                assert (info["entity_id"], pkg["system"].upper(), pkg["package"]) in verdicts
    assert verdicts[("e_keep", "PYPI", "evx-catchup-fixture-kept")] == "verified"
    assert verdicts[("e_other", "NPM", "evx-catchup-fixture-foreign")] == "other_repo"
    assert verdicts[("e_none", "CARGO", "evx-catchup-fixture-nolink")] == "no_link"
    assert verdicts[("e_mod", "GO", "github.com/acme/mod")] == "no_link"
    assert verdicts[("e_miss", "PYPI", "evx-catchup-fixture-missing")] == "not_admitted"
    assert verdicts[("e_dup_a", "PYPI", "evx-catchup-fixture-dup")] == "not_admitted"
    assert verdicts[("e_dup_b", "PYPI", "evx-catchup-fixture-dup")] == "not_admitted"
    record = (tmp_path / "record.md").read_text(encoding="utf-8")
    assert "2026-10-19" in record and digest in record
    assert "github.com/" not in record and "acme/" not in record
    assert "Methodology m5 is unchanged" in record
    monkeypatch.setattr(ident, "CATCHUP_MANIFEST", out / "expansion-manifest-2026-10-19.json")
    monkeypatch.setattr(ident, "CATCHUP_AUDIT", out / "linkage-audit-2026-10-19.json")
    again, again_sha, again_names = collect.panel_for_partition("2026-10-12")
    after, after_sha, after_names = collect.panel_for_partition("2026-10-19")
    assert again == before and again_sha == before_sha and again_names == before_names
    assert after_sha != before_sha and after_names == before_names
    for eid, pkgs in before.items():
        assert pkgs <= after[eid]
    assert ("PYPI", "evx-catchup-fixture-kept") in after["e_keep"]
    assert ("CARGO", "evx-catchup-fixture-nolink") in after["e_none"]
    assert ("GO", "github.com/acme/mod") in after["e_mod"]
    assert "e_other" not in after or ("NPM", "evx-catchup-fixture-foreign") not in after["e_other"]
    assert "e_dup_a" not in after and "e_miss" not in after
    assert calls


def test_resume_uses_the_cache_and_a_rate_limit_writes_nothing(monkeypatch, tmp_path):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    calls = []
    monkeypatch.setattr(catchup, "_http_get", _fake_http(calls))
    repos = [("e_keep", "acme/keep")]
    cache = tmp_path / "cache"
    out = tmp_path / "out"
    assert catchup.execute("2026-10-19", out, repos=repos, cache=cache, token="", taken=set(), limit=1) == 0
    first = len(calls)

    def refuse(url, headers, pacer):
        raise AssertionError(url)

    monkeypatch.setattr(catchup, "_http_get", refuse)
    assert catchup.execute("2026-10-19", out, repos=repos, cache=cache, token="", taken=set(),
                           resume=True, limit=1) == 0
    assert len(calls) == first

    def limited(url, headers, pacer):
        if "api.github.com" in url:
            return 403, url, b"API rate limit exceeded"
        return _fake_http([])(url, headers, pacer)

    monkeypatch.setattr(catchup, "_http_get", limited)
    blocked = tmp_path / "blocked"
    assert catchup.execute("2026-10-19", blocked, repos=[("e_other", "acme/other")],
                           cache=tmp_path / "empty-cache", token="", taken=set()) == 3
    assert not (blocked / "expansion-manifest-2026-10-19.json").exists()


def test_limit_writes_preview_files_and_not_the_panel_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    monkeypatch.setattr(catchup, "_http_get", _fake_http([]))
    out = tmp_path / "out"
    code = catchup.execute(
        "2026-10-19", out, repos=[("e_keep", "acme/keep")], cache=tmp_path / "cache",
        token="", taken=set(), limit=1)
    assert code == 0
    assert not (out / "expansion-manifest-2026-10-19.json").exists()
    assert not (out / "linkage-audit-2026-10-19.json").exists()
    assert not (out / "expansion-manifest-2026-10-19.json.sha256").exists()
    preview = out / "expansion-manifest-2026-10-19.preview.json"
    preview_audit = out / "linkage-audit-2026-10-19.preview.json"
    body = json.loads(preview.read_text(encoding="utf-8"))
    assert body["complete"] is False
    assert body["systems_viewed"] == 1
    assert preview_audit.is_file()
    monkeypatch.setattr(ident, "CATCHUP_MANIFEST", preview)
    monkeypatch.setattr(ident, "CATCHUP_AUDIT", preview_audit)
    with pytest.raises(ValueError, match="not complete"):
        ident.load_panel_m4("2026-10-19")
    ident.load_panel_m4("2026-10-12")


def test_write_record_does_not_overwrite_a_dated_record(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    monkeypatch.setattr(catchup, "_http_get", _fake_http([]))
    record = tmp_path / "AXIS3-PANEL-CATCHUP-2026-10-19.md"
    record.write_text("original dated record\n", encoding="utf-8")
    code = catchup.execute(
        "2026-10-19", tmp_path / "out", repos=[("e_keep", "acme/keep")],
        cache=tmp_path / "cache", token="", taken=set(),
        write_record=True, record_file=record)
    assert code == 2
    assert record.read_text(encoding="utf-8") == "original dated record\n"
    assert not (tmp_path / "out" / "expansion-manifest-2026-10-19.json").exists()
    assert not (tmp_path / "out" / "linkage-audit-2026-10-19.json").exists()
    assert not (tmp_path / "out" / "expansion-manifest-2026-10-19.json.sha256").exists()
    assert "изменённые данные → новая датированная запись" in capsys.readouterr().out


_PUBLISHED = (
    "expansion-manifest-2026-10-19.json",
    "expansion-manifest-2026-10-19.json.sha256",
    "linkage-audit-2026-10-19.json",
)


def _run_keep(tmp_path, out, *, write_record=False, record_file=None):
    return catchup.execute(
        "2026-10-19", out, repos=[("e_keep", "acme/keep")], cache=tmp_path / "cache",
        token="", taken=set(), write_record=write_record, record_file=record_file)


@pytest.mark.parametrize("name", _PUBLISHED)
def test_different_published_artifact_writes_nothing(monkeypatch, tmp_path, name):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    monkeypatch.setattr(catchup, "_http_get", _fake_http([]))
    out = tmp_path / "out"
    out.mkdir()
    planted = out / name
    planted.write_bytes(b"different\n")
    record = tmp_path / "record.md"
    code = _run_keep(tmp_path, out, write_record=False, record_file=record)
    assert code == 2
    assert planted.read_bytes() == b"different\n"
    for other in _PUBLISHED:
        if other != name:
            assert not (out / other).exists()
    assert not record.exists()


def test_different_governance_record_blocks_a_run_without_write_record(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    monkeypatch.setattr(catchup, "_http_get", _fake_http([]))
    record = tmp_path / "record.md"
    record.write_text("original dated record\n", encoding="utf-8")
    out = tmp_path / "out"
    code = _run_keep(tmp_path, out, write_record=False, record_file=record)
    assert code == 2
    assert record.read_text(encoding="utf-8") == "original dated record\n"
    assert not out.exists()
    assert "изменённые данные → новая датированная запись" in capsys.readouterr().out


def test_identical_published_files_are_left_untouched(monkeypatch, tmp_path):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    monkeypatch.setattr(catchup, "_http_get", _fake_http([]))
    out = tmp_path / "out"
    record = tmp_path / "record.md"
    assert _run_keep(tmp_path, out, write_record=True, record_file=record) == 0
    paths = [out / name for name in _PUBLISHED] + [record]
    stamp = 1_000_000_000_000_000_000
    for path in paths:
        os.utime(path, ns=(stamp, stamp))
    assert _run_keep(tmp_path, out, write_record=False, record_file=record) == 0
    assert _run_keep(tmp_path, out, write_record=True, record_file=record) == 0
    for path in paths:
        assert path.stat().st_mtime_ns == stamp


def test_governance_record_is_created_exclusively(monkeypatch, tmp_path):
    monkeypatch.setattr(catchup._Pace, "wait", lambda self: None)
    monkeypatch.setattr(catchup, "_http_get", _fake_http([]))
    modes = []
    real_open = open

    def spy(file, mode="r", *args, **kwargs):
        if str(file).endswith(".md") and mode != "r":
            modes.append(mode)
            if "x" not in mode:
                raise AssertionError(mode)
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr("builtins.open", spy)
    record = tmp_path / "record.md"
    out = tmp_path / "out"
    assert _run_keep(tmp_path, out, write_record=True, record_file=record) == 0
    assert modes == ["x"]
    assert "2026-10-19" in record.read_text(encoding="utf-8")
    modes.clear()
    stamp = record.stat().st_mtime_ns
    assert _run_keep(tmp_path, out, write_record=True, record_file=record) == 0
    assert modes == []
    assert record.stat().st_mtime_ns == stamp


class _Config:
    def __init__(self, *, dry_run: bool = False, use_query_cache: bool = True):
        self.dry_run = dry_run
        self.use_query_cache = use_query_cache


class _Job:
    total_bytes_processed = 551000000000

    def result(self):
        raise AssertionError("dry run must not read rows")


class _Client:
    def __init__(self):
        self.job_config = None

    def query(self, sql, job_config=None):
        self.job_config = job_config
        self.sql = sql
        return _Job()


def test_dry_run_estimates_bytes_without_reading_rows():
    client = _Client()
    nbytes = collect.estimate_query_bytes("SELECT 1", client, job_config_cls=_Config)
    assert nbytes == 551000000000
    assert client.job_config.dry_run is True
    assert client.job_config.use_query_cache is False
    assert "SELECT 1" == client.sql


def test_bq_dry_run_parser_does_not_spawn_bq():
    class Proc:
        returncode = 0
        stderr = "This query will process 12,345 bytes when run."
        stdout = ""

    def runner(cmd, **_kwargs):
        assert "--dry_run" in cmd
        assert "SELECT 1" in cmd
        return Proc()

    assert collect.estimate_query_bytes("SELECT 1", runner=runner) == 12345


def test_bq_dry_run_reads_total_bytes_processed_from_json():
    class Proc:
        returncode = 0
        stderr = "This query will process 1 bytes when run."
        stdout = '{"statistics":{"query":{"totalBytesProcessed":"123456"}}}'

    def runner(cmd, **_kwargs):
        assert "--dry_run" in cmd and "--format=json" in cmd
        return Proc()

    assert collect.estimate_query_bytes("SELECT 1", runner=runner) == 123456


def test_bq_dry_run_accepts_a_numeric_total_bytes_processed():
    class Proc:
        returncode = 0
        stderr = ""
        stdout = '{"statistics":{"query":{"totalBytesProcessed":123456}}}'

    assert collect.estimate_query_bytes("SELECT 1", runner=lambda _cmd, **_kwargs: Proc()) == 123456


def test_bq_dry_run_json_without_the_byte_field_does_not_use_the_text_phrase():
    class Proc:
        returncode = 0
        stderr = "This query will process 12,345 bytes when run."
        stdout = '{"statistics":{"query":{}}}'

    with pytest.raises(RuntimeError, match="no byte estimate"):
        collect.estimate_query_bytes("SELECT 1", runner=lambda _cmd, **_kwargs: Proc())


def test_setup_name_comes_from_the_real_call_only():
    from collectors.axis3_panel_catchup import _literal_setup_name as name
    assert name('from setuptools import setup\nsetup(name="demo", version="1.0")\n') == "demo"
    assert name('# setup(name="decoy")\nsetup(name="real")\n') == "real"
    assert name('setup(name="foo" + "-bar")\n') is None
    assert name('name = "other"\nsetup(version="1")\n') is None
    assert name('import setuptools\nsetuptools.setup(name="pkg")\n') == "pkg"
    assert name('setup(name=') is None


def test_manifest_names_no_repository():
    """The published manifest is keyed by entity ID and carries no repository names."""
    import inspect
    import collectors.axis3_panel_catchup as catchup
    source = inspect.getsource(catchup)
    assert '"head_name": record' not in source
    assert 'repos[record["entity_id"]]' in source
