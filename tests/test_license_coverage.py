"""Every tracked file must fall under at least one REUSE.toml annotation.

2026-07-02 finding: collectors/ (including claim_urn.py, the reference
implementation of the LOCKED claim-URN contract), dead-man/ and .github/ were
outside every annotation - default all-rights-reserved in a repo whose pitch
is open licensing. This lint prevents the recurrence when new top-level
directories appear.
"""
import fnmatch
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# Files that are self-licensing or license plumbing, exempt from annotations.
EXEMPT = (
    "LICENSE", "LICENSE-data.md", "LICENSING.md", "NOTICE", "REUSE.toml",
    "LICENSES/*", ".gitignore", ".gitattributes", "README.md",
    "*.md",           # root-level docs describe the project; prose covered by LICENSING.md
    "web/package.json", "web/package-lock.json", "web/tsconfig.json",
    "web/astro.config.mjs", "web/vercel.json", "web/public/*",
    "etl/.env.example", "deploy.env.example",
)


def _annotation_globs() -> list:
    text = (REPO / "REUSE.toml").read_text()
    globs = []
    for block in re.findall(r"path\s*=\s*\[([^\]]+)\]", text):
        globs.extend(g.strip().strip('"') for g in block.split(","))
    return globs


def _covered(path: str, globs: list) -> bool:
    for g in globs:
        # REUSE '**' semantics: prefix match on the directory part
        if g.endswith("/**") and (path.startswith(g[:-2]) or path == g[:-3]):
            return True
        if fnmatch.fnmatch(path, g) or fnmatch.fnmatch(Path(path).name, g):
            return True
    return False


def test_every_tracked_file_has_a_license_annotation():
    tracked = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.splitlines()
    globs = _annotation_globs()
    uncovered = [
        f for f in tracked
        if not _covered(f, globs)
        and not any(fnmatch.fnmatch(f, e) or fnmatch.fnmatch(Path(f).name, e) for e in EXEMPT)
    ]
    assert not uncovered, (
        "files outside every REUSE.toml annotation (add a path or an explicit exemption): "
        + ", ".join(uncovered[:20])
    )


if __name__ == "__main__":
    sys.exit(test_every_tracked_file_has_a_license_annotation() or 0)
