"""POSITION-A native-dispatch open/close recording seam (P3d concern module).

Records a NATIVE subagent dispatch as a Brick Building reusing the existing
evidence writers: open() records received_work, close() records the returned
payload + a COMPUTED Link gate. It does NOT launch the subagent, walk a plan,
call the agent_adapter, or run any CLI; it records only. Crosses to Agent
(performer-lane word) and Link (movement/transition fact builders) via the
canonical NATIVE_DISPATCH_PERFORMANCE_MODE / make_movement_fact / make_transition_fact
contracts; it authors no Movement and judges no success or quality."""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from brick_protocol.agent.performance import NATIVE_DISPATCH_PERFORMANCE_MODE
from brick_protocol.link.movement import MOVEMENT_LITERALS

from brick_protocol.support.operator.building_operation_common import (
    DEFAULT_BUILDINGS_ROOT,
    _clean_text,
)
from brick_protocol.support.operator.primitives import (
    _AGENT_OBJECT_ALLOWED_KEYS,
    _AGENT_OBJECT_REF_FIELDS,
)


NATIVE_DISPATCH_EXECUTION_PATH = NATIVE_DISPATCH_PERFORMANCE_MODE


NATIVE_DISPATCH_DEFAULT_GATE_REFS: tuple[str, ...] = ("link-gate:default-transition",)


NATIVE_DISPATCH_PROOF_LIMITS: tuple[str, ...] = (
    "native-dispatch support evidence only",
    "support recorded a native subagent dispatch; support did not launch it",
    "gate sufficiency is the Link rule computation over the supplied return",
    "not source truth",
    "not success judgment",
    "not quality judgment",
    "not Movement authority",
)


# ============================================================================
# FORCED-WHEN-IN-A-BRICK native-dispatch context.
#
# B1 (voluntary) keyed recording on a per-prompt ``BRICK-TRACK:<id>`` marker the
# agent had to type. This makes recording CONTEXT-driven instead: a single
# active "brick context" persisted at a fixed path turns recording ON. While the
# context is SET, EVERY native Agent-tool child spawn auto-records as a child
# native-dispatch Building (the open/close hooks read the context; the agent
# cannot opt out and no per-prompt marker is needed). While it is CLEARED, the
# hooks NO-OP, so ordinary dev subagents make no recording noise.
#
# "브릭은 브릭을 부를 때만 진행": the context turns ON only when a brick is
# explicitly entered (set_brick_context) and OFF when it is left
# (clear_brick_context). CHOICE of subagent/workflow/self stays FREE; only the
# RECORDING-while-in-a-brick is forced.
#
# This is support MECHANICS (a fixed-path JSON record), not source truth, not a
# Movement chooser, and not a success/quality judgment.
#
# Proof limits / out-of-scope (documented, not solved here):
#   - SINGLE active context only. NESTED brick contexts (a brick entered while
#     another is already active) are OUT OF SCOPE: set overwrites, clear removes
#     the one record. A nested model would need a stack, not this single file.
#   - CONCURRENCY across sessions is OUT OF SCOPE: two sessions sharing this one
#     fixed path would race. A single-operator, single-active-brick model is
#     assumed. No file lock is taken.
# ============================================================================

# Fixed path for the single active brick context. The env override exists ONLY so
# a test/probe can redirect it off the shared default; live use leaves it unset.
_BRICK_CONTEXT_DEFAULT_PATH = os.path.join("/tmp", "brick-native-dispatch-context.json")


def _brick_context_path() -> str:
    """Resolve the single-active brick-context file path (env-overridable seam)."""
    override = os.environ.get("BRICK_NATIVE_DISPATCH_CONTEXT_PATH")
    return override if override else _BRICK_CONTEXT_DEFAULT_PATH


def set_brick_context(building_id: str, parent_step_ref: str = "") -> dict[str, str]:
    """Turn the brick context ON: persist {building_id, parent_step_ref}.

    Called when a brick is explicitly ENTERED. While this record exists, the
    native-dispatch open/close hooks FORCE-record every child Agent-tool spawn as
    a child native-dispatch Building. SINGLE active context: a second call
    overwrites the first (nested contexts are out of scope -- see module note).

    Returns the written record. ``building_id`` must be a non-empty string;
    ``parent_step_ref`` is optional (defaults to "").
    """
    if not isinstance(building_id, str) or not building_id.strip():
        raise ValueError("set_brick_context requires a non-empty building_id")
    step = parent_step_ref.strip() if isinstance(parent_step_ref, str) else ""
    record = {"building_id": building_id.strip(), "parent_step_ref": step}
    path = _brick_context_path()
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(record, fh)
    return record


def clear_brick_context() -> bool:
    """Turn the brick context OFF: remove the active-context record.

    Called when a brick is LEFT. After this, the open/close hooks NO-OP (no
    recording) so ordinary dev subagents make no noise. Idempotent: returns True
    if a record was removed, False if none existed.
    """
    path = _brick_context_path()
    try:
        os.remove(path)
        return True
    except FileNotFoundError:
        return False


def read_brick_context() -> dict[str, str] | None:
    """Read the single active brick context, or None if not in a brick.

    Returns ``{"building_id": <str>, "parent_step_ref": <str>}`` when a context
    is set, else ``None`` (no record / unreadable / malformed). A malformed or
    building_id-less record reads as None (fail to NO-OP, never to a forged
    recording): a recording-trigger must never fire on garbage.
    """
    path = _brick_context_path()
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (FileNotFoundError, ValueError, OSError):
        return None
    if not isinstance(data, dict):
        return None
    building_id = data.get("building_id")
    if not isinstance(building_id, str) or not building_id.strip():
        return None
    step = data.get("parent_step_ref", "")
    if not isinstance(step, str):
        step = ""
    return {"building_id": building_id.strip(), "parent_step_ref": step.strip()}


def native_dispatch_child_building_id(building_id: str, prompt: str) -> str:
    """Derive a DETERMINISTIC child building id from the parent + this spawn.

    The PreToolUse open and PostToolUse close hooks each see the same
    ``tool_input.prompt`` but share NO per-call correlation id, so they must
    agree on the child id from inputs alone. A stable sha256 over
    ``building_id + prompt`` gives an id both hooks recompute identically (no
    random/time component). Same context + same prompt -> same child id.
    """
    digest = hashlib.sha256(f"{building_id}{prompt}".encode("utf-8")).hexdigest()[:16]
    return f"{building_id}-child-{digest}"


# ============================================================================
# HARNESS-PAYLOAD boundary (B4-REPAIR defect 1, 0611).
#
# The close hooks receive the harness's RAW Agent tool-result payload (Claude
# Code PostToolUse tool_result/tool_response). That payload is a TRANSPORT
# ENVELOPE: alongside the subagent's returned content it carries harness
# metadata keys the recording machinery does not consume ('status', durations,
# token counts, usage, ...). 'status' is in RETURNED_FORBIDDEN_KEYS, so feeding
# the raw envelope into close_native_dispatch_brick(returned=...) made EVERY
# hook-driven close fail (B4 0611: ValueError "returned_value contains
# forbidden key 'status'") -- children stayed open-only, handles accumulated.
#
# SEAM DECISION (which side is tolerant): the closed key set
# (agent.return_fact.RETURNED_FORBIDDEN_KEYS, enforced at
# support/operator/run.py complete_agent_run_from_prepared) guards AXIS
# semantics -- an Agent RETURN RECORD must never carry verdict / movement /
# secret keys -- and it stays CLOSED, untouched. What gets the tolerance is the
# HARNESS ENVELOPE only, at this explicit extraction boundary: known content
# keys are consumed; unknown envelope keys are IGNORED (names reported to the
# caller for its logfile) or, when no content key is recognized at all, the
# WHOLE envelope is preserved as ONE raw JSON string (a string carries no keys,
# so nothing is lost and nothing can trip a key guard). This mirrors the
# engine's own provider boundary (connection/agent_adapter: declared fields are
# lifted from raw CLI output, forbidden keys stripped upstream AND re-checked
# downstream). Crucially the AGENT'S OWN structured return (a Mapping under a
# content key) passes through UNCHANGED, so a subagent return that itself
# smuggles 'status'/'success'/... still rejects downstream: the tolerance never
# opens the closed set, it only stops the transport wrapper from being recorded
# as if the agent had returned it.
# ============================================================================

# Known harness CONTENT keys, in consumption priority order: the subagent's
# actual returned content lives under ONE of these in an Agent tool-result
# envelope ("output" first for parity with the previous hook behaviour). Every
# OTHER top-level envelope key is transport metadata and is not consumed.
NATIVE_DISPATCH_HARNESS_CONTENT_KEYS: tuple[str, ...] = (
    "output",
    "result",
    "content",
    "text",
)


def returned_value_from_harness_payload(payload: Any) -> tuple[Any, tuple[str, ...]]:
    """Extract the subagent's returned content from a harness tool-result envelope.

    Returns ``(returned_value, unconsumed_envelope_keys)``:

      - ``payload`` not a Mapping (already a plain return: str/None/...) -> as-is,
        no unconsumed keys. A bare list is treated as a content-block list.
      - Mapping WITH a known content key (NATIVE_DISPATCH_HARNESS_CONTENT_KEYS,
        first match wins): that value is the return -- a str passes verbatim, a
        content-block list is joined to text, a Mapping passes through UNCHANGED
        (it is the agent's structured return; the closed RETURNED_FORBIDDEN_KEYS
        validation downstream still applies in full). The OTHER top-level keys
        are the unconsumed envelope metadata: ignored, names returned so the
        hook can log them.
      - Mapping with NO known content key: the whole envelope is preserved as
        ONE raw JSON string (mechanical, sort_keys, default=repr) so the close
        can always complete without opening any closed key set; all top-level
        key names are reported as unconsumed.

    Support records facts; it does not fail on transport metadata it never
    consumes. No Movement, no success/quality judgment is read or derived here.
    """

    if not isinstance(payload, Mapping):
        if isinstance(payload, (list, tuple)):
            return _harness_content_value(list(payload)), ()
        return payload, ()
    for key in NATIVE_DISPATCH_HARNESS_CONTENT_KEYS:
        if key in payload:
            unconsumed = tuple(str(k) for k in payload.keys() if k != key)
            return _harness_content_value(payload[key]), unconsumed
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=repr),
        tuple(str(k) for k in payload.keys()),
    )


def _harness_content_value(value: Any) -> Any:
    """Normalize ONE harness content value mechanically (no judgment).

    str -> verbatim. Content-block list -> joined text (block["text"] when it is
    a text block, a bare str block verbatim, any other block as raw JSON text).
    Mapping or anything else -> UNCHANGED: a Mapping here is the agent's own
    structured return and must still face the closed downstream validation.
    """

    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        parts: list[str] = []
        for block in value:
            if isinstance(block, Mapping) and isinstance(block.get("text"), str):
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
            else:
                parts.append(
                    json.dumps(block, ensure_ascii=False, sort_keys=True, default=repr)
                )
        return "\n".join(parts)
    return value


# Agent Object REFS authorized to RECORD a non-forward Movement (reroute) on the
# native-dispatch close seam. Reroute is a CoO/Link authority act (see
# route_materialization.ALLOWED_AUTHOR_PREFIXES: human:/coo:). Lane CANNOT
# distinguish the authorized author: coo AND all four *-lead agents
# (cto/pm/design/qa-lead) share lane="leader", but team-leads return
# observed-only and must NOT author Movement -- only the CoO does. So the guard
# keys on the ORIGINATING agent_object_ref, not the lane. forward by ANY ref is
# fine (it is the default, no-authority path). This is a support GUARD that
# records the basis, not a new authority: support still authors no Movement and
# judges no success/quality.
NATIVE_DISPATCH_MOVEMENT_AUTHORIZED_REFS: frozenset[str] = frozenset({"agent-object:coo"})


# The Brick comparison at close is COMPUTED from the return
# (BrickComparisonFact.from_returned_value), NEVER a caller-supplied observation.
# A caller-supplied comparison_observation is REJECTED outright: the gate
# sufficiency is driven by `missing_return_fields` parsed from
# `comparison_evidence` (brick/comparison.py + link/gate.py), so honoring ANY
# caller comparison_observation (not just observed_match_kind) would let the
# caller forge a sufficiency verdict (e.g. comparison_evidence carrying
# "missing_return_fields: none" over a return that is actually missing required
# fields). Native close therefore computes the comparison from the return only.
NATIVE_DISPATCH_MOVEMENT_AUTHORITY_PROOF_LIMIT: str = (
    "orchestration/Movement authority is user/Link-owned; support records only"
)


# Agent-object key/ref field-sets are SINGLE-SOURCED on the Agent axis
# (support/operator/primitives.py, derived from CASTING_FIELDS) and IMPORTED here
# rather than re-enumerated. The prior local copies OMITTED the casting keys
# (preferred_adapter_ref / preferred_model_ref), so the unknown-key check below
# RAISED on a real role Agent Object that legitimately carries casting -- a live
# latent bug. Importing the canonical allowlist (which includes the casting keys)
# both FIXES that bug and removes a 3rd mirror of the Agent-object field-set
# (E2 / S1, mirror M8; field_set_registry.yaml enforces this stays single-source).
# The ref-field coercion below loops ``("callable_performer_refs", *_AGENT_OBJECT_REF_FIELDS)``
# to preserve the prior behavior (callable_performer_refs was coerced as a text
# array too); the canonical resolver does the same (agent_resources._load_agent_object).


_NATIVE_DISPATCH_FORBIDDEN_AGENT_OBJECT_KEYS = frozenset(
    {
        "provider_connector_refs",
        "provider_request_body",
        "credential_body",
        "setup_token",
        "setup_token_value",
        "session_id",
        "provider_session_id",
        "agent_fact_shape",
        "agentfact_shape",
        "success",
        "failure",
        "quality",
        "movement_choice",
        "choose_movement",
        "default_gatefact",
        "default_gate_fact",
    }
)


@dataclass(frozen=True)
class NativeDispatchBrickHandle:
    """Open-state handle the caller keeps between open() and close().

    Carries the declared Brick work and Agent Object binding so close() can
    rebuild the exact same single-step preparation and record the returned
    payload. It carries no provider state, no session, and no secret.
    """

    building_id: str
    step_ref: str
    brick_instance_ref: str
    next_brick_instance_ref: str
    agent_object_ref: str
    work_statement: str
    received_work: str
    required_return_shape: str
    comparison_rule: str
    source_facts: tuple[str, ...]
    declared_gate_refs: tuple[str, ...]
    target_ref: str
    agent_object: Mapping[str, Any]
    output_root: str
    task_source_ref: str
    proof_limits: tuple[str, ...]
    written_files: tuple[str, ...] = field(default_factory=tuple)
    # Optional PLAIN provenance record (B2a): when this child Building was opened
    # by a PARENT orchestration step, this maps the parent {building_id, step_ref}.
    # It is a record-only edge: it carries NO Movement, NO success/quality, NO
    # adoption. ``None`` = a normal standalone native dispatch (no parent).
    parent_orchestration_ref: Mapping[str, str] | None = None


def open_native_dispatch_brick(
    *,
    building_id: str,
    received_work: str,
    required_return_shape: str,
    agent_object_ref: str,
    work_statement: str = "",
    comparison_rule: str = "",
    source_facts: Sequence[str] = (),
    declared_gate_refs: Sequence[str] = NATIVE_DISPATCH_DEFAULT_GATE_REFS,
    target_ref: str = "",
    agent_object: Mapping[str, Any] | None = None,
    output_root: Path | str = DEFAULT_BUILDINGS_ROOT,
    overwrite_existing: bool = False,
    task_source_ref: str = "",
    proof_limits: Sequence[str] = NATIVE_DISPATCH_PROOF_LIMITS,
    parent_building_id: str = "",
    parent_step_ref: str = "",
) -> NativeDispatchBrickHandle:
    """Open a Brick Building for one native subagent dispatch.

    Writes the task, the Brick work_contract (work/building-work.json), and a
    brick_opened capture event into buildings/<building_id>/, recording
    execution_path="native-dispatch" as a plain record field. Returns a handle
    the caller keeps; the caller then dispatches the subagent NATIVELY and
    passes the returned payload to close_native_dispatch_brick().

    This function does not launch the subagent, call the agent_adapter, or run
    any CLI.

    B2a parent-child orchestration link (record-only): when BOTH
    ``parent_building_id`` and ``parent_step_ref`` are non-empty, a PLAIN
    provenance record ``parent_orchestration_ref = {parent_building_id,
    parent_step_ref}`` is injected into the CHILD's recorded Brick work record
    (work/building-work.json). It carries NO Movement, NO success/quality, and NO
    adoption -- it only records WHICH parent step dispatched this child. Supplying
    NEITHER is a normal standalone dispatch (unchanged). Supplying EXACTLY ONE
    (one empty, one not) is an ORPHAN and is rejected fail-closed.
    """

    from support.operator.run import prepare_agent_run_from_step_rows  # noqa: PLC0415
    from support.recording.capture import (  # noqa: PLC0415
        BuildingLifecyclePacket,
        CaptureEvent,
        write_building_lifecycle,
    )

    building_id_text = _clean_text("building_id", building_id)
    received_work_text = _clean_text("received_work", received_work)
    parent_orchestration_ref = _native_dispatch_parent_orchestration_ref(
        parent_building_id, parent_step_ref
    )
    statement = work_statement.strip() if isinstance(work_statement, str) else ""
    statement = statement or received_work_text
    checked_proof_limits = _native_dispatch_proof_limits(proof_limits)
    fixture = _native_dispatch_step_fixture(
        building_id=building_id_text,
        received_work=received_work_text,
        work_statement=statement,
        required_return_shape=required_return_shape,
        comparison_rule=comparison_rule,
        source_facts=source_facts,
        agent_object_ref=agent_object_ref,
        agent_object=agent_object,
        declared_gate_refs=declared_gate_refs,
        target_ref=target_ref,
        task_source_ref=task_source_ref,
        proof_limits=checked_proof_limits,
    )
    prepared = prepare_agent_run_from_step_rows(fixture, proof_limits=checked_proof_limits)
    raw_ref = prepared.raw_refs[0] if prepared.raw_refs else f"raw:{building_id_text}:native-dispatch"
    not_proven = list(prepared.not_proven)
    building_work: dict[str, Any] = {
        "work_statement": prepared.brick_work.work_statement,
        "comparison_rule": prepared.brick_work.comparison_rule,
        "required_return_shape": prepared.brick_work.required_return_shape,
        "source_facts": list(prepared.brick_work.source_facts),
        "building_id": building_id_text,
        "step_refs": [prepared.step_rows.step_ref],
        "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
        "open_state": "received_work_recorded_awaiting_native_return",
        "proof_limits": list(checked_proof_limits),
        "not_proven": not_proven,
    }
    if task_source_ref.strip():
        building_work["task_source_ref"] = task_source_ref.strip()
    if parent_orchestration_ref is not None:
        # PLAIN provenance edge to the parent orchestration step. Record-only:
        # no Movement, no success/quality, no adoption. Extra building_work keys
        # are admitted by capture._require_fact_keys (a must-contain check, not an
        # exact-set check); building_work already carries building_id/step_refs/
        # execution_path beyond the required BRICK_WORK_KEYS.
        building_work["parent_orchestration_ref"] = dict(parent_orchestration_ref)
    capture_events = (
        CaptureEvent(
            event_id="native-dispatch-building-opened",
            event_type="building_opened",
            role_in_event="operator",
            axis_attribution="Support residue",
            raw_ref=raw_ref,
            not_proven=tuple(not_proven),
            building_ref=building_id_text,
            receipt_text="Building evidence root opened for a native subagent dispatch",
            facts={
                "work_ref": "work/building-work.json",
                "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
            },
        ),
        CaptureEvent(
            event_id="native-dispatch-brick-opened",
            event_type="brick_opened",
            role_in_event="work_author",
            axis_attribution="Brick",
            raw_ref=raw_ref,
            not_proven=tuple(not_proven),
            brick_ref=prepared.brick_instance_ref,
            receipt_text="Brick work was opened before the native subagent received it",
            facts={
                "work_statement": prepared.brick_work.work_statement,
                "comparison_rule": prepared.brick_work.comparison_rule,
                "required_return_shape": prepared.brick_work.required_return_shape,
                "source_facts": list(prepared.brick_work.source_facts),
            },
        ),
        CaptureEvent(
            event_id="native-dispatch-execution-path",
            event_type="support_note",
            role_in_event="support_writer",
            axis_attribution="Support residue",
            raw_ref=raw_ref,
            not_proven=tuple(not_proven),
            receipt_text=(
                "execution_path=native-dispatch: the main agent launches the "
                "subagent natively; support did not go through run.py's plan walk"
            ),
            facts={
                "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
                "agent_object_ref": prepared.agent_object.object_ref,
            },
        ),
    )
    lifecycle_packet = BuildingLifecyclePacket(
        building_id=building_id_text,
        building_work=building_work,
        capture_events=capture_events,
        raw_manifest={
            "building_id": building_id_text,
            "raw_refs": [raw_ref],
            "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
            "entries": [{"raw_ref": raw_ref, "raw_refs": [raw_ref]}],
        },
        evidence_manifest={
            "building_id": building_id_text,
            "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
            "open_state": "received_work_recorded_awaiting_native_return",
            "building_work_ref": "work/building-work.json",
            "proof_limits": list(checked_proof_limits),
            "not_proven": list(_manifest_native_not_proven(not_proven)),
        },
        proof_limits=tuple(checked_proof_limits),
    )
    lifecycle_write = write_building_lifecycle(
        lifecycle_packet,
        output_root=output_root,
        overwrite_existing=overwrite_existing,
    )
    task_path = lifecycle_write.root / "work" / "task.md"
    _write_native_dispatch_task(
        task_path,
        building_id=building_id_text,
        received_work=received_work_text,
        work_statement=prepared.brick_work.work_statement,
        required_return_shape=prepared.brick_work.required_return_shape,
        agent_object_ref=prepared.agent_object.object_ref,
        declared_gate_refs=fixture["step_rows"]["rows"][2].get("declared_gate_refs", ()),
        proof_limits=checked_proof_limits,
    )
    written = tuple(str(path) for path in (*lifecycle_write.written_files, task_path))
    return NativeDispatchBrickHandle(
        building_id=building_id_text,
        step_ref=prepared.step_rows.step_ref,
        brick_instance_ref=prepared.brick_instance_ref,
        next_brick_instance_ref=prepared.next_brick_instance_ref,
        agent_object_ref=prepared.agent_object.object_ref,
        work_statement=prepared.brick_work.work_statement,
        received_work=received_work_text,
        required_return_shape=prepared.brick_work.required_return_shape,
        comparison_rule=prepared.brick_work.comparison_rule,
        source_facts=tuple(prepared.brick_work.source_facts),
        declared_gate_refs=tuple(fixture["step_rows"]["rows"][2].get("declared_gate_refs", ())),
        target_ref=str(fixture["step_rows"]["rows"][2].get("target_ref", "")),
        agent_object=dict(fixture["agent_objects"][prepared.agent_object.object_ref]),
        output_root=str(output_root),
        task_source_ref=task_source_ref.strip(),
        proof_limits=tuple(checked_proof_limits),
        written_files=written,
        parent_orchestration_ref=parent_orchestration_ref,
    )


def close_native_dispatch_brick(
    handle: NativeDispatchBrickHandle,
    *,
    returned: Any,
    movement: str = "forward",
    movement_reason: str = "",
    overwrite_existing: bool = True,
    comparison_observation: Mapping[str, Any] | None = None,
    route_decision_basis: Sequence[str] = (),
    proof_limits: Sequence[str] | None = None,
) -> Mapping[str, Any]:
    """Close a native-dispatch Brick Building from the supplied return payload.

    Builds AgentFact(received_work, returned); computes the ζ1 Brick comparison
    (BrickComparisonFact.from_returned_value) and the ζ2 Link movement gate
    (evaluate_declared_movement_gate) as the COMPUTED measurement; then writes
    claim_trace + step-output + closure + building-map by reusing
    write_accumulated_building_evidence, so the produced buildings/<id>/ evidence
    has the SAME shape as a run.py-produced Building plus the native-dispatch
    marker. The gate verdict is computed by the Link rule, never a hardcoded pass.

    'returned' is supplied by the caller (the natively dispatched subagent's
    output). This function does not launch the subagent or call any adapter/CLI.

    The Brick comparison is COMPUTED from `returned`; ANY caller-supplied
    comparison_observation is REJECTED (fail-closed) so no caller can forge a
    sufficiency verdict (the gate sufficiency is driven by missing_return_fields
    parsed from comparison_evidence, not by observed_match_kind, so rejecting the
    whole observation -- not just observed_match_kind -- is required). A
    non-forward Movement (reroute) is a CoO/Link authority act: it requires a
    non-empty route_decision_basis (human/Link decision refs) AND that the
    originating agent_object_ref is agent-object:coo (lane cannot distinguish coo
    from the *-lead agents, which also share lane="leader" but must NOT author
    Movement); forward by any ref is fine. The caller_lane + route_decision_basis
    are recorded into the movement reason so the recorded Movement is auditable.
    """

    if not isinstance(handle, NativeDispatchBrickHandle):
        raise TypeError("handle must be a NativeDispatchBrickHandle from open_native_dispatch_brick")

    from support.operator.run import (  # noqa: PLC0415
        complete_agent_run_from_prepared,
        prepare_agent_run_from_step_rows,
    )
    from support.operator.evidence_assembly import write_accumulated_building_evidence  # noqa: PLC0415
    from support.operator.contracts import BuildingRunSupportResult  # noqa: PLC0415
    from support.connection.agent_adapter import AgentAdapterRequest, AgentAdapterResult  # noqa: PLC0415
    from brick_protocol.link.movement import make_movement_fact  # noqa: PLC0415
    from brick_protocol.link.transition import make_transition_fact  # noqa: PLC0415

    movement_text = _clean_text("movement", movement)
    if movement_text not in MOVEMENT_LITERALS:
        raise ValueError("native-dispatch close movement must be forward or reroute")

    # FIX A (forced verdict): the native-dispatch Brick comparison is COMPUTED
    # from the return (the from_returned_value path inside
    # complete_agent_run_from_prepared, taken ONLY when comparison_observation is
    # None). The Link gate sufficiency is driven by `missing_return_fields` parsed
    # from `comparison_evidence` (brick/comparison.py + link/gate.py), NOT by
    # observed_match_kind. A caller passing ANY comparison_observation could forge
    # a sufficiency verdict -- e.g. comparison_evidence=["missing_return_fields:
    # none"] over a return actually missing required fields yields a forced
    # "sufficient" gate (= support authoring a Movement-enabling verdict, an axis
    # violation). Rejecting only observed_match_kind was insufficient. Reject ANY
    # non-None comparison_observation fail-closed, and pass None below so the
    # COMPUTED-from-return path always runs.
    if comparison_observation is not None:
        raise ValueError(
            "native-dispatch close computes the Brick comparison from the "
            "return; caller comparison_observation is not admitted"
        )

    # FIX B (smuggled Movement): reroute is a CoO/Link authority act. Require a
    # basis AND that the ORIGINATING agent_object_ref is the CoO. Lane CANNOT
    # gate this: coo AND every *-lead share lane="leader", but only the CoO
    # authors Movement; a team-lead (cto/pm/design/qa-lead) returns observed-only.
    # So compare the REF, not the lane. The cleaned ref is the handle's
    # agent_object_ref (already validated agent-object:* at open). caller_lane is
    # still resolved -- for the AUDIT record only (recorded into the movement
    # reason + returned), not for the authority decision. forward by any ref is
    # the no-authority default path; the ref check only runs (and only fails
    # closed) on a non-forward Movement.
    cleaned_route_decision_basis = tuple(
        text for text in (str(item).strip() for item in route_decision_basis) if text
    )
    caller_ref = _clean_text("agent_object_ref", handle.agent_object_ref)
    caller_lane = _native_dispatch_caller_authority_lane(handle.agent_object_ref)
    if movement_text != "forward":
        if not cleaned_route_decision_basis:
            raise ValueError(
                "native-dispatch reroute requires route_decision_basis "
                "(human/Link decision)"
            )
        if caller_ref not in NATIVE_DISPATCH_MOVEMENT_AUTHORIZED_REFS:
            raise ValueError(
                "native-dispatch reroute is a CoO/Link authority act; caller ref "
                f"{caller_ref!r} is not authorized to record a Movement "
                "(authorized refs: "
                + ", ".join(sorted(NATIVE_DISPATCH_MOVEMENT_AUTHORIZED_REFS))
                + ")"
            )

    base_proof_limits = (
        _native_dispatch_proof_limits(proof_limits)
        if proof_limits is not None
        else tuple(handle.proof_limits)
    )
    checked_proof_limits = base_proof_limits
    if NATIVE_DISPATCH_MOVEMENT_AUTHORITY_PROOF_LIMIT not in checked_proof_limits:
        checked_proof_limits = (
            *checked_proof_limits,
            NATIVE_DISPATCH_MOVEMENT_AUTHORITY_PROOF_LIMIT,
        )
    fixture = _native_dispatch_step_fixture(
        building_id=handle.building_id,
        received_work=handle.received_work,
        work_statement=handle.work_statement,
        required_return_shape=handle.required_return_shape,
        comparison_rule=handle.comparison_rule,
        source_facts=handle.source_facts,
        agent_object_ref=handle.agent_object_ref,
        agent_object=handle.agent_object,
        declared_gate_refs=handle.declared_gate_refs,
        target_ref=handle.target_ref,
        task_source_ref=handle.task_source_ref,
        proof_limits=checked_proof_limits,
    )
    prepared = prepare_agent_run_from_step_rows(fixture, proof_limits=checked_proof_limits)
    target_fact = f"brick:{prepared.next_brick_instance_ref}"
    movement_fact_reason = (
        movement_reason.strip()
        or "native subagent dispatch recorded; Link Movement declared by caller"
    )
    if movement_text != "forward":
        # Record the authority BASIS into the movement reason so the recorded
        # reroute is auditable (caller_lane + the human/Link decision refs).
        movement_fact_reason = (
            f"{movement_fact_reason}; caller_lane={caller_lane}; "
            "route_decision_basis="
            + ", ".join(cleaned_route_decision_basis)
        )
    link_fact = make_movement_fact(
        movement_text,
        reason=movement_fact_reason,
        handoff_target_fact=target_fact,
    )
    transition_fact = make_transition_fact(
        movement_text,
        target_fact=target_fact,
        handoff_reference=f"native-dispatch:{prepared.building_id}:{prepared.step_rows.step_ref}",
    )
    completion = complete_agent_run_from_prepared(
        prepared,
        returned_value=returned,
        adapter_result=None,
        link_fact=link_fact,
        transition_fact=transition_fact,
        # ALWAYS None: the Brick comparison is COMPUTED from `returned`
        # (from_returned_value). Any caller comparison_observation was already
        # rejected above (FIX A); passing None here guarantees the computed path.
        comparison_observation=None,
        proof_limits=checked_proof_limits,
    )
    movement_gate_fact = completion.crossing_record.movement_gate_fact
    if movement_gate_fact is None:
        raise ValueError(
            "native-dispatch close requires declared_gate_refs so the Link gate "
            "computes a sufficiency verdict; none was produced"
        )
    # Synthetic adapter record carries ONLY the caller-supplied native return so
    # the existing accumulated writers can emit the canonical agent-return raw
    # stream and claim trace. adapter_ref="adapter:local" is a placeholder for
    # the data container; connect_agent_brain is never called, no CLI launches.
    adapter_request = AgentAdapterRequest(
        building_id=prepared.building_id,
        agent_object_ref=prepared.agent_object.object_ref,
        adapter_ref="adapter:local",
        brick_instance_ref=prepared.brick_instance_ref,
        next_brick_instance_ref=prepared.next_brick_instance_ref,
        work_statement=prepared.brick_work.work_statement,
        comparison_rule=prepared.brick_work.comparison_rule,
        required_return_shape=prepared.brick_work.required_return_shape,
        proof_limits=tuple(checked_proof_limits),
        not_proven=prepared.not_proven,
    )
    adapter_result = AgentAdapterResult(
        request=adapter_request,
        returned_value=returned,
        proof_limits=tuple(checked_proof_limits),
        not_proven=prepared.not_proven,
    )
    step_result = BuildingRunSupportResult(
        building_id=prepared.building_id,
        preparation=prepared,
        adapter_result=adapter_result,
        completion=completion,
        lifecycle_write=_empty_lifecycle_write(),
        building_map_write=_empty_map_write(),
        written_files=(),
        capture_event_types=(),
        building_map_packet=completion.building_map_packet,
        proof_limits=tuple(checked_proof_limits),
        not_proven=completion.not_proven,
    )
    # The declared plan MUST carry the ONE native-dispatch step under ``steps`` in
    # the SAME shape a run.py single-step plan declares (``{step_ref, rows:[Brick,
    # Agent, Link]}``). declaration_packets copies this into
    # ``declared_plan_copy.steps`` and the Evidence-Spine projector reads it
    # (``_declared_plan_steps`` + per-step BrickInput/AgentBinding). Without it the
    # projector RAISES (declared_plan_copy.steps is not a JSON list). The fixture's
    # ``step_rows`` is exactly that shape and is the SAME rows ``prepare_agent_run_
    # from_step_rows`` already consumed, so the declared step matches the executed
    # step. The Brick-row ``comparison_rule`` is added unconditionally (mirroring the
    # prepared brick work, which is "" when none was supplied) because the spine
    # BrickInput projection requires that field on the declared Brick row.
    native_step = _native_dispatch_declared_step(fixture, prepared)
    # COMPOSITION-MODE STAMP (B4-REPAIR defect 2, 0611): declaration_packets
    # copies the top-level plan ``composition_mode`` into the building-map's
    # ``declaration_provenance``; check_building_declaration_integrity gap 3
    # REJECTS a declared launch-chain root whose provenance records an EMPTY
    # mode, so an unstamped native-dispatch building can never sit green in the
    # repo tree. The literal is SINGLE-SOURCED from the engine's linear stamp
    # (composition.LINEAR_COMPOSITION_MODE -- the same value
    # render_declared_step_template_plan stamps on every caller/COO-declared
    # linear plan): the native-dispatch plan is a one-step caller-declared
    # linear composition (work_statement / agent binding / gate refs are all
    # caller-supplied at open; support only wraps them in the fixed single-step
    # shape), and execution_path="native-dispatch" already distinguishes the
    # path, so no new vocabulary literal is invented here.
    from support.operator.composition import LINEAR_COMPOSITION_MODE  # noqa: PLC0415

    plan: dict[str, Any] = {
        "plan_ref": f"native-dispatch-plan:{prepared.building_id}",
        "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
        "composition_mode": LINEAR_COMPOSITION_MODE,
        "steps": [native_step],
        "proof_limits": list(checked_proof_limits),
        "not_proven": list(prepared.not_proven),
        "raw_refs": list(prepared.raw_refs),
    }
    if handle.task_source_ref:
        plan["task_source_ref"] = handle.task_source_ref
    evidence_write = write_accumulated_building_evidence(
        building_id=prepared.building_id,
        plan_ref=plan["plan_ref"],
        plan=plan,
        step_results=(step_result,),
        output_root=handle.output_root,
        overwrite_existing=overwrite_existing,
        proof_limits=tuple(checked_proof_limits),
    )
    # B2a: write_accumulated_building_evidence REBUILDS work/building-work.json
    # from the step results (lifecycle_emit._accumulated_lifecycle_packet) and
    # does NOT carry arbitrary keys through, so the parent_orchestration_ref that
    # open() injected would be CLOBBERED by the close rewrite. Re-inject the PLAIN
    # provenance record onto the freshly-written record so the CHILD's on-disk
    # work record carries it after close too. Record-only: no Movement, no
    # success/quality, no adoption. Skipped entirely for a standalone dispatch.
    if handle.parent_orchestration_ref is not None:
        _reinject_parent_orchestration_ref(
            evidence_write.lifecycle_write.root,
            handle.parent_orchestration_ref,
        )
    orchestration_packet = {
        "child_building_id": prepared.building_id,
        "gate_sufficiency": movement_gate_fact.sufficiency,
        "parent_orchestration_ref": (
            dict(handle.parent_orchestration_ref)
            if handle.parent_orchestration_ref is not None
            else None
        ),
    }
    return {
        "kind": "native_dispatch_brick_close",
        "building_id": prepared.building_id,
        "building_root": str(evidence_write.lifecycle_write.root),
        "execution_path": NATIVE_DISPATCH_EXECUTION_PATH,
        "movement": link_fact.movement,
        "caller_lane": caller_lane,
        "route_decision_basis": list(cleaned_route_decision_basis),
        "gate_stage": movement_gate_fact.stage,
        "gate_sufficiency": movement_gate_fact.sufficiency,
        "gate_required_public_facts": list(movement_gate_fact.required_public_facts),
        "gate_missing_required_facts": list(movement_gate_fact.missing_required_facts),
        "observed_match_kind": completion.brick_comparison.observed_match_kind,
        # B2a: surfaces the child building id + the COMPUTED gate sufficiency
        # (pulled from the already-computed movement_gate_fact, not recomputed,
        # not hardcoded) + the PLAIN parent provenance record (or None for a
        # standalone dispatch), so a future parent step can consume it.
        "orchestration_packet": orchestration_packet,
        "written_files": [str(path) for path in evidence_write.written_files],
        "capture_event_types": list(evidence_write.capture_event_types),
        "proof_limits": list(checked_proof_limits),
        "not_proven": list(completion.not_proven),
    }


def _reinject_parent_orchestration_ref(
    building_root: Path,
    parent_orchestration_ref: Mapping[str, str],
) -> None:
    """Re-add the PLAIN parent_orchestration_ref onto the closed work record.

    write_accumulated_building_evidence rebuilds work/building-work.json from the
    step results and drops keys it does not know about, so the open()-time
    injection is gone after close. This re-reads that freshly-written graph-ready
    record, adds the one plain provenance key, and rewrites it with the SAME
    canonical serialization the lifecycle writer uses (capture._json_text:
    json.dumps(indent=2, sort_keys=True, ensure_ascii=False) + "\\n"), so the
    graph-ready envelope (@context/@id/CloudEvents fields) is preserved untouched.
    This runs AFTER all writers have returned; nothing re-reads the file in this
    close path, so the post-write patch cannot be clobbered. Record-only: it
    writes a plain {parent_building_id, parent_step_ref} mapping, no Movement,
    no success/quality, no adoption.
    """

    import json  # noqa: PLC0415
    from support.recording.capture import _json_text  # noqa: PLC0415

    work_path = building_root / "work" / "building-work.json"
    record = json.loads(work_path.read_text(encoding="utf-8"))
    record["parent_orchestration_ref"] = dict(parent_orchestration_ref)
    work_path.write_text(_json_text(record), encoding="utf-8")


def _native_dispatch_parent_orchestration_ref(
    parent_building_id: str,
    parent_step_ref: str,
) -> dict[str, str] | None:
    """Resolve the optional B2a parent-child orchestration provenance record.

    Fail-closed ORPHAN rule:
      - NEITHER non-empty  -> None (normal standalone dispatch, unchanged).
      - BOTH non-empty     -> {"parent_building_id", "parent_step_ref"} record.
      - EXACTLY ONE        -> ValueError (orphan: a child cannot point at half a
                              parent step; the edge would be unresolvable).

    The returned record is PLAIN provenance only: it carries no Movement, no
    success/quality, and no adoption. It records WHICH parent step dispatched
    this child, nothing more.
    """

    building = parent_building_id.strip() if isinstance(parent_building_id, str) else ""
    step = parent_step_ref.strip() if isinstance(parent_step_ref, str) else ""
    if not building and not step:
        return None
    if not building or not step:
        raise ValueError(
            "native-dispatch orchestration ref requires BOTH parent_building_id "
            "and parent_step_ref (or neither)"
        )
    return {"parent_building_id": building, "parent_step_ref": step}


def _native_dispatch_declared_step(
    fixture: Mapping[str, Any],
    prepared: Any,
) -> dict[str, Any]:
    """Build the ONE declared plan step for the native-dispatch close.

    Reuses the SAME ``fixture["step_rows"]`` (step_ref + [Brick, Agent, Link] rows)
    that ``prepare_agent_run_from_step_rows`` already consumed, so the declared
    step in ``declared-building-plan.json`` matches the executed step exactly (same
    step_ref / brick_instance_ref). This mirrors a run.py single-step plan step's
    shape (``{step_ref, rows:[...]}``) rather than inventing a new one.

    The only adjustment: the Brick row's ``comparison_rule`` is added
    unconditionally (the fixture omits it when empty, but the Evidence-Spine
    BrickInput projection lists it as a required Brick-row field). The value is the
    PREPARED brick work's comparison_rule (``""`` when none was supplied), which is
    exactly what the comparison computed over, so the declared row stays truthful.
    """

    step_rows = fixture["step_rows"]
    rows: list[dict[str, Any]] = []
    for row in step_rows["rows"]:
        new_row = dict(row)
        if new_row.get("axis") == "Brick" and "comparison_rule" not in new_row:
            new_row["comparison_rule"] = prepared.brick_work.comparison_rule
        rows.append(new_row)
    return {
        "step_ref": step_rows["step_ref"],
        "rows": rows,
    }


def _native_dispatch_step_fixture(
    *,
    building_id: str,
    received_work: str,
    work_statement: str,
    required_return_shape: str,
    comparison_rule: str,
    source_facts: Sequence[str],
    agent_object_ref: str,
    agent_object: Mapping[str, Any] | None,
    declared_gate_refs: Sequence[str],
    target_ref: str,
    task_source_ref: str,
    proof_limits: Sequence[str],
) -> dict[str, Any]:
    object_ref = _clean_text("agent_object_ref", agent_object_ref)
    if not object_ref.startswith("agent-object:"):
        raise ValueError("agent_object_ref must start with agent-object:")
    resolved_object = _native_dispatch_agent_object(object_ref, agent_object)
    step_ref = f"{building_id}-native-dispatch"
    brick_instance_ref = f"brick:{building_id}:native-dispatch"
    next_brick_instance_ref = f"brick:{building_id}:native-dispatch-closed"
    gate_refs = [str(item).strip() for item in declared_gate_refs if str(item).strip()]
    brick_row: dict[str, Any] = {
        "axis": "Brick",
        "row_ref": f"brick-row:{step_ref}",
        "brick_instance_ref": brick_instance_ref,
        "brick_work_ref": "work/building-work.json",
        "work_statement": _clean_text("work_statement", work_statement),
        "required_return_shape": required_return_shape.strip()
        if isinstance(required_return_shape, str)
        else "",
    }
    if isinstance(comparison_rule, str) and comparison_rule.strip():
        brick_row["comparison_rule"] = comparison_rule.strip()
    cleaned_source_facts = [str(item).strip() for item in source_facts if str(item).strip()]
    if cleaned_source_facts:
        brick_row["source_facts"] = cleaned_source_facts
    link_target = target_ref.strip() or f"brick:{next_brick_instance_ref}"
    link_row: dict[str, Any] = {
        "axis": "Link",
        "row_ref": f"link-row:{step_ref}",
        "movement": "forward",
        "target_ref": link_target,
        "next_brick_instance_ref": next_brick_instance_ref,
    }
    if gate_refs:
        link_row["declared_gate_refs"] = gate_refs
    fixture: dict[str, Any] = {
        "building_id": building_id,
        "step_rows": {
            "step_ref": step_ref,
            "rows": [
                brick_row,
                {
                    "axis": "Agent",
                    "row_ref": f"agent-row:{step_ref}",
                    "agent_object_ref": object_ref,
                },
                link_row,
            ],
        },
        "agent_objects": {object_ref: resolved_object},
        "proof_limits": list(proof_limits),
    }
    if task_source_ref.strip():
        fixture["task_source_ref"] = task_source_ref.strip()
    return fixture


def _native_dispatch_caller_authority_lane(agent_object_ref: str) -> str:
    """Resolve the ORIGINATING performer's declared authority lane for the ref.

    handle.agent_object.lane is always the native-dispatch performance mode (the
    dispatch surface, not an authority lane). The real authority lane lives in
    agent/objects/<role>.yaml; resolve it via the canonical Agent-resource
    resolver. If the ref is not an admitted Agent Object (so no declared lane can
    be proven), return the cleaned ref text unchanged: the Movement-authorized-set
    check then rejects it (fail-closed) on a non-forward Movement.
    """

    ref = _clean_text("agent_object_ref", agent_object_ref)
    from support.connection.agent_resources import (  # noqa: PLC0415
        AgentResourceError,
        resolve_agent_object,
    )

    try:
        resolved = resolve_agent_object(ref)
    except AgentResourceError:
        return ref
    # resolve_agent_object returns an agent-resource-resolution packet; the
    # declared authority lane is nested under its "agent_object" mapping.
    agent_object = resolved.get("agent_object")
    if not isinstance(agent_object, Mapping):
        return ref
    lane = str(agent_object.get("lane", "")).strip()
    return lane or ref


def _native_dispatch_agent_object(
    object_ref: str,
    agent_object: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if agent_object is not None:
        resolved = dict(agent_object)
    else:
        resolved = {
            "object_ref": object_ref,
            "name": object_ref.removeprefix("agent-object:"),
            "lane": NATIVE_DISPATCH_PERFORMANCE_MODE,
        }
    resolved.setdefault("object_ref", object_ref)
    if resolved.get("object_ref") != object_ref:
        raise ValueError("agent_object.object_ref must match agent_object_ref")
    resolved.setdefault("name", object_ref.removeprefix("agent-object:"))
    resolved.setdefault("lane", NATIVE_DISPATCH_PERFORMANCE_MODE)
    _validate_native_dispatch_agent_object(resolved)
    return resolved


def _validate_native_dispatch_agent_object(agent_object: dict[str, Any]) -> None:
    forbidden = sorted(set(agent_object) & _NATIVE_DISPATCH_FORBIDDEN_AGENT_OBJECT_KEYS)
    if forbidden:
        raise ValueError("native-dispatch agent_object forbidden keys: " + ", ".join(forbidden))
    unknown = sorted(set(agent_object) - _AGENT_OBJECT_ALLOWED_KEYS)
    if unknown:
        raise ValueError("native-dispatch agent_object unknown keys: " + ", ".join(unknown))
    for key in ("object_ref", "name", "lane"):
        _clean_text(f"agent_object.{key}", agent_object.get(key, ""))
    if agent_object["lane"] != NATIVE_DISPATCH_PERFORMANCE_MODE:
        raise ValueError("native-dispatch agent_object.lane must be native-dispatch")
    for key in ("callable_performer_refs", *_AGENT_OBJECT_REF_FIELDS):
        agent_object[key] = _optional_text_array(f"agent_object.{key}", agent_object.get(key, []))


def _optional_text_array(label: str, value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{label} must be a text array")
    return [_clean_text(f"{label}[]", item) for item in value]


def _native_dispatch_proof_limits(proof_limits: Sequence[str]) -> tuple[str, ...]:
    cleaned: list[str] = []
    for item in proof_limits:
        text = str(item).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    for default in NATIVE_DISPATCH_PROOF_LIMITS:
        if default not in cleaned:
            cleaned.append(default)
    return tuple(cleaned)


def _manifest_native_not_proven(values: Sequence[str]) -> tuple[str, ...]:
    exact = {
        "source truth",
        "success judgment",
        "quality judgment",
        "movement authority",
    }
    adjusted: list[str] = []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text.lower() in exact:
            adjusted.append(f"not proven: {text}")
        else:
            adjusted.append(text)
    return tuple(adjusted)


def _empty_lifecycle_write():
    from support.recording.capture import BuildingLifecycleWriteResult  # noqa: PLC0415

    return BuildingLifecycleWriteResult(root=Path(), written_files=())


def _empty_map_write():
    from support.recording.building_map import BuildingMapWriteResult  # noqa: PLC0415

    return BuildingMapWriteResult(root=Path(), path=Path(), written_files=())


def _write_native_dispatch_task(
    path: Path,
    *,
    building_id: str,
    received_work: str,
    work_statement: str,
    required_return_shape: str,
    agent_object_ref: str,
    declared_gate_refs: Sequence[str],
    proof_limits: Sequence[str],
) -> None:
    gate_line = ", ".join(str(item) for item in declared_gate_refs) or "(none declared)"
    proof_lines = "\n".join(f"- {str(item)}" for item in proof_limits)
    body = (
        f"# Native Dispatch Brick Task: {building_id}\n\n"
        f"execution_path: {NATIVE_DISPATCH_EXECUTION_PATH}\n\n"
        "## Received Work\n\n"
        f"{received_work}\n\n"
        "## Work Statement\n\n"
        f"{work_statement}\n\n"
        "## Required Return Shape\n\n"
        f"{required_return_shape or '(unspecified)'}\n\n"
        "## Agent Object\n\n"
        f"{agent_object_ref}\n\n"
        "## Declared Link Gate Refs\n\n"
        f"{gate_line}\n\n"
        "## Proof Limits\n\n"
        f"{proof_lines}\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
