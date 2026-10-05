# Project accounts: 13 of the 21 neutral-name systems are published under their names (2026-10-05)

> status: DECIDED 2026-10-05; takes effect when the loader change ships (etl/project_accounts.json).
> Relates to: CONSTITUTION.md invariant 1; PERSON-FREE-AT-SCALE-2026-09-27.md and its addendum.

## Question
21 systems live in a repository under a GitHub account of type User whose handle equals or is
contained in the system's name. Since 2026-09-26 they are published as "System {entity_id}".
For each: is the handle a project's identity or a natural person's account?

## Rule (fail-closed)
A User account counts as a project account only if all hold: the display name is empty or the
project/company name; bio, blog and company point to the project or an organisation; the
account hosts only that project's repositories (plus forks it needs); public sources present
the project as a project or team. Any personal name, personal homepage or a portfolio of
unrelated personal projects makes it a person. Mixed or missing evidence keeps the mask.

## Decision
Project accounts (published like an Organization repository; GitHub `owner_type` stays User in
`etl/owner_types.json`):
aingdesk, alfworld, cliport, dreamgaussian, helicalinsight, jax-md, Jittor, joeynmt, LycheeMem,
openakita, RecursiveMAS, sentrux, voxelmorph.

Stay masked, 8 systems (handles are not published here): person — e_33CWR7PEWV8,
e_DTTS569XR58, e_Z5TE67Z8W1X, e_36TP847274S, e_5DH0W0KKMD6 (a personal display name, or a
portfolio of unrelated personal projects); unclear — e_RV88MF53RX3 (the profile links a
personal social account), e_XTWX3FQRKCG (no owner named, hosts unrelated forks),
e_CWPNYQ12XS1 (the package author is a named individual).

Evidence per account (sources opened 2026-10-05): `etl/project_accounts.json`.

## Review
A project account that later shows a personal name, or starts hosting unrelated personal
repositories, returns to the mask in the next snapshot; the decision is re-checked at each
quarterly deposit.
