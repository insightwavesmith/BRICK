"""IMPORTER: post-hoc workflow-result recording verbs (support mechanic only).

WHY (B4 measurement, 0610-0612): the Agent recording hooks fire for DIRECT
subagent spawns (close path repaired, B4-REPAIR 0611) but NOT for agents
spawned INSIDE a harness Workflow -- those go through a harness back door the
Pre/PostToolUse hooks cannot observe (measured verdict: the hooks never ring;
not fixable at the hook). A workflow's substantial work therefore leaves NO
building evidence on its own. This module is the post-hoc channel: the
operator opens a recording building BEFORE a big workflow
(``open_workflow_recording``), runs the workflow (unrecorded), then
``import_workflow_result`` stamps the workflow RESULT into the building as
evidence and drives it to a closed/complete recorded state through the SAME
repaired close seam the mail/native hooks use
(``close_native_dispatch_brick``: envelope-tolerant harness extraction,
COMPUTED Link gate, composition_mode stamped, closed RETURNED_FORBIDDEN_KEYS
unchanged).

HONESTY (hard rule -- the whole point of this module): the harness does NOT
expose per-internal-agent identities/threads for workflow agents. This module
records the workflow as ONE recorded performer act whose raw output is the
workflow's verbatim result (it rides the existing agent-return raw stream in
``raw/``), plus a structured ``workflow_import`` packet on
``work/building-work.json`` recording ONLY what the harness actually provides:
the workflow ref/label, agent_count and token/usage totals IF present,
timestamps IF passed in, the unconsumed envelope key NAMES, and an explicit
"internal agent detail not observable (workflow back door)" note. It NEVER
fabricates per-internal-agent AgentBinding/AgentReceipt rows or claim_trace
entries it has no evidence for -- an honest partial record beats a fabricated
full one.

POST-HOC and EXPLICIT: the operator calls these verbs; nothing here hooks,
polls, or schedules anything (the back door cannot be hooked -- that is the
measured premise).

Support evidence only: records facts, judges nothing. NOT source truth, NOT
success judgment, NOT quality judgment, NOT Movement authority. Owns no axis
crossing and admits no new packet shape on the Brick/Agent/Link axes (the
``workflow_import`` packet is a support record key on the support-owned work
record, like ``parent_orchestration_ref``).
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.operator.native_dispatch import (
    NATIVE_DISPATCH_DEFAULT_GATE_REFS,
    NativeDispatchBrickHandle,
    close_native_dispatch_brick,
    open_native_dispatch_brick,
    returned_value_from_harness_payload,
)
from brick_protocol.support.recording.capture import (
    _json_text,
    buildings_root_for,
)


# The honest boundary, verbatim: this note rides every imported building's
# workflow_import packet. The honesty FIRE case (workflow_import_case) REDs if
# an imported building's packet ever loses it.
WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE = (
    "internal agent detail not observable (workflow back door); "
    "recorded as one performer act"
)

# Importer-specific proof limits, layered ON TOP of the native-dispatch
# defaults (the open/close seam appends its own). They flow into every claim
# trace fact the close writes, so the recorded evidence itself states the
# honesty boundary.
WORKFLOW_IMPORT_PROOF_LIMITS: tuple[str, ...] = (
    "workflow result imported post-hoc by the operator; support recorded the result, not the run",
    WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE,
)

# The ONE recorded performer for an imported workflow result: a synthetic
# Agent Object naming the workflow unit. It claims no declared repo agent
# (brick_protocol/agent/objects/*.yaml) performed the work -- the declared binding the close
# writes is this same ref, self-consistently, and the packet says internal
# detail is not observable. FORCED, not caller-overridable (fabrication fix
# 0612): a caller-supplied "more specific" performer ref would let a careless
# or compromised caller stamp a SPECIFIC performer identity the harness never
# exposed -- one AgentBinding/Receipt/Return (passing the count pin) with a
# fabricated WHO. The importer's premise is that per-internal-agent identity
# is NOT observable through the workflow back door, so the recorded performer
# is ALWAYS this synthetic constant. The FIRE case (workflow_import_case) pins
# the performer ref VALUE in the spine, so a re-introduced override REDs.
WORKFLOW_IMPORT_DEFAULT_AGENT_OBJECT_REF = "agent-object:workflow"

# The support record key the structured packet lives under on
# work/building-work.json (extra keys are admitted on the work record; same
# class as parent_orchestration_ref).
WORKFLOW_IMPORT_PACKET_KEY = "workflow_import"

# USAGE METRIC ALLOWLIST (importer re-review fix 0612, Medium): the aggregate
# token-tally key names a usage mapping may carry. The flat-shape check alone
# admitted ANY non-empty string key with an int value, so a per-agent LABEL
# under a neutral key name the forbidden-key deny-list does not flag (e.g.
# ``{"x_team": 3}``) rode into the recorded packet as per-agent detail --
# contradicting the module's no-per-internal-agent-detail claim. A usage tally
# has a KNOWN vocabulary: the provider usage block's token counters
# (input/output/cache-creation/cache-read) plus the aggregate total the
# importer itself records (``total_tokens``, the envelope ``totalTokens``
# lift). Anything else is rejected loudly, fail-closed -- the operator passes
# clean aggregate totals, and no producer in this repo emits any other usage
# key (the FIRE case and probes emit input_tokens/output_tokens only).
WORKFLOW_IMPORT_USAGE_METRIC_KEYS: frozenset[str] = frozenset(
    {
        "input_tokens",
        "output_tokens",
        "total_tokens",
        "cache_creation_input_tokens",
        "cache_read_input_tokens",
    }
)

# HONESTY GUARD (defense in depth; the FIRE case re-asserts this over the
# on-disk packet): per-internal-agent identity keys the packet must NEVER
# carry. If a future change tries to record per-agent detail the harness does
# not expose, the verb itself refuses before anything is written.
WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS: tuple[str, ...] = (
    "agents",
    "internal_agents",
    "agent_bindings",
    "agent_receipts",
    "agent_ids",
    "agent_threads",
    "agent_sessions",
    "claim_trace",
)

# Harness-envelope TOTALS the importer may lift when the caller did not pass
# them explicitly: (packet_field, envelope_keys, validator). Totals only --
# never per-agent detail. Anything else in the envelope stays an ignored key
# NAME in the packet.
_ENVELOPE_INT_LIFTS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("agent_count", ("agent_count", "agentCount")),
    ("total_tokens", ("totalTokens", "total_tokens")),
)
_ENVELOPE_USAGE_KEYS: tuple[str, ...] = ("usage",)


def open_workflow_recording(
    *,
    building_id: str,
    received_work: str,
    project_ref: str = "project:brick-protocol",
    required_return_shape: str = "",
    output_root: Path | str | None = None,
    overwrite_existing: bool = False,
) -> NativeDispatchBrickHandle:
    """Open a recording building for a workflow the operator is about to run.

    Thin opener over the existing ``open_native_dispatch_brick`` seam: the
    recording building lives in the vessel derived from ``project_ref``
    through ``buildings_root_for`` (THE single derivation seam), unless an
    explicit ``output_root`` overrides it (tests/probes). The importer proof
    limits -- including the not-observable honesty note -- are stamped at open
    so every claim-trace fact the later close writes carries them.

    PERFORMER IS FORCED (fabrication fix 0612): there is deliberately NO
    ``agent_object_ref`` parameter. The recorded performer is ALWAYS the
    synthetic ``WORKFLOW_IMPORT_DEFAULT_AGENT_OBJECT_REF`` -- the importer
    records the workflow unit, never a caller-claimed specific agent, because
    the harness exposes no per-internal-agent identity for workflow agents
    and a caller-supplied performer ref would be an unobserved (fabricated)
    identity claim riding an otherwise-honest single performer act. The
    parameter was REMOVED rather than guarded: no caller ever passed it, so
    there is no signature-compat need, and an absent parameter cannot be
    bypassed. Passing it raises TypeError loudly; the FIRE case additionally
    pins the spine's recorded performer ref VALUE.

    The returned handle is the OPEN recording building; the operator keeps it,
    runs the workflow natively (unrecorded -- the back door), then passes the
    workflow's result payload to ``import_workflow_result``.
    """

    root = Path(output_root) if output_root is not None else buildings_root_for(project_ref)
    return open_native_dispatch_brick(
        building_id=building_id,
        received_work=received_work,
        required_return_shape=required_return_shape,
        agent_object_ref=WORKFLOW_IMPORT_DEFAULT_AGENT_OBJECT_REF,
        declared_gate_refs=NATIVE_DISPATCH_DEFAULT_GATE_REFS,
        output_root=root,
        overwrite_existing=overwrite_existing,
        proof_limits=WORKFLOW_IMPORT_PROOF_LIMITS,
    )


def import_workflow_result(
    handle: NativeDispatchBrickHandle,
    *,
    workflow_result: Any,
    workflow_ref: str,
    agent_count: int | None = None,
    usage: Mapping[str, Any] | None = None,
    total_tokens: int | None = None,
    started_at: str = "",
    finished_at: str = "",
) -> Mapping[str, Any]:
    """Stamp a finished workflow's RESULT into the open recording building.

    Post-hoc, operator-called. Given the OPEN recording building's handle and
    the workflow's result payload (the harness payload as the operator has it:
    a plain string, a content-block list, or a transport envelope carrying
    metadata keys like status/usage/totalTokens):

      1. EXTRACT the result content through the SAME envelope-tolerant
         boundary the repaired close hooks use
         (``returned_value_from_harness_payload``): envelope metadata is
         tolerated (names recorded, values not consumed beyond the explicit
         totals lift below); the agent's/workflow's OWN structured return
         passes through UNCHANGED so the closed RETURNED_FORBIDDEN_KEYS
         validation downstream still applies in full (no laundering).
      2. CLOSE the building through ``close_native_dispatch_brick``
         (movement="forward"; the Link gate verdict is COMPUTED from the
         return, never asserted here). The verbatim result rides the existing
         agent-return raw stream in ``raw/`` and the ONE Agent claim-trace
         fact -- the workflow's single recorded performer act.
      3. RECORD the structured ``workflow_import`` packet onto
         ``work/building-work.json`` (post-close re-injection, the same
         support-record pattern as ``parent_orchestration_ref``): workflow
         ref, agent_count / usage / total_tokens IF present (explicit
         arguments win; bare totals are lifted from the envelope top level
         when not passed), timestamps IF passed in, the ignored envelope key
         NAMES, and the honest not-observable note.

    HONESTY: the harness exposes no per-internal-agent identity for workflow
    agents, so NONE is recorded -- exactly one performer act, no fabricated
    per-agent AgentBinding/AgentReceipt/claim_trace rows. A close rejection
    (e.g. a structured return smuggling a forbidden key) PROPAGATES -- the
    importer never swallows or rewrites it.

    THREAT-MODEL BOUNDARY (codex review 0612, explicit): the guards here
    defend against ordinary payloads and normal handles -- the realistic
    operator-calls-the-verb model. They do NOT defend against an in-process
    HOSTILE PYTHON OBJECT (a handle/payload subclass that mutates a frozen
    dataclass via object.__setattr__ after the ref check, or a __getattr__
    that returns different values on successive reads). That requires
    arbitrary code execution in the operator process, at which point the
    attacker can write any evidence directly and bypass every checker -- it is
    not a boundary any application-level seam can hold, and is out of this
    module's model by design. The structural vectors (fabricated performer
    ref, nested/labelled per-agent identity, envelope laundering) ARE closed
    and pinned.
    """

    if not isinstance(handle, NativeDispatchBrickHandle):
        raise TypeError(
            "import_workflow_result requires the NativeDispatchBrickHandle "
            "returned by open_workflow_recording"
        )
    # FABRICATION GUARD (importer re-review fix 0612, High): the isinstance
    # check above pins the handle CLASS, not the performer the handle CLAIMS.
    # open_workflow_recording forces agent-object:workflow, but a handle built
    # any other way (open_native_dispatch_brick on the same import path,
    # dataclasses.replace, a hand-rolled instance) carries whatever
    # agent_object_ref its builder set -- and the close below would stamp that
    # WHO into the AgentBinding/Receipt/Return evidence as a recorded specific
    # performer the harness never exposed. The only thing previously blocking
    # the native_dispatch-built path was an ACCIDENT of the dual import-path
    # module split (one source file, two class objects), which is identity
    # trivia, not a guard. Require the synthetic performer ref EXPLICITLY so
    # the one-synthetic-performer guarantee is independent of class-identity
    # accidents. The FIRE case (workflow_import_case) feeds a same-class
    # handle with a forged ref; removing this check REDs it.
    handle_performer_ref = getattr(handle, "agent_object_ref", None)
    if handle_performer_ref != WORKFLOW_IMPORT_DEFAULT_AGENT_OBJECT_REF:
        raise ValueError(
            "import_workflow_result only records the synthetic "
            f"{WORKFLOW_IMPORT_DEFAULT_AGENT_OBJECT_REF!r} performer; refusing "
            "a handle that claims a specific performer identity "
            f"({handle_performer_ref!r}) -- per-internal-agent identity is not "
            "observable through the workflow back door; open the recording "
            "building with open_workflow_recording"
        )
    workflow_ref_text = workflow_ref.strip() if isinstance(workflow_ref, str) else ""
    if not workflow_ref_text:
        raise ValueError("import_workflow_result requires a non-empty workflow_ref")

    returned, unconsumed_keys = returned_value_from_harness_payload(workflow_result)
    # HONESTY GUARD (fabrication fix 0612): the extracted return rides the ONE
    # Agent claim fact verbatim, and the closed RETURNED_FORBIDDEN_KEYS set
    # guards verdict/movement/secret keys but carries NO per-agent identity
    # names -- so a STRUCTURED return could smuggle agents/agent_ids/claim_trace
    # shapes into the claim fact while the spine count pin stays at 1. The
    # importer's premise is that per-internal-agent identity is NOT observable
    # through the workflow back door, so identity-shaped keys in the structured
    # return cannot be evidence: reject them at ANY depth, before any write.
    # (Plain TEXT returns are untouched -- text carries no keys; the
    # no-content-key envelope fallback is one raw JSON STRING for the same
    # reason.)
    _reject_identity_keys(returned, "import_workflow_result structured workflow return")

    lifted: dict[str, Any] = {}
    lifted_keys: set[str] = set()
    if isinstance(workflow_result, Mapping):
        for field, envelope_keys in _ENVELOPE_INT_LIFTS:
            for key in envelope_keys:
                value = workflow_result.get(key)
                if isinstance(value, int) and not isinstance(value, bool):
                    lifted[field] = value
                    lifted_keys.add(key)
                    break
        for key in _ENVELOPE_USAGE_KEYS:
            value = workflow_result.get(key)
            if isinstance(value, Mapping):
                lifted["usage_totals"] = _flat_usage_totals(value)
                lifted_keys.add(key)
                break

    packet: dict[str, Any] = {
        "workflow_ref": workflow_ref_text,
        "internal_agent_detail": WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE,
        "recorded_performer_acts": 1,
        "envelope_keys_ignored": [
            key for key in unconsumed_keys if key not in lifted_keys
        ],
    }
    packet.update(_checked_totals(agent_count, usage, total_tokens, lifted))
    for field, value in (("started_at", started_at), ("finished_at", finished_at)):
        text = value.strip() if isinstance(value, str) else ""
        if value and not isinstance(value, str):
            raise TypeError(f"import_workflow_result {field} must be a string timestamp")
        if text:
            packet[field] = text
    _validate_workflow_import_packet(packet)

    close_record = close_native_dispatch_brick(handle, returned=returned, movement="forward")

    building_root = Path(close_record["building_root"])
    _inject_workflow_import_packet(building_root, packet)

    return {
        "kind": "workflow_result_import",
        "building_id": close_record["building_id"],
        "building_root": str(building_root),
        "movement": close_record["movement"],
        "gate_sufficiency": close_record["gate_sufficiency"],
        "observed_match_kind": close_record["observed_match_kind"],
        WORKFLOW_IMPORT_PACKET_KEY: dict(packet),
        "written_files": list(close_record["written_files"]),
        "proof_limits": list(close_record["proof_limits"]),
        "not_proven": list(close_record["not_proven"]),
    }


def _checked_totals(
    agent_count: int | None,
    usage: Mapping[str, Any] | None,
    total_tokens: int | None,
    lifted: Mapping[str, Any],
) -> dict[str, Any]:
    """Merge explicit totals over envelope-lifted ones, mechanically validated.

    Explicit arguments WIN over lifted envelope values. Only counts/totals are
    admitted -- ints (not bools, not negative) and ONE FLAT usage mapping
    (``_flat_usage_totals``: string keys -> non-negative ints, nothing nested;
    a usage tally is numbers, never identity).
    """

    merged: dict[str, Any] = dict(lifted)
    if agent_count is not None:
        if isinstance(agent_count, bool) or not isinstance(agent_count, int) or agent_count < 0:
            raise ValueError("import_workflow_result agent_count must be a non-negative int")
        merged["agent_count"] = agent_count
    if total_tokens is not None:
        if isinstance(total_tokens, bool) or not isinstance(total_tokens, int) or total_tokens < 0:
            raise ValueError("import_workflow_result total_tokens must be a non-negative int")
        merged["total_tokens"] = total_tokens
    if usage is not None:
        if not isinstance(usage, Mapping):
            raise TypeError("import_workflow_result usage must be a mapping of totals")
        merged["usage_totals"] = _flat_usage_totals(usage)
    for field in ("agent_count", "total_tokens"):
        value = merged.get(field)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            # An envelope-lifted total already passed the isinstance(int) lift
            # filter; this re-check keeps the merged packet closed either way.
            raise ValueError(f"import_workflow_result {field} must be a non-negative int")
    return merged


def _flat_usage_totals(value: Mapping[str, Any]) -> dict[str, int]:
    """usage_totals is a token/usage TALLY and nothing else: ALLOWLISTED FLAT ints.

    Fabrication fix 0612: ``usage_totals`` used to be copied verbatim
    (``dict(value)``), so a nested mapping/list could ride per-internal-agent
    identity into the packet under an admitted field while the TOP-LEVEL
    forbidden-key check stayed green. A usage tally has exactly one honest
    shape -- ALLOWLISTED aggregate metric keys mapped to non-negative ints --
    so anything else (nested mappings, lists, bools, negatives, non-string
    keys) is rejected loudly, on BOTH the explicit ``usage`` argument and the
    envelope-lifted ``usage`` key.

    Importer re-review fix 0612 (Medium): keys are checked against
    ``WORKFLOW_IMPORT_USAGE_METRIC_KEYS``, not merely "any non-empty string"
    -- an arbitrary key name (``{"x_team": 3}``) is a per-agent labelling
    vector the identity deny-list cannot enumerate, so the vocabulary is
    closed instead: not-allowlisted -> reject, fail-closed. (Identity-shaped
    key NAMES are additionally rejected by the deep scan in
    ``_validate_workflow_import_packet`` -- defense in depth behind the
    allowlist.)
    """

    totals: dict[str, int] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(
                "import_workflow_result usage totals must be a flat mapping "
                f"with non-empty string keys (got key {key!r})"
            )
        if key not in WORKFLOW_IMPORT_USAGE_METRIC_KEYS:
            raise ValueError(
                "import_workflow_result usage totals admit only the aggregate "
                f"metric keys {sorted(WORKFLOW_IMPORT_USAGE_METRIC_KEYS)}; got "
                f"non-allowlisted key {key!r} -- an arbitrary usage key is a "
                "per-agent labelling vector (rejected fail-closed; pass clean "
                "aggregate totals)"
            )
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            raise ValueError(
                "import_workflow_result usage totals must be a flat mapping of "
                f"non-negative int totals only (got {key!r} = {raw!r}); a usage "
                "tally carries numbers, never nested structure or identity"
            )
        totals[key] = raw
    return totals


def _reject_identity_keys(value: Any, where: str, _path: str = "") -> None:
    """HONESTY GUARD (deep): refuse per-internal-agent identity keys at ANY depth.

    Fabrication fix 0612: the original guard intersected only the TOP-LEVEL
    packet keys with ``WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS``, so the same
    forbidden names nested under an admitted field passed silently. This walks
    every Mapping (keys checked, values recursed) and every list/tuple item,
    rejecting the FIRST forbidden key name found with its full path. Text is
    never scanned -- a string carries no keys, and verbatim result text
    legitimately MENTIONS agents without recording identity structure.
    """

    if isinstance(value, Mapping):
        for key, child in value.items():
            key_text = key if isinstance(key, str) else str(key)
            child_path = f"{_path}.{key_text}" if _path else key_text
            if key_text in WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS:
                raise ValueError(
                    f"{where} must not carry per-internal-agent identity keys "
                    "at any depth (not observable through the workflow back "
                    f"door): {child_path}"
                )
            _reject_identity_keys(child, where, child_path)
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _reject_identity_keys(child, where, f"{_path}[{index}]")


def _validate_workflow_import_packet(packet: Mapping[str, Any]) -> None:
    """HONESTY GUARD: refuse a packet carrying per-internal-agent identity keys.

    The harness does not expose per-internal-agent identities for workflow
    agents; recording any would be fabrication. DEEP (fabrication fix 0612):
    the scan covers every nesting level, not just the top-level key set, so
    identity names cannot ride under admitted fields like ``usage_totals``.
    The FIRE case (workflow_import_case) independently re-asserts the on-disk
    packet, so removing this guard alone cannot reopen the hole silently.
    """

    _reject_identity_keys(packet, "workflow_import packet")


def _inject_workflow_import_packet(
    building_root: Path,
    packet: Mapping[str, Any],
) -> None:
    """Re-inject the workflow_import packet onto the closed work record.

    Same pattern (and same reason) as native_dispatch's
    ``_reinject_parent_orchestration_ref``: ``write_accumulated_building_evidence``
    rebuilds ``work/building-work.json`` from the step results and carries no
    arbitrary keys through, so the packet is written AFTER the close, with the
    SAME canonical serialization the lifecycle writer uses (``_json_text``),
    preserving the graph-ready envelope untouched. Record-only: a plain
    support mapping, no Movement, no success/quality, no adoption.
    """

    work_path = building_root / "work" / "building-work.json"
    record = json.loads(work_path.read_text(encoding="utf-8"))
    record[WORKFLOW_IMPORT_PACKET_KEY] = dict(packet)
    work_path.write_text(_json_text(record), encoding="utf-8")


__all__ = [
    "WORKFLOW_IMPORT_DEFAULT_AGENT_OBJECT_REF",
    "WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS",
    "WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE",
    "WORKFLOW_IMPORT_PACKET_KEY",
    "WORKFLOW_IMPORT_PROOF_LIMITS",
    "WORKFLOW_IMPORT_USAGE_METRIC_KEYS",
    "import_workflow_result",
    "open_workflow_recording",
]
