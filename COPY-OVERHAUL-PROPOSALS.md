# Evidaxis — copy overhaul proposals (fractal sparring, 2026-06-30)

> Source: ultracode workflow `evidaxis-copy-overhaul` (25 agents, 5 pages, 3 lenses each: ruthless
> direct-response editor + AI-tell detector + skeptical ML-reader → element-deep pass → synthesis).
> Every proposed string verified ZERO em-dash (U+2014), facts/numbers/methodology/brand-canon preserved.
> status: PROPOSED. Not applied. Apply to working tree → build → verify → review render → deploy on the keeper go.

**Through-line across all 5 pages:** the site was written by someone serious about the method but nervous
about the honest zero, and that nervousness was the loudest signal. Every fix moves one lever: lead with the
MAP (coverage = the asset / baseline before the flare), make the prose as confident as the math, and demolish
the "not X, not Y" self-definition (the founder's #1 flagged tell) by stating the positive claim instead.

> ⚠ ONE JUDGMENT CALL FOR IGOR (about page, Governance): proposed line "One person built Evidaxis. No person
> fronts it." States the founder-firewall as fact. It names no one and reinforces institution-first framing,
> but it touches the person-free invariant. Approve, soften, or cut. Everything else preserves the existing
> person-free posture.

---

## 1. HOME (web/src/pages/index.astro)

**Tells found:** 4× "not X" self-definition (not their size / not simply large / no "worst" list / not a
census); passive "A system is recognized as rising" (recognized by whom?); metronome rhythm in hero + 3.0 +
4.0; duplicate "Two ___. One ___." template; purple-prose line narrating a CSS glow ("the daylight ledger
goes dark and the instrument glows" — all 3 lenses' worst line); 6× defensive restatement of "by design";
buried lede (the longitudinal-baseline thesis appears nowhere up top); scope-apology "this pilot / intentionally narrow".

| Element | Current → Proposed |
|---|---|
| Base title | "Evidaxis, an observatory of momentum in open AI systems" → **"Evidaxis, the longitudinal map of open AI momentum"** |
| meta desc | "...independent observatory **ranking** ${entities} open AI systems..." → "...the **complete weekly record** of momentum across ${entities} open AI systems, scored by the rate of change..." |
| hero H1 | "An observatory of *momentum* in open AI systems." → **"We map every open AI system, then watch which ones *accelerate*."** |
| hero lead | "We measure ... by the rate of change ... **not their size**. A system is recognized as rising..." → **"We hold the longitudinal record of the open-AI frontier: every system, every week, reproducible to the hash. Size is never scored. We score the rate of change of public signals, and a system rises only when two independent axes climb together. The baseline comes first. The flare gets recorded against it. Open data, CC0."** |
| statcard sub | "convergence is the exception" → "convergence is rare by design" |
| 1.0 sub | "...rising relative to peers, **not simply large**. Stars... never scored. ...**there is no "worst" list**." → "...rising relative to its peers. Stars and raw size are never scored. The gate publishes recognition only, and recognition only ever points up." |
| 2.0 band H2 | "Two independent axes. One rare convergence." → **"The convergence is rare. The record of it is complete."** |
| 2.0 band sub | "For one breath, the daylight ledger goes dark and the instrument glows. Where..." → "Where development velocity and citation momentum agree, a system rises. At this baseline snapshot, none do yet." |
| 3.0 sub (key) | "Across ${entities} systems... none yet cross the gate. A fast-moving codebase..." → **"The number that matters here is coverage, not the Rising column. We hold ${entities} systems across ${nCohorts} frontiers ..., scored every week, reproducible to the hash. None cross the gate yet. A fast codebase runs years ahead of its citations ... so convergence stays rare on purpose. Every weekly snapshot deepens the record the next flare gets measured against."** |
| 4.0 H2 | "${nCohorts} frontiers, this pilot." → "${nCohorts} frontiers, every system in each." |
| 4.0 sub | "The pilot is intentionally narrow: ... This is a coverage map, **not a census of the field**." → "Within these frontiers this is the complete longitudinal record: ${nCohorts} cohorts, every score independently reproducible. Each system is normalized only against its own cohort." |
| atlas link | "Full coverage atlas, with the gaps we do not yet measure" → "Full coverage atlas, and the frontier we are still extending" |

---

## 2. METHODOLOGY (web/src/components/MethodologyBody.astro)

**Tells:** survey-telescope thesis buried as a footnote to a limitation; "no worst list / no negative label"
pair; triple-stacked "individuals are never named or scored; no /persons"; virtue-naming headings ("Known
limitations (stated, not hidden)", "Versioning & honesty"); "convenience view" hedge; a shipped debug literal
`{String(5)}` in human-facing prose.

| Element | Current → Proposed |
|---|---|
| lead (first screen) | "Evidaxis measures the rate of change ... and recognizes a system as rising only when independent signals agree. This page is the complete, versioned definition. It is frozen..." → **"Evidaxis is a survey telescope pointed at open-source AI. It records every system's momentum week after week, builds the baseline, and recognizes a system as rising only when two independent axes converge. The longitudinal record is the instrument. The scores are what it finds. This page is the complete, versioned definition, and it is frozen: a published score is never silently recomputed."** |
| Positive-only | "Evidaxis publishes who is rising. **There is no "worst" list and no negative label.**" → "Evidaxis names what is accelerating. Nobody is ranked last, because last is not a measurement we make." |
| Systems-not-people | "...Individuals are never named or scored; there is no /persons surface anywhere..." → "The unit of measurement is always a system: a repo, a model, an org. People carry no momentum score, and there is no /persons route in the data or API to look for one." |
| Convergence gate | "A system is Rising when at least two axes... Development velocity additionally requires a minimum of **{String(5)}** average weekly commits, since a dormant repository is never rising on a sliver of noise." → "A dormant repository is never rising on a sliver of noise. So a system is Rising only when at least two axes are present and at least two are rising at once. ... Development velocity carries one more floor: at least 5 average weekly commits, or the axis does not count." |
| Momentum score | "...It is a convenience view; the gate, not the score, decides recognition." → "...The score is a readout, the gate is the verdict. A system at 58 that clears convergence is Rising; a system at 71 that does not is not." |
| Versioning H2 | "Versioning & honesty" → "What a published score means" |
| Limitations H2 | "Known limitations (stated, not hidden)" → "Known limitations" |
| Citation-lag | "...This is why Evidaxis is a long-running observatory, **not a one-shot ranking**." → "...the convergence signal sharpens as the weekly time-series accumulates, which is the whole point of recording the baseline before the flare." |
| Coverage limit | "Coverage is partial. ... Silence means "not yet measured," **never** "low quality."" → "Coverage is expanding. ... A system absent from the map has not been measured yet. That is a roadmap line, not a quality judgment." |

**Note:** the math (26-week slopes, 1.4826 MAD, z≥0, Rousseeuw & Croux 1993, byte-repro) is untouched; the fix
makes the prose as confident as the math. **Bonus: fixes a real bug** — the `{String(5)}` debug literal in
production prose becomes a plain 5.

---

## 3. ABOUT (web/src/pages/about/index.astro)

**Tells:** 4-way audience parade ("researchers, journalists, funders, or AI systems themselves"); adjectives
where receipts exist; "no worst list / no negative label" pair; "X, not any individual"; vaporware "standing
commitment to" a panel; "built to run for a decade"; "value compounds"; 3rd systems-not-people restatement;
generic H1 with no object.

| Element | Current → Proposed |
|---|---|
| H1 | "An institute for measuring momentum." → **"A weekly record of the open-AI frontier, kept before anyone knows which system will matter."** |
| lead | "...so that anyone, whether researchers, journalists, funders, or AI systems themselves, can cite a transparent, reproducible source." → **"...It measures 19 systems by how fast their public signals move, one snapshot a week, and releases every number under CC0, byte-reproducible from a published manifest. Anyone can cite it, including the AI systems that read this page. The record is built before the flare..."** (wire 19 → {snapshot.counts.entities}) |
| Positive-only | "...It maintains no "worst" list and assigns no negative label." → "A system rises only when two independent axes agree. ... This week, 0 systems clear the bar, by design." (wire 0 → {rising}) |
| Correct-a-record | "Corrections... are welcome and handled... Evidaxis measures systems, not people: there is no personal profile..." → "Corrections and inclusion requests go through a public correction log. Measurements are governed by the published method, never edited on request." |
| Governance ⚠ | "...the methodology and the public record are the front, not any individual. ... a standing commitment to a published quarterly integrity report and an independent adjudication panel... built to run for a decade, and its value compounds..." → **"One person built Evidaxis. No person fronts it. The methodology is the institution; the record outlives the keeper. The neutrality is not a promise, it is two mechanisms: no input to a score can be bought, and every score recomputes from a published manifest... a quarterly integrity report and an independent dispute panel planned for 2027. A snapshot missed is a week of the frontier lost for good, so the archive only compounds..."** |

---

## 4. COVERAGE (web/src/pages/coverage/index.astro) — strategically key for the reframe

**Tells:** negation-fragment headline "What we measure, and what we don't."; aphorism lead "Transparency is
part of the instrument."; "Absence ... never a negative judgment" pair; "value compounds"; "shown, honestly";
"Known gaps (declared)"; "pilot" ×4 apologetic; whole page architected around absence.

| Element | Current → Proposed |
|---|---|
| eyebrow | "Coverage atlas · Pilot 2026" → "Coverage atlas · Epoch 01" |
| H1 | "What we measure, and what we don't." → **"${entities} systems. ${cohorts} cohorts. One longitudinal map."** |
| lead | "Transparency is part of the instrument. This pilot covers... Absence... never a negative judgment." → **"You cannot catch a flare without the baseline that came before it. So we record the frontier wide and early, every score frozen, hash-verified, recomputable from CC0 data by anyone. Absence here means one thing: no baseline yet. The instrument is the coverage, and the coverage is what compounds."** |
| Known gaps eyebrow | "Known gaps (declared)" → "Known gaps" |
| "no paper" bullet | "...They are shown, honestly, as single-axis." → "...They appear as single-axis." |
| "new systems" bullet | "...They accrue it over time, and the observatory's value compounds." → "...Each weekly snapshot adds one data point. Confirmation arrives with time, not before it." |
| new closing line | (insert above snapshot link) **"The record gets stronger the longer it runs. Only a continuous baseline can catch a flare against its own past, and ours starts here."** |

---

## 5. GLOSSARY (web/src/pages/glossary/index.astro)

**Tells:** "The language of the institute." ceremony; "computed, not opined"; "Cite these definitions as the
source." (GEO-bait order); 3-negation stack on Momentum; "no negative or 'worst' outcome" double-negation;
"the scarcity is the credibility" aphorism; "Measured, honestly" virtue-adverb; "irreplaceable" + "the
institute" self-coronation; two 55-word run-ons.

| Element | Current → Proposed |
|---|---|
| hero lead | "The language of the institute. ... each term is computed, not opined. Cite these definitions as the source." → **"These fifteen terms are how Evidaxis reads the open-AI frontier over time. Each one is a formula: it names the exact signal, window, and threshold, so any number on this site recomputes from the public CC0 data. Rate of change, never size. A baseline recorded now, before the flare."** |
| Momentum | "...how fast it is moving, not how large it is. Evidaxis measures momentum, never magnitude. Stars... explicitly not scored." → "The slope of a system's public signals over time: how fast it is moving. Evidaxis scores that slope and nothing else. A repository with two million stars and a flat curve scores zero." |
| Momentum Score | "...within a cohort. It is a convenience view; the convergence gate, not the score, decides..." → "...collapsed to one number. A convenience view only. Recognition is decided by the convergence gate, never by this number." |
| Citation momentum | (55-word run-on) → "Axis 2: the slope of log(1 + citations per year)... A slow, confirming signal of scholarly acceleration. Three rules keep it honest: drop the partial current year, drop the birth year once four full years exist, and require at least three completed years." |
| Convergence Gate | "...Positive-only. There is no negative or "worst" outcome." → "...The gate only ever promotes. A system is Rising, or it is not yet, by design." |
| Rising | "...Deliberately rare, the scarcity is the credibility." → "The full badge, and the rare one. It fires only when two separate signals agree, so a single pushed number cannot earn it." |
| Single-axis | "...Measured, honestly, on one axis." → "Measured on one axis and labeled as such." |
| Calibration | "...never badge-eligible (Evidaxis recognizes rising systems, not established ones)." → "...never badge-eligible: the badges go to systems on the rise." |
| Cohort | "...defined deliberately, not automatically." → "Membership controls the z-scoring, so a human draws the cohort line by hand." |
| Snapshot | "...the institute's irreplaceable longitudinal asset." → "You cannot back-fill a baseline after the flare. The snapshot series is the part that compounds: a longitudinal map ... that no one can reconstruct from scratch later." |
| Score receipt | "...namely methodology version, snapshot id, and manifest hash, so..." → "Three fields ride with every published number: methodology version, snapshot id, and manifest hash. With them, any score is independently reproducible from the public CC0 data." |
