import json
from pathlib import Path
import subprocess

import pytest
import yaml

from scripts import gate_change_guard as guard

ROOT = Path(__file__).resolve().parent.parent
HUMAN = {'login': 'test-sender', 'type': 'User'}
BOT = {'login': 'github-actions[bot]', 'type': 'Bot'}


def test_pr_replay_covers_protected_paths_and_all_drills():
    workflow = yaml.safe_load((ROOT / '.github/workflows/rehearsal-replay.yml').read_text())
    paths = workflow[True]['pull_request']['paths']
    for pattern in json.loads((ROOT / guard.POLICY_PATH).read_text()):
        assert any(guard.fnmatch.fnmatchcase(pattern, trigger) for trigger in paths), pattern
    matrix = workflow['jobs']['replay']['strategy']['matrix']['drill']
    for drill in ('none', 'benign_all', 'site_test', 'hf_handle', 'canary_missing'):
        assert f'"{drill}"' in matrix


@pytest.mark.parametrize('path', [
    'web/scripts/card-b-consistency.mjs',
    'web/scripts/badge-dist.mjs',
    'web/scripts/nested/new-check.mjs',
    'web/src/pages/snapshots/[date]/snapshot.json.ts',
    'web/src/pages/feed.json.ts',
    'web/src/other/new.data.test.ts',
    'tests/new.data.test.ts',
    'scripts/gate-paths.json',
    'scripts/gate_change_guard.py',
])
def test_protected_paths(path):
    patterns = json.loads((ROOT / guard.POLICY_PATH).read_text())
    assert guard.protected(path, patterns)


def commit(root, path, content, *options):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    guard.git('add', '--', path)
    guard.git('commit', '-m', 'Test change', *options)
    return guard.git('rev-parse', 'HEAD')


@pytest.fixture
def repo(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, 'ROOT', tmp_path)
    guard.git('init', '-b', 'main')
    guard.git('config', 'user.name', 'Evidaxis test')
    guard.git('config', 'user.email', 'test@example.test')
    guard.git('config', 'commit.gpgsign', 'false')
    guard.git('config', 'core.hooksPath', '/dev/null')
    commit(tmp_path, guard.POLICY_PATH, (ROOT / guard.POLICY_PATH).read_text())
    commit(tmp_path, 'web/scripts/check-dist.mjs', '// Initial check\n')
    return tmp_path


def pulls(monkeypatch, records):
    def response(endpoint):
        # The guard must never infer the push sender from commit attribution.
        assert '/pulls?' in endpoint
        return [records]
    monkeypatch.setattr(guard, 'api', response)


@pytest.mark.parametrize(('records', 'expected'), [
    ([], 1),
    ([{'merged_at': None, 'base': {'ref': 'main'}}], 1),
    ([{'merged_at': '2026-01-01', 'base': {'ref': 'other'}}], 1),
    ([{'merged_at': '2026-01-01', 'base': {'ref': 'main'}}], 0),
])
def test_guard_requires_merged_main_pr(repo, monkeypatch, records, expected):
    before = guard.git('rev-parse', 'HEAD')
    after = commit(repo, 'web/package.json', '{}\n')
    pulls(monkeypatch, records)
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == expected


def test_push_cannot_replace_its_own_policy(repo, monkeypatch):
    before = guard.git('rev-parse', 'HEAD')
    commit(repo, guard.POLICY_PATH, '[]\n')
    after = commit(repo, 'web/scripts/check-dist.mjs', '// Changed check\n')
    pulls(monkeypatch, [])
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == 1


@pytest.mark.parametrize(('sender', 'expected'), [(BOT, 0), (HUMAN, 1), ({}, 1)])
def test_only_event_sender_can_claim_bot_exception(repo, monkeypatch, sender, expected):
    before = guard.git('rev-parse', 'HEAD')
    after = commit(repo, 'web/package.json', '{}\n',
                   '--author=github-actions[bot] <bot@example.test>')
    event = repo / 'event.json'
    event.write_text(json.dumps({
        'before': before, 'after': after, 'sender': sender,
        'pusher': {'name': 'test-sender'},
    }))
    monkeypatch.setenv('GITHUB_EVENT_NAME', 'push')
    monkeypatch.setenv('GITHUB_REF', 'refs/heads/main')
    monkeypatch.setenv('GITHUB_EVENT_PATH', str(event))
    monkeypatch.setenv('GITHUB_REPOSITORY', 'evidaxis/evidaxis')
    pulls(monkeypatch, [])
    assert guard.main() == expected


def test_unprotected_changes_do_not_query_github(repo, monkeypatch):
    before = guard.git('rev-parse', 'HEAD')
    after = commit(repo, 'data/latest.json', '{}\n')
    monkeypatch.setattr(guard, 'api', lambda endpoint: pytest.fail(endpoint))
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == 0


def test_docs_merge_does_not_recheck_changes_already_on_main(repo, monkeypatch):
    guard.git('checkout', '-b', 'docs')
    commit(repo, 'docs/replay.md', 'Replay documentation\n')
    guard.git('checkout', 'main')
    before = commit(repo, 'web/scripts/check-dist.mjs', '// Reviewed check\n')
    guard.git('merge', '--no-ff', 'docs', '-m', 'Merge documentation')
    after = guard.git('rev-parse', 'HEAD')
    monkeypatch.setattr(guard, 'api', lambda endpoint: pytest.fail(endpoint))
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == 0


def test_merge_cannot_introduce_unreviewed_check(repo, monkeypatch):
    before = guard.git('rev-parse', 'HEAD')
    guard.git('checkout', '-b', 'check-change')
    commit(repo, 'web/scripts/check-dist.mjs', '// Unreviewed check\n')
    guard.git('checkout', 'main')
    guard.git('merge', '--no-ff', 'check-change', '-m', 'Merge check')
    after = guard.git('rev-parse', 'HEAD')
    pulls(monkeypatch, [])
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == 1


def test_rename_cannot_hide_protected_deletion(repo, monkeypatch):
    before = guard.git('rev-parse', 'HEAD')
    guard.git('mv', 'web/scripts/check-dist.mjs', 'notes.txt')
    guard.git('commit', '-m', 'Move check')
    after = guard.git('rev-parse', 'HEAD')
    pulls(monkeypatch, [])
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == 1


@pytest.mark.parametrize('reviewed', [False, True])
def test_initial_installation_requires_review_without_trusting_new_policy(repo, monkeypatch, reviewed):
    guard.git('rm', guard.POLICY_PATH)
    guard.git('commit', '-m', 'Test baseline without policy')
    before = guard.git('rev-parse', 'HEAD')
    after = commit(repo, guard.POLICY_PATH, '[]\n')
    pulls(monkeypatch, [{'merged_at': '2026-01-01', 'base': {'ref': 'main'}}] if reviewed else [])
    assert guard.check_push(before, after, 'evidaxis/evidaxis', HUMAN) == (0 if reviewed else 1)


def test_guard_script_stays_stdlib_only():
    # CI runs this before installing requirements-dev.txt.
    result = subprocess.run(
        ['python3', '-S', str(ROOT / 'scripts/gate_change_guard.py')],
        env={'GITHUB_EVENT_NAME': 'pull_request'}, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
