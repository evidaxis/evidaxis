# Person-free guard at registry scale (2026-09-27)

> status: FIXED 2026-09-27, recorded before deployment of the 2026-09-26 snapshot.
> Relates to: CONSTITUTION.md invariant 1 (systems, not people); COLLECTION-CAPACITY-2026-09-26.md.

## What happened
The 2026-09-26 snapshot (5,914 systems) was collected and committed, but the site build failed
closed on the person-free guard. The guard compared every text with every personal GitHub owner
handle as a plain substring. With 2,319 personal owners in the registry, handles such as "f",
"av", "78" or "100" matched ordinary words and numbers in every card, so the build stopped
without finding a single published handle. The post-build check had the same design, and its
stale-path rule treated any "apple/" or "us/" as a moved repository's old owner.

## What changes (the invariant is unchanged; the matching becomes exact)
- A personal handle counts as published when it appears as a GitHub path or slug prefix
  ("handle/"), as an @mention, or as a standalone word when the handle is distinctive (4+
  characters, not only digits). Short or all-digit handles count only in an explicit GitHub
  context (github.com/handle/, repos/handle/). One module serves the card guard and the
  post-build check (`web/src/lib/personFree.mjs`).
- Moved repositories: the exact old path "owner/repository" is rejected; a former owner that is
  not an Organization today is matched in GitHub context only.
- Binary assets (fonts, images) are not scanned as text.
- 20 systems whose public name or repository name is itself a personal handle (repositories
  under a personal account named after the account, plus two names that contain the owner's
  handle) are published under a neutral name "System {entity_id}", with the repository label
  "repository not shown". Their measurements are published; the archive files are unchanged.
- Dated badges `/badge/{id}/{period}.svg` are now generated for every archived week, so an
  embedded dated badge does not turn into a 404 when the next snapshot arrives.

## Checks before deployment
Full build of 5,914 systems; post-build check PASS; card consistency 0 discrepancies; the 268
originally frozen template-A files contain no projected strings.
