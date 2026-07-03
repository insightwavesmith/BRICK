"""Runtime-mail handoff address helpers for the dynamic graph walker."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from brick_protocol.agent.return_fact import ALWAYS_SECRET_KEYS, TOP_LEVEL_VERDICT_KEYS
from brick_protocol.support.connection.adapter_validation import safe_source_fact_body
from brick_protocol.support.operator.primitives import _optional_text_value
from brick_protocol.support.operator.walker_carry import _step_output_body_from_file
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref

_RUNTIME_CONCERN_PAPER1_FIELD_NAMES: frozenset[str] = frozenset(
    {"transition_concern_evidence"}
)

def _runtime_handoff_unresolved_address(
    building_root: Path,
    reason_refs: Sequence[Any],
) -> str:
    """The FIRST runtime address claiming a ledger residence with no document.

    B1: a reason_ref of step-output FORM (a filesystem-path-shaped ref or a
    ``step-output:<slug>:attempt-N`` manifest ref) addresses a DOCUMENT in the
    Building ledger; a missing document is a broken ticket -> the caller HOLDs.
    Opaque refs (observation:/brick-comparison:/...) have their recorded
    residence in the runtime row document itself, which the ledger reader
    verifies separately. Returns "" when every address resolves. (run.py
    ``_is_step_output_source_fact_ref`` is a contiguous-marker predicate on a
    DIFFERENT surface -- declared Brick-row source_fact bodies, repo-root
    contained via ``_readable_source_fact_path`` -- runtime mail never routes
    through it, so it is intentionally NOT mirrored here since FIX 1c.)

    FIX 1 (0611 path traversal / cross-building smuggling): the ONLY ledger
    residence a step-output-form address may name is THIS Building's
    ``work/step-outputs/`` subtree. A mere existence probe is NOT containment:
    ``work/step-outputs/../../../other-building/raw/secret.json`` exists and
    would have been silently delivered. Therefore an address is UNRESOLVED
    (-> the caller HOLDs loudly; never delivered) when it
      - starts with ``/`` (an absolute path is never a building-relative
        ledger address),
      - carries a ``..`` (or empty/``.``) path segment, or
      - does not ``resolve()`` to a file STRICTLY INSIDE
        ``<building_root>/work/step-outputs/`` (symlink escapes fail too).

    FIX 1c (0611 spelling-independence, codex round-3 STILL-OPEN): the path
    FORM is no longer detected by how the ``work/step-outputs/`` MARKER is
    SPELLED -- it is decided by WHERE the ref RESOLVES. Prior rounds detected
    the marker as a CONTIGUOUS string (FIX 1 exact-case, FIX 1b casefolded),
    so a ref that RESOLVES into (then out of) the subtree but is SPELLED
    non-contiguously -- ``work/./step-outputs/../../escape/x.json``,
    ``work//step-outputs/../../escape/x.json`` -- bypassed detection entirely,
    fell through as an "opaque" ref, and was DELIVERED (operator-verified
    0611: returned ""). That is the SAME CLASS recurring; the spelling match
    was the root cause, so it is gone. The branching is now:

      - ``step-output:<slug>:attempt-N`` MANIFEST refs (a scheme, no ``/``)
        keep their existing handling: shape-validated, then containment.
      - ANY remaining ref carrying a ``/`` is filesystem-path-shaped. The only
        ledger residence a path-form runtime ref may name is THIS Building's
        ``work/step-outputs/`` subtree, so EVERY such ref must ``resolve()``
        (under ``building_root``) to a document strictly inside it. Absolute
        paths are never building-relative ledger addresses -> UNRESOLVED.
        Whatever the spelling (``work/./step-outputs``, ``work//step-outputs``,
        ``Work/Step-Outputs`` on a case-insensitive filesystem), an in-subtree
        resolution delivers and an out-of-subtree resolution is UNRESOLVED ->
        the caller HOLDs (fail-closed). FIX 1d (0611, codex round-4
        trusted-intermediate symlink): containment is anchored on the RESOLVED
        BUILDING ROOT, never on a resolved ledger subtree -- see
        ``_step_output_address_escapes_ledger``.
      - Refs with NO ``/`` and no manifest scheme are the opaque scheme tokens
        (observation:/brick-comparison:/...) verified elsewhere, unchanged.
    """

    for ref in reason_refs:
        text = str(ref).replace("\\", "/")
        if text.casefold().startswith("step-output:"):
            parts = text.split(":")
            if (
                len(parts) != 3
                or not parts[1]
                or not parts[2].casefold().startswith("attempt-")
            ):
                return str(ref)
            relative = f"work/step-outputs/{parts[1]}-{parts[2]}/step-output.json"
            if _step_output_address_escapes_ledger(building_root, relative):
                return str(ref)
            continue
        if "/" not in text:
            # Opaque scheme token (observation:, brick-comparison:, ...):
            # its recorded residence is verified by the ledger reader.
            continue
        if text.startswith("/"):
            return str(ref)
        if _step_output_address_escapes_ledger(building_root, text):
            return str(ref)
    return ""


def _runtime_handoff_undelivered_citation_ref(ref: str) -> bool:
    """True for old citation-shaped refs that must be recorded but not delivered.

    Security-address failures still fail closed through
    ``_runtime_handoff_unresolved_address``. This exception only covers recorded
    old evidence that used citation syntax where runtime mail now expects
    deliverable ``work/step-outputs/...`` addresses.
    """

    text = ref.replace("\\", "/")
    if "#" in text:
        return True
    if re.search(r"(?:/|^[^:]+\.[A-Za-z0-9]+):[0-9]+$", text):
        return True
    if "/" in text and not text.startswith("/") and ".." not in text.split("/"):
        return not text.startswith("work/step-outputs/")
    return False


def _runtime_concern_summary_fields_from_step_output(
    building_root: Path,
    step_output_ref: str,
) -> dict[str, str]:
    body = _step_output_body_from_file(building_root, step_output_ref)
    if body is None:
        return {}
    try:
        document = json.loads(body)
    except ValueError:
        return {}
    if not isinstance(document, Mapping):
        return {}
    returned = document.get("returned")
    if not isinstance(returned, Mapping):
        return {}
    result: dict[str, str] = {}
    for raw_key in sorted(returned, key=str):
        key = str(raw_key)
        normalized_key = key.strip().lower().replace("-", "_").replace(" ", "_")
        if (
            normalized_key in _RUNTIME_CONCERN_PAPER1_FIELD_NAMES
            or normalized_key in ALWAYS_SECRET_KEYS
            or normalized_key in TOP_LEVEL_VERDICT_KEYS
        ):
            continue
        result[key] = safe_source_fact_body(
            json.dumps(returned[raw_key], ensure_ascii=False, sort_keys=True)
        )
    return result


def _step_output_address_escapes_ledger(
    building_root: Path,
    relative: str,
) -> bool:
    """True when a step-output-form address must NOT be delivered (fail-closed).

    FIX 1 (0611): containment, not just existence. FIX 1c (0611): containment
    by RESOLUTION, not by segment spelling. FIX 1d (0611, codex round-4
    trusted-intermediate symlink): containment is anchored on the RESOLVED
    BUILDING ROOT, never on a resolved ledger subtree. The prior round
    ``resolve()``d ``<building_root>/work/step-outputs`` FIRST and trusted
    that inode as the containment root (``samestat`` ancestry), so when
    ``work/step-outputs`` ITSELF was a symlink pointing OUTSIDE the building,
    the symlink TARGET became the trusted root and
    ``work/step-outputs/x.json`` was DELIVERED while resolving outside the
    building (operator-reproduced 0611). Deriving the containment root by
    following a symlink is the root cause, so no intermediate path is ever
    resolved into a trusted root any more. The rule is now:

      - ``real_root = building_root.resolve(strict=True)`` is the ONLY
        trusted anchor (resolving the root cannot be redirected by ledger
        content -- the building root is operator-supplied, not
        address-supplied);
      - the candidate ``(building_root / relative).resolve()`` (collapsing
        ``.``/``..``/doubled separators and following EVERY symlink) must be
        a FILE whose resolved path lies under ``real_root`` -- an escape
        outside the building rejects; AND
      - the candidate's path RELATIVE TO ``real_root`` must begin with the
        literal ``("work", "step-outputs")`` components and name a document
        STRICTLY BELOW them (lexical prefix on the POST-resolve relative
        path).

    A ledger directory that symlinks elsewhere therefore always fails: the
    candidate either resolves outside ``real_root`` (first guard) or resolves
    inside but its post-resolve relative path no longer starts with
    ``work/step-outputs`` (second guard). That closes the whole
    trusted-intermediate-symlink CLASS, not one spelling of it. A ``..`` that
    climbs out, an in-building symlink detour, or a missing root/document all
    reject; a weirdly-spelled ref (dot segments, doubled ``/``) that resolves
    to a real document strictly inside ``real_root/work/step-outputs`` is
    contained.
    """

    try:
        real_root = building_root.resolve(strict=True)
    except OSError:
        return True
    try:
        candidate = (building_root / relative).resolve()
    except OSError:
        return True
    if not candidate.is_file():
        return True
    try:
        candidate_in_root = candidate.relative_to(real_root)
    except ValueError:
        return True
    return (
        len(candidate_in_root.parts) <= 2
        or candidate_in_root.parts[:2] != ("work", "step-outputs")
    )


def _runtime_concern_handoff_from_ledger(
    *,
    building_root: Path,
    source_step_ref: str,
    source_brick_ref: str,
    source_attempt_index: int,
    adopted_concern: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    """Build the adopted-concern runtime mail entry FROM THE RECORDED FACT.

    Reads the source occurrence's written transition-concern.json (the runtime
    row's formal residence in the ledger; written by record_step_output BEFORE
    adoption) and delivers the RECORDED reason_refs -- never the in-memory
    values -- with provenance (row ref + kind + recorded residence) so replay
    reads the recorded fact. The concern document's own recorded address always
    rides as ``concern_doc_ref`` once the row is verified. Old citation-shaped
    refs are quarantined under ``undelivered_citation_refs`` rather than
    delivered. Returns ``(entry, "")`` on success, or
    ``(None, hold_reason)`` fail-closed (B1) when the recorded residence is
    missing/unreadable, the recorded row is not the adopted row, the mandatory
    recorded reason_refs are empty, or a security-shaped recorded address does
    not resolve in the ledger.
    """

    manifest_ref = _step_output_manifest_ref(source_step_ref, source_attempt_index)
    concern_doc_ref = (
        manifest_ref[: -len("step-output.json")] + "transition-concern.json"
        if manifest_ref.endswith("step-output.json")
        else manifest_ref
    )
    body = _step_output_body_from_file(building_root, concern_doc_ref)
    if body is None:
        if _is_machine_authored_proof_concern(adopted_concern):
            return _machine_authored_proof_concern_mail(
                building_root=building_root,
                source_step_ref=source_step_ref,
                source_brick_ref=source_brick_ref,
                source_attempt_index=source_attempt_index,
                adopted_concern=adopted_concern,
            )
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    try:
        document = json.loads(body)
    except ValueError:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    if not isinstance(document, Mapping):
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    recorded = document.get("transition_concern_returned")
    if not isinstance(recorded, Mapping):
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    recorded_row_ref = _optional_text_value(recorded.get("concern_ref")) or ""
    adopted_row_ref = _optional_text_value(adopted_concern.get("concern_ref")) or ""
    if not recorded_row_ref or recorded_row_ref != adopted_row_ref:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    raw_reason_refs = recorded.get("reason_refs")
    reason_refs = [
        text
        for text in (
            _optional_text_value(ref)
            for ref in (raw_reason_refs if isinstance(raw_reason_refs, list) else [])
        )
        if text
    ]
    if not reason_refs:
        return None, f"runtime_handoff_concern_row_unrecorded_in_ledger:{concern_doc_ref}"
    deliverable_reason_refs: list[str] = []
    undelivered_citation_refs: list[str] = []
    for ref in reason_refs:
        unresolved = _runtime_handoff_unresolved_address(building_root, [ref])
        if not unresolved:
            deliverable_reason_refs.append(ref)
            continue
        if _runtime_handoff_undelivered_citation_ref(ref):
            undelivered_citation_refs.append(ref)
            continue
        return None, f"runtime_handoff_address_unresolved_in_ledger:{unresolved}"
    summary_fields = _runtime_concern_summary_fields_from_step_output(
        building_root,
        _optional_text_value(document.get("step_output_ref")) or "",
    )
    entry: dict[str, Any] = {
        "from_step_ref": source_step_ref,
        "from_brick_instance_ref": source_brick_ref,
        "row_kind": "transition_concern",
        "row_ref": recorded_row_ref,
        "concern_doc_ref": concern_doc_ref,
        "reason_refs": list(deliverable_reason_refs),
        "provenance": {
            "runtime_row_ref": _optional_text_value(
                document.get("transition_concern_ref")
            )
            or recorded_row_ref,
            "row_kind": "transition_concern",
            "recorded_in": concern_doc_ref,
        },
    }
    if undelivered_citation_refs:
        entry["undelivered_citation_refs"] = undelivered_citation_refs
    if summary_fields:
        entry["recorded_summary_fields"] = summary_fields
    return (
        entry,
        "",
    )


def _is_machine_authored_proof_concern(concern: Mapping[str, Any]) -> bool:
    concern_ref = _optional_text_value(concern.get("concern_ref")) or ""
    return concern_ref.startswith("transition-concern:proof-obligation:")


def _machine_authored_proof_concern_mail(
    *,
    building_root: Path,
    source_step_ref: str,
    source_brick_ref: str,
    source_attempt_index: int,
    adopted_concern: Mapping[str, Any],
) -> tuple[dict[str, Any] | None, str]:
    reason_refs = [
        text
        for text in (
            _optional_text_value(ref)
            for ref in adopted_concern.get("reason_refs", [])
        )
        if text
    ]
    if not reason_refs:
        return None, "runtime_handoff_machine_proof_concern_missing_reason_refs"
    unresolved = _runtime_handoff_unresolved_address(building_root, reason_refs)
    if unresolved:
        return None, f"runtime_handoff_address_unresolved_in_ledger:{unresolved}"
    concern_ref = _optional_text_value(adopted_concern.get("concern_ref")) or ""
    return (
        {
            "from_step_ref": source_step_ref,
            "from_brick_instance_ref": source_brick_ref,
            "row_kind": "machine_transition_concern",
            "row_ref": concern_ref,
            "concern_doc_ref": reason_refs[0],
            "reason_refs": reason_refs,
            "provenance": {
                "runtime_row_ref": concern_ref,
                "row_kind": "machine_transition_concern",
                "recorded_in": reason_refs[0],
                "source_attempt_index": source_attempt_index,
            },
        },
        "",
    )
