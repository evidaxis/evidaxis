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
from pathlib import Path

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
    "protein-structure", "drug-discovery", "fine-tuning",
    # The spelled-out form must be listed explicitly: stripping separators from
    # "retrieval-augmented-generation" does not leave the substring "rag", so
    # the abbreviation alone never covered it.
    "retrieval-augmented-generation",
})

# Ambiguous topics: real words in other fields ("inference" = type inference,
# "ai" on a database GUI, "agents" on a build system). Measured false admits:
# gvergnaud/ts-pattern 15.1k, gcanti/io-ts 6.8k (topic "inference"),
# dbeaver/dbeaver 51.3k (topic "ai"). They admit ONLY with a second channel.
AI_TOPICS_WEAK = frozenset({
    "ai", "agents", "inference", "diffusion", "transformer", "tts",
    "robotics", "embedding",
    # `embeddings` was strong until supabase (107k, a Postgres platform) entered
    # on it: pgvector makes it an honest tag for a database. Ambiguous, so it
    # now needs a second register like every other ambiguous term.
    "embeddings",
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


# Vocabulary bootstrapped from the census's OWN admitted members, re-derived at
# every version: a topic qualifies when it is >=15x more frequent among members
# than in the full >=500-star universe and appears on >=3 members. Lift does the
# separating that a human otherwise would (python 1x, typescript 1x, cli 4x
# against robot-learning 232x, moe 199x, vllm 60x). These are WEAK signals -
# derived evidence must not carry the weight of the a-priori frozen set - and
# the file is dated so an amendment is a versioned act, not an edit.
# Known limit, stated rather than hidden: bootstrapping can only teach what the
# roster already contains. The 137 legacy members carry no classical
# computer-vision cohort, so this channel could never have recovered detectron2;
# that gap is closed by the task vocabulary above, from an external taxonomy.
def _load_bootstrap() -> frozenset[str]:
    p = Path(__file__).resolve().parent.parent / "data" / "topic_lexicon_2026-08.json"
    if not p.exists():
        return frozenset()
    return frozenset(json.loads(p.read_text())["topics"])


_STRONG_NORM = {norm_topic(t) for t in AI_TOPICS_STRONG}
_WEAK_NORM = {norm_topic(t) for t in AI_TOPICS_WEAK} | {
    norm_topic(t) for t in _load_bootstrap()}


_SPLIT = re.compile(r"[^a-z0-9]+|(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])")


def _topic_hit(topics, table) -> bool:
    """Match a frozen entry against a topic by FORM, never by bare substring.

    The first version matched any frozen entry as a substring of the normalised
    topic. Measured consequence: `rag` is inside `sto-rag-e`, `cove-rag-e`,
    `f-rag-ment`, `d-rag-anddrop`, so localForage (25.8k), lowdb (22.6k),
    juicefs (14.3k), puter (42.9k) and simplecov (4.9k) all classified as AI
    systems on the storefront channel alone. Irony that proves the rule was
    wrong: `retrieval-augmented-generation` does NOT contain the substring
    `rag` once separators are stripped, so a genuine RAG topic missed while
    object storage hit.

    The rule now: a topic matches if a frozen entry equals its normalised form
    or one of its separator/digit-boundary parts (`gpt-4o` -> {gpt, 4, o}),
    or - only for entries of 5+ characters, where accidental containment is
    vanishingly unlikely - appears inside the normalised form.
    """
    for raw in topics or []:
        low = raw.lower()
        n = norm_topic(raw)
        forms = {n} | {p for p in _SPLIT.split(low) if p}
        for e in table:
            if e in forms:
                return True
            if len(e) >= 5 and e in n:
                return True
    return False


# One regex, one source. `(?![a-z])` instead of `\b` after a stem: the first
# draft ended the group with `\b`, so "fine tuning", "voice cloning", "image
# generation" and "molecular docking" ALL failed to match - the very words the
# stems existed for. Separators are explicit `[- ]?`, not `.?`, which had
# accepted "deepXlearning".
AI_RE = re.compile(
    r"(?<![a-z])("
    # architectures and paradigms
    r"LLMs?|GPTs?|transformers?|diffusion|neural|"
    r"deep[- ]?learning|machine[- ]?learning|reinforcement[- ]?learning|"
    r"language model|foundation model|multi[- ]?modal|embedding|"
    r"fine[- ]?tun|RLHF|RAG|retrieval[- ]?augmented|pre[- ]?train|"
    # canonical TASK names of the field's subdisciplines. Sourced from the
    # standard task taxonomy every practitioner shares (arXiv cs.CV/cs.CL/cs.LG
    # subject descriptions and the Papers-With-Code task list), not from any
    # repository that failed a fixture. Their absence was measured, not
    # suspected: detectron2 ("object detection, segmentation and other visual
    # recognition", 34.6k stars) and faiss ("similarity search and clustering
    # of dense vectors", 40.7k) were invisible to a classifier that knew
    # "computer-vision" only as a topic string.
    r"object[- ]detection|instance[- ]segmentation|semantic[- ]segmentation|"
    r"image[- ](classification|segmentation|recognition|generat)|"
    r"visual[- ]recognition|pose[- ]estimation|face[- ](detection|recognition)|"
    r"video[- ]generat|scene[- ]understanding|depth[- ]estimation|"
    r"similarity[- ]search|vector[- ](search|database|index)|"
    r"nearest[- ]neighbou?r|dense[- ]vectors|"
    r"speech[- ](recognition|synthesis)|voice[- ](clon|conversion)|"
    r"text[- ]?to[- ]?(image|video|speech|3d)|speech[- ]?to[- ]?text|"
    r"machine[- ]translation|sentiment[- ]analysis|named[- ]entity|"
    r"question[- ]answering|summari[sz]ation|"
    # systems built ON models, by their own declared identity
    r"inference[- ](engine|server|pipeline)|model[- ]serving|"
    r"(AI|LLM|ML|coding|autonomous|browser|computer[- ]use|research|"
    r"software) [- ]?(agents?|assistants?)|"
    r"agentic|copilot|chatbot|vision[- ]?language|VLM|OCR|ASR|TTS|"
    # scientific AI
    r"protein[- ](structure|design|folding)|molecul|drug[- ]discovery|"
    r"robot[- ](learning|manipulation)|embodied"
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

    TWO evidentiary tiers, because a claim and a mention are not the same act.

    ADMITS ALONE - the storefront: a high-specificity topic, or the task/system
    vocabulary in the repository's NAME or DESCRIPTION. That text is the
    project's public label; it is what users see first and what the maintainers
    chose as their identity.

    ADMITS ONLY IN PAIRS - README prose, a framework-tier dependency, and an
    ambiguous topic. Each of these is a MENTION, not a label, and a mention
    alone admitted absurdities on live data: freeCodeCamp (453k stars, a
    learning platform) entered because its README says "machine learning
    curriculum", and TheAlgorithms/Python (223k, an algorithms collection)
    entered because `keras` appears in a manifest. The council had already
    ruled that an implementation detail must never admit on its own; that
    ruling applies to incidental prose exactly as it applies to an API client.
    Two independent supporting signals restore the declaration: a project whose
    README says AI AND that builds on a framework, or that carries an AI topic,
    has said it twice in two different registers.

    The returned dict is published on the admitted member's card: which channel
    admitted it and which token fired. Publishing the evidence is what keeps a
    weak channel honest - an entry obtained by writing "LLM agent" into a README
    becomes a public self-declaration, falsifiable by anyone, rather than an
    inference the institute made privately.
    """
    if _topic_hit(topics, _STRONG_NORM):
        return {"channel": "storefront", "signal": "topic"}
    label = f"{name} {description or ''}"
    m = AI_RE.search(label)
    if m:
        return {"channel": "storefront", "signal": m.group(0).lower()}

    support: list[dict] = []
    if _topic_hit(topics, _WEAK_NORM):
        support.append({"kind": "topic", "signal": "weak-topic"})
    else:
        mt = AI_RE.search(" ".join(topics or []))
        if mt:
            support.append({"kind": "topic", "signal": mt.group(0).lower()})
    if manifests:
        for fn, text in manifests.items():
            hit = parse_manifest(fn, text) & FRAMEWORK_DEPS
            if hit:
                support.append({"kind": "manifest", "signal": sorted(hit)[0],
                                "manifest": fn})
                break
    mr = AI_RE.search((readme or "")[:README_PREFIX])
    if mr:
        support.append({"kind": "readme", "signal": mr.group(0).lower()})

    # A non-system marker anywhere disqualifies the WEAK tier. Measured:
    # Snailclimb/JavaGuide (157k) is a Java interview guide carrying topics
    # `agent`/`ai`/`deepseek` and the word RAG in its README - two supporting
    # signals and nothing else. Against a public identity label such a marker
    # loses (catboost ships tutorials and is still a library); against a pair of
    # mentions it wins, because mentions are exactly what a guide accumulates.
    if BLOCK_WEAK_TIER.search(f"{description or ''} {' '.join(topics or [])}"):
        return None

    # Two mentions are not a declaration. The council's line is declared
    # IDENTITY or declared CONSTRUCTION; a repository that fails the identity
    # tier can only be admitted on construction evidence, corroborated by a
    # second register. Measured: supabase (107k, "The Postgres development
    # platform") carries the topics `ai`+`embeddings` and the word Embedding in
    # its README - two mentions, honest ones, from a database that supports
    # pgvector - and declares no ML framework anywhere. kokoro, by contrast,
    # declares torch AND says TTS: it is built out of the field, not adjacent
    # to it.
    has_construction = any(x["kind"] == "manifest" for x in support)
    if len(support) >= 2 and has_construction:
        ev = {"channel": "corroborated",
              "signal": "+".join(x["signal"] for x in support),
              "sources": [x["kind"] for x in support]}
        man = next((x for x in support if x["kind"] == "manifest"), None)
        if man:
            ev["manifest"] = man["manifest"]
        return ev
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
    r"courses?|tutorials?|mirrors?|weights|checkpoints?|"
    r"beginners?|lessons?|handbooks?|bootcamps?|workshops?|"
    r"learning[- ]paths?|study[- ]guides?)(?![a-z])",
    re.IGNORECASE)
# Strong tokens: unambiguous non-system markers WHEREVER they appear. A working
# library does not call itself awesome/roadmap/cheatsheet in its own pitch.
# Teaching artifacts declare themselves in the same breath as their subject:
# "21 Lessons, Get Started Building with Generative AI" is a course about the
# field, not a system in it. These disqualify a NAME outright, and disqualify a
# weak-tier admission wherever they appear.
BLOCK_WEAK_TIER = re.compile(
    r"(?<![a-z])(interviews?|lessons?|tutorials?|courses?|curriculum|"
    r"beginners?|handbooks?|bootcamps?|workshops?|roadmaps?|"
    r"cheat-?sheets?|study[- ]guides?|learning[- ]paths?|"
    r"awesome|curated)(?![a-z])", re.IGNORECASE)

BLOCK_STRONG = re.compile(
    r"(?<![a-z])(awesome|roadmaps?|cheat-?sheets?|reading-?lists?|"
    r"paper-?lists?|question-?banks?|study-?guides?)(?![a-z])",
    re.IGNORECASE)


def is_blocked(name: str, description: str | None, topics: list[str]) -> bool:
    """Non-system filter.

    The name is matched on its SEPARATOR-SPLIT parts as well as whole, because
    repository names are compounds: `generative-ai-for-beginners` (115k, "21
    Lessons, Get Started Building with Generative AI") is a course about the
    field and carries the strong topic `generative-ai`, so only the name can
    disqualify it - and only if `beginners` is seen as its own token.
    """
    """Non-system filter, deliberately narrow.

    Weak tokens fire on the repository NAME only. In a description or a topic
    they are ordinary words of working software: catboost (9.1k, Apache-2.0)
    carries the topic `tutorial` because it ships tutorials; timm describes
    itself as "the largest collection of PyTorch image encoders". Both are
    systems. List-shaped repositories that slip past this filter are removed by
    the code-language leg instead - an awesome-list is Markdown-only - which is
    a structural property rather than a word match.
    """
    name_forms = name + " " + " ".join(_SPLIT.split(name.lower()))
    if BLOCK_NAME.search(name_forms):
        return True
    topic_str = " ".join(topics or [])
    return bool(BLOCK_STRONG.search(f"{name} {description or ''} {topic_str}"))
