"""Production consumers may read classifications, but may not infer owner privacy."""
import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ('scripts', 'collectors', 'web/src', 'web/scripts')
# The rehearsal deliberately chooses mutations with an independent oracle.
# It is not a publication classifier and must not share the implementation under test.
ALLOWED = {
    'scripts/person_free.py', 'web/src/lib/personFree.mjs',
    'collectors/owner_classify.py', 'scripts/rehearsal_drill.py',
}


def decisions(source, suffix):
    if suffix == '.py':
        tree = ast.parse(source)
        aliases = set()

        def raw_type(node):
            return any(
                (isinstance(child, ast.Attribute) and child.attr == 'owner_type')
                or (isinstance(child, ast.Constant) and child.value == 'owner_type')
                or (isinstance(child, ast.Name) and child.id in aliases)
                for child in ast.walk(node))

        assignments = [node for node in ast.walk(tree) if isinstance(node, (ast.Assign, ast.AnnAssign))]
        for _ in assignments:
            for node in assignments:
                if node.value and raw_type(node.value):
                    targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                    aliases.update(child.id for target in targets for child in ast.walk(target)
                                   if isinstance(child, ast.Name))
        return [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Compare)
                and raw_type(node)
                and any(isinstance(child, ast.Constant) and child.value in ('User', 'Organization')
                        for child in ast.walk(node))]
    # Keep strings (including https://) and line numbers while removing comments.
    # Actor.type, JSON-LD types and publicOwnerType() results are not raw owner types.
    tokens = r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|/\*[\s\S]*?\*/|//[^\n]*'''
    source = re.sub(tokens, lambda m: re.sub(r'[^\n]', ' ', m[0])
                    if m[0].startswith(('//', '/*')) else m[0], source)
    aliases = {'owner_type'}
    assignments = re.findall(r'\b([\w$]+)\s*=(?![=>])\s*([^;\n]+)', source)
    aliases.update(re.findall(r'\bowner_type\s*:\s*([\w$]+)\s*[,}]', source))

    def raw_type(expression):
        # Computed access is data; a schema key list or example string is metadata.
        expression = re.sub(r'''\[\s*['"]owner_type['"]\s*\]''', '.owner_type', expression)
        expression = re.sub(r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*' ''', ' ', expression, flags=re.X)
        return any(re.search(r'\b' + re.escape(alias) + r'\b', expression) for alias in aliases)

    for _ in assignments:
        for name, expression in assignments:
            if raw_type(expression):
                aliases.add(name)
    comparison = r'''(?:[!=]==?\s*['"](?:User|Organization)['"]|['"](?:User|Organization)['"]\s*[!=]==?)'''
    membership = r'\.(?:includes|has)\s*\('
    conditional = r'\b(?:if|switch)\s*\('
    return [source.count('\n', 0, m.start()) + 1 for m in re.finditer(r'[^;{}]+', source)
            if raw_type(m[0]) and re.search(f'{comparison}|{membership}|{conditional}', m[0])]


def test_person_free_single_source():
    violations = []
    for folder in SOURCES:
        for path in (ROOT / folder).rglob('*'):
            relative = path.relative_to(ROOT).as_posix()
            if (path.suffix not in {'.py', '.ts', '.mjs', '.js', '.astro'}
                    or '.test.' in path.name or relative in ALLOWED):
                continue
            for line in decisions(path.read_text(), path.suffix):
                violations.append(f'{relative}:{line}')
    assert not violations, 'owner classification outside the shared modules: ' + ', '.join(violations)


@pytest.mark.parametrize('source', [
    "if (entry.owner_type === 'User') mask();",
    "if (entry?.owner_type !== 'Organization') mask();",
    "const privateRow = entry['owner_type'] == 'User';",
    "const kind = entry.owner_type; if (kind === 'User') mask();",
    "if ('User' === entry.owner_type) mask();",
    "if (['User'].includes(entry.owner_type)) mask();",
    "const { owner_type: kind } = entry; if (kind === 'User') mask();",
    "const url = 'https://example.invalid'; if (entry.owner_type === 'User') mask();",
    "const privateRow = entry.owner_type\n  === 'User';",
    "if (['User'].includes(\n  entry.owner_type\n)) mask();",
])
def test_guard_catches_javascript_decisions(source):
    assert decisions(source, '.ts')


@pytest.mark.parametrize('source', [
    "if entry['owner_type'] == 'User': mask()",
    "if entry.get('owner_type') in {'User'}: mask()",
    "kind = entry['owner_type']\nif kind != 'Organization': mask()",
])
def test_guard_catches_python_decisions(source):
    assert decisions(source, '.py')


@pytest.mark.parametrize('source', [
    "if (actor?.type === 'User') return 'human';",
    "const ownerType = publicOwnerType(e); if (ownerType === 'Organization') render();",
    "if (publicOwnerType(e) === 'Organization') render();",
    "if (registry.schema_version !== 'owner_types_1') fail();",
    "const entry = { owner_type: 'User' };",
    "sample(rows, e => registry.repos[e.github_repo]?.owner_type); if (e) render();",
    "if (!validOwnerEntry(entry) || keys !== JSON.stringify(['owner_type', 'full_name'])) fail();",
])
def test_guard_allows_metadata_and_shared_results(source):
    assert not decisions(source, '.ts')
