"""Native dispatch close behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from brick_protocol.support.checkers.lib.yaml_subset import ProfileError, json_path_exists, require_mapping, require_string, rule_items


def _case_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "case"


def run_native_dispatch_close_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """FIRE the two native-dispatch close governance guards via real open/close.

    For each declared item (a marker; no required fields) this drives the real
    open_native_dispatch_brick -> close_native_dispatch_brick seam against a TEMP
    output_root and asserts these behaviours that RED the holes and GREEN the fix:

      (1) HOLE A (forced verdict, observed_match_kind): close with a
          comparison_observation carrying observed_match_kind="matched" while
          `returned` is MISSING required fields MUST raise ValueError. ANY caller
          comparison_observation is now rejected outright.
      (1b) HOLE A (forced verdict, comparison_evidence): close with a
          comparison_observation carrying comparison_evidence (e.g.
          ["missing_return_fields: none"]) over a return MISSING required fields
          MUST raise ValueError. The gate sufficiency is driven by
          missing_return_fields parsed from comparison_evidence, NOT by
          observed_match_kind, so a fix that rejected only observed_match_kind
          would let THIS forge a "sufficient" gate. This case proves the fix
          rejects the WHOLE observation: before the fix it produced gate
          sufficiency="sufficient"; now it RAISES.
      (2) HOLE B (smuggled Movement, no basis): close with movement="reroute" and
          EMPTY route_decision_basis MUST raise ValueError.
      (3) HOLE B (smuggled Movement, non-CoO ref): close with movement="reroute"
          by a NON-CoO ref MUST raise ValueError even WITH a basis. Covers both a
          worker-lane ref (agent-object:dev) AND a *-lead ref (agent-object:cto-
          lead) -- the *-lead shares lane="leader" with the CoO, so a lane check
          would WRONGLY admit it; only the agent-object:coo ref is authorized.
      (4) POSITIVE (real successful close over a FRESH building tree): the
          governance guards must NOT over-block legitimate inputs, AND a
          legitimate close must actually COMPLETE and produce a building. A
          forward close (default, agent-object:dev) and a legit reroute
          (agent-object:coo + non-empty basis) must each:
            - NOT raise (no guard ValueError, and -- since the steps regression
              is fixed -- no SpineProjectionError either);
            - return a building_root that is a real directory on disk;
            - record execution_path=native-dispatch;
            - have written work/declared-building-plan.json whose
              declared_plan_copy.steps is a NON-EMPTY JSON list (the exact shape
              whose absence used to RAISE SpineProjectionError);
            - record the expected movement / lane / basis / COMPUTED (never
              forced "matched") comparison.
          This case REDs if a guard wrongly rejects a legitimate forward/reroute
          OR if a fresh close fails to produce a steps-bearing building tree.
      (6) B4-REPAIR defect 1 (0611): harness-envelope tolerance BOTH ways --
          the extracted content of a live-shaped Agent tool_result envelope
          (carrying 'status' + metadata) must close successfully; an
          unknown-shape envelope must fall back to ONE raw JSON string that
          closes; and a Mapping carrying 'status' passed DIRECTLY as returned
          must STILL be rejected (the closed RETURNED_FORBIDDEN_KEYS set was
          NOT opened).
      (7) B4-REPAIR defect 2 (0611): the closed building must record
          declaration_provenance.composition_mode == the single-sourced engine
          linear literal (composition.LINEAR_COMPOSITION_MODE) and pass the
          REAL check_building_declaration_integrity validator.

    HISTORY: a prior baseline made ANY live native-dispatch close raise
    SpineProjectionError at write_accumulated_building_evidence, because the
    close plan declared no declared_plan_copy.steps while the spine projector
    requires them. That regression hid behind the STALE on-disk posA proof
    building (validated by the structural rules; never re-closed). This case now
    runs a FRESH open->close to a temp output_root and asserts the close
    SUCCEEDS, so that regression class can no longer hide behind a stale
    artifact.
    """

    items = rule_items(profile, "native_dispatch_close_case")
    if not items:
        return 0
    from brick_protocol.support.operator.building_operation import (
        close_native_dispatch_brick,
        open_native_dispatch_brick,
    )
    # Import from the canonical brick_protocol.* package path so the caught type
    # is the SAME class object that evidence_assembly raises (the support.* alias
    # is a DIFFERENT class under this repo's dual import-identity, and would not
    # match the except clause).
    from brick_protocol.support.recording.spine_projection import SpineProjectionError

    count = 0
    for item in items:
        mapping = require_mapping(item, "native_dispatch_close_case item")
        label = require_string(
            mapping.get("label", "native-dispatch-close"),
            "native_dispatch_close_case.label",
        )
        slug = _case_slug(label)
        # A return that is MISSING the required fields, so the COMPUTED Brick
        # comparison can never be "match". This is the lever the forced verdict
        # would override.
        missing_return = {"unrelated_field": "no required fields present"}
        ok_return = {"observed_evidence": "present", "not_proven": "documented"}

        def _open(building_id: str, agent_object_ref: str, output_root: Path):
            return open_native_dispatch_brick(
                building_id=building_id,
                received_work=f"{label}: native dispatch work",
                required_return_shape="observed_evidence, not_proven",
                agent_object_ref=agent_object_ref,
                declared_gate_refs=["link-gate:default-transition"],
                output_root=output_root,
                overwrite_existing=True,
            )

        with tempfile.TemporaryDirectory(prefix=f"bp-native-dispatch-close-{slug}-") as tmpdir:
            output_root = Path(tmpdir) / "buildings"

            # (1) HOLE A: ANY caller comparison_observation MUST be rejected by the
            # GUARD. observed_match_kind="matched" over a return MISSING the
            # required fields is one forced verdict; the guard now rejects the
            # WHOLE observation before the comparison is built. The assertion pins
            # the GUARD's SPECIFIC message ("caller comparison_observation is not
            # admitted"), so a downstream rejection (different type/message) does
            # NOT masquerade as the guard firing: if the guard is removed, this
            # case REDs (the close raises SpineProjectionError, not this
            # ValueError, and is not caught).
            _GUARD_A_MSG = "caller comparison_observation is not admitted"
            handle_a = _open(f"{slug}-forced-verdict", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_a,
                    returned=missing_return,
                    movement="forward",
                    comparison_observation={"observed_match_kind": "matched"},
                )
            except ValueError as exc:
                if _GUARD_A_MSG not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: forced-verdict "
                        f"was NOT rejected by guard A (expected message "
                        f"{_GUARD_A_MSG!r}); observed: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: HOLE A OPEN -- "
                    "close admitted a caller-forced observed_match_kind"
                )

            # (1b) HOLE A (the REAL P0 lever): a comparison_observation carrying
            # comparison_evidence=["missing_return_fields: none"] over a return
            # MISSING required fields MUST be rejected. The Link gate sufficiency
            # is driven by missing_return_fields parsed from comparison_evidence,
            # NOT by observed_match_kind, so a fix rejecting only
            # observed_match_kind would let THIS forge a "sufficient" gate (it did,
            # before the fix). Same pinned guard message: the WHOLE observation is
            # rejected. If the reject is narrowed back to observed_match_kind-only,
            # this close would SUCCEED with a forged "sufficient" gate and this
            # case REDs (else-branch fires).
            handle_a2 = _open(f"{slug}-spoof-evidence", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_a2,
                    returned=missing_return,
                    movement="forward",
                    comparison_observation={
                        "comparison_evidence": ["missing_return_fields: none"]
                    },
                )
            except ValueError as exc:
                if _GUARD_A_MSG not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: spoofed "
                        f"comparison_evidence was NOT rejected by guard A (expected "
                        f"message {_GUARD_A_MSG!r}); observed: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: HOLE A OPEN -- "
                    "close admitted a caller comparison_observation carrying "
                    "comparison_evidence (would forge a 'sufficient' gate over a "
                    "return missing required fields)"
                )

            # (2) HOLE B: reroute with EMPTY route_decision_basis MUST be rejected.
            handle_b = _open(f"{slug}-reroute-nobasis", "agent-object:coo", output_root)
            try:
                close_native_dispatch_brick(
                    handle_b,
                    returned=ok_return,
                    movement="reroute",
                    route_decision_basis=(),
                )
            except ValueError as exc:
                if "route_decision_basis" not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: reroute-no-basis "
                        f"raised an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: HOLE B OPEN -- "
                    "close admitted a reroute with no route_decision_basis"
                )

            # (3) HOLE B: reroute by a NON-CoO ref MUST be rejected even WITH a
            # basis. Covered by TWO refs:
            #   - agent-object:dev (lane=worker): the obvious non-author.
            #   - agent-object:cto-lead (lane=leader): the SUBTLE one -- it shares
            #     lane="leader" with the CoO, so a lane-membership check would
            #     WRONGLY admit it. Only the agent-object:coo REF is authorized;
            #     a *-lead returns observed-only and must NOT author Movement.
            # Before the ref-based fix, the cto-lead reroute was ADMITTED (lane in
            # {leader}) -> this sub-case REDs the lane-only hole.
            for bad_ref, tag in (
                ("agent-object:dev", "reroute-badlane"),
                ("agent-object:cto-lead", "reroute-leadref"),
            ):
                handle_c = _open(f"{slug}-{tag}", bad_ref, output_root)
                try:
                    close_native_dispatch_brick(
                        handle_c,
                        returned=ok_return,
                        movement="reroute",
                        route_decision_basis=["human:smith/decision-0"],
                    )
                except ValueError as exc:
                    if "authoriz" not in str(exc).lower():
                        raise ProfileError(
                            f"native_dispatch_close_case rejected {label}: {tag} "
                            f"raised an unexpected message: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: HOLE B OPEN -- "
                        f"close admitted a reroute from a non-CoO ref {bad_ref!r}"
                    )

            # (4a) POSITIVE (real successful close): forward by the default
            # dev/worker lane must get PAST the guards AND complete -- producing a
            # building tree whose declared-building-plan carries steps. A
            # SpineProjectionError here is NO LONGER tolerated: it WAS the
            # regression (declared_plan_copy.steps absent), so catching it would
            # let the regression hide again. Any raise REDs.
            handle_d = _open(f"{slug}-forward-ok", "agent-object:dev", output_root)
            try:
                forward_result = close_native_dispatch_brick(
                    handle_d,
                    returned=missing_return,
                    movement="forward",
                )
            except SpineProjectionError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward "
                    "close RAISED SpineProjectionError -- a fresh native-dispatch "
                    "close must SUCCEED and produce a steps-bearing building "
                    f"(regression returned): {exc}"
                ) from exc
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward was "
                    f"wrongly rejected by a governance guard: {exc}"
                ) from exc
            if forward_result.get("movement") != "forward":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward "
                    f"did not record movement=forward: {forward_result.get('movement')!r}"
                )
            if forward_result.get("observed_match_kind") == "matched":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: positive forward over "
                    "a return MISSING required fields recorded observed_match_kind=matched "
                    "(the comparison was not COMPUTED from the return)"
                )
            _assert_native_dispatch_building_produced(label, forward_result)

            # (4b) POSITIVE (real successful close): a LEGIT reroute (leader lane +
            # non-empty basis) must get PAST both guards AND complete. Same
            # disposition as (4a): a SpineProjectionError is the regression and is
            # NO LONGER tolerated -- any raise REDs. On success assert
            # movement=reroute + caller_lane=leader + recorded route_decision_basis
            # AND a steps-bearing building tree.
            handle_e = _open(f"{slug}-reroute-ok", "agent-object:coo", output_root)
            try:
                reroute_result = close_native_dispatch_brick(
                    handle_e,
                    returned=ok_return,
                    movement="reroute",
                    route_decision_basis=["human:smith/decision-1", "link:reroute-gate"],
                )
            except SpineProjectionError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute "
                    "close RAISED SpineProjectionError -- a fresh native-dispatch "
                    "close must SUCCEED and produce a steps-bearing building "
                    f"(regression returned): {exc}"
                ) from exc
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute was "
                    f"wrongly rejected by a governance guard: {exc}"
                ) from exc
            if reroute_result.get("movement") != "reroute":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute did not "
                    f"record movement=reroute: {reroute_result.get('movement')!r}"
                )
            if reroute_result.get("caller_lane") != "leader":
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute did not "
                    f"record caller_lane=leader: {reroute_result.get('caller_lane')!r}"
                )
            if not reroute_result.get("route_decision_basis"):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: legit reroute did not "
                    "record route_decision_basis"
                )
            _assert_native_dispatch_building_produced(label, reroute_result)

            # (5) B2a PARENT-CHILD ORCHESTRATION LINK (record-only provenance).
            # The native-dispatch open accepts OPTIONAL parent_building_id +
            # parent_step_ref. When BOTH are supplied the CHILD building's
            # work/building-work.json must carry a PLAIN parent_orchestration_ref
            # (both parts), and close's return must surface an orchestration_packet
            # mirroring it + a COMPUTED gate_sufficiency. Supplying EXACTLY ONE is
            # an ORPHAN and MUST raise (fail-closed). Supplying NEITHER is a normal
            # standalone dispatch: NO key on disk, packet.parent_orchestration_ref
            # is None. These RED if the orphan guard or the injection is removed.

            # (5a) BOTH parent refs: child work record carries parent_orchestration_ref
            # after close (close REBUILDS building-work.json, so this also pins the
            # re-injection that survives the rewrite), and orchestration_packet
            # mirrors the ref + carries a COMPUTED gate_sufficiency.
            parent_building_id = f"{slug}-parent-bld"
            parent_step_ref = f"{slug}-parent-bld-step-0"
            handle_p = open_native_dispatch_brick(
                building_id=f"{slug}-orch-child",
                received_work=f"{label}: orchestrated child work",
                required_return_shape="observed_evidence, not_proven",
                agent_object_ref="agent-object:dev",
                declared_gate_refs=["link-gate:default-transition"],
                output_root=output_root,
                overwrite_existing=True,
                parent_building_id=parent_building_id,
                parent_step_ref=parent_step_ref,
            )
            orch_result = close_native_dispatch_brick(
                handle_p,
                returned=ok_return,
                movement="forward",
            )
            _assert_native_dispatch_building_produced(label, orch_result)
            child_root = Path(orch_result["building_root"])
            child_work = json.loads(
                (child_root / "work" / "building-work.json").read_text(encoding="utf-8")
            )
            on_disk_ref = child_work.get("parent_orchestration_ref")
            if not isinstance(on_disk_ref, Mapping):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: B2a child work "
                    "record is MISSING parent_orchestration_ref after close (got "
                    f"{on_disk_ref!r})"
                )
            if (
                on_disk_ref.get("parent_building_id") != parent_building_id
                or on_disk_ref.get("parent_step_ref") != parent_step_ref
            ):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: B2a child work "
                    "record parent_orchestration_ref does not carry BOTH parts "
                    f"(got {dict(on_disk_ref)!r})"
                )
            packet = orch_result.get("orchestration_packet")
            if not isinstance(packet, Mapping):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: close return is "
                    f"MISSING orchestration_packet (got {packet!r})"
                )
            if packet.get("child_building_id") != orch_result.get("building_id"):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: orchestration_packet "
                    "child_building_id does not match the closed building_id"
                )
            packet_ref = packet.get("parent_orchestration_ref")
            if not isinstance(packet_ref, Mapping) or (
                packet_ref.get("parent_building_id") != parent_building_id
                or packet_ref.get("parent_step_ref") != parent_step_ref
            ):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: orchestration_packet "
                    f"parent_orchestration_ref does not mirror the ref (got {packet_ref!r})"
                )
            # gate_sufficiency must be the COMPUTED gate value (the same one the
            # top-level result already reports), not hardcoded/absent.
            if packet.get("gate_sufficiency") != orch_result.get("gate_sufficiency"):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: orchestration_packet "
                    "gate_sufficiency does not match the COMPUTED close gate_sufficiency "
                    f"(packet={packet.get('gate_sufficiency')!r} vs "
                    f"close={orch_result.get('gate_sufficiency')!r})"
                )

            # (5b) ORPHAN: EXACTLY ONE of {parent_building_id, parent_step_ref}
            # MUST raise ValueError at OPEN (fail-closed). Covers both halves.
            for orphan_kwargs, tag in (
                ({"parent_building_id": parent_building_id}, "orphan-bld-only"),
                ({"parent_step_ref": parent_step_ref}, "orphan-step-only"),
            ):
                try:
                    open_native_dispatch_brick(
                        building_id=f"{slug}-{tag}",
                        received_work=f"{label}: orphan",
                        required_return_shape="observed_evidence, not_proven",
                        agent_object_ref="agent-object:dev",
                        declared_gate_refs=["link-gate:default-transition"],
                        output_root=output_root,
                        overwrite_existing=True,
                        **orphan_kwargs,
                    )
                except ValueError as exc:
                    if "requires BOTH parent_building_id and parent_step_ref" not in str(exc):
                        raise ProfileError(
                            f"native_dispatch_close_case rejected {label}: {tag} raised "
                            f"an unexpected message: {exc}"
                        ) from exc
                else:
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: ORPHAN OPEN -- "
                        f"open admitted exactly one parent ref ({tag})"
                    )

            # (5c) NEITHER: a standalone dispatch must close normally with NO
            # parent_orchestration_ref key on disk and a None in the packet.
            handle_s = _open(f"{slug}-standalone", "agent-object:dev", output_root)
            standalone_result = close_native_dispatch_brick(
                handle_s,
                returned=ok_return,
                movement="forward",
            )
            _assert_native_dispatch_building_produced(label, standalone_result)
            standalone_work = json.loads(
                (Path(standalone_result["building_root"]) / "work" / "building-work.json").read_text(
                    encoding="utf-8"
                )
            )
            if "parent_orchestration_ref" in standalone_work:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: standalone close "
                    "wrongly wrote a parent_orchestration_ref onto the child work record"
                )
            standalone_packet = standalone_result.get("orchestration_packet")
            if not isinstance(standalone_packet, Mapping):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: standalone close is "
                    f"MISSING orchestration_packet (got {standalone_packet!r})"
                )
            if standalone_packet.get("parent_orchestration_ref") is not None:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: standalone "
                    "orchestration_packet.parent_orchestration_ref is not None (got "
                    f"{standalone_packet.get('parent_orchestration_ref')!r})"
                )

            # (6) B4-REPAIR defect 1 (0611): HARNESS-ENVELOPE TOLERANCE in BOTH
            # directions. The live Claude Code Agent tool_result is a transport
            # envelope carrying harness metadata keys ('status', durations,
            # token counts, usage) alongside the subagent's content; 'status'
            # is in the closed RETURNED_FORBIDDEN_KEYS set, so the raw envelope
            # fed into close made EVERY hook-driven close fail (B4 hooks log:
            # ValueError "returned_value contains forbidden key 'status'").
            # Direction 1 REDs if the tolerance regresses (extraction stops
            # consuming the content / close starts rejecting the harness
            # payload again). Direction 2 REDs if someone "fixes" defect 1 the
            # WRONG way by opening the closed key set: a raw dict carrying
            # 'status' passed DIRECTLY as returned must STILL raise.
            from brick_protocol.support.operator.building_operation import (  # noqa: PLC0415
                returned_value_from_harness_payload,
            )

            harness_text = "observed_evidence: present\nnot_proven: documented"
            harness_envelope = {
                "status": "completed",
                "content": [{"type": "text", "text": harness_text}],
                "totalDurationMs": 4321,
                "totalTokens": 99,
                "usage": {"input_tokens": 10, "output_tokens": 5},
            }
            harness_returned, unconsumed = returned_value_from_harness_payload(
                harness_envelope
            )
            if harness_returned != harness_text:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: harness "
                    "extraction did not yield the subagent's content text "
                    f"(got {harness_returned!r})"
                )
            if "status" not in unconsumed or "usage" not in unconsumed:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: harness "
                    "extraction did not report the envelope metadata keys as "
                    f"unconsumed (got {unconsumed!r})"
                )
            handle_h = _open(f"{slug}-harness-close", "agent-object:dev", output_root)
            try:
                harness_result = close_native_dispatch_brick(
                    handle_h,
                    returned=harness_returned,
                    movement="forward",
                )
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: DEFECT 1 "
                    "RETURNED -- a close over the extracted harness content was "
                    f"rejected: {exc}"
                ) from exc
            _assert_native_dispatch_building_produced(label, harness_result)

            # (6b) unknown-shape envelope (no recognized content key): the
            # extraction must fall back to ONE raw JSON string (a string
            # carries no keys) so the close still completes -- nothing lost,
            # no closed set opened.
            raw_returned, raw_keys = returned_value_from_harness_payload(
                {"status": "completed", "unknown_envelope_key": {"detail": "x"}}
            )
            if not isinstance(raw_returned, str) or "unknown_envelope_key" not in raw_returned:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: unknown-shape "
                    "harness envelope was not preserved as one raw JSON string "
                    f"(got {raw_returned!r})"
                )
            handle_h2 = _open(f"{slug}-harness-raw", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_h2, returned=raw_returned, movement="forward"
                )
            except ValueError as exc:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: raw-string "
                    f"fallback close was rejected: {exc}"
                ) from exc

            # (6c) DIRECTION 2 -- the closed declaration seam stays CLOSED: a
            # Mapping carrying the forbidden 'status' key passed DIRECTLY as
            # returned (an agent return record, NOT a harness envelope) must
            # still be rejected by the unchanged RETURNED_FORBIDDEN_KEYS guard.
            handle_h3 = _open(f"{slug}-harness-strict", "agent-object:dev", output_root)
            try:
                close_native_dispatch_brick(
                    handle_h3,
                    returned={"status": "completed", "observed_evidence": "x"},
                    movement="forward",
                )
            except ValueError as exc:
                if "forbidden key 'status'" not in str(exc):
                    raise ProfileError(
                        f"native_dispatch_close_case rejected {label}: direct "
                        "dict-with-'status' was rejected with an unexpected "
                        f"message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: CLOSED KEY "
                    "SET OPENED -- close admitted a returned Mapping carrying "
                    "the forbidden 'status' key"
                )

            # (7) B4-REPAIR defect 2 (0611): COMPOSITION-MODE STAMP. A
            # native-dispatch close must stamp the SINGLE-SOURCED engine linear
            # composition-authorship literal into the plan so the building-map's
            # declaration_provenance records it; an EMPTY mode fails
            # check_building_declaration_integrity gap 3 and the building can
            # never sit green in the repo tree. Compared against the
            # composition.LINEAR_COMPOSITION_MODE constant (same vocabulary the
            # engine stamps for linear plans -- REDs if the stamp is lost OR if
            # native-dispatch drifts to a different literal), then the REAL
            # declaration-law validator is driven over the produced root.
            from brick_protocol.support.operator.composition_intent import (  # noqa: PLC0415
                LINEAR_COMPOSITION_MODE,
            )
            from brick_protocol.support.checkers.check_building_declaration_integrity import (  # noqa: PLC0415
                validate_building_root,
            )

            harness_root = Path(harness_result["building_root"])
            harness_map = json.loads(
                (harness_root / "work" / "building-map.json").read_text(encoding="utf-8")
            )
            provenance = harness_map.get("declaration_provenance")
            stamped_mode = (
                provenance.get("composition_mode")
                if isinstance(provenance, Mapping)
                else None
            )
            if stamped_mode != LINEAR_COMPOSITION_MODE:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: DEFECT 2 "
                    "RETURNED -- closed building declaration_provenance."
                    f"composition_mode is {stamped_mode!r}, expected the "
                    f"single-sourced {LINEAR_COMPOSITION_MODE!r}"
                )
            integrity_violations = validate_building_root(harness_root)
            if integrity_violations:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: produced "
                    "native-dispatch building fails the declaration-law "
                    f"validator: {integrity_violations}"
                )

            # (8) posA EVIDENCE-SHAPE BACKSTOP FOLD (CLEAN-YARD v3, Smith 0611):
            # the NATIVE-DISPATCH-BRICK-BACKSTOP-0 profile used to pin the
            # standing posA-native-complete dogfood root (path_exists +
            # json_required_paths + text_contains/text_absent). The product
            # repo ships no standing dogfood evidence, so the SAME properties
            # are asserted here over the FRESHLY generated standalone close
            # tree (ok_return, forward) -- the close-case seam IS the
            # generator. Property list migrated 1:1 from the retired pins; see
            # _assert_native_dispatch_pos_a_shape.
            _assert_native_dispatch_pos_a_shape(
                label, Path(standalone_result["building_root"])
            )

        count += 1
    return count


# posA evidence-shape property set, migrated 1:1 from the retired standing-root
# pins of native_dispatch_brick_backstop.yaml (json_required_paths blocks).
_POS_A_JSON_REQUIRED: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("work", "building-work.json"),
        ("execution_path", "building_id", "step_refs[]", "required_return_shape"),
    ),
    (
        ("work", "building-map.json"),
        (
            "execution_path",
            "kind",
            "agent_bindings[].agent_performer_ref",
            "agent_bindings[].brick_instance_ref",
            "agent_bindings[].produced_public_fact_refs[]",
            "link_edges[].movement_fact_ref",
            "link_edges[].transition_fact_ref",
        ),
    ),
    (("evidence", "evidence-manifest.json"), ("execution_path",)),
    (
        ("evidence", "claim_trace", "brick", "work_contract.json"),
        (
            "facts[].fact.observed_match_kind",
            "facts[].fact.required_return_shape_evidence",
            "facts[].fact.comparison_evidence",
            "facts[].fact.forbidden_shortcut_evidence",
            "facts[].fact.work_statement",
        ),
    ),
    (
        ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
        (
            "facts[].fact.stage",
            "facts[].fact.sufficiency",
            "facts[].fact.required_public_facts[]",
            "facts[].fact.checked_public_fact",
            "facts[].fact.reason",
        ),
    ),
    (
        ("evidence", "claim_trace", "link", "movement_trace.json"),
        (
            "facts[].fact.movement",
            "facts[].fact.declared_gate_refs[]",
            "facts[].fact.public_fact_refs[]",
        ),
    ),
    (
        ("evidence", "claim_trace", "agent", "returned_claims.json"),
        (
            "facts[].fact.agent_object_ref",
            "facts[].fact.received_work",
            "facts[].fact.returned",
        ),
    ),
)


# text_contains pins migrated 1:1 (execution_path literal value, open-capture
# events recorded before the subagent return, COMPUTED-gate honesty notes).
_POS_A_TEXT_CONTAINS: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (("work", "building-work.json"), ('"execution_path": "native-dispatch"',)),
    (("work", "building-map.json"), ('"execution_path": "native-dispatch"',)),
    (("evidence", "evidence-manifest.json"), ('"execution_path": "native-dispatch"',)),
    (
        ("capture", "events.jsonl"),
        (
            '"event_type":"building_opened"',
            '"event_type":"brick_opened"',
            '"event_type":"brick_compared"',
            '"event_type":"link_movement"',
        ),
    ),
    (
        ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
        ('"stage": "movement"',),
    ),
    (
        ("evidence", "claim_trace", "brick", "work_contract.json"),
        (
            "brick_protocol/support/run did not classify Agent return",
            "brick_protocol/support/run did not judge success or quality",
        ),
    ),
)


# text_absent pins migrated 1:1 (the gate must be COMPUTED, never hardcoded).
_POS_A_TEXT_ABSENT: tuple[tuple[tuple[str, ...], tuple[str, ...]], ...] = (
    (
        ("evidence", "claim_trace", "link", "sufficiency_trace.json"),
        ("hardcoded_pass", "default_gatefact", "forced_sufficient"),
    ),
)


def _assert_native_dispatch_pos_a_shape(label: str, building_root: Path) -> None:
    """posA evidence-shape backstop over a FRESH native-dispatch close tree.

    Asserts, 1:1, the property set the retired standing posA-native-complete
    pins asserted: the 8 evidence files exist, the required JSON paths resolve,
    the execution_path literal + open-capture event types + COMPUTED-gate
    honesty notes are present, and no hardcoded-gate literal appears.
    """

    for parts, required in _POS_A_JSON_REQUIRED:
        path = building_root.joinpath(*parts)
        if not path.is_file():
            raise ProfileError(
                f"native_dispatch_close_case rejected {label}: posA shape -- "
                f"evidence file missing on the fresh close tree: {'/'.join(parts)}"
            )
        value = json.loads(path.read_text(encoding="utf-8"))
        for dotted in required:
            if not json_path_exists(value, dotted):
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: posA shape -- "
                    f"{'/'.join(parts)} is missing required path {dotted!r}"
                )
    for parts, needles in _POS_A_TEXT_CONTAINS:
        path = building_root.joinpath(*parts)
        if not path.is_file():
            raise ProfileError(
                f"native_dispatch_close_case rejected {label}: posA shape -- "
                f"evidence file missing on the fresh close tree: {'/'.join(parts)}"
            )
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: posA shape -- "
                    f"{'/'.join(parts)} does not contain {needle!r}"
                )
    for parts, needles in _POS_A_TEXT_ABSENT:
        text = building_root.joinpath(*parts).read_text(encoding="utf-8")
        for needle in needles:
            if needle in text:
                raise ProfileError(
                    f"native_dispatch_close_case rejected {label}: posA shape -- "
                    f"{'/'.join(parts)} must NOT contain {needle!r} (the gate must "
                    "be COMPUTED, never hardcoded)"
                )


def _assert_native_dispatch_building_produced(
    label: str, result: Mapping[str, Any]
) -> None:
    """Assert a native-dispatch close produced a real steps-bearing building.

    Proves the close did NOT just return -- it wrote a building tree marked
    execution_path=native-dispatch whose work/declared-building-plan.json has a
    NON-EMPTY declared_plan_copy.steps list. The absence of that steps list was
    the exact regression that raised SpineProjectionError; asserting its presence
    over a FRESH close (not a stale on-disk proof) closes the backstop hole.
    """

    building_root = result.get("building_root")
    if not building_root or not Path(building_root).is_dir():
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: close did not produce a "
            f"building_root directory (got {building_root!r})"
        )
    if result.get("execution_path") != "native-dispatch":
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: produced building did not "
            f"record execution_path=native-dispatch (got {result.get('execution_path')!r})"
        )
    plan_path = Path(building_root) / "work" / "declared-building-plan.json"
    if not plan_path.is_file():
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: produced building has no "
            f"work/declared-building-plan.json at {plan_path}"
        )
    try:
        packet = json.loads(plan_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: declared-building-plan.json "
            f"was not readable JSON: {exc}"
        ) from exc
    declared_plan = packet.get("declared_plan_copy")
    steps = declared_plan.get("steps") if isinstance(declared_plan, Mapping) else None
    if not isinstance(steps, list) or not steps:
        raise ProfileError(
            f"native_dispatch_close_case rejected {label}: declared_plan_copy.steps is "
            "not a NON-EMPTY JSON list -- the steps regression has returned "
            f"(got {steps!r})"
        )
