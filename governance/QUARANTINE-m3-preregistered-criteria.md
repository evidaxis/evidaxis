# Pre-registered A/B promotion criteria — candidate axis m3 (deps.dev dependents momentum)

> status: FIXED 2026-07-02, BEFORE data accumulation began; post-hoc edits forbidden.
> This file is the in-repo record of the criteria referenced by
> `DRAFT-m3-quarantine-adjudication.md` and `ADJUDICATION-2026-07-11.md` §1.
> Until 2026-07-16 the fixed text lived only in the keeper's internal planning layer;
> per the provenance-quarantine rule ("promotion criteria written and committed BEFORE
> looking at the data") it is hereby committed verbatim (dated transfer, not an edit).
> The Russian original below is the authoritative fixed text; the English rendering is
> a faithful translation added at transfer time.

## Criteria (English rendering)

A promotion proposal may be brought to the keeper ONLY if, after **>= 28 days of
accumulation** AND **>= 2 consecutive weekly shadow runs**, ALL of the following hold
(shadow-floor amendment, ADJUDICATION-2026-07-11 §6b: >= 28 calendar days AND >= 1 full
methodological period, whichever is greater):

1. **Coverage:** gate-capable entities (>= 2 axes present) grows from 9/103 to **>= 30**.
2. **Independence:** pooled within-cohort **|pearson(z3, z1)| < 0.5** over cohorts with
   n >= 5 (additionally record r(z3, z2) where axis-2 exists — informative).
3. **Stability:** between consecutive weekly shadow runs, the axis-3 rising-vote
   flip-rate is **< 30%** of voting entities.
4. **Non-degeneracy:** the axis-3 rising-vote share in every voting cohort lies within
   **(0%, 40%)** — neither "everyone" nor "no one".
5. **Honesty floors:** a vote exists only at >= 14 daily points AND latest dependents
   >= 5 (DEPS_FLOOR, the activity-floor analog) — built into the shadow script;
   a violation fails the criterion.
6. **No look-ahead (financial-PIT donor):** a vote at week t uses only observations
   <= t — structurally guaranteed (the script reads only accumulated observations).

Axis definition under test (v1, unchanged since fixing): momentum of the deps.dev
dependents count — least-squares slope of log(1 + dependents) over daily capture
points, within-cohort robust-z (median / 1.4826*MAD, clamp +/-3), residualized on
log(1 + latest dependents) as the size proxy — mirroring m2 semantics.

Mandatory pre-promotion gates (checklist, from the same fixed record):
- [x] deps.dev licence (CC-BY 4.0) vs invariant I4: position recorded in RIGHTS-BASIS.md
      (score = CC0, raw = hash + pointer). *(closed 2026-07-16, commit 108c45e)*
- [ ] BigQuery history bridge — shadow-backfill namespace only, `reconstructable:true`.
- [ ] Cross-correlation monitor (CP-1 C3) computed on the same shadow run — published
      together with m3, not earlier.

## Оригинал (зафиксирован 2026-07-02; дословно, с одной редакцией: имя основателя
## заменено на роль «хранителю» по инварианту person-free — пороги не тронуты)

Промоушен-предложение выносится хранителю ТОЛЬКО если после ≥28 дней накопления И ≥2
последовательных еженедельных shadow-прогонов выполняются ВСЕ:

1. **Coverage:** gate-capable (≥2 осей present) растёт с 9/103 до **≥30**.
2. **Независимость:** pooled within-cohort **|pearson(z3, z1)| < 0.5** по когортам с
   n≥5 (плюс записать r(z3,z2) где ось-2 есть — информативно).
3. **Стабильность:** между последовательными еженедельными прогонами flip-rate
   rising-голоса оси-3 **< 30%** голосующих сущностей.
4. **Недегенеративность:** доля rising-голосов оси-3 в каждой голосующей когорте в
   интервале **(0%, 40%)** — не «все» и не «никто».
5. **Флоры честности:** голос только при ≥14 точках И latest dependents ≥ 5
   (DEPS_FLOOR, аналог activity-floor) — встроено в скрипт, нарушение = провал критерия.
6. **No look-ahead (донор financial-PIT):** голос на неделе t использует только
   наблюдения ≤ t — структурно гарантировано (скрипт читает только накопленные
   observations).
