#!/usr/bin/env python3
"""ai_scope - the frozen AI-v1 scope classifier, as three declaration channels.

Frozen by governance/CENSUS-AI-V1-PREDICATE-2026-08-03.md. This module is the
single source of the signals; the act quotes it and the act's sha256 anchors it.
Never inline a copy of these patterns anywhere else (the first draft had the act
and the code disagree on the regex, which is a frozen-predicate defect).

DESIGN: the classifier reads only what a project DECLARES ABOUT ITSELF, in
descending order of how public the declaration is. Nothing here infers identity
from third-party data.

  ch-1 STOREFRONT  name + description + topics          (the repo's own label)
  ch-2 README      first 2000 chars of README.md        (the repo's own pitch)
  ch-3 MANIFEST    direct runtime deps, framework tier  (the repo's own build)

Measured 2026-08-03 against a 31-repo recall fixture (known AI systems that the
storefront channel alone misses) and a 180-repo precision sample drawn at random
from the live universe rows the storefront channel called non-AI:

  channel                    recall(31)      false(180)
  ch-1 only                    0/31            0/180     <- the baseline gap
  ch-3 manifest only          16/31  51.6%     1/180  0.6%
  ch-2 README[:2000]          20/31  64.5%    11/180  6.1%
  ch-2 OR ch-3                23/31  74.2%    12/180  6.7%   <- FROZEN
  ch-2 README[:20000]         25/31  80.6%    27/180 15.0%
  ch-2[:20000] OR ch-3        27/31  87.1%    28/180 15.6%

The 2000-char cut is a rule about WHERE a self-declaration lives (a project that
is an AI system says so in its opening pitch; a project that merely uses one
mentions it further down), not a tuned parameter: no repo name entered the rule.
Going to the full README buys 4 more of the fixture for 2.3x the false rate.

C27 discipline: not one token below was added by looking at the fixture's rows.
The regex and topic set predate the fixture; the fixture may only FALSIFY a rule
(reveal an over-broad block), never supply tokens to match its own members.
"""
from __future__ import annotations

import json
import re
import tomllib

README_PREFIX = 2000

# --------------------------------------------------------------- ch-1 signals

# High-specificity topics: unambiguous in the GitHub topic namespace.
AI_TOPICS_STRONG = frozenset({
    "machine-learning", "deep-learning", "artificial-intelligence", "llm",
    "llms", "large-language-models", "nlp", "natural-language-processing",
    "computer-vision", "diffusion-models", "transformers", "generative-ai",
    "genai", "ai-agents", "agentic", "rag", "rlhf", "reinforcement-learning",
    "speech-recognition", "text-to-speech", "speech-synthesis", "asr",
    "multimodal", "vlm", "neural-network", "neural-networks", "gpt",
    "stable-diffusion", "model-serving", "mlops", "embodied-ai",
    "protein-structure", "drug-discovery", "fine-tuning", "embeddings",
})

# Ambiguous topics: real words in other fields ("inference" = type inference,
# "ai" on a database GUI, "agents" on a build system). Measured false admits:
# gvergnaud/ts-pattern 15.1k, gcanti/io-ts 6.8k (topic "inference"),
# dbeaver/dbeaver 51.3k (topic "ai"). They admit ONLY with a second channel.
AI_TOPICS_WEAK = frozenset({
    "ai", "agents", "inference", "diffusion", "transformer", "tts",
    "robotics", "embedding",
})


def norm_topic(t: str) -> str:
    """Lowercase and strip non-alphanumerics before matching.

    GitHub topics are owner-authored and unnormalised: the live misses carry
    `multi-modal` (vs frozen `multimodal`), `gpt-4`, `gpt-4o`, `gpt-35-turbo`,
    `chatgpt`. Normalising, then matching a frozen entry as a substring of the
    normalised topic, is one mechanical rule; enumerating those variants would
    be fitting the fixture.
    """
    return re.sub(r"[^a-z0-9]", "", t.lower())


_STRONG_NORM = {norm_topic(t) for t in AI_TOPICS_STRONG}
_WEAK_NORM = {norm_topic(t) for t in AI_TOPICS_WEAK}


def _topic_hit(topics, table) -> bool:
    for raw in topics or []:
        n = norm_topic(raw)
        if any(e in n for e in table):
            return True
    return False


# One regex, one source. `(?![a-z])` instead of `\b` after a stem: the first
# draft ended the group with `\b`, so "fine tuning", "voice cloning", "image
# generation" and "molecular docking" ALL failed to match - the very words the
# stems existed for. Separators are explicit `[- ]?`, not `.?`, which had
# accepted "deepXlearning".
AI_RE = re.compile(
    r"(?<![a-z])("
    r"LLMs?|GPTs?|transformers?|diffusion|neural|"
    r"deep[- ]?learning|machine[- ]?learning|reinforcement[- ]?learning|"
    r"text[- ]?to[- ]?(image|video|speech|3d)|speech[- ]?to[- ]?text|"
    r"language model|foundation model|multi[- ]?modal|embedding|"
    r"inference (engine|server|pipeline)|fine[- ]?tun|RLHF|RAG|"
    r"retrieval[- ]?augmented|AI (agent|assistant|framework|toolkit|model)|"
    r"agentic|copilot|vision[- ]?language|VLM|OCR|ASR|TTS|"
    r"voice clon|image generat|video generat|"
    r"protein (structure|design|folding)|molecul|drug discovery|"
    r"robot (learning|manipulation)|embodied"
    r")",
    re.IGNORECASE)

# --------------------------------------------------------------- ch-3 signals

# Framework tier ONLY: importing one of these means the repo BUILDS an AI
# system. API-client markers (openai, anthropic, langchain, tiktoken, the npm
# package literally named `ai`) are deliberately NOT here - they mark software
# that CALLS a model, which is a different population (measured: home-assistant
# /core carries openai+anthropic and would enter). If that population is ever
# wanted it needs its own dated act, not a quiet allowlist edit.
FRAMEWORK_DEPS = frozenset({
    "torch", "tensorflow", "tensorflow-gpu", "jax", "jaxlib", "flax", "keras",
    "transformers", "diffusers", "accelerate", "peft", "trl", "safetensors",
    "timm", "sentence-transformers", "onnxruntime", "onnxruntime-gpu", "vllm",
    "sglang", "xformers", "bitsandbytes", "deepspeed", "einops", "optax",
    "gymnasium", "mujoco", "sentencepiece", "tokenizers", "ultralytics",
    "candle-core", "tch", "stable-baselines3", "lightning", "pytorch-lightning",
})

MANIFESTS = ("requirements.txt", "pyproject.toml", "package.json", "Cargo.toml")


def _norm_pkg(n: str) -> str:
    """PEP 503 style normalisation, applied to every ecosystem."""
    return re.sub(r"[-_.]+", "-", n.strip().lower())


def parse_manifest(filename: str, text: str) -> set[str]:
    """Direct RUNTIME dependency names a repo declares about itself.

    Deliberately excluded, each for a measured reason:
      * dev/test groups and lockfiles - a `pytest` chain drags in ML extras;
      * `path` / `git` / `workspace` / `file:` / `link:` entries - measured
        false positive: zed-industries/zed (a text editor) declares
        `anthropic = { path = "crates/anthropic" }`, its OWN internal crate;
      * setup.py - arbitrary Python, not parseable without executing it.
    Names are parsed, never regexed out of raw text: substring matching would
    let `tch` match "patch/fetch/watch" and `ort` match "sort/report".
    """
    try:
        if filename == "requirements.txt":
            out = set()
            for line in text.splitlines():
                line = line.split("#")[0].strip()
                if not line or line.startswith("-"):
                    continue
                m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", line)
                if m:
                    out.add(_norm_pkg(m.group(1)))
            return out
        if filename == "pyproject.toml":
            d = tomllib.loads(text)
            out = set()
            for x in (d.get("project") or {}).get("dependencies") or []:
                if isinstance(x, str):
                    m = re.match(r"^([A-Za-z0-9][A-Za-z0-9._-]*)", x)
                    if m:
                        out.add(_norm_pkg(m.group(1)))
            return out
        if filename == "package.json":
            d = json.loads(text)
            return {_norm_pkg(k)
                    for k, v in (d.get("dependencies") or {}).items()
                    if isinstance(v, str)
                    and not v.startswith(("file:", "link:", "workspace:"))}
        if filename == "Cargo.toml":
            d = tomllib.loads(text)
            out = set()
            for k, v in (d.get("dependencies") or {}).items():
                if isinstance(v, dict) and (
                        v.get("path") or v.get("git") or v.get("workspace")):
                    continue
                out.add(_norm_pkg(k))
            return out
    except (tomllib.TOMLDecodeError, json.JSONDecodeError, ValueError,
            TypeError, AttributeError):
        return set()          # unparseable manifest = no signal, never a crash
    return set()


# ------------------------------------------------------------- the classifier

def classify(name: str, description: str | None, topics: list[str],
             readme: str | None = None,
             manifests: dict[str, str] | None = None) -> dict | None:
    """Return the POSITIVE evidence that admitted this repo, or None.

    The returned dict is published on the admitted member's card: which channel
    admitted it and which token fired. Publishing the evidence is what keeps a
    weak channel honest - an entry obtained by writing "LLM agent" into a README
    becomes a public self-declaration, falsifiable by anyone, rather than an
    inference the institute made privately.
    """
    storefront = f"{name} {description or ''}"
    if _topic_hit(topics, _STRONG_NORM):
        return {"channel": "storefront", "signal": "topic"}
    m = AI_RE.search(storefront)
    if m:
        return {"channel": "storefront", "signal": m.group(0).lower()}

    weak_topic = _topic_hit(topics, _WEAK_NORM)
    dep_hit = None
    if manifests:
        for fn, text in manifests.items():
            hit = parse_manifest(fn, text) & FRAMEWORK_DEPS
            if hit:
                dep_hit = (fn, sorted(hit)[0])
                break
    readme_m = AI_RE.search((readme or "")[:README_PREFIX])

    if dep_hit:
        return {"channel": "manifest", "signal": dep_hit[1],
                "manifest": dep_hit[0]}
    if readme_m:
        return {"channel": "readme", "signal": readme_m.group(0).lower()}
    if weak_topic and (dep_hit or readme_m):      # ambiguous topic + 2nd signal
        return {"channel": "weak-topic+second", "signal": "topic"}
    return None


# ------------------------------------------------------------- the non-system

# Weak tokens match only NAME and TOPICS. Measured on 16,860 live universe rows
# (Fable agent, 2026-08-03): matching them in DESCRIPTION too killed 367 of
# 2,592 AI-scope repos - 14.2% - including huggingface/pytorch-image-models
# (timm), whose description is "The largest collection of PyTorch image encoders
# / backbones". timm is not among the 137 legacy members, so a fixture built on
# those 137 passed green while silently excluding one of the most depended-upon
# AI libraries on GitHub. That is the argument against fixture-as-target, and it
# is measured rather than asserted.
BLOCK_NAME = re.compile(
    r"(?<![a-z])(curated|collection[- ]of|list[- ]of|interviews?|books?|"
    r"courses?|tutorials?|mirrors?|weights|checkpoints?)(?![a-z])",
    re.IGNORECASE)
# Strong tokens: unambiguous non-system markers WHEREVER they appear. A working
# library does not call itself awesome/roadmap/cheatsheet in its own pitch.
BLOCK_STRONG = re.compile(
    r"(?<![a-z])(awesome|roadmaps?|cheat-?sheets?|reading-?lists?|"
    r"paper-?lists?|question-?banks?|study-?guides?)(?![a-z])",
    re.IGNORECASE)


def is_blocked(name: str, description: str | None, topics: list[str]) -> bool:
    """Non-system filter, deliberately narrow.

    Weak tokens fire on the repository NAME only. In a description or a topic
    they are ordinary words of working software: catboost (9.1k, Apache-2.0)
    carries the topic `tutorial` because it ships tutorials; timm describes
    itself as "the largest collection of PyTorch image encoders". Both are
    systems. List-shaped repositories that slip past this filter are removed by
    the code-language leg instead - an awesome-list is Markdown-only - which is
    a structural property rather than a word match.
    """
    if BLOCK_NAME.search(name):
        return True
    topic_str = " ".join(topics or [])
    return bool(BLOCK_STRONG.search(f"{name} {description or ''} {topic_str}"))
