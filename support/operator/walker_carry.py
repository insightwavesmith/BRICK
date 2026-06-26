"""Carry, step-output, and wiki-view helpers for the dynamic graph walker."""

from __future__ import annotations

import json
import shutil
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.brick.work import parse_carries_forward_fields
from brick_protocol.support.connection.adapter_validation import safe_source_fact_body
from brick_protocol.support.operator.contracts import BuildingRunSupportResult
from brick_protocol.support.operator.primitives import _merge_texts
from brick_protocol.support.recording.declaration_packets import (
    _write_declaration_work_evidence,
)
from brick_protocol.support.recording.step_outputs import _step_output_manifest_ref

def _carries_forward_fields_for_result(
    result: BuildingRunSupportResult,
) -> tuple[str, ...]:
    """The UPSTREAM step's declared carries_forward_fields (the HANDOFF subset).

    Read off ``result.preparation.step_rows.brick_row`` -- the SAME Brick row
    surface that carries ``required_return_shape`` -- and parsed with the
    canonical Brick parser ``parse_carries_forward_fields``. Returns ``()`` when
    the row omits the key (a kind with no declared carry-set) OR when the
    preparation/row is missing, which the carry filter reads as "no filter"
    (full-summary carry, backward-safe). Support reads the VALUE off the row; it
    never reads the return.yaml form directly.
    """

    preparation = getattr(result, "preparation", None)
    step_rows = getattr(preparation, "step_rows", None)
    brick_row = getattr(step_rows, "brick_row", None)
    if not isinstance(brick_row, Mapping):
        return ()
    return parse_carries_forward_fields(brick_row.get("carries_forward_fields"))


def _source_fact_body_carry_for_step(
    *,
    building_root: Path,
    building_id: str,
    target_step_ref: str,
    cascade_depth: int,
    step: Mapping[str, Any],
    step_results: list[BuildingRunSupportResult],
    step_result_events: list[Mapping[str, Any]],
    fan_in_sources_by_target: Mapping[str, tuple[str, ...]],
    cohort_skip_carry_forward: set[tuple[str, int]] | None = None,
) -> Mapping[str, Any]:
    source_facts = _brick_source_facts(step)
    skip_carry_forward = cohort_skip_carry_forward or set()
    attempts = _step_result_attempt_indices(step_results)
    result_refs: dict[int, str] = {}
    for index, result in enumerate(step_results):
        attempt_index = attempts[index]
        step_ref = result.preparation.step_rows.step_ref
        result_refs[index] = _step_output_manifest_ref(step_ref, attempt_index)

    # The UPSTREAM kind's HANDOFF subset, keyed by the carried result index. Read
    # off result.preparation.step_rows.brick_row -- the SAME row carrying
    # required_return_shape -- and parsed with the canonical Brick parser. Empty
    # => no filter (full-summary carry). This is what FILTERS the forwarded
    # summary down to the upstream kind's declared carries_forward_fields.
    forward_fields_by_index: dict[int, tuple[str, ...]] = {}
    for index, result in enumerate(step_results):
        forward_fields_by_index[index] = _carries_forward_fields_for_result(result)

    bodies: dict[str, str] = {}
    carried_step_output_refs: list[str] = []
    missing_source_fact_refs: list[str] = []
    carried_result_indices: set[int] = set()
    observed_source_step_refs: list[str] = []
    missing_source_step_refs: list[str] = []

    for source_fact in source_facts:
        match = _matching_step_output_index(
            source_fact,
            cascade_depth=cascade_depth,
            result_refs=result_refs,
            step_result_events=step_result_events,
        )
        if match is None:
            if "step-output" in source_fact:
                missing_source_fact_refs.append(source_fact)
            continue
        body = _step_output_wiki_carry_body(
            building_root,
            result_refs[match],
            forward_fields_by_index.get(match, ()),
        )
        if body is None:
            missing_source_fact_refs.append(source_fact)
            source_step_ref = _step_ref_from_step_output_ref(result_refs[match])
            if source_step_ref:
                missing_source_step_refs.append(source_step_ref)
            continue
        bodies[source_fact] = body
        carried_result_indices.add(match)
        carried_step_output_refs.append(result_refs[match])
        source_step_ref = _step_ref_from_step_output_ref(result_refs[match])
        if source_step_ref:
            observed_source_step_refs.append(source_step_ref)

    for source_step_ref in fan_in_sources_by_target.get(target_step_ref, ()):
        match = _latest_completed_step_index(
            source_step_ref,
            cascade_depth=cascade_depth,
            step_result_events=step_result_events,
        )
        if match is None and (source_step_ref, cascade_depth) in skip_carry_forward:
            # A HUMAN-vouched (sibling_independence) skipped sibling is not
            # re-walked at this reroute cascade-depth; carry its PRIOR PASS
            # (its most recent completion at an earlier depth) forward so the
            # fan-in target's carry gate is satisfied without re-running it.
            match = _latest_completed_step_index_any_depth(
                source_step_ref,
                step_result_events=step_result_events,
            )
        if match is None:
            missing_source_fact_refs.append(
                f"fan-in-source:{source_step_ref}:cascade-{cascade_depth}"
            )
            missing_source_step_refs.append(source_step_ref)
            continue
        if match in carried_result_indices:
            continue
        body = _step_output_wiki_carry_body(
            building_root,
            result_refs[match],
            forward_fields_by_index.get(match, ()),
        )
        if body is None:
            missing_source_fact_refs.append(
                f"fan-in-source:{source_step_ref}:step-output-body-missing:"
                f"cascade-{cascade_depth}"
            )
            missing_source_step_refs.append(source_step_ref)
            continue
        bodies.setdefault(result_refs[match], body)
        carried_result_indices.add(match)
        carried_step_output_refs.append(result_refs[match])
        observed_source_step_refs.append(source_step_ref)

    if not source_facts and target_step_ref not in fan_in_sources_by_target:
        return {"source_fact_bodies": bodies, "observation": None}

    carried_unique = list(dict.fromkeys(carried_step_output_refs))
    missing_unique = list(dict.fromkeys(missing_source_fact_refs))
    observation = {
        "kind": "source_fact_body_carry_observation",
        "target_step_ref": target_step_ref,
        "cascade_depth": cascade_depth,
        "declared_source_fact_refs": list(source_facts),
        "fan_in_source_step_refs": list(fan_in_sources_by_target.get(target_step_ref, ())),
        "observed_source_step_refs": list(dict.fromkeys(observed_source_step_refs)),
        "missing_source_step_refs": list(dict.fromkeys(missing_source_step_refs)),
        "carried_step_output_refs": carried_unique,
        "supplied_source_fact_body_refs": list(bodies),
        "missing_source_fact_refs": missing_unique,
        "body_absent": bool(missing_unique),
        "carry_gate_observation": _carry_gate_observation(
            target_step_ref=target_step_ref,
            carried_step_output_refs=carried_unique,
            missing_source_fact_refs=missing_unique,
        ),
        "carry_fact_observation": _carry_fact_observation(
            target_step_ref=target_step_ref,
            carried_step_output_refs=carried_unique,
        ),
        "proof_limits": [
            "Link carry/gate observation over declared step-output refs only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
        "not_proven": [
            "semantic sufficiency of carried bodies",
            "partial QA reuse",
        ],
    }
    return {"source_fact_bodies": bodies, "observation": observation}


def _carry_gate_observation(
    *,
    target_step_ref: str,
    carried_step_output_refs: list[str],
    missing_source_fact_refs: list[str],
) -> Mapping[str, Any]:
    required = tuple(dict.fromkeys([*carried_step_output_refs, *missing_source_fact_refs]))
    missing = tuple(dict.fromkeys(missing_source_fact_refs))
    return {
        "kind": "link_carry_gate_observation",
        "stage": "carry",
        "sufficiency": "missing_required_facts" if missing else "sufficient",
        "checked_public_fact": f"step-output-carry:{target_step_ref}",
        "required_public_facts": list(required),
        "missing_required_facts": list(missing),
        "reason": (
            "declared Link fan-in carry gate over already-written step-output evidence"
        ),
        "proof_limits": [
            "support records Link carry gate observation only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _carry_fact_observation(
    *,
    target_step_ref: str,
    carried_step_output_refs: list[str],
) -> Mapping[str, Any] | None:
    carried = tuple(dict.fromkeys(carried_step_output_refs))
    if not carried:
        return None
    return {
        "kind": "link_carry_fact_observation",
        "carried_fact_refs": list(carried),
        "source_owner_axis": "Agent",
        "target_boundary_ref": target_step_ref,
        "evidence_reference": f"step-output-carry:{target_step_ref}",
        "proof_limits": [
            "support records Link carry observation only",
            "not source truth",
            "not success judgment",
            "not quality judgment",
            "not Movement authority",
        ],
    }


def _fan_in_observation_from_carry_observation(
    observation: Mapping[str, Any],
    *,
    required_sources: tuple[str, ...],
) -> Mapping[str, Any]:
    observed_sources = tuple(
        str(ref)
        for ref in observation.get("observed_source_step_refs", ())
        if str(ref)
    )
    missing_sources = tuple(
        str(ref)
        for ref in observation.get("missing_source_step_refs", ())
        if str(ref)
    )
    carry_gate = observation.get("carry_gate_observation")
    missing_required_facts: list[str] = []
    if isinstance(carry_gate, Mapping):
        missing_required_facts = [
            str(ref)
            for ref in carry_gate.get("missing_required_facts", ())
            if str(ref)
        ]
    return {
        "kind": "fan_in_wait_all_observation",
        "target_step_ref": observation.get("target_step_ref", ""),
        "cascade_depth": observation.get("cascade_depth", 0),
        "required_source_step_refs": list(required_sources),
        "observed_source_step_refs": list(dict.fromkeys(observed_sources)),
        "missing_source_step_refs": list(dict.fromkeys(missing_sources)),
        "pending_source_step_refs": [],
        "carry_gate_observation": dict(carry_gate) if isinstance(carry_gate, Mapping) else {},
        "missing_required_facts": list(dict.fromkeys(missing_required_facts)),
        "proof_limits": list(observation.get("proof_limits", ())),
        "not_proven": list(observation.get("not_proven", ())),
    }


# run_building_intake (support/operator/driver.py) writes its materialized
# INPUT plan to <building_root>/declared-building-plan.json and then
# immediately walks it; without an admission for exactly that artifact, the
# first defaults use always self-collided here (FileExistsError). The
# admission is fail-closed and EXACT: a pre-existing root is admitted IFF it
# holds ONLY regular non-symlink file(s) named in this set -- any other name,
# any subdirectory, any symlink, or an EMPTY root still rejects. (The run's
# own work/declared-building-plan.json declaration packet lives under work/
# and is a different file.) This PRE-ADAPTER predicate intentionally remains
# narrower than support.recording.adapter_error_frontier's POST-ADAPTER
# declaration-chain/root-state handling, which may preserve report/declaration
# artifacts or mark partial roots after an adapter interruption. Parity copy
# lives in run.py.
_PREEXISTING_ROOT_INTAKE_ARTIFACTS: frozenset[str] = frozenset(
    {"declared-building-plan.json"}
)


def _root_holds_only_intake_plan_artifact(root: Path) -> bool:
    entries = list(root.iterdir())
    if not entries:
        return False
    for entry in entries:
        if entry.name not in _PREEXISTING_ROOT_INTAKE_ARTIFACTS:
            return False
        if entry.is_symlink() or not entry.is_file():
            return False
    return True


def _preflight_step_output_building_root(
    output_root: Path | str,
    building_id: str,
    *,
    overwrite_existing: bool,
) -> Path:
    root = Path(output_root) / building_id
    if root.exists():
        if not root.is_dir():
            raise NotADirectoryError(f"Building lifecycle root is not a directory: {root}")
        if not overwrite_existing and not _root_holds_only_intake_plan_artifact(root):
            raise FileExistsError(
                "Building lifecycle root already exists; choose a new building_id "
                "or pass overwrite_existing=True"
            )
    return root


def _clear_overwrite_claim_trace_manifest(root: Path) -> None:
    if not root.exists() or not root.is_dir():
        return
    claim_trace = root / "evidence" / "claim_trace"
    if claim_trace.exists():
        if claim_trace.is_symlink() or claim_trace.is_file():
            claim_trace.unlink()
        else:
            shutil.rmtree(claim_trace)
    raw_manifest = root / "raw" / "raw-manifest.json"
    if raw_manifest.exists():
        raw_manifest.unlink()


def _materialize_initial_declaration_evidence(
    building_root: Path,
    *,
    building_id: str,
    plan_ref: str,
    plan: Mapping[str, Any],
    declaration_plan: Mapping[str, Any],
    graph_context: Mapping[str, Any] | None,
    task_source_ref: str | None,
    proof_limits: tuple[str, ...],
) -> None:
    building_root.mkdir(parents=True, exist_ok=True)
    _write_declaration_work_evidence(
        building_root,
        building_id=building_id,
        plan_ref=plan_ref,
        plan=plan,
        declaration_plan=declaration_plan,
        graph_context=graph_context,
        task_source_ref=task_source_ref,
        proof_limits=proof_limits,
        not_proven=_merge_texts(plan.get("not_proven")),
    )


def _brick_source_facts(step: Mapping[str, Any]) -> tuple[str, ...]:
    rows = step.get("rows")
    if not isinstance(rows, list):
        return ()
    for row in rows:
        if isinstance(row, Mapping) and row.get("axis") == "Brick":
            raw = row.get("source_facts", ())
            if not isinstance(raw, list):
                return ()
            return tuple(str(item).strip() for item in raw if str(item).strip())
    return ()


def _step_result_attempt_indices(
    step_results: list[BuildingRunSupportResult],
) -> tuple[int, ...]:
    counts: dict[str, int] = {}
    attempts: list[int] = []
    for result in step_results:
        step_ref = result.preparation.step_rows.step_ref
        counts[step_ref] = counts.get(step_ref, 0) + 1
        attempts.append(counts[step_ref])
    return tuple(attempts)


def _matching_step_output_index(
    source_fact: str,
    *,
    cascade_depth: int,
    result_refs: Mapping[int, str],
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    normalized = str(source_fact).strip()
    if not normalized:
        return None
    for index, ref in result_refs.items():
        if int(step_result_events[index].get("cascade_depth", 0)) != cascade_depth:
            continue
        if normalized == ref or normalized.endswith("/" + ref):
            return index
    return None


def _latest_completed_step_index(
    step_ref: str,
    *,
    cascade_depth: int,
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    for index in range(len(step_result_events) - 1, -1, -1):
        event = step_result_events[index]
        if event.get("step_ref") == step_ref and int(event.get("cascade_depth", 0)) == cascade_depth:
            return index
    return None


def _latest_completed_step_index_any_depth(
    step_ref: str,
    *,
    step_result_events: list[Mapping[str, Any]],
) -> int | None:
    """Latest completion of step_ref at ANY cascade-depth (prior-pass carry).

    Used only for a HUMAN-vouched (sibling_independence) skipped fan-in source:
    the sibling is not re-walked at the reroute depth, so its most recent prior
    completion carries forward to satisfy the fan-in target's carry gate.
    """

    for index in range(len(step_result_events) - 1, -1, -1):
        if step_result_events[index].get("step_ref") == step_ref:
            return index
    return None


def _step_ref_from_step_output_ref(step_output_ref: str) -> str:
    parts = str(step_output_ref).replace("\\", "/").split("/")
    if len(parts) < 3:
        return ""
    slug = parts[-2]
    marker = "-attempt-"
    if marker not in slug:
        return slug
    return slug[: slug.rindex(marker)]


def _step_output_body_from_file(building_root: Path, step_output_ref: str) -> str | None:
    try:
        return (building_root / step_output_ref).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


# ---------------------------------------------------------------------------
# WIKI-CARRY (Kaparthy wiki pattern): the walker carries a COMPACT wiki VIEW
# between steps -- NOT the full step-output.json body. Carrying the full body
# (envelope + evidence_refs + proof_limits + graph metadata + returned) made
# the carried context blow up step over step (token amplification). The wiki
# view carries only:
#   * SUMMARY  = the step-output's ``returned`` field (the agent's CURATED
#                output), serialized compactly and floored by
#                ``safe_source_fact_body`` (runaway-returned backstop / secret
#                redaction). No envelope, no evidence_refs, no proof_limits.
#   * PATH     = the ABSOLUTE path of the real step-output.json on disk, so the
#                worker can "go look" with its own file-read tool when the
#                summary is not enough (codex --sandbox read-only reads
#                ~/.brick absolute paths -- WIKI_READ_PROOF).
#   * NOTE     = a plain-text instruction telling the worker the body is a
#                summary and where the full output lives.
# The on-disk step-output.json / raw/ are NEVER touched -- the path merely
# points at them. ``source_fact_bodies`` rides ONLY as text context in the
# agent prompt (agent_adapter._source_fact_bodies_for_prompt -> prompt JSON);
# no runtime program parses it (the checker simulators that parse it read the
# SUMMARY section back via ``wiki_carry_summary_text``).
#
# VIEW ORDER (load-bearing): PATH + NOTE come FIRST, the SUMMARY comes LAST.
# The view is floored by ``safe_source_fact_body`` here, and the agent adapter
# floors it AGAIN downstream (``_clean_source_fact_bodies`` and
# ``_source_fact_bodies_for_prompt``, limit 12000 / gemini 4000). All of those
# floors truncate the TAIL (``body[:limit]``). A large ``returned`` can push the
# whole view past a downstream limit; if the PATH/NOTE were in the tail they
# would be silently amputated and the worker would lose the "go look" address.
# By placing the absolute PATH and the NOTE BEFORE the summary, any tail-
# truncate (whichever limit fires) eats only the END of the summary and ALWAYS
# preserves the load-bearing path + note. This is adapter-agnostic: it does not
# matter which floor cuts -- the head is preserved.
# ---------------------------------------------------------------------------

_WIKI_CARRY_VIEW_HEADER = "[BRICK WIKI CARRY VIEW]"
_WIKI_CARRY_SUMMARY_PREFIX = "summary (this step's returned -- agent's curated output):"
_WIKI_CARRY_PATH_PREFIX = "full step output path:"
_WIKI_CARRY_NOTE = (
    "note: the summary below is THIS step's returned (the agent's curated "
    "output) only. The FULL step output (the whole step-output document with "
    "its evidence pointers, proof limits, and metadata) is NOT inline here -- "
    "it lives in the file at the path above. If the summary is not enough, "
    "read that file with your own file-read tool."
)


def _returned_summary_for_carry(
    body: str, forward_fields: tuple[str, ...] = ()
) -> str:
    """The compact wiki SUMMARY = the step-output's ``returned`` field.

    ``returned`` is the agent's CURATED output. We serialize ONLY it (never the
    surrounding step-output envelope) and floor it through
    ``safe_source_fact_body`` so a runaway ``returned`` is still truncated and
    raw secrets are redacted. Fallbacks (missing/oversize/non-JSON file) keep a
    safe, non-empty summary so the carry never silently drops the worker's
    context.

    CARRY FILTER: when ``forward_fields`` is non-empty it is the UPSTREAM kind's
    declared ``carries_forward_fields`` (the HANDOFF subset). The serialized
    ``returned`` is then narrowed to JUST those fields (PRESENT ones --
    ``if k in returned`` -- a real step-output may omit a declared field) before
    the dump, so the COMMON ENVELOPE (observed_evidence, not_proven, ...) and any
    adapter cruft never cross inline. Empty ``forward_fields`` => no filter
    (full ``returned`` carried, the pre-filter behavior). The full step-output
    stays reachable at the PATH the wiki view prepends -- filtering narrows the
    INLINE summary only, it never removes reachability.
    """

    try:
        packet = json.loads(body)
    except (json.JSONDecodeError, ValueError):
        return safe_source_fact_body(body)
    if not isinstance(packet, Mapping) or "returned" not in packet:
        return safe_source_fact_body(body)
    returned = packet.get("returned")
    if forward_fields and isinstance(returned, Mapping):
        returned = {
            key: returned[key] for key in forward_fields if key in returned
        }
    try:
        rendered = json.dumps(returned, ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        return safe_source_fact_body(body)
    return safe_source_fact_body(rendered)


def _wiki_carry_view(
    building_root: Path,
    step_output_ref: str,
    body: str,
    forward_fields: tuple[str, ...] = (),
) -> str:
    """Build the compact wiki VIEW carried in place of the full step-output body.

    ``forward_fields`` (the upstream kind's carries_forward_fields) narrows the
    INLINE summary; the PATH + NOTE pointing at the full step-output are always
    emitted unchanged, so a filtered field stays reachable via the file.
    """

    absolute_path = str((building_root / step_output_ref).resolve())
    summary = _returned_summary_for_carry(body, forward_fields)
    # PATH + NOTE FIRST, SUMMARY LAST: downstream re-truncation
    # (safe_source_fact_body, limit 12000 / gemini 4000) cuts the TAIL, so the
    # load-bearing absolute path and note always survive while only the END of an
    # oversize summary is trimmed. See the VIEW ORDER note above.
    return (
        f"{_WIKI_CARRY_VIEW_HEADER}\n"
        f"{_WIKI_CARRY_PATH_PREFIX} {absolute_path}\n"
        f"{_WIKI_CARRY_NOTE}\n"
        f"{_WIKI_CARRY_SUMMARY_PREFIX}\n"
        f"{summary}"
    )


def _step_output_wiki_carry_body(
    building_root: Path,
    step_output_ref: str,
    forward_fields: tuple[str, ...] = (),
) -> str | None:
    """Read the step-output and return its compact wiki VIEW (or None if absent).

    ``forward_fields`` is the UPSTREAM step's declared carries_forward_fields;
    when non-empty the inline summary is FILTERED to that handoff subset.
    """

    body = _step_output_body_from_file(building_root, step_output_ref)
    if body is None:
        return None
    return _wiki_carry_view(building_root, step_output_ref, body, forward_fields)


def wiki_carry_summary_text(view: str) -> str | None:
    """Recover the SUMMARY section from a carried wiki view (checker/consumer aid).

    Returns the summary text (the serialized ``returned``) when ``view`` is a
    wiki-carry view, else None. Consumers that need the structured ``returned``
    JSON parse this summary; they MUST NOT expect the full step-output envelope
    to be inline.

    ORDER-INDEPENDENT: this scans for the SUMMARY_PREFIX line and captures every
    line AFTER it. In the current layout the SUMMARY is LAST (PATH + NOTE lead),
    so capture runs to the end of the view; the ``startswith(PATH_PREFIX)`` break
    is a defensive guard kept so an older layout (summary before path) is parsed
    identically. Either way the summary is delimited by its own PREFIX line, not
    by position.
    """

    if not view.startswith(_WIKI_CARRY_VIEW_HEADER):
        return None
    lines = view.splitlines()
    summary_lines: list[str] = []
    capturing = False
    for line in lines:
        if not capturing:
            if line == _WIKI_CARRY_SUMMARY_PREFIX:
                capturing = True
            continue
        if line.startswith(_WIKI_CARRY_PATH_PREFIX):
            break
        summary_lines.append(line)
    if not summary_lines:
        return None
    return "\n".join(summary_lines).strip()


def wiki_carry_path_text(view: str) -> str | None:
    """Recover the absolute step-output PATH from a carried wiki view."""

    if not view.startswith(_WIKI_CARRY_VIEW_HEADER):
        return None
    for line in view.splitlines():
        if line.startswith(_WIKI_CARRY_PATH_PREFIX):
            return line[len(_WIKI_CARRY_PATH_PREFIX):].strip()
    return None


# ---------------------------------------------------------------------------
# MAIL-REPAIR (Smith rulings 0611, B1/B2/B3): runtime rows ride the mail.
#
# The mailbox assembler previously read PLAN-DECLARED rows only
# (_incoming_link_handoff_refs); runtime rows -- the transition concern the
# gate ADOPTED for a reroute, and the human/COO disposition row of a resume --
# never reached the redo workers' agent inputs (b5b measured RED: runtime
# concern.reason_refs markers arrived in 0/10 redo inputs while declared refs
# arrived in all). The repair is ONE assembler widening: an adopted reroute's
# appended queue items carry a ``runtime_handoffs`` packet section built by
# READING THE RECORDED ROW BACK FROM THE LEDGER (the written
# transition-concern.json step-output document), never from memory, so replay
# reads the recorded fact and the packet stamps provenance (which runtime row
# fed it: row ref + kind + recorded residence). ADDRESSES ONLY ride (refs; no
# bodies, no free text).
#
# B3 (narrow, fail-closed): ONLY two runtime rows are truck-eligible --
#   (1) the transition concern ADOPTED by the gate for THIS reroute (its
#       mandatory reason_refs), and
#   (2) the disposition row of THIS resume (its reason_refs, raise lane).
# Nothing else rides (no speculative/unadopted rows; the gate-sequence
# reroute adopts a DECLARED policy action row, not a runtime row, so it
# carries no runtime mail).
#
# B1 (broken ticket, fails-closed): an address that claims a ledger residence
# (step-output form) but has no document, or an adopted concern row whose
# recorded ledger document is missing/mismatched, must NOT be silently
# delivered -> the walk HOLDs via the EXISTING hold machinery (loud
# hold_reason; no new Movement vocabulary).
#
# ζ7 unchanged: support delivers recorded addresses and records; it authors no
# route, Movement, success, or quality.
# ---------------------------------------------------------------------------

