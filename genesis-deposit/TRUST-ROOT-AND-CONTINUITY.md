# Evidaxis Genesis — Trust-Root & Continuity Protocol v1.0

> Ships with the genesis DOI deposit; its hash is inscribed in the genesis record. Grounded in an internal trust-root/succession review. States the SHAPE of continuity honestly — it does NOT claim custody machinery that does not yet exist.

## Trust-root
- The genesis event-ledger and the DOI deposit are signed with a **single operational Ed25519 key**. The **block-zero public key + fingerprint are inscribed permanently** (you can rotate a key forward; you can never change who signed block zero). The KeyRegistry records the algorithm per key and **permits a future M-of-N / threshold scheme by forward rotation** — so a heavier custody model is added later WITHOUT re-rooting.

## Past-integrity is decoupled from the key (the load-bearing property)
- Every sealed snapshot is **externally anchored** over the FULL signed manifest (not the bare state_root): **OpenTimestamps** (Bitcoin-backed, free, survives the operator) as primary + an **RFC-3161 TSA** receipt as corroborator. The ledger is **byte-reproducible** from the public CC0 inputs.
- Therefore: **losing the key destroys only the ability to sign NEW events — it does not destroy the verifiability of PAST records.** Any third party recomputes the state from the public inputs and checks the anchor, with zero access to the key. "Orphan hash = catastrophe" becomes "**the record stops growing but stays cryptographically verifiable forever**" — a citable historical asset, not a dead one.
- The anchored object includes the **ordered input-set content-hash** (so a different input history cannot rebuild to the same anchored root) and the schema-version + KeyRegistry-as-of. The **verification recipe is published** with the deposit.

## Key custody (proportionate — honest about what exists)
- **Now (solo, pre-revenue, seed):** a single operational key with a basic offline backup. The external anchor + reproducibility (above) are what actually defuse the bus-factor risk, so a full air-gapped multi-party ceremony is **not claimed and not required at genesis** — claiming an escrow that does not exist would be theater.
- **Later (when the project has value worth attacking, by forward rotation):** an air-gapped key-generation ceremony + Shamir-split escrow among trusted holders, and institutional custody once a legal entity exists. The KeyRegistry already supports this; declaring it as the *expected* path here is what makes the later hardening NOT a retrofit.

## Rotation / revocation / compromise
- **Rotation:** the current key signs a KeyRegistry event authorizing the new key (chained delegation), anchored; the dead-man's-switch (if/when set) rebinds to the new key.
- **Revocation:** a signed, anchored revocation event.
- **Compromise:** committed posture — any suspected compromise is disclosed publicly as a signed/anchored event with the compromise window. Anchors prove what existed pre-compromise (a stolen key cannot back-date); only post-compromise unanchored signing is suspect.
- **Post-quantum:** algorithm-agility is inscribed (per-key algorithm in the KeyRegistry); Ed25519 now, migrate to a NIST PQC signature (ML-DSA/SLH-DSA) later by rotation. The hash-based anchor is already post-quantum-safe for PAST integrity, so PQC urgency applies only to future signing (rotatable).

## Continuity / tombstone / canonical-fork rule
- The record **outlives any single steward**: it is anchored + reproducible by anyone. The institute reserves the **right to pause, end, or be inherited** — an honest tombstone, never a silent rewrite or a retroactive mutation.
- Institutional succession (a custodian entity / board / escrow) is **expected to be added later by rotation**, not at genesis.
- **Canonical-fork rule (binds successor intent without a legal entity):** to be considered the canonical Evidaxis, any successor must keep the record **CC0 + positive-only by construction**. A key that signs a policy-violating event is, by this published rule, non-canonical — citers and downstream consumers should reject its seals.

*Basis: an internal trust-root/succession review. The mechanism (KeyRegistry, ArchiveManifest.external_anchor, byte-reproducible rebuild, SourceRegistry retention) already exists in the spine schema; this document is the genesis POLICY layered on it.*
