# Amendment proposal: invariant 1, systems not people (2026-10-19)

> status: PROPOSED 2026-10-19, under the Amendment rule of `CONSTITUTION.md`.
> Freeze: 30 days from the publication of this file on the main branch. Published on
> 2026-10-19, the earliest valid decision date is **2026-11-18**. If this file reaches
> main later, both dates move by the same number of days.
> Touches: invariant 1 (text). Checked and left unchanged: invariants 3, 4 and 6, and
> the anti-roadmap. Decision: signed with the block-zero key (section 8).
> In force now, as a separate strengthening covenant: `governance/ERASURE-REQUESTS-2026-10-19.md`.

## 1. Summary

Invariant 1 promises that no natural-person handle is stored or published. The public
archive stores and publishes thousands of repository addresses that contain the account
names of natural persons. This proposal keeps the promise where it can be kept for
decades and states plainly where it cannot:

- data about a person is never stored or published, as today;
- an account name that is part of a system's address is never published, and the public
  repository counts as publication;
- collectors may keep such an address in a restricted store that holds locators and
  nothing else, because they need it to reach the system;
- published records use account-free identifiers, and the text says that this keeps
  persons out of the record without making a one-person system unlinkable.

Dated files committed before the switch keep their bytes (invariant 4). Identifiers leave
them only by tombstone, on request.

## 2. Why: the rule and the practice differ

### 2.1 What the rule says

- `CONSTITUTION.md`, invariant 1: "No natural-person name, handle, email, avatar, or
  contributor identity is stored or published."
- `RIGHTS-BASIS.md`: "Does NOT ship (ever, under CC0): ... natural-person account
  handles"; "Default: publish only Organization-type handles ...; strip natural-person
  (User) handles from the CC0 deposit"; "Strip → hash → retain → publish (irreversible
  order): the published content-hash is of the PERSON-FREE artifact."
- `README.md`: "Public projections omit personal account identifiers and apply
  person-free checks before publication."

### 2.2 What the archive holds (counted 2026-10-19 on main)

An address under a personal account means `<account>/<repository>` where the account has
type User and is not one of the 10 project accounts of
`governance/PROJECT-ACCOUNTS-2026-10-05.md`.

| Surface | Count |
|---|---|
| Snapshot 2026-10-17, `snapshot.json` (fields `github_repo`, `homepage`, and for 29 systems also `name` and `slug`) | 2,766 addresses; 2,775 systems have a User-type owner |
| Snapshot 2026-10-17, `provenance.json` and `dropped.json` | 2,775 and 9 addresses |
| Daily capture 2026-10-18: `observations.jsonl`, `deps.jsonl` | 2,774 and 2,775 addresses |
| Daily capture 2026-10-18: per-system provenance files (field `full_name`) | 2,775 of 6,324 files |
| `etl/owner_types.json` (registry) | 6,342 repositories, 2,795 of type User; 2,785 after project accounts; 2,480 distinct personal logins |
| `etl/seeds.json`, `etl/id_map.json` | 2,775 addresses each |
| `entities/` (permanent system records) | 2,786 records |
| `data/deps_id_map.json` (package identity pins) | 715 of 1,804 pins keyed by such an address |
| `data/census/2026-10/pending-manifest.json` | 2,744 addresses |
| Expansion manifest of 2026-10-19 (axis 3) | 119 package names in a personal namespace (80 Go modules `github.com/<account>/...`, 39 npm scopes `@<account>/...`), 114 of them verified; 9 more package names equal a personal login |
| `web/src/data/person-free-handles.json` | 12 personal handles, listed in plain text by the file that keeps them out of publication |
| Hand-written files and commit messages | 5 documents name a current or former personal owner, among them the owner-transfer records of 2026-10-03 and 2026-10-04 and `governance/CENSUS-AI-V1-PREDICATE-2026-08-03.md`; manual commit messages name such addresses too, for example owner-cache confirmations |
| CI of the public repository | the frozen collector prints every address it collects; several collectors and both publication guards print addresses or handles in warnings; the rehearsal and any failed weekly run upload the raw snapshot folder as an artifact for 14 days. Logs and artifacts of a public repository are open to any signed-in GitHub user |

Every surface above is public: it is served by GitHub, mirrored to GitLab and archived by
Software Heritage. The Hugging Face dataset and the Zenodo versions published since
2026-10-05 apply a person-free projection. The website projects snapshots and provenance,
but it serves each date's `dropped.json` as raw bytes, which its guard exempts: 6 of 19
dated files hold 28 distinct addresses under personal accounts.

### 2.3 Deposits

- The genesis deposit (2026-06-27, DOI 10.5281/zenodo.21076012) contains 1 such address,
  in `snapshot.json`, `provenance.json` and `archive-pointers.json`. Its README states
  that the deposit is person-free. The same bytes are in `genesis-deposit/` and
  `data/snapshots/2026-06-27/`, and CI keeps them byte-identical.
- The Zenodo version of 2026-07-10 (DOI 10.5281/zenodo.21307528) contains 10 such
  addresses. The identical zip file is tracked at the root of this repository.

### 2.4 Earlier decisions already pointed this way

- `governance/ADJUDICATION-2026-07-11.md`, item 7, adopted option (c) forward: from the
  next methodology version, committed archive files carry only stable system ids,
  organization slugs and numeric ids, and personal path segments do not enter new bytes.
  Methodologies m3 (2026-09-14), m4 (2026-10-04) and m5 (2026-10-16) shipped without it.
- `data/registry_ids.json` (2026-08-03) already anchors identity on the numeric GitHub
  repository id, which survives renames and transfers.
- Since 2026-10-05, Zenodo versions are strict person-free projections, because a CC0
  DOI cannot be withdrawn (`TRUST-ROOT-AND-CONTINUITY.md`).
- `governance/NOTE-2026-10-18-public-provenance.md` publishes `gh:<repo_id>` in place of
  repository addresses on the website.

### 2.5 What masking does not do

- The permanent Evidaxis id of a system is computed from its original address: `e_`
  plus 10 Crockford characters from the first 64 bits of the SHA-256 of the lower-cased
  address (`etl/collect.py`, `mint_entity_id`). Anyone who knows an address can compute
  its id.
- The numeric repository id resolves to the current owner through the platform's API.
- A record that shows "System e_..." therefore hides a name on the page. It does not make
  the record anonymous. Pseudonymous data is still personal data, as `RIGHTS-BASIS.md`
  already says for actor ids.

### 2.6 Rights-basis trigger

`RIGHTS-BASIS.md` lists, as solicitor-later trigger 3, a written opinion on erasure and
immutable DOIs "before the project reaches natural-person-data scale". With 2,785
repositories under personal accounts, that scale is reached. The decision in section 8
records whether the opinion is obtained before the switch, or why it is deferred and until
which event.

## 3. Where the line runs

Two readings were considered.

**Angle A: a repository address identifies a program, not a person.** This is right
about the unit and the purpose. Evidaxis observes the program, and it uses the address
only to reach the program. It never treats the account as a subject. This is why a
restricted locator store is legitimate.

Read as permission to publish, angle A fails three tests. First, the account part of the
address is the account holder's online identifier, by the project's own analysis in
`RIGHTS-BASIS.md`. Second, publication is not necessary: the platform's numeric id serves
citation, verification and continuity equally well. Third, CC0 bytes in git, mirrors and
DOIs cannot be called back.

**Angle B as first worded: replace "stored or published" with "published".** This is
right about publication. Taken literally, it would also lift the storage ban for data about persons,
which must stay absolute. It would also let the word "person-free" keep implying that the
records cannot be linked to anyone.

**The line proposed here** runs between "a program's identifier in someone else's
registry" and "a personal account as a subject". It decides storage. Publication follows
a stricter, mechanical test: does the value contain a personal account name? Three
classes result.

| Class | Examples | Stored | Published |
|---|---|---|---|
| Data about a person | name, email, avatar, bio, followers, contributor list, any measure of a person, any owner-level grouping | never | never |
| Personal account identifier inside a locator | `<account>/<repository>`, `github.com/<account>/...`, `<account>.github.io`, `@<account>/<package>`, a package named exactly like the login | restricted locator store only, for collection | never |
| Account-free identifiers of a system | Evidaxis id, numeric GitHub repository id `gh:<id>`, GraphQL node id, repository name that does not reveal the account | yes | yes |

The necessity test decides each case: Evidaxis may use a value where collection needs it,
and publishes only what citation, verification and continuity need. No published purpose
needs an account name.

## 4. Proposed text, was and becomes

These texts change only after the signed decision. Dates in angle brackets are fixed by
that decision.

### 4.1 `CONSTITUTION.md`, invariant 1

Was:

> 1. **Systems, not people.** No natural-person name, handle, email, avatar, or
>    contributor identity is stored or published. Enforced mechanically: a snapshot
>    containing a person field does not serialize and fails CI. Online identifiers are
>    personal data (UK GDPR) even when public; the first leak into a CC0 DOI is
>    irreversible, so the gate is fail-closed.

Becomes:

> 1. **Systems, not people.** Evidaxis observes systems, never persons. No natural
>    person's name, email, avatar, profile or contributor identity, and no measure of a
>    person (such as a per-contributor count), is stored or published. A personal
>    account identifier, meaning the login of a natural person's account or any address
>    or package name that contains it, is never published: the public repository, its
>    mirrors, the website, dataset mirrors, deposits, and CI logs and artifacts are all
>    publication. A collector may hold such an identifier only as the locator of a
>    system it observes or reviews, in a restricted store that holds nothing else, and
>    deletes it when the system leaves the observed set or the account holder asks. Published records of such a system use
>    account-free identifiers. This keeps persons out of the record; it does not make a
>    system run by one person impossible to link to that person. Files committed before
>    the person-free switch (date in the changelog) keep their bytes under invariant 4;
>    an identifier leaves them only by tombstone, on request. Online identifiers are
>    personal data (UK GDPR) even when public, and a CC0 deposit cannot be withdrawn, so
>    the gate is fail-closed: new published bytes that contain a personal account
>    identifier fail CI.

### 4.2 `CONSTITUTION.md`, changelog entry on decision

> - **<decision date>: amendment of invariant 1 (signed).** Personal account identifiers
>   are never published, the public repository included; collectors may keep them only
>   as locators in a restricted store; published records use account-free identifiers;
>   the text states that this is not anonymity. Person-free switch: weekly release
>   <switch date>. Proposal: `governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`;
>   decision and signature: `governance/AMENDMENT-DECISION-<date>-invariant-1.md`.
>   Invariants 3, 4 and 6 are unchanged (proposal, section 5).

### 4.3 `RIGHTS-BASIS.md`

The genesis text stays readable, as for sources. A dated section is appended after
"Personal data (UK GDPR — systems-not-people)".

Was (the operative sentence):

> **Default: publish only `Organization`-type handles** (verified via the platform
> account-`type` field); **strip natural-person (`User`) handles from the CC0 deposit**;
> any internal pseudonymous actor-id stays in the PRIVATE store only
> (pseudonymization ≠ anonymization — a re-identifiable salted hash is still personal
> data, so it is not published).

Becomes (appended section):

> **Personal data: amendment of invariant 1** *(dated append <decision date>; applies to
> files committed from <switch date>)*
>
> - **Publication.** The public git repository (files, history, commit messages), its
>   mirror and archive copies, the website, the Hugging Face dataset, Zenodo deposits,
>   and the logs and artifacts of the public repository's CI.
> - **Personal account identifier.** The login of a natural person's account, and any
>   value that contains it: `<account>/<repository>`, a URL under `github.com/<account>`,
>   `<account>.github.io` or `raw.githubusercontent.com/<account>/`, a package name in the
>   account's namespace (`@<account>/<package>`, `github.com/<account>/<module>`), a
>   package name equal to the login. A User-type account is personal unless it is a
>   project account under `governance/PROJECT-ACCOUNTS-2026-10-05.md`. An
>   Organization-type account is not personal by default; one later found to stand for a
>   single natural person is treated as personal from the next release.
> - **Published.** Nothing Evidaxis publishes contains a personal account identifier. A
>   system under a personal account is published with its Evidaxis id, its numeric GitHub
>   repository id (`gh:<id>`) and node id, and its repository name unless that name
>   reveals the account. Its homepage is omitted. A package name that reveals the account
>   is replaced by a stable opaque key. The numeric id identifies the repository, not its
>   owner: no owner id, login or actor id is published, and no view groups systems by
>   owner.
> - **Stored.** Personal account identifiers are kept only in the restricted locator
>   store, a private repository of the Evidaxis organization that the collection
>   workflows and the steward read and write. It holds the locators, current and former,
>   of observed systems and of census candidates under review, plus the numeric ids of
>   repositories retired at their account holder's request, and nothing else: no
>   measured or computed value and no attribute of any person. It feeds no product and is
>   never shared, sold or licensed. A locator is deleted within 30 days after its system
>   leaves the observed universe or its candidate is decided, and within one month of an
>   erasure request, from the store's history too. The store can be rebuilt from public
>   numeric ids and the platforms, so its loss loses nothing canonical.
> - **Not anonymity.** Account-free identifiers are pseudonymous. The platform resolves a
>   numeric id to the current owner, and the Evidaxis ids of systems admitted so far are
>   derived from their original address. Evidaxis does not describe its records as
>   anonymous, and it honors erasure requests (`governance/ERASURE-REQUESTS-2026-10-19.md`).
> - **Before the switch.** Dated files keep their captured bytes (invariant 4) and
>   contain personal account identifiers; the 2026-10-17 snapshot holds 2,766. The genesis
>   deposit holds 1 and the Zenodo version of 2026-07-10 holds 10, although the genesis
>   README describes the deposit as person-free. Identifiers leave these files only by
>   tombstone, on request.
> - **Order.** "Strip → hash → retain → publish" applies to every dated file from the
>   switch: checksums, manifest hashes and snapshot ids are computed over the person-free
>   bytes.
> - **Superseded forward.** "natural-person account handles" in the "Does NOT ship" list
>   now means personal account identifiers on every publication surface. "Strip
>   natural-person (User) handles from the CC0 deposit" now applies to every publication
>   surface. The actor-id sentence and the erasure sentence ("publish an
>   erratum/redaction record, never a retroactive rewrite") stay as written.

### 4.4 `README.md`

Was: "Publication projections apply the person-free rules before distribution."

Becomes: "From <switch date>, the files committed here are the person-free record itself,
so the website and mirrors carry the same bytes. Earlier dated files keep their captured
bytes, which include repository addresses under personal accounts."

Was: "The unit of observation is a system. Public projections omit personal account
identifiers and apply person-free checks before publication."

Becomes: "The unit of observation is a system. From <switch date>, nothing committed to
this repository names a personal account: a system under a personal account appears by
its Evidaxis id and its numeric GitHub repository id. This keeps people out of the
record; it does not make a one-person system unlinkable to its maintainer. Removal
requests: hello@evidaxis.org
([procedure](governance/ERASURE-REQUESTS-2026-10-19.md))."

The last sentence describes a procedure that is in force now and may be added at once.

### 4.5 `AGENTS.md`

Was: no person-free rule.

Becomes, under "Hard rules":

> - Person-free (invariant 1): never write a repository address, URL or package name of
>   a personal account into a tracked file, commit message, issue, log line or artifact;
>   use the entity id or `gh:<repo_id>`. From <switch date> privacy-gate fails on it.
>   Only collectors read the locator store.

This is a self-restriction and may be added at once.

### 4.6 Changed together with the switch

- `distribution/hf/README.md`: from <switch date>, the dated `snapshot.json` is
  byte-identical to the archived file.
- Website, about page: "with raw provenance published" becomes "with source provenance
  published"; the snapshot page states that for dates from <switch date> the downloaded
  files match `SHA256SUMS`.
- `TRUST-ROOT-AND-CONTINUITY.md`, copy map: one row for the restricted locator store,
  marked as not a copy of the archive.

### 4.7 Not changed

`IDENTITY.md` (it concerns the institution's own identity); `genesis-deposit/` (frozen;
its statement is corrected by section 2.3 of this record); dated governance records.

## 5. Invariants 3 and 6: an amendment, not a fork

The Amendment rule says: "A change that violates Invariant 3 or 6 is not an amendment, it
is a fork." The relevant texts:

- Invariant 3: "Every computed fact, score, schema, and metadata field is released CC0."
- Anti-roadmap covenant of 2026-07-02: "every paid byte must remain derivable from the
  public git ... The public archive keeps full captured granularity; there is no privately
  hoarded finer-grained series."
- Invariant 6: "The record is anchored and byte-reproducible from public inputs, so its
  past integrity does not depend on any living person."

A restricted store keeps this change inside the amendment process only while five
conditions hold. Each one gets a CI test or a rehearsal check before the switch.

1. **Locators only.** The store holds no measured or computed value, no series and no
   attribute of a person. Every measurement stays in the public archive at full captured
   granularity, with package-level rows under opaque keys where a package name would
   reveal an account.
2. **No computation reads the store.** Every published value is computed from files in
   the public repository. The store is used only to fetch.
3. **Rebuildable.** Every system under a personal account carries its numeric repository
   id and node id in public. A successor without the store resolves them on the platform
   and continues the record.
4. **Hashes over published bytes.** Checksums, manifest hashes, snapshot ids and Merkle
   roots are computed over the person-free files, so anyone can verify them from public
   files.
5. **No product.** The store feeds no product, paid or free, and is never shared.

The account name is not a computed fact or a metadata field of Evidaxis. It is a third
party's identifier, and invariant 1 has always kept such identifiers out of the released
set. Withholding it coarsens no measurement.

The change would become a fork if any condition failed: a private copy of measurements, a
computation that needs the store, a record whose continuation needs the store, a hash
over private bytes, or a product built on the store.

## 6. Invariant 4 and history

The change is forward-only. Dated files committed before the switch keep their bytes, and
git history is not rewritten: the main branch refuses force-pushes, administrators
included. A person's identifiers leave the current tree only through the erasure
procedure, by tombstone, which the anti-roadmap permits ("only legal or privacy removal
via a tombstone that preserves the fact-of-existence"). Earlier commits and copies held by
others keep them, and the procedure says so to the requester.

## 7. What changes when

### 7.1 From 2026-10-19 (strengthening only)

- The erasure procedure is in force once its changelog entry is published.
- No personal account identifier is added by hand to tracked files, governance records,
  commit messages, issues or pull requests. Automated data commits continue unchanged
  until the switch.
- Until the switch, the project is out of line with the word "stored" and with the
  publication rule, as it has been since genesis. This record says so; no partial step
  is described as compliance.

### 7.2 During the freeze (2026-10-19 to 2026-11-17)

The implementation is built and rehearsed on a branch. The restricted store may be seeded
for rehearsals with copies of identifiers that are public at that time. It becomes their
only holder at the switch, after the decision. The weekly releases keep their current
format; release-chain changes follow `governance/RELEASE-SCHEDULE-2026-10-18.md`.

### 7.3 On the signed decision (not before 2026-11-18)

The texts of section 4 change in one commit that cites the decision. The decision fixes
the switch date: the first weekly release after the decision with a green full rehearsal,
targeted for **2026-11-21**. A new person-free check in CI goes live on that date and
fails on any new published byte that contains a personal account identifier.

### 7.4 If the decision rejects the storage exception

No store is kept. Collectors resolve addresses at run time from public numeric ids and
keep nothing between runs. The publication rule of section 4 still applies.

## 8. Signature (step 3 of the Amendment rule)

**Facts.** `CONSTITUTION.md` and `TRUST-ROOT-AND-CONTINUITY.md` name an Ed25519
block-zero key whose public key and fingerprint are "inscribed permanently". The public
repository holds no such public key, no key registry and no signature file, and the
genesis deposit on Zenodo contains none. The dead-man heartbeat key of
`dead-man/DEAD-MAN.md` has not been generated: `data/integrity/` holds no
`heartbeat-pubkey.txt`. The M-of-N recovery deadline of 2026-10-01
(`governance/ADJUDICATION-2026-07-11.md`, item 3) has no record. The adoptions of
2026-07-11 were recorded without a cryptographic signature. This amendment is the first act
that requires one.

**Procedure.**

1. Before 2026-11-18, the steward generates an Ed25519 key offline. The private key never
   enters CI, a chat, a shared drive or this repository. The steward commits a dated key
   record (`governance/KEY-REGISTRY-<date>.md` with the public key file and
   `governance/allowed_signers`): algorithm, public key, fingerprint, and the statement
   that it is the block-zero key of the governance chain. The record is stamped with
   OpenTimestamps in the same week. The same key serves as the dead-man heartbeat key, so
   there is one trust root.
2. On or after 2026-11-18, the steward writes
   `governance/AMENDMENT-DECISION-<date>-invariant-1.md`: adopt, adopt with changes, or
   reject; the final texts; the switch date; the comments received and the answers.
3. The steward signs that file with the block-zero key and commits the detached
   signature next to it, with the command that verifies it from public files only. With
   an OpenSSH key: `ssh-keygen -Y sign -f <key> -n evidaxis-governance <file>` to sign,
   and `ssh-keygen -Y verify -f governance/allowed_signers -I <signer identity>
   -n evidaxis-governance -s <file>.sig < <file>` to verify.
4. The decision file is stamped with OpenTimestamps and the stamp is committed.
5. The texts of section 4 and the changelog entry follow in one commit citing the
   decision. The next weekly manifest anchors the new hash of the constitution.

Only the steward signs; an agent may draft the decision. A decision signed before the
earliest date, by another key, or without a stamp is not valid. A material change to this
proposal restarts the freeze; an editorial correction does not.

## 9. Comments during the freeze

Write to hello@evidaxis.org with the subject "Invariant 1 proposal", or open a public
issue that names no person and no account. The decision lists every comment received and
its answer, without personal data.

## 10. Falsification

This formulation is wrong if, by 2026-12-31, any byte published after the switch contains
a personal account identifier, a value of a post-switch snapshot cannot be recomputed from
public files alone, or an erasure request cannot be completed within one month without
rewriting git history. Checked by the CI person-free check, a rehearsal with an empty
locator store, a full scan before the next quarterly Zenodo version, and the request
records of the erasure procedure.

## 11. Related items not decided here

- **Shadow layer.** `governance/SHADOW-LAYER-2026-08-03.md` keeps, in a private
  repository, the address (`full_name`) of every repository in the 200 to 499 star band,
  personal accounts included, and weekly star observations retained indefinitely "for a
  possible future private data product". That is stored personal account data under the
  current invariant 1, and a private series that the covenant of 2026-07-02 does not
  provide for. This proposal does not authorize either. A separate act should address
  repositories by node id and decide on the private series.
- **Ids of new admissions.** New systems receive ids derived from their address, because
  the frozen collector mints them. This is the main link that remains after the switch:
  with a public list of repository names, anyone can recover the original address from
  the id, even after the repository is renamed or deleted. Whether systems admitted
  under personal accounts should receive ids that are not derived from the address is a
  question for the claim-URN rules, best decided before the switch.
- **Invariant 6 wording.** `governance/ERRATUM-2026-09-14-byte-reproducible-claim-on-derived-surfaces.md`
  left the phrase "byte-reproducible from public inputs" open. This proposal does not
  change it.
- **Upstream text and rows.** Daily provenance files keep free-text repository
  descriptions, and `data/observations/` keeps raw rows from the deps.dev BigQuery
  tables, while `RIGHTS-BASIS.md` excludes description prose and upstream response bytes.
  This concerns rights, not persons, and needs its own record.

*Positive-only note: this proposal concerns the project's own handling of identifiers.
No measurement, score, recognition or system identity is created, changed or withdrawn
by it.*
