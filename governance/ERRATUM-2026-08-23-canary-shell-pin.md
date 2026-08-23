# Erratum — canary control-shell pin broke on ordinary weekly data motion (2026-08-23)

**Class:** correctness defect in a CI guard (freeze-exempt per
METHODOLOGY-FREEZE-2026-08-20, "correctness defects and data errors — fixed
immediately via dated errata"). No methodology, threshold, axis, admission,
or displayed string changes.

**What happened.** The matched-pair canary (introduced 2026-08-20) pins the
"control shell" of all 24 control entity pages to a byte-exact SHA-256 of the
pre-canary render. The pinned regions include the receipt's snapshot id and
period, the nav snapshot link, and the claim-URN date (cite-as and citation
footer) — tokens the weekly snapshot legitimately rewrites on control and
treatment alike. The first weekly snapshot after the pin (2026-08-22) changed
those tokens, the guard reported all 24 controls as mutated, `web-ci` failed
closed, and publication stalled: prod served the 2026-08-15 snapshot while the
archive held 2026-08-22 (>31 h, hourly freshness alerts).

**Diagnosis, verified live.** A rebuild of the last green tree (`7d68dd72`)
reproduces the stored baseline hashes exactly (24/24), and after masking the
weekly tokens (snapshot id, `YYYY-MM-DD` dates, `YYYY-wNN` periods) its control
shells are byte-identical to the current tree's (24/24). The entire drift is
weekly data motion; no control page received any other change.

**Fix.** `check-dist.mjs` now masks the weekly tokens before hashing; every
remaining shell byte stays pinned, methodology version included, so a
methodology bump still demands a conscious baseline regeneration. The baseline
was regenerated from the pre-canary-proven render (schema
`canary_control_shell_2`), not from the current tree. Guard re-verified after
the fix: a one-byte mutation of a stable shell region fails the build, and a
treatment marker (`/feed.atom`) leaking onto a control fails the build.

**Isolation semantics unchanged.** Controls keep the baseline title, receive no
treatment-only blocks, citation UI, feed links, or analytics tags; the
treatment/control assignment and all measurement records are untouched.
