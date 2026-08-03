"""Regression tests for AI-v1's two evidentiary tiers."""
from __future__ import annotations

import sys
from pathlib import Path

COLLECTORS = Path(__file__).resolve().parent.parent / "collectors"
sys.path.insert(0, str(COLLECTORS))

from ai_scope import classify


def test_freecodecamp_shaped_readme_only_does_not_admit():
    evidence = classify(
        "freecodecamp",
        "The open source codebase and curriculum",
        [],
        readme="A curriculum including machine learning with Python.",
    )

    assert evidence is None


def test_keras_in_manifest_only_does_not_admit():
    evidence = classify(
        "python",
        "All algorithms implemented in Python",
        [],
        manifests={"requirements.txt": "keras>=3.0\n"},
    )

    assert evidence is None


def test_ai_topic_and_framework_dependency_admit_as_corroborated():
    evidence = classify(
        "application",
        "General purpose software",
        ["ai"],
        manifests={"requirements.txt": "keras>=3.0\n"},
    )

    assert evidence == {
        "channel": "corroborated",
        "signal": "weak-topic+keras",
        "sources": ["topic", "manifest"],
        "manifest": "requirements.txt",
    }
