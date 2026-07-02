# ERRATUM — SHA256SUMS correction (2026-07-02)

**What was wrong.** The `SHA256SUMS` file published with this snapshot did not
match the snapshot's actual bytes: all three entries failed `shasum -c`.

**Cause.** Pipeline step ordering. The frozen collector (`etl/collect.py`)
writes `SHA256SUMS` as part of its run, but the weekly pipeline then applies
two sanctioned, deterministic post-steps — `etl/reclass_pre_spine.py`
(PROVISIONAL re-class) and `collectors/taxonomy_v2.py` (taxonomy v2 remap) —
which mutate the bundle files (`snapshot.json`, `manifest.json`,
`provenance.json`) after the sums were written. No step re-hashed the bundle
before publication.

**What this erratum changes.** ONLY the `SHA256SUMS` witness file. The data
files (`snapshot.json`, `manifest.json`, `provenance.json`) are byte-identical
to the final published state of 2026-07-01 (the bundle was amended in place
during publication day; every earlier same-day state remains in git history);
no number, classification, or timestamp was altered. The pre-correction `SHA256SUMS` remains available in git history.

| file | recorded (wrong) | corrected (actual bytes) |
|---|---|---|
| `snapshot.json` | `d60b69fc8138e88e0563e1e0f795fde0286aaeb9440f321a80b238ca9dd22aa0` | `66cfff9085fa08ab0b520454fb2b38e82a665f938e7f89fe561827c71949e123` |
| `manifest.json` | `9c7612eb05acf7d808e3ccae33fcdac3a22d14092569834b3fdecd7e459d8eab` | `82b7004a46b9f5fa849fe19a82f1a57869990e3f69702e949efee17c5e6da891` |
| `provenance.json` | `f896859a3025e80efea32b412415f7ba2648dcafed7dc9528651f2bd4ac06df1` | `bc8a986557a40c4816a56754c9b4525952a13985f8ed0f6b80d866d17fd8203e` |

**Fix forward.** `collectors/refresh_sums.py` is now the mandatory FINAL
content step of the weekly pipeline (`.github/workflows/weekly-snapshot.yml`):
nothing may mutate the snapshot after it runs. A standing archive-integrity CI
job additionally verifies every published snapshot's checksums against actual
bytes on every push and nightly. The archive Merkle root for 2026-07-02 was
re-recorded after this correction; the superseded root file remains in git
history.

**Discovered.** 2026-07-02, scheduled integrity review (renewal challenge-prompt
CP-6: reproducibility & honest base-rates). The genesis snapshot (2026-06-27)
was verified unaffected: it passes its own checksums and remains byte-identical
to the Zenodo genesis deposit.
