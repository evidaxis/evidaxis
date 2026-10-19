# Erasure requests: how Evidaxis removes a person's identifiers (2026-10-19)

> status: IN FORCE since its changelog entry in `CONSTITUTION.md` (2026-10-19). This is a
> strengthening covenant: it adds obligations and loosens none, so under the Amendment
> rule it needs only a public changelog entry. Revised the same day after an independent
> review (section 9); the revision keeps every obligation and sharpens several.
> Relates to: invariant 1; the anti-roadmap clause "only legal or privacy removal via a
> tombstone that preserves the fact-of-existence"; `RIGHTS-BASIS.md` ("On a verified
> erasure request, publish an erratum/redaction record, never a retroactive rewrite");
> `governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`.

## 1. Who can ask, and about what

Any natural person whose identifiers appear in anything Evidaxis publishes or keeps can
ask for their removal, alone or through someone acting for them. Identifiers are the
login of their account and any value that contains it: a repository address
`<account>/<repository>`, a GitHub URL or Pages host of the account, or a package name
in the account's namespace. A person who maintains a system alone can also ask Evidaxis
to stop observing that system.

The same applies to an organization account that stands for a single natural person.

Corrections of measurements are not handled here. They follow the published method.

## 2. How to ask

Write to **hello@evidaxis.org** with the subject "Privacy removal". Give the repository
address, the Evidaxis id (`e_...`) or the link to the system's page, and one way to show
that the account is yours (section 3). No identity document is needed.

Please do not open a public issue: the issue itself would publish the identifier. If one
is opened, the steward copies it to email, deletes the issue and answers by email.

## 3. Checking the request

Evidaxis checks control of the account, not identity. Any one of these is enough:

- a short code that Evidaxis sends within 2 days, placed for a day in a public gist, the
  profile, or a commit of the account;
- an email from an address that the account shows publicly.

If the account no longer exists, a plausible request is accepted on the address alone,
because removal only takes data away. A request about another person's account is
declined.

## 4. What Evidaxis does, and when

Evidaxis acknowledges a request within **7 days** and completes it within **one month**
of receiving it. If more time is truly needed, the requester is told within that month
why, and the work ends within two further months. Each step below is part of that month.

1. **Stop, before the next run.** Within one day after control is shown, the steward adds
   the repository's numeric id to the do-not-observe list. Every daily and weekly run
   reads that list before any request about the repository, so no run that starts after
   the entry collects it. The list is kept, without versions, as a repository secret,
   with an encrypted backup held by the steward. It holds numeric ids and nothing else,
   and it is the only data the collection systems keep about the request. Unless the
   requester asked only to remove identifiers, the retirement is declared in the run's
   records with the reason class "privacy", never with the person's details.
2. **Nothing else to clean in the collection systems.** Collectors keep no personal
   account identifier between runs (`governance/AMENDMENT-PROPOSAL-2026-10-19-invariant-1.md`,
   section 4.3). Until the person-free switch, such identifiers live in the public files,
   which step 3 covers.
3. **Current tree of the public repository.** By a normal commit, every occurrence of the
   person's identifiers in tracked files is replaced with a tombstone: in text,
   `[redacted: privacy removal, see governance/REDACTION-<date>-<n>.md]`; inside a JSON
   string, `"redacted:privacy:<date>-<n>"`. This covers files rebuilt each week (registry,
   seeds, system records, caches) and dated archive files (snapshots, observations,
   manifests) alike. Copies of deposit files tracked in the repository are removed from
   the current tree or rebuilt with the tombstone. The system's Evidaxis id and its
   measurements stay: they preserve the fact of existence that the constitution
   requires. If the requester also asks to remove the measurements, the steward decides
   within the same month and records the reason.
4. **Integrity.** For every dated file it changes, the redaction record lists the path,
   the SHA-256 of the original bytes and a commit that still holds them. Integrity checks
   verify the original from that commit, and accept the current file only if it differs
   from the original by the listed substitutions.
5. **History.** Earlier commits keep the identifier. Evidaxis does not rewrite git history,
   and its main branch refuses force-pushes, administrators included. If a court or the
   regulator orders removal from history, the steward follows the order and records it,
   without the identifier.
6. **Mirrors, archives and copies.** Evidaxis removes the identifier from the copies it
   controls and names the copies it does not.
   - *GitLab mirror:* receives the tombstone commit with the next push; its history matches
     the main repository's.
   - *Software Heritage* archives the full history. Its content policy
     (softwareheritage.org/legal/content-policy, read 2026-10-19) says it cannot alter or
     delete version-control history, and it takes removal requests through its takedown
     form or by post to Inria. Evidaxis tells the requester this and sends a written
     confirmation of what it removed, which that request asks for.
   - *Hugging Face* holds publication projections only. The steward checks every dated
     folder and every revision of the dataset. If an identifier is found, the steward
     re-uploads the person-free file for that date and, if older revisions still hold it,
     squashes the dataset's history. The dataset is a mirror; the git archive keeps its
     own history. Hugging Face may keep unreachable revisions on its own systems; the
     redaction record states what the dataset's public history shows after the squash.
   - *Zenodo.* Versions published from 2026-10-05 are strict person-free projections. The
     genesis version of 2026-06-27 holds 1 address under a personal account and the
     version of 2026-07-10 holds 10. If a request concerns one of them, the steward first
     adds the SHA-256 and MD5 checksums of that version's files to its public
     description, because a record with restricted files lists none. Then the steward
     sets that version's files to restricted, with a public note that points to the
     redaction record. Zenodo keeps the files, and the DOI and metadata stay public.
     Evidaxis does not ask Zenodo to delete a version.
   - *Internet Archive:* for the genesis seed only, Evidaxis requested Wayback captures of
     source pages. The requester can ask the Internet Archive to exclude their pages;
     Evidaxis requests no new captures.
   - *Forks and clones made by others* are outside Evidaxis's control.
7. **CI.** Logs of workflow runs that show the identifier are deleted through the GitHub
   API, and their artifacts at once. Logs and artifacts are operational records, not the
   archive. GitHub's own backups are outside Evidaxis's control.
8. **Website.** The site is rebuilt from the tombstoned tree. Where a search engine still
   shows a removed page, the steward asks it to refresh the page with its public removal
   tool.
9. **Answer.** The requester is told what was removed and where copies remain: earlier
   commits, Software Heritage, Zenodo's restricted copy where one applies, forks and
   clones made by others, and the backups of the services Evidaxis uses. They are told how
   to contact Software Heritage. Before step 3 they are told that the tombstone and the
   system's id stay visible, and that anyone who already knows the address can compute
   the id of a system admitted before the person-free switch.

## 5. Public record

Each completed request produces `governance/REDACTION-<date>-<n>.md`, as in
`governance/REDACTION-2026-10-18-steward-identifiers.md`. It states the date, the class of
value removed, the files changed with the SHA-256 of their original bytes, and what was
not changed (history, measurements, ids). It never contains the identifier or any detail
of the requester.

## 6. Correspondence

Requests and answers stay in the project mailbox, outside the record. They are never
copied into the repository or into any data system. A monthly check deletes every thread
that would pass two years after the request was closed before the next check, so no
thread stays longer than two years, unless a dispute about it is open. The mail
provider's own backups expire on the provider's schedule.

## 7. What this procedure does not promise

It does not erase earlier git commits, copies held by others, backups held by the
services Evidaxis uses, or the fact that a system existed. It does not change any other
system's measurements or recognition.

## 8. Why this takes effect now

Every step either uses a permission the constitution already grants (privacy removal by
tombstone, a disclosed retirement) or adds an obligation (a deadline, a record, contact
with mirrors). Nothing in it relaxes a commitment. Under the Amendment rule, such a
strengthening covenant needs only a public changelog entry. Its entry, published on
2026-10-19:

> - **2026-10-19: additive covenant (erasure requests).** Added a procedure for privacy
>   removal requests (`governance/ERASURE-REQUESTS-2026-10-19.md`): Evidaxis answers within
>   one month, stops observing a system at its sole maintainer's request, and replaces the
>   person's identifiers by tombstones in the current tree and on every surface it
>   controls, without rewriting git history. This is a pure self-restriction under the
>   anti-roadmap's privacy-removal clause; no invariant changes.

## 9. Revision 2026-10-19

An independent review of the first version found that some promises outran their
mechanisms. The revision:

- moves the stop before the next run: the do-not-observe entry is made within one day of
  verification, and every run reads the list before any request about the repository;
- keeps the do-not-observe list as a secret without versions, with numeric ids only;
- drops the step for a locator store, because no such store will exist;
- promises deletion for the copies Evidaxis controls and names the copies it does not
  (Hugging Face's internal revisions, GitHub's backups, the mail provider's backups);
- bounds the deletion of correspondence by a monthly check that keeps no thread longer
  than two years.

Every obligation of the first version remains or becomes stricter, so the changelog entry
above stays accurate.

*Positive-only note: this procedure concerns personal identifiers. It creates, changes
or withdraws no measurement or recognition of any system other than one retired at its
maintainer's request.*
