# Pre-registration addendum - readability thresholds (2026-09-23)

> status: FIXED 2026-09-23, after template B went live (18:48 UTC) and before any
> outcome data for the comparison has been read. Adds to
> `FOUNDATION-RETROFIT-CARDS-PREREG-2026-09-23.md`; nothing in it is changed.

The pre-registration said that without power the verdict is "no answer", but did not
state when power is reached. The Foundation methodology (engine B, section 5) sets the
threshold used across the portfolio; it applies here unchanged:

- **Readable** only when each arm has at least 100 sessions landing on cards from
  organic search AND at least 30 completed tasks in arm B (download, citation copy,
  follow, error report). Below either threshold the reading is "insufficient power",
  which is the expected outcome at the current traffic and is not a failure.
- **Practical threshold** for the impressions outcome stays as registered (1.3x on the
  live cards). An effect is claimed as "at least 1.3x" only when the lower bound of
  its interval is at least 1.3; a point estimate above 1.3 with an interval that
  includes 1.0 is reported as "direction, not established".
- **Search Console export:** value and observation status are stored separately; a
  cell shown as "~" or "-" is "not measured", never zero, and never triggers a
  conclusion or a prune.
- **T+90** reading is added to the calendar: around 2026-12-23.

Why filed now: the omission was found by an internal audit of the release against the
Foundation checklist on the evening of 2026-09-23. No Search Console, GA4 or PostHog
data for the comparison window has been opened.
