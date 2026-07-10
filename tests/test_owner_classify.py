import json
from pathlib import Path

import pytest

from collectors import owner_classify


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return json.dumps(self.payload).encode()


def test_fetch_classification_keeps_only_publication_fields_and_auth_header():
    seen = {}

    def opener(request, timeout):
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return Response({
            "id": 42,
            "full_name": "Aider-AI/aider",
            "owner": {"type": "Organization", "login": "named-owner", "avatar_url": "https://example.test/a"},
        })

    assert owner_classify.fetch_classification("old/aider", "secret", opener) == {
        "owner_type": "Organization", "repo_id": 42, "full_name": "Aider-AI/aider",
    }
    assert seen == {"authorization": "Bearer secret", "timeout": 40}


@pytest.mark.parametrize("owner_type", ["User", "Organization"])
def test_fetch_accepts_supported_owner_types(owner_type):
    result = owner_classify.fetch_classification(
        "owner/repo", "token",
        lambda *_args, **_kwargs: Response({"id": 7, "full_name": "owner/repo", "owner": {"type": owner_type}}),
    )
    assert result["owner_type"] == owner_type


def test_fetch_rejects_unknown_owner_type():
    with pytest.raises(ValueError, match=r"owner\.type"):
        owner_classify.fetch_classification(
            "owner/repo", "token",
            lambda *_args, **_kwargs: Response({"id": 7, "full_name": "owner/repo", "owner": {"type": "Bot"}}),
        )


def test_offline_refresh_retains_existing_cache(tmp_path, capsys):
    id_map = tmp_path / "id_map.json"
    cache = tmp_path / "owner_types.json"
    id_map.write_text(json.dumps({"owner/repo": "e_1"}))
    original = '{"keep": true}\n'
    cache.write_text(original)
    assert owner_classify.refresh(id_map, cache, token=None) is False
    assert cache.read_text() == original
    assert "existing cache retained" in capsys.readouterr().err


def test_refresh_is_atomic_across_fetch_errors(tmp_path):
    id_map = tmp_path / "id_map.json"
    cache = tmp_path / "owner_types.json"
    id_map.write_text(json.dumps({"one/repo": "e_1", "two/repo": "e_2"}))
    original = '{"original": true}\n'
    cache.write_text(original)

    def fetcher(repo, _token):
        if repo == "two/repo":
            raise RuntimeError("API unavailable")
        return {"owner_type": "User", "repo_id": 1, "full_name": repo}

    with pytest.raises(RuntimeError, match="API unavailable"):
        owner_classify.refresh(id_map, cache, token="token", fetcher=fetcher)
    assert cache.read_text() == original


def test_refresh_requires_manual_confirmation_for_user_to_org(tmp_path):
    id_map = tmp_path / "id_map.json"
    cache = tmp_path / "owner_types.json"
    id_map.write_text(json.dumps({"owner/repo": "e_1"}))
    cache.write_text(json.dumps({
        "schema_version": "owner_types_1",
        "repos": {"owner/repo": {"owner_type": "User", "repo_id": 1, "full_name": "owner/repo"}},
    }))
    with pytest.raises(RuntimeError, match="manual confirmation"):
        owner_classify.refresh(
            id_map, cache, token="token",
            fetcher=lambda *_args: {"owner_type": "Organization", "repo_id": 1, "full_name": "Org/repo"},
        )


def test_refresh_rejects_repository_identity_mismatch(tmp_path):
    id_map = tmp_path / "id_map.json"
    cache = tmp_path / "owner_types.json"
    id_map.write_text(json.dumps({"owner/repo": "e_1"}))
    cache.write_text(json.dumps({
        "schema_version": "owner_types_1",
        "repos": {"owner/repo": {"owner_type": "Organization", "repo_id": 1, "full_name": "owner/repo"}},
    }))
    with pytest.raises(RuntimeError, match="identity"):
        owner_classify.refresh(
            id_map, cache, token="token",
            fetcher=lambda *_args: {"owner_type": "Organization", "repo_id": 2, "full_name": "other/repo"},
        )


def test_verify_cache_complete_incomplete_and_malformed():
    ids = {"owner/repo": "e_1"}
    complete = {
        "schema_version": "owner_types_1",
        "repos": {"owner/repo": {"owner_type": "User", "repo_id": 1, "full_name": "owner/repo"}},
    }
    assert owner_classify.verify_cache(ids, complete) == []
    assert owner_classify.verify_cache(ids, {"schema_version": "owner_types_1", "repos": {}})
    malformed = {**complete, "repos": {"owner/repo": {**complete["repos"]["owner/repo"], "login": "person"}}}
    assert owner_classify.verify_cache(ids, malformed)


def test_repository_cache_covers_internal_id_map():
    root = Path(__file__).resolve().parents[1]
    ids = json.loads((root / "etl/id_map.json").read_text())
    cache = json.loads((root / "etl/owner_types.json").read_text())
    assert owner_classify.verify_cache(ids, cache) == []
