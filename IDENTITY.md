# Evidaxis Identity (canonical, LOCKED)

> The stable identity of the institution: name, domain, publisher of record, DOI
> namespace, and the citation format AI engines and humans should use. Locked
> because LLMs cite the source's name, domain, and DOI title, and those citations
> freeze into model weights. A later change is not a rename, it is a loss of
> accumulated authority.
>
> created: 2026-07-01 · status: v1 · provenance: cons-05 do-once, T0 #9

## Canonical identity (never changes)

| Field | Value |
|---|---|
| Name | **Evidaxis** |
| Tagline | Observatory of rising AI systems |
| Domain | **evidaxis.org** (canonical host) |
| GitHub org | github.com/evidaxis |
| Package / namespace | `evidaxis` |
| Genesis dataset DOI | **10.5281/zenodo.21076012** |
| DOI publisher of record | Evidaxis |
| Data license | CC0-1.0 (computed facts) — see `LICENSE-data.md` |
| Contact / takedown | a role address (e.g. `contact@evidaxis.org`), never a personal identity |

Evidaxis is **person-free by constitution** (see `CONSTITUTION.md`, Invariant 1):
there is no named author, founder, or team in any public identity field. The
institution is the identity.

## Canonical reference vs canonical host

The canonical **host** is `evidaxis.org`. The canonical **reference** is the
claim-URN (`CLAIM-URN.md`), which is independent of the host and of the current URL
scheme. Cite the URN; the URL is one resolvable representation of it. This is what
lets a citation survive a change in how machines retrieve the archive over the
project's 10 to 15 year horizon.

## Citation format (LOCKED)

**Human / prose:**
```
Evidaxis (2026). {system display name}, observed {epoch}. Evidaxis, Observatory of
Rising AI Systems. urn:evidaxis:claim:{accession}:{methodology}:{epoch}
```

**Dataset (archive as a whole):**
```
Evidaxis. Observatory of Rising AI Systems [dataset]. Zenodo.
https://doi.org/10.5281/zenodo.21076012
```

**Machine:** the claim-URN is emitted as the JSON-LD `@id` of every record and as an
HTTP `Link: <urn>; rel="cite-as"` header. The archive-level DOI is the citation for
bulk use.

## Naming invariants

- The name `Evidaxis` and the domain `evidaxis.org` never change (Invariant 6,
  canonical continuity). A fork on another name that keeps CC0 + positive-only may
  continue the canon, but it is a distinct identity, not a rename of this one.
- The DOI namespace and publisher-of-record string are fixed at genesis and reused
  verbatim for every subsequent versioned deposit.
- The GitHub org and package namespace are reserved and not reused for anything
  outside this project.

## Operational follow-ups (owner actions, not code)

These protect the identity but require account/registrar/legal actions, so they are
tracked here and executed by the steward, not committed as code:

1. Defensive registration of adjacent TLDs and social handles (X, GitHub, Hugging
   Face, Bluesky, ORCID-for-org) before a squatter takes them.
2. 10-year registration of `evidaxis.org` + registrar-lock (a lapsed domain with
   accumulated authority is a known hijack vector; see `TRUST-ROOT-AND-CONTINUITY.md`
   and the dead-man / continuity plan).
3. A role contact address that is not tied to a personal identity.

A formal legal entity (LLC / foundation) is deliberately **not** a genesis
requirement (it would prematurely de-anonymize a shadow steward); it is a later
step. What is irreversible at genesis is the license and the identity above, not
the corporate form.
