# Evidaxis Genesis — Rights-Basis Manifest

> Ships with the genesis DOI deposit. Documents the legal basis on which Evidaxis ingests, retains, and (CC0-)publishes the genesis corpus. Grounded in a multi-source review of the primary terms cited below. This is a documented conservative posture, NOT live legal advice; see the solicitor-later triggers at the end.

## The core rule
**CC0 covers ONLY Evidaxis-owned rights** — the extracted facts/metrics, the computed scores, the schema, and Evidaxis's own compilation (incl. an explicit waiver of any sui-generis database right Evidaxis holds). It does NOT, and cannot, license third-party trademarks, upstream expressive content, or source-platform rights. A declared/detected upstream license string is a **FACT we record, never a PERMISSION we inherit**.

## Per-component license
| Component | License |
|---|---|
| Raw facts / metrics · computed scores / convergence · JSON schema · the collection-as-such | **CC0-1.0** (+ explicit sui-generis DB-right waiver) |
| Methodology document · authored prose | **CC-BY-4.0** |
| Collector + scoring code | **Apache-2.0** |
| Name / logo / "Evidaxis Rising" badge | **Trademark-controlled — NOT open-licensed** |

## What the genesis deposit SHIPS vs does NOT ship
**Ships (public, CC0):** extracted facts/metrics; SHA-256 content-hashes of each consumed source record (hashes of copyrighted bytes are themselves facts); a re-fetch recipe (endpoint + query + pinned-crawler commit + UTC timestamp); the Apache-2.0 transform/repro code + pipeline hash; external-archive pointers (Wayback / Software Heritage); the provenance + bias notices.
**Does NOT ship (ever, under CC0):** raw upstream expressive bytes (READMEs, model-card prose, source code); reconstructed plaintext abstracts; free-text repo `description` / model summary prose; natural-person account handles.
**Reproducibility ≠ redistribution:** a third party re-fetches via the recipe (or the archive pointer) → hashes → matches the deposit's content-hash. No upstream expressive byte is ever republished.

## Per-source reuse basis (primary-sourced)
- **arXiv** — bibliographic metadata AND the **abstract** are dedicated CC0 by arXiv's Submission Agreement ("Metadata includes title, author, abstract…") + API ToU. Abstracts MAY be CC0-republished WITH a per-record footer ("abstract: arXiv CC0 descriptive metadata; upstream paper rights reserved"); pin to the arXiv **abstract page**, never the PDF; e-prints (PDF/TeX) are author-copyright, never redistributed. *(Genesis may still exclude abstract prose for facts-only consistency; it is legally clear either way.)*
- **OpenAlex** — CC0 for facts + citation topology. **Do NOT reconstruct or republish plaintext abstracts** from the inverted index (OpenAlex ships an inverted index precisely "due to legal constraints"; the chain-of-title defect is REAL — the maintainer has removed Springer Nature abstracts inherited from MAG that lacked an open license). For any abstract need, source from arXiv (CC0), not OpenAlex.
- **GitHub** — public repo **facts/metrics only** (stars, forks, dates, language, topics, SPDX license-id, commit COUNTS) via compliant rate-limited API. NO README/code/description prose. Raw responses retained PRIVATE (sanitized) or pinned to a public archive — never CC0-redistributed.
- **Hugging Face** — public model **facts only** (id, downloads, likes, tags, pipeline, license-id). NO model-card prose. Same retention posture.

## Personal data (UK GDPR — systems-not-people)
- A GitHub/HF account `login`/handle that can relate to a natural person IS personal data (UK GDPR Art.4(1) "online identifiers"; ICO: a handle "uniquely identifies that individual"). An **Organization**-type account is a legal person, outside Art.4.
- **Default: publish only `Organization`-type handles** (verified via the platform account-`type` field); **strip natural-person (`User`) handles** from the CC0 deposit; any internal pseudonymous actor-id stays in the PRIVATE store only (pseudonymization ≠ anonymization — a re-identifiable salted hash is still personal data, so it is not published).
- **Immutable-DOI × right-to-erasure (Art.17):** an immutable CC0 DOI cannot be erased → personal handles in it are indefensible. On a verified erasure request, publish an **erratum/redaction record**, never a retroactive rewrite.
- **Strip → hash → retain → publish** (irreversible order): the published content-hash is of the PERSON-FREE artifact. Never build cross-source person profiles.

## Archive-pinning
- Pin each source pre-image to **Internet Archive Wayback (Save Page Now)** AND **Software Heritage (Save Code Now)** — independent archives that hold the pre-image under their OWN legal basis. **Async, throttled** (Wayback ≈15/min/IP; SWH ≈1,200/hr auth), robots-respecting, public-content-only — decoupled from the crawl. Store only the archive URL/SWHID + hash, never rehosted bytes.
- **Do NOT IPFS-pin raw upstream expressive bytes** (IPFS makes them publicly retrievable = breaks "expressive bytes stay private"); IPFS-pin only the derived CC0 facts dataset. Use both archives (single-archiver = SPOF; Wayback was DDoS-down Oct–Nov 2024).

## Deposit platform
**Zenodo provides no legal shield** — the uploader is solely responsible; CERN/Zenodo do not monitor or enforce. The conservative posture above is the only protection.

## Bias-of-inclusion (must travel with the deposit)
Genesis covers only open/public-API surfaces (GitHub-public, Hugging Face-public, arXiv, OpenAlex). It is a **hand-curated 19-system seed** across 3 cohorts (robotics-embodied, ai-drug-discovery, ai-coding-agents), a single t=0 observation point. **Closed / commercial / non-API / non-English / individual-maintained systems are systematically under-covered.** Inclusion correlates with openness. This is a **coverage-map of public-API-visible AI systems, not a census of AI; absence ≠ non-existence ≠ low-rank.**

## Solicitor-later triggers (NONE triggered by the genesis seed; priority order)
1. **OpenAlex publisher-rights** — at the first publisher notice, OR before scaling beyond ~10⁵ works.
2. **UK originality for short descriptive prose** (Infopaq/Meltwater unsettled) — before re-adding any free-text descriptions.
3. **Art.17 erasure × immutable-DOI** — a written opinion before the project reaches natural-person-data scale.

*Basis: a multi-source review of the primary terms cited above. Re-validate per-source terms annually.*
