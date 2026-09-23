# Growth policy amendment - content-based indexability for template B cards (2026-09-23)

> status: FIXED 2026-09-23. Amends one clause of `REGISTRY-GROWTH-POLICY-2026-07-21.md`,
> which is retained unchanged as the record of what was decided on 21 July.

## Clause amended

> **Cards index after 4 weekly observations**; before that, admitted systems are
> visible in a machine-readable pending manifest (membership is complete and auditable
> from day one; thin-content GEO risk avoided).

## Why

The clause protects against publishing cards that show nothing: the template of 21
July, before four observations, prints measurement states ("Gate: not computable",
"insufficient", "n/a") instead of values. The stated risk is thin content, not the
age of a page. No published search-engine rule sets a waiting period; Google's spam
policy on scaled content targets pages made primarily to manipulate rankings without
helping users, and says neither automation nor page count proves that
(developers.google.com/search/docs/essentials/spam-policies#scaled-content).

Template B shows measured values of the system from the first snapshot: the 52-week
commit series arrives complete with the first capture, the star count is recorded,
citations and dependents are shown as numbers when measured.

## What replaces it

A card is indexable when its answer paragraph carries at least one measured value of
this system with a niche comparator, and the page shows at least two measured values
of this system, each with source and date. `n/a`, "insufficient", "not computable"
and "no reading" do not count as values. The same function drives the robots meta
tag and sitemap membership, and `check-dist` asserts that noindex and sitemap
absence coincide.

Template A keeps its current rule. Before four observations an A card shows states
instead of values and does not meet the criterion, so the rule and the criterion
coincide for A by construction and A output is unchanged.

The sitemap is published whole, without waves.

## Rollback signal

A repeated defect in a stratified sample of at least 30 B cards (an empty card, or
another system's numbers) returns noindex to the affected cohort until fixed. Absence
of impressions, or "Crawled, currently not indexed", does not by itself justify a
rollback.
