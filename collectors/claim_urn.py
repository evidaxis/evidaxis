"""claim_urn - build/parse the format-independent canonical reference (see CLAIM-URN.md).

Scheme (LOCKED):
    urn:evidaxis:claim:{accession_id}:{methodology_version}:{epoch}

    accession_id        = EVX:{TYPE}:{BODY}   opaque, 3 colon-separated components,
                          | e_{BODY}            legacy live-entity id (colon-free),
                                              Crockford base32 body (never I L O U)
    methodology_version = m{N}                colon-free
    epoch               = YYYY-Www | YYYY-MM-DD  colon-free (no time-of-day)

Two accession forms are accepted: the future opaque `EVX:TYPE:BODY` (three
colon-separated components) and the legacy `e_BODY` that the live snapshots
already carry (colon-free). Both bind the claim to a system, never to a URL.

Because an EVX accession itself contains ':', the parser takes the LAST two colon
tokens as methodology and epoch (both colon-free by grammar) and rejoins the rest
as the accession. A legacy `e_` accession is colon-free, so it survives the same
rule as a single leading token. This keeps the URN human-readable and unambiguous.

New code, lives OUTSIDE the frozen etl/. Pure standard library.
"""
import re

PREFIX = "urn:evidaxis:claim"

# accession alphabet mirrors spine/schemas/_id.json (Crockford base32, no I L O U).
# Two forms: future opaque EVX:TYPE:BODY, and the legacy colon-free live id e_BODY.
_ACCESSION_RE = re.compile(
    r"^(?:EVX:[A-Z]{2,4}:[0-9A-HJKMNP-TV-Z]{11,40}|e_[0-9A-HJKMNP-TV-Z]{11,40})$"
)
_METHOD_RE = re.compile(r"^m[0-9]+$")
_EPOCH_RE = re.compile(r"^\d{4}-(?:w\d{2}|\d{2}-\d{2})$")


class ClaimURNError(ValueError):
    """Raised when a claim-URN or one of its fields violates the locked grammar."""


def _validate(accession_id, methodology_version, epoch):
    if not _ACCESSION_RE.match(accession_id):
        raise ClaimURNError(f"bad accession_id {accession_id!r}: want EVX:TYPE:BODY (Crockford base32)")
    if not _METHOD_RE.match(methodology_version):
        raise ClaimURNError(f"bad methodology_version {methodology_version!r}: want m<N>")
    if not _EPOCH_RE.match(epoch):
        raise ClaimURNError(f"bad epoch {epoch!r}: want YYYY-Www or YYYY-MM-DD (colon-free)")


def build(accession_id, methodology_version, epoch):
    """Construct a claim-URN string, validating each field against the locked grammar."""
    _validate(accession_id, methodology_version, epoch)
    return f"{PREFIX}:{accession_id}:{methodology_version}:{epoch}"


def parse(urn):
    """Parse a claim-URN into {accession_id, methodology_version, epoch}. Raises ClaimURNError."""
    if not isinstance(urn, str) or not urn.startswith(PREFIX + ":"):
        raise ClaimURNError(f"not a claim-URN: {urn!r}")
    parts = urn[len(PREFIX) + 1:].split(":")
    # minimum is accession(>=1 token) + method + epoch; EVX accession contributes 3
    # tokens, legacy e_ accession contributes 1. Method and epoch are colon-free.
    if len(parts) < 3:
        raise ClaimURNError(f"too few segments in {urn!r}: want accession+method+epoch")
    accession_id = ":".join(parts[:-2])
    methodology_version, epoch = parts[-2], parts[-1]
    _validate(accession_id, methodology_version, epoch)
    return {"accession_id": accession_id, "methodology_version": methodology_version, "epoch": epoch}
