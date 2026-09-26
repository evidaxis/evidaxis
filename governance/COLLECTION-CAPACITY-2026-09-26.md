# Collection capacity at registry scale (2026-09-26)

> status: FIXED 2026-09-26, recorded before the corrected weekly run.
> Relates to: GROWTH-POLICY-AMENDMENT-2026-09-20.md (rule 1: capacity measured inside the
> platform's own limits), FOUNDATION-RETROFIT-CARDS-PREREG-2026-09-23.md (new cards).

## What happened
The scheduled weekly run of 2026-09-26 (Actions run 36239155695) stopped after 1 h 20 min on
GitHub HTTP 403: the job used the built-in `GITHUB_TOKEN` (about 1,000 REST requests per hour
for the repository) and the fetch layer aborted the whole collection on the first 403. No
snapshot was written; the site kept serving the 2026-09-19 snapshot. The capacity dry run of
2026-09-20 had measured a personal token (5,000 per hour) on a local machine, so rule 1 of the
amendment ("inside the platform's own limits") was not actually met for CI.

## What changes (fetch layer only; `etl/collect.py` stays byte-frozen, scoring unchanged)
- A GitHub App (`evidaxis-collector`, organisation-owned, own rate budget) authenticates
  collection; installation tokens are refreshed before their 1-hour expiry.
- Rate limits are waited out (reset time or Retry-After) and the same request is retried,
  instead of aborting.
- Repository metadata the collector reads (stars, creation date) and owner classification come
  from GraphQL, 100 repositories per query, with REST for misses; values are the same GitHub
  fields.
- `/stats/commit_activity`: a warm pass triggers GitHub's computation once per repository and
  keeps every complete answer; the capture pass reuses them and retries the rest.
- The snapshot date is computed once per run (or given); `captured_at` stays the real time.
- The daily collector uses the same path.

## Registry
Two queued systems whose repositories are deleted on GitHub (HTTP 404 on 2026-09-26) are not
collected: `aitytech/agentkits-marketing`, `Saganaki22/ComfyUI-OmniVoice-TTS`. They never had
cards. Collection covers 5,937 systems.

## Expected load (from the code, before the run)
About 60 GraphQL queries and 8,500 to 13,500 REST requests, 2.5 to 3.5 hours on the App budget.
A dry run at full size precedes the committing run, as rule 1 requires; both carry the date
2026-09-26.
