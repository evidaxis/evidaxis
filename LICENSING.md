# Licensing — Evidaxis (authoritative per-component map)

> created: 2026-06-30 (audit baseline). This is the single source of truth for how
> Evidaxis is licensed. The repository is **multi-licensed by component**; there is no
> single repo-wide license. Machine-readable form: [`REUSE.toml`](REUSE.toml). Full
> license texts: [`LICENSES/`](LICENSES/).

Evidaxis is deliberately multi-licensed so that each kind of artifact carries the
license that fits it. Mixing the licenses in a single root `LICENSE` file would let
GitHub / Zenodo / SPDX scanners infer one wrong repo-wide license ("license soup"),
so each component is mapped explicitly below and in `REUSE.toml`.

| Component | Paths | SPDX | Text |
|---|---|---|---|
| **Code** | `etl/`, `web/src/`, `web/scripts/`, `spine/*.py`, `tests/`, `collectors/` (incl. `claim_urn.py`, the claim-URN reference implementation), `dead-man/`, `.github/` workflows, deploy scripts | `Apache-2.0` | [`LICENSES/Apache-2.0.txt`](LICENSES/Apache-2.0.txt) + [`NOTICE`](NOTICE) |
| **Data** | `data/`, `entities/`, `taxonomy/`, `relationships.tsv`, `redirects.yaml` | `CC0-1.0` | [`LICENSE-data.md`](LICENSE-data.md) |
| **Methodology prose** | the `/methodology` site pages (`web/src/pages/methodology/`), methodology write-ups | `CC-BY-4.0` | https://creativecommons.org/licenses/by/4.0/ |
| **Fonts** | `web/public/fonts/*.woff,*.woff2` | `OFL-1.1` | [`LICENSES/OFL-1.1.txt`](LICENSES/OFL-1.1.txt) + [`web/public/fonts/OFL.txt`](web/public/fonts/OFL.txt) |
| **Trademark** | the name "Evidaxis", logos | not a copyright license | see [`RIGHTS-BASIS.md`](RIGHTS-BASIS.md) — claimed (™), unregistered |

## Why these choices
- **Data = CC0** is load-bearing: open, freely-reusable data is preferentially cited by
  AI engines and indexed by dataset search. It is permanent (see `LICENSE-data.md`).
- **Code = Apache-2.0** gives downstream a patent grant and clear reuse terms.
- **Methodology prose = CC-BY-4.0** keeps the method open while requiring attribution.

## The genesis Zenodo deposit is CC0 — including its code copies
The genesis deposit (`genesis-deposit/`, minted to a Zenodo DOI) is a **CC0 public-domain
dedication of its specific contents** — its `genesis.jsonld` declares `CC0-1.0`. It bundles
verbatim copies of `code/collect.py` and `code/archive_pin.py`; inside that deposit those
copies are CC0-dedicated (the author may dedicate their own Apache-2.0 code to the public
domain for a specific release). The repository keeps the same files under `etl/` as
**Apache-2.0**. This dual-track is intentional, not a conflict:
- repo `etl/collect.py` → Apache-2.0 (ongoing, evolving code);
- `genesis-deposit/code/collect.py` → CC0, frozen verbatim under the genesis DOI
  (drift-guarded by `tests/test_genesis_deposit_sync.py`).

## Downstream quick guide
- Reusing **data** from Zenodo or `data/`: no attribution required (CC0), appreciated.
- Reusing **code** from `etl/`/`web/`: Apache-2.0 — keep `NOTICE`, no warranty, patent grant applies.
- Reusing the **fonts**: OFL-1.1 — ship `OFL.txt` with them, do not sell the fonts alone.
