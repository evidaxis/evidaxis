# Amendment proposal: invariant 1, systems not people (2026-10-19)

> status: PROPOSED 2026-10-19, under the Amendment rule of `CONSTITUTION.md`. Revised the
> same day after an independent review (section 12); the revision is material.
> Freeze: 30 days from the publication of this file on the main branch. Published, in
> its revised form, on 2026-10-19, so the earliest valid decision date is **2026-11-18**.
> If the revision reaches main later, both dates move by the same number of days.
> Touches: invariant 1 (text). Checked and left unchanged: invariants 3, 4 and 6, and
> the anti-roadmap. Decision: signed with the block-zero key (section 8).
> In force now, as a separate strengthening covenant: `governance/ERASURE-REQUESTS-2026-10-19.md`.

## 1. Summary

Invariant 1 promises that no natural-person handle is stored or published. The public
archive stores and publishes thousands of repository addresses that contain the account
names of natural persons. This proposal keeps the promise where it can be kept for
decades and states plainly where it cannot:

- the record holds no data about a person, as today;
- an account name that is part of a system's address is never published, and the public
  repository counts as publication;
- collectors use such an address only while a run lasts, to reach the system, and keep
  nothing of it afterwards: there is no store of these addresses;
- messages that people send to Evidaxis are kept apart from the record, on a deletion
  schedule;
- published records use account-free identifiers that public sources resolve, and the
  text says that this keeps persons out of the record without making a one-person system
  unlinkable.

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
| CI of the public repository | the frozen collector prints every address it collects; several collectors and both publication guards print addresses or handles in warnings; the rehearsal and any failed weekly run upload the raw snapshot folder and a list of addresses (`warm-202.json`) as an artifact for 14 days. Logs and artifacts of a public repository are open to any signed-in GitHub user |

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
only to reach the program. It never treats the account as a subject. This is why
collectors may use the address while a run lasts.

Read as permission to publish, angle A fails three tests. First, the account part of the
address is the account holder's online identifier, by the project's own analysis in
`RIGHTS-BASIS.md`. Second, publication is not necessary: the platform's numeric id serves
citation, verification and continuity equally well. Third, CC0 bytes in git, mirrors and
DOIs cannot be called back.

**Angle B as first worded: replace "stored or published" with "published".** This is
right about publication. Taken literally, it would also lift the storage ban for data
about persons, which must stay absolute. It would also let the word "person-free" keep
implying that the records cannot be linked to anyone.

**The line proposed here** runs between "a program's identifier in someone else's
registry" and "a personal account as a subject". It decides use. Publication follows a
stricter, mechanical test: does the value contain a personal account name? Keeping
follows the strictest test: nothing that contains one outlives the run that used it.

| Class | Examples | Kept between runs | Published |
|---|---|---|---|
| Data about a person | name, email, avatar, bio, followers, contributor list, any measure of a person, any owner-level grouping | never | never |
| Personal account identifier inside a locator | `<account>/<repository>`, `github.com/<account>/...`, `<account>.github.io`, `@<account>/<package>`, a package named exactly like the login | never; used within a run only | never |
| Account-free identifiers and pointers | Evidaxis id, numeric GitHub repository id `gh:<id>`, GraphQL node id, repository name that does not reveal the account, pointer to the manifest that declares a package | yes | yes |
| Correspondence | a removal request and its answer | in the project mailbox only, on a deletion schedule | never |

The necessity test decides each case: Evidaxis uses a value only where collection needs
it, and publishes only what citation, verification and continuity need. No published
purpose needs an account name, and no collection step needs to keep one: the platform
resolves account-free ids to current addresses at the start of each run.

## 4. Proposed text, was and becomes

These texts change only after the signed decision. Dates in angle brackets are fixed by
the switch record and the decision.

### 4.1 `CONSTITUTION.md`, invariant 1

Was:

> 1. **Systems, not people.** No natural-person name, handle, email, avatar, or
>    contributor identity is stored or published. Enforced mechanically: a snapshot
>    containing a person field does not serialize and fails CI. Online identifiers are
>    personal data (UK GDPR) even when public; the first leak into a CC0 DOI is
>    irreversible, so the gate is fail-closed.

Becomes:

> 1. **Systems, not people.** Evidaxis observes systems, never persons, and keeps three
>    kinds of data apart. **The record** (snapshots, observations, registries, system
>    records and everything derived from them) holds no natural person's name, email,
>    avatar, profile or contributor identity, and no measure of a person, such as a
>    per-contributor count. **Locators:** a personal account identifier, meaning the
>    login of a natural person's account or any address or package name that contains
>    it, is never published; the public repository, its mirrors, the website, dataset
>    mirrors, deposits, and CI logs and artifacts are all publication. Collectors and
>    checks use such an identifier only within a run, to reach a system or to recognize
>    the identifier, and keep nothing of it after the run; the record names such a
>    system by account-free identifiers that public sources resolve. **Correspondence**
>    with people who write to Evidaxis, such as removal requests, is not part of the
>    record: it stays in the project mailbox and is deleted on the schedule of the
>    erasure procedure. Account-free identifiers keep persons out of the record; they do
>    not make a system run by one person impossible to link to that person. Files
>    committed before the person-free switch (date in the changelog) keep their bytes
>    under invariant 4; an identifier leaves them only by tombstone, on request. Online
>    identifiers are personal data (UK GDPR) even when public, and a CC0 deposit cannot be
>    withdrawn, so automated publication is fail-closed: a check before every push,
>    upload and deployment stops new bytes that contain a personal account identifier.

### 4.2 `CONSTITUTION.md`, changelog entry on decision

> - **<decision date>: amendment of invariant 1 (signed).** The record, locators and
>   correspondence are kept apart. Personal account identifiers are never published, the
>   public repository included; collectors use them only within a run and keep nothing;
>   published records use account-free identifiers; the text states that this is not
>   anonymity; automated publication is checked before it happens. Person-free switch:
>   weekly release <switch date>. Proposal:
>   `governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`; decision and signature:
>   `governance/AMENDMENT-DECISION-<date>-invariant-1.md`. Invariants 3, 4 and 6 are
>   unchanged (proposal, section 5).

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
>   single natural person is treated as personal from the next release. A package
>   namespace counts as personal unless it is verified to belong to an organization.
> - **Published.** Nothing Evidaxis publishes contains a personal account identifier. A
>   system under a personal account is published with its Evidaxis id, its numeric GitHub
>   repository id (`gh:<id>`) and node id, and its repository name unless that name
>   reveals the account. Its homepage is omitted. A package whose name reveals the
>   account is recorded by an account-free pointer to the manifest that declares it: the
>   repository id, the file path and the git blob id. The numeric id identifies the
>   repository, not its owner: no owner id, login or actor id is published, and no view
>   groups systems by owner.
> - **Used within a run, never kept.** Collectors and checks obtain personal account
>   identifiers at run time, from the platform by account-free id or from files committed
>   before the switch, and use them only within that run, in memory and in the run's
>   temporary files. No copy is kept between runs, in the repository or anywhere else.
>   Systems admitted after the switch take `gh:<repository id>` as their natural key, so
>   their Evidaxis id is not derived from an address.
> - **Do-not-observe list.** The numeric ids of repositories retired at their account
>   holder's request are kept, without versions, in a repository secret that every run
>   reads before any request about those repositories, with an encrypted backup held by
>   the steward. The list holds numeric ids and nothing else.
> - **Correspondence.** Messages from people who write to Evidaxis stay in the project
>   mailbox, outside the record, and are deleted under
>   `governance/ERASURE-REQUESTS-2026-10-19.md`.
> - **Not anonymity.** Account-free identifiers are pseudonymous. The platform resolves a
>   numeric id to the current owner, and the Evidaxis ids of systems admitted before the
>   switch are derived from their original address. Evidaxis does not describe its
>   records as anonymous, and it honors erasure requests.
> - **Reproducing and continuing.** Every published value, and every link between
>   published records, can be recomputed and interpreted from public files and public
>   sources alone; no closed table is needed. Continuing collection depends on the
>   platform: if a repository, or the manifest behind a package pointer, is deleted
>   upstream and is not archived elsewhere (for example by Software Heritage), its
>   further observation, and the package name behind that pointer, can be lost. This
>   holds for every system.
> - **Checked before publication.** Automated publication (the weekly and daily commits,
>   the dataset upload, the Zenodo stage and the website deployment) runs a person-free
>   check before it pushes, uploads or deploys, and stops on a finding. Hand-made commits
>   pass a local check before they are pushed. A check after each push catches what
>   bypasses it, and the steward removes such a finding by tombstone within a day.
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
record; it does not make a one-person system unlinkable to its maintainer."

The sentence on removal requests has been in the README since 2026-10-19.

### 4.5 `AGENTS.md`

The section "Person-free (invariant 1)" has been in force since 2026-10-19. On the switch,
it gains one rule:

> - Install the repository's pre-push check (`git config core.hooksPath scripts/hooks`)
>   and never bypass it. No store of personal account identifiers exists: collectors
>   resolve them within a run and keep nothing.

### 4.6 Changed together with the switch

- `distribution/hf/README.md`: from <switch date>, the dated `snapshot.json` is
  byte-identical to the archived file.
- Website, about page: "with raw provenance published" becomes "with source provenance
  published"; the snapshot page states that for dates from <switch date> the downloaded
  files match `SHA256SUMS`.

### 4.7 Not changed

`IDENTITY.md` (it concerns the institution's own identity); `TRUST-ROOT-AND-CONTINUITY.md`
(no new copy of the archive and no new store); `genesis-deposit/` (frozen; its statement
is corrected by section 2.3 of this record); dated governance records.

## 5. Invariants 3 and 6: an amendment, not a fork

The Amendment rule says: "A change that violates Invariant 3 or 6 is not an amendment, it
is a fork." The relevant texts:

- Invariant 3: "Every computed fact, score, schema, and metadata field is released CC0."
- Anti-roadmap covenant of 2026-07-02: "every paid byte must remain derivable from the
  public git ... The public archive keeps full captured granularity; there is no privately
  hoarded finer-grained series."
- Invariant 6: "The record is anchored and byte-reproducible from public inputs, so its
  past integrity does not depend on any living person."

The change stays an amendment while five conditions hold.

1. **Nothing about persons is kept.** No store of personal account identifiers exists.
   The only closed list, the do-not-observe list, holds numeric repository ids. It
   decides what is collected next and never changes a published value.
2. **Every computation runs on public files.** Every published value is computed from
   files in the public repository, at full captured granularity, package-level rows
   included.
3. **Every key resolves through public sources.** Each system under a personal account
   carries its numeric repository id and node id; each package row in a personal
   namespace carries its manifest pointer. A reader interprets them through the platform
   or an archive such as Software Heritage. No closed table is needed to read any
   published series; if one were needed, that would breach invariants 3 and 6.
4. **Hashes over published bytes.** Checksums, manifest hashes, snapshot ids and Merkle
   roots are computed over the person-free files, so anyone can verify them from public
   files.
5. **Nothing closed feeds a product.** The do-not-observe list and the run-time memory of
   a collector feed no product, paid or free, and are never shared.

A check confirms the conditions, not a definition of what counts as metadata. The
archive-integrity workflow runs on the public repository alone, without any secret, after
every data push. From the switch, it fails if a post-switch record lacks an account-free
link (a system without `gh:<id>`, a package row in a personal namespace without a
pointer), or if any recomputation of scores, checksums, snapshot ids or ledgers needs a
file that is not public.

Reproducing the past and continuing the record are different promises. Past values and
links are reproducible from public files indefinitely. Continuing to observe a system
needs the platform, for every system: if a repository is deleted upstream, its
observation ends, as it does today.

The change would become a fork if any of these appeared: a private copy of a measurement;
a computation or an interpretation that needs a closed table; a persistent store of
personal account identifiers on which a record or its continuation depends; a hash over
private bytes; a product built on anything closed.

## 6. Invariant 4 and history

The change is forward-only. Dated files committed before the switch keep their bytes, and
git history is not rewritten: the main branch refuses force-pushes, administrators
included. A person's identifiers leave the current tree only through the erasure
procedure, by tombstone, which the anti-roadmap permits ("only legal or privacy removal
via a tombstone that preserves the fact-of-existence"). Earlier commits and copies held by
others keep them, and the procedure says so to the requester.

## 7. What changes when

### 7.1 From 2026-10-19 (strengthening only)

- The erasure procedure is in force; its changelog entry was published on 2026-10-19.
- No personal account identifier is added by hand to tracked files, governance records,
  commit messages, issues or pull requests. Automated data commits continue unchanged
  until the switch.
- No store of personal account identifiers is created, now or later.
- Until the switch, the project is out of line with the word "stored" and with the
  publication rule, as it has been since genesis. This record says so; no partial step
  is described as compliance.

### 7.2 During the freeze (2026-10-19 to 2026-11-17)

The implementation is built and rehearsed on a branch. The weekly releases keep their
current format, and release-chain changes follow `governance/RELEASE-SCHEDULE-2026-10-18.md`.

### 7.3 The switch

The switch is not a change made by this proposal. It brings practice in line with the
current text of invariant 1 and `RIGHTS-BASIS.md`, which already forbid publishing such
handles: it publishes less and keeps nothing new. It therefore needs no decision, and
the texts of section 4 still change only with the decision. A dated record fixes the
switch date before the switch. The target stays the
weekly release of **2026-11-21**: the implementation needs about three weeks, and a large
change to the release chain during the four-release reliability series of
`governance/RELEASE-SCHEDULE-2026-10-18.md` (2026-10-24 to 2026-11-14) would put that
series at risk. Preconditions:

- a green full rehearsal of the switched chain;
- the pre-publication checks of section 4.3 in place in the weekly and daily chains, the
  dataset upload, the Zenodo stage and the website deployment;
- the shadow layer no longer keeps repository addresses (section 11).

### 7.4 On the signed decision (not before 2026-11-18)

The texts of section 4 change in one commit that cites the decision.

### 7.5 If the decision rejects the amendment

The switch stands, because it complies with the current text. Invariant 1 keeps that text,
and the gaps that this record discloses (files committed before the switch,
correspondence) stay open until another proposal resolves them.

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

The key described below is therefore new. Its key record is its first publication, and it
authenticates nothing earlier: acts before that record rest on git history and on
OpenTimestamps stamps where they exist.

**Who does what.** The steward decides. The steward's assistant, software that acts for
the steward on the steward's own computer, performs the mechanical steps. It acts only on
the steward's explicit approval of a named file and that file's SHA-256. The key never
enters CI, a remote machine, a chat, a shared drive or this repository. An air gap is not
claimed.

**Procedure.**

1. **Key, once, early in the freeze.** The assistant generates an Ed25519 key on the
   steward's computer. The key folder has mode 0700 and the private key file mode 0600.
   The private key is encrypted with a passphrase stored apart from it, in the steward's
   encrypted store of project secrets; no interactive prompt and no system keychain are
   involved. An encrypted copy of the key file goes into the steward's backup of project
   secrets. The backup is tested once: a copy restored from it signs a test message, and
   that signature verifies against the published public key.
2. **Key record.** `governance/KEY-REGISTRY-<date>.md` with `governance/allowed_signers`:
   algorithm, public key, fingerprint, purpose (governance decisions only), date of first
   publication, the statement that the key authenticates nothing earlier, and the date of
   the backup test. The record is stamped with OpenTimestamps in the same week. The
   dead-man heartbeat keeps its own key and procedure: a heartbeat must show that the
   steward acts, which an automated signature with this key would not show.
3. **Decision.** On or after 2026-11-18, the decision is written in
   `governance/AMENDMENT-DECISION-<date>-invariant-1.md`: adopt, adopt with changes, or
   reject; the final texts; the switch record it relies on; the comments received and the
   answers.
4. **Approval.** The assistant shows the steward the file's path and SHA-256. The
   steward's approval names that hash. The assistant computes the hash again and signs
   only if it matches. Any later change to the file needs a new approval.
5. **Signature.** A detached SSH signature (namespace `evidaxis-governance`) is committed
   next to the file, with a short note stating the approved SHA-256 and the date of
   approval.
6. **Independent check.** A CI job verifies the signature with the standard OpenSSH tool
   and the committed `allowed_signers`, on GitHub's machines, separately from the signing
   computer: `ssh-keygen -Y verify -f governance/allowed_signers -I <signer identity>
   -n evidaxis-governance -s <file>.sig < <file>`. Anyone can repeat it.
7. **Stamp.** The decision file is stamped with OpenTimestamps and the stamp is committed.
8. **Texts.** The texts of section 4 and the changelog entry follow in one commit citing
   the decision. The next weekly manifest anchors the new hash of the constitution.

What the passphrase protects: a copy of the key file that travels without it, for example
a stray copy outside the key folder. It does not protect against software running as the
steward, which can read both, and it adds nothing to the encrypted backup, which holds
both under its own encryption. On a single computer it adds little beyond disk encryption
and file permissions; it is kept because it costs nothing. The protections that matter
are that the key stays off CI, remote machines and this repository, and that the key
record is public and timestamped, so any later misuse is visible.

A decision is not valid if it is signed before the earliest date, by another key, without
an approval that names its hash, or without a stamp. A material change to this proposal
restarts the freeze; an editorial correction does not.

## 9. Comments during the freeze

Write to hello@evidaxis.org with the subject "Invariant 1 proposal", or open a public
issue that names no person and no account. The decision lists every comment received and
its answer, without personal data.

## 10. Falsification

This formulation is wrong if, by 2026-12-31, any byte published after the switch contains
a personal account identifier, any personal account identifier is found kept between
runs, a value or link of a post-switch snapshot cannot be recomputed or interpreted from
public sources alone, or an erasure request cannot be completed within one month without
rewriting git history. Checked by the pre-publication checks, the archive-integrity
workflow running without secrets, a full scan before the next quarterly Zenodo version,
and the records of the erasure procedure.

## 11. Related items

- **Shadow layer (precondition of the switch).** `governance/SHADOW-LAYER-2026-08-03.md`
  keeps, in a private repository, the address (`full_name`) of every repository in the
  200 to 499 star band, personal accounts included. The observation step needs only an
  account-free node id, so a successor schema under its own dated act keeps numeric ids
  and node ids and nothing else; the act also decides what happens to the identity sets
  already kept. The same layer keeps weekly star observations "for a possible future
  private data product", a private series that the covenant of 2026-07-02 does not
  provide for. That question is separate and is not decided here.
- **Ids.** Systems admitted after the switch take `gh:<repository id>` as their natural
  key, so their ids are not derived from an address and survive renames. Ids of systems
  admitted before the switch stay as they are: they are permanent, and they remain
  derivable from the original address (section 2.5).
- **Invariant 6 wording.** `governance/ERRATUM-2026-09-14-byte-reproducible-claim-on-derived-surfaces.md`
  left the phrase "byte-reproducible from public inputs" open. This proposal does not
  change it.
- **Upstream text and rows.** Daily provenance files keep free-text repository
  descriptions, and `data/observations/` keeps raw rows from the deps.dev BigQuery
  tables, while `RIGHTS-BASIS.md` excludes description prose and upstream response bytes.
  This concerns rights, not persons, and needs its own record.

## 12. Revision 2026-10-19 (second opinion)

An independent review of the first version asked for changes on four points. Each is
taken up here.

1. **The invariant contradicted the erasure procedure.** The first text banned storing
   any name or email, while the procedure keeps correspondence for up to two years. The
   text now separates three kinds of data: the record, locators and correspondence. The
   review also held that a closed table needed to read published package series would
   breach invariants 3 and 6. The opaque package keys of the first version needed such a
   table; they are replaced by account-free pointers to the declaring manifest, which
   public sources resolve. That the conditions hold is now shown by a check that runs
   without any secret (section 5), not by a definition.
2. **Deleting from a restricted store is not reliable.** Rewriting the history of a
   private repository does not guarantee that every copy and server-side reference is
   gone. The first version needed the store for original addresses, census candidates,
   package names and former owners. Each need is now met without one: original addresses
   of earlier systems come from files committed before the switch; new systems take
   `gh:<repository id>` as their natural key; candidates and systems are resolved from
   public ids at run time; package names are read from the manifest that a public pointer
   names; former owners up to the switch come from the public history, and after the
   switch a former owner's login never enters public bytes. One gap remains: a login that
   no longer resolves on the platform, typed by hand into a document, is not recognized.
   The do-not-observe list, which holds numeric ids only, is kept separately and without
   versions.
3. **The signing procedure did not match how the steward works.** The steward's
   assistant performs the steps on the steward's computer, on an approval that names the
   file's hash. The procedure now names the file modes, the passphrase and what it really
   protects, a tested backup, and an independent check of the signature. It marks the key
   as new, authenticating nothing earlier. It separates the governance key from the
   dead-man heartbeat.
4. **Some promises outran their mechanisms.** The erasure stop now takes effect before the
   next run; deletion is promised for the copies Evidaxis controls, and the remaining
   copies are named; reproducing the past is separated from continuing collection; and
   fail-closed now rests on checks that run before every automated push, upload and
   deployment, with the post-push check stated as a second line.

This revision is material. It was published on the day of the original, so the freeze
runs from 2026-10-19 and the earliest decision date stays 2026-11-18. A later material
change restarts the freeze from its own publication.

*Positive-only note: this proposal concerns the project's own handling of identifiers.
No measurement, score, recognition or system identity is created, changed or withdrawn
by it.*
