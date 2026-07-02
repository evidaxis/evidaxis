# Evidaxis is dormant

> This notice is published automatically by the independent watcher when the
> keeper's signed heartbeat has been silent past its window. It is pre-drafted and
> (optionally) pre-signed with the Evidaxis trust-root key; the watcher only moves
> it into place, it does not author it.

Evidaxis has entered a **dormant** state. Active maintenance (weekly snapshots,
new measurements, methodology updates) has paused because the keeper's liveness
heartbeat lapsed past its window.

**The archive is not gone, and nothing here is retracted.** Every snapshot, every
measurement, every methodology version remains published under CC0, hash-pinned,
Merkle-anchored, and OpenTimestamps-stamped. It stays readable and citable forever.
What has stopped is the addition of *new* measurements, not the integrity of the
existing record.

- **Data**: still CC0, still at the same canonical URLs and JSON endpoints.
- **Integrity**: the last archive Merkle root and its timestamp remain valid; verify
  with `collectors/merkle_root.py --verify`.
- **Methodology**: frozen at the last published version; scores are never recomputed.
- **Continuity**: recovery and succession instructions are held under a Shamir split
  by the keeper's trusted holders. If you are a holder acting to continue Evidaxis,
  follow the sealed instructions; the methodology and the record are designed to
  outlive any single keeper.

Snapshots resume if and when the keeper (or a successor with the trust-root key)
signs a new heartbeat.
