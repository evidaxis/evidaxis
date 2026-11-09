#!/usr/bin/env python3
"""Reject unreviewed changes to the publication checks on main."""
import fnmatch
import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
POLICY_PATH = 'scripts/gate-paths.json'


def protected(path, patterns):
    # fnmatch's * spans directories; **/ must also allow zero directories.
    return any(fnmatch.fnmatchcase(path, pattern)
               or fnmatch.fnmatchcase(path, pattern.replace('**/', ''))
               for pattern in patterns)


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT).decode().strip()


def api(endpoint):
    return json.loads(subprocess.check_output(['gh', 'api', '--paginate', '--slurp', endpoint]))


def check_push(before, after, repository, sender):
    if not before or set(before) == {'0'}:
        raise ValueError('push has no previous commit')
    # Commit authors are user-controlled; only the push event identifies the bot.
    if sender.get('login') == 'github-actions[bot]' and sender.get('type') == 'Bot':
        return 0
    if git('ls-tree', '--name-only', before, '--', POLICY_PATH):
        patterns = json.loads(git('show', f'{before}:{POLICY_PATH}'))
    else:
        # The first installation has no policy yet: require a merged PR for every
        # commit rather than trust a path list supplied by the incoming push.
        patterns = ['*']
    commits = git('rev-list', '--reverse', f'{before}..{after}').splitlines()
    for sha in commits:
        parents = git('rev-list', '--parents', '-n', '1', sha).split()[1:]
        if parents:
            paths = git('diff', '--name-only', '--no-renames', parents[0], sha).splitlines()
        else:
            paths = git('diff-tree', '--root', '--no-commit-id', '--name-only', '-r', sha).splitlines()
        if not any(protected(path, patterns) for path in paths):
            continue
        pages = api(f'repos/{repository}/commits/{sha}/pulls?per_page=100')
        if not any(pr.get('merged_at') and pr.get('base', {}).get('ref') == 'main'
                   for page in pages for pr in page):
            print(f'unreviewed protected change: {sha}', file=sys.stderr)
            return 1
    return 0


def main():
    if os.environ.get('GITHUB_EVENT_NAME') != 'push' or os.environ.get('GITHUB_REF') != 'refs/heads/main':
        return 0
    event = json.loads(Path(os.environ['GITHUB_EVENT_PATH']).read_text())
    return check_push(event['before'], event['after'], os.environ['GITHUB_REPOSITORY'],
                      event.get('sender') or {})


if __name__ == '__main__':
    sys.exit(main())
