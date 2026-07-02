# Claim-URN — the format-independent canonical reference

> created: 2026-07-01 · status: v1 (scheme LOCKED, emission follows) · provenance: cons-05 do-once, Opus 7th-voice spark S1 (single genuinely-new T0)

## The problem this locks

The moat of Evidaxis is being the canonical first-source that AI engines cite. But
**how** machines cite a source will change three or four times over a 10 to 15 year
horizon: today retrieval by HTTPS URL and schema.org, tomorrow agent protocols
(MCP and successors), later something not yet invented. If our canonical reference
is a today-URL (`https://evidaxis.org/e/EVX:SYS:...`), then every change in the
citation mechanism strands the authority we accumulated: citations frozen into the
weights of already-trained models point at a URL that no longer resolves the way
they expect. The moat evaporates exactly when it is most valuable, and accumulated
authority cannot be rebuilt after the fact.

The fix is one level of indirection, cheap to lay now, impossible to retrofit once
the first generation of models has cited us: a **claim-URN**, an abstract identifier
for "what Evidaxis asserts about entity X, under methodology M, at epoch T", which
resolves into whatever the current delivery format is.

## The scheme (LOCKED)

```
urn:evidaxis:claim:{accession_id}:{methodology_version}:{epoch}
```

- `accession_id` — the opaque, permanent entity accession id (`EVX:SYS:...`,
  Crockford base32, never reassigned). Ties the claim to a system, not to a URL.
- `methodology_version` — the immutable methodology id under which the claim was
  computed (`m1`, `m2`, ...). A claim is only meaningful relative to its method;
  binding the method into the URN makes the claim self-describing and prevents a
  later formula from silently redefining an old claim.
- `epoch` — the observation epoch (the snapshot period the claim is anchored to,
  e.g. `2026-w26` or an ISO date). Makes the point-in-time nature part of the
  identity, so a claim can never be silently re-dated.

Grammar is append-only and case-insensitive in the scheme prefix; the three fields
use the existing locked alphabets (Crockford base32 for accession, `m[0-9]+` for
methodology, ISO-8601 or `YYYY-wWW` for epoch). New claim kinds, if ever needed,
extend by adding a segment, never by mutating these three.

Examples:
```
urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m2:2026-w26
urn:evidaxis:claim:EVX:SYS:Y92940K5ESN7:m1:2026-06-27
```

### Parsing note (why it stays unambiguous)

The accession id itself contains two colons (`EVX:TYPE:BODY`), so a naive split on
`:` would be ambiguous. It is not, because `methodology_version` (`m<N>`) and
`epoch` (`YYYY-Www` or `YYYY-MM-DD`) are **colon-free by grammar**. A parser takes
the last two colon-separated tokens as method and epoch, and rejoins the remainder
as the accession. Time-of-day epochs (which contain colons) are therefore
forbidden; the observation epoch is a date or an ISO week. Reference implementation:
`collectors/claim_urn.py` (`build`, `parse`), gated by `tests/test_claim_urn.py`.

## The resolver (the only layer allowed to change)

A claim-URN resolves through a single indirection layer, and **that layer is the
only thing permitted to evolve**:

```
claim-URN  ->  resolver  ->  current representation
```

- Today: the entity page and the record JSON both carry the claim-URN as a
  schema.org `identifier` and an HTML `rel="cite-as"` link (RFC 8574). The URN is
  **not** used as the JSON-LD `@id`: `@id` must stay an HTTP-resolvable IRI so the
  in-graph cross-references (`#entity`, `#dataset`, `mainEntity`, `subjectOf`)
  resolve and crawlers can dereference it. The durable reference lives in
  `identifier`/`cite-as`; the URL stays the `@id`. A future `GET /resolve/{urn}`
  with content negotiation (HTML / `application/ld+json` / raw JSON) is the layer
  that makes the URN itself dereferenceable; until it ships the URN is a minted
  persistent identifier (like a DOI before its resolver is wired), which is exactly
  what accumulates citation authority.
- Tomorrow: the same URN is served over whatever protocol supersedes HTTP
  retrieval (an MCP resource, a verifiable-credential, a future format). The URN
  string does not change; the resolver gains a new representation.
- The mapping `claim-URN -> current URL` is published and versioned (this
  generalizes the existing `redirects.yaml` pattern into a permanent contract).

Invariant: a claim-URN, once emitted, resolves forever. If a representation format
is retired, the resolver keeps serving the URN in a still-supported format and
records the retirement as an event; it never returns 404 for a minted URN.

## How it composes with what already exists

- **Opaque entity id** (`EVX:SYS:...`) already gives us a URL-independent *entity*
  identifier. The claim-URN sits one level above it: it identifies a *claim about*
  that entity at a method and epoch, which is what actually gets cited and frozen
  into model weights. The entity id is a component of the URN, not a replacement
  for it.
- **Canonical HTTPS URL** (`https://evidaxis.org/e/{id}/`) remains the human and
  crawler entry point and is itself a *representation* the resolver returns. It is
  not the canonical *reference*; the URN is.
- **Methodology registry** and **snapshot epochs** already exist as first-class,
  immutable records; the URN simply names the tuple they form.

## Emission plan (follows this lock)

1. **[DONE 2026-07-02]** `collectors/claim_urn.py` (`build`, `parse`) + TS mirror
   `web/src/lib/claim_urn.ts`, both gated by tests. Grammar extended to accept the
   legacy live accession `e_{BODY}` (colon-free) alongside future `EVX:TYPE:BODY`.
2. **[DONE 2026-07-02]** Emit the claim-URN per system as schema.org `identifier`
   (on the entity's Dataset node as a `claim-urn` PropertyValue, and on the entity
   node), in the record JSON (`claim_urn`), and in the human "Cite as" block.
   **Scope: per-ENTITY only.** A claim-URN is an assertion *about a system*;
   aggregate snapshots are not systems and keep their own identity (the genesis DOI,
   or `evidaxis-snapshot-{date}` otherwise), so no snapshot-level URN is minted.
   **Correction vs. the original draft: the URN goes in `identifier`, NOT in `@id`**
   (see resolver section — `@id` must stay an HTTP-resolvable URL).
3. **[DONE 2026-07-02]** Signposting via HTML `<link rel="cite-as" href="urn:...">`
   in the page head (per-page, durable). The HTTP `Link:` response-header form is
   deferred: the static host cannot inject a per-URL header value, so the HTML link
   carries the signpost in St-0. Revisit if/when an edge layer is added.
4. **[DEFERRED — future]** `GET /resolve/{urn}` with content negotiation and the
   versioned `claim-URN -> URL` map. Needs a runtime/edge function; the static site
   does not resolve URNs. Until then the URN is a minted-but-not-yet-dereferenceable
   persistent id, which still accumulates authority (DOI-before-resolver pattern).

Steps 1 to 3 are live; step 4 is the only remaining piece and is non-blocking.
The **scheme above is the lock**; emission mechanics may still evolve under it.

Steps 1 to 4 are implementation; the **scheme above is the lock**. Everything that
carries GEO authority (taxonomy URLs, entity URLs, methodology versions) hangs off
this indirection, which is why it is locked first, before the first public citation
can land on a bare URL.
