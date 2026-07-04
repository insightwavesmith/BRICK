"""Workflow import behavioral profile runner.

Pure relocation sibling of case_runners; support evidence only.
"""

from __future__ import annotations

import json
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from support.checkers.lib.yaml_subset import (
    ProfileError,
    require_mapping,
    require_string,
    rule_items,
)


def _case_slug(value: str) -> str:
    slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in value.strip())
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "case"


def run_workflow_import_case(repo: Path, profile: Mapping[str, Any]) -> int:
    """FIRE the IMPORTER honesty pin via a real open -> import over a temp root.

    WHY: workflow-internal agents pass through a harness back door the
    recording hooks cannot observe (B4 measurement), so the importer records a
    workflow's RESULT post-hoc as ONE performer act. The hard rule is HONESTY:
    the importer must NEVER fabricate per-internal-agent evidence it did not
    observe. For each declared item (a marker; no required fields) this drives
    the real support/operator/workflow_import.py verbs and asserts:

      (1) RESULT AS EVIDENCE: the verbatim workflow result text rides the
          existing agent-return raw stream (raw/agent-return.jsonl) -- no new
          raw shape invented.
      (2) HONEST PACKET on disk: work/building-work.json carries the
          workflow_import packet with the workflow_ref, the harness-provided
          totals (agent_count / usage / totalTokens), the passed-in
          timestamps, the ignored envelope key NAMES, AND the verbatim
          "internal agent detail not observable (workflow back door)" note;
          the packet carries NO per-internal-agent identity key.
      (3) HONESTY PIN (one performer act): the Evidence Spine records EXACTLY
          ONE AgentBinding, ONE AgentReceipt, and ONE AgentReturn event, and
          the agent claim trace carries EXACTLY ONE returned fact. A second
          (fabricated) per-agent row REDs this case.
      (4) NO LAUNDERING: a STRUCTURED workflow return (a Mapping under the
          envelope content key) smuggling the forbidden 'status' key MUST
          still be rejected by the unchanged closed RETURNED_FORBIDDEN_KEYS
          validation, THROUGH the import verb (the importer must propagate,
          never swallow or rewrite, the rejection).
      (5) B4-REPAIR NON-RECURRENCE: the imported building records
          declaration_provenance.composition_mode == the single-sourced
          engine linear literal AND passes the REAL
          check_building_declaration_integrity validator.
      (6) FORCED SYNTHETIC PERFORMER (fabrication fix 0612): the spine's
          recorded performer ref VALUE on every AgentBinding / AgentReceipt /
          AgentReturn event EQUALS the checker-side literal
          "agent-object:workflow" (deliberately NOT the producer constant --
          a two-place pin), AND opening with a caller-supplied
          agent_object_ref="agent:fake-specific-person" is rejected loudly
          (TypeError: the override parameter was removed; a compat parameter
          re-introduced with a guard must raise ValueError). A re-introduced
          unguarded override that stamps a caller-claimed specific performer
          REDs on the ref-value pin even though the count pin (3) stays at 1.
      (7) NO NESTED IDENTITY (fabrication fix 0612): usage totals must be a
          FLAT str->non-negative-int tally (nested mapping rejected on BOTH
          the explicit usage argument and the envelope-lifted usage key); an
          identity-shaped key NAME in usage is rejected (since the re-review
          allowlist fix, by the usage-key allowlist firing BEFORE the deep
          packet scan; the deep scan stays as defense in depth and is pinned
          independently on the structured-return path, 7d); a STRUCTURED
          workflow return smuggling a forbidden identity key at any depth is
          rejected before it can ride the single Agent claim fact. The happy
          path (flat allowlisted usage, no identity keys) above proves the
          guards admit honest input.
      (8) HANDLE PERFORMER-REF PIN (importer re-review fix 0612, High): a
          handle of the ACCEPTED class whose agent_object_ref is NOT the
          synthetic "agent-object:workflow" -- built fully consistently via
          the brick_protocol-path open_native_dispatch_brick, the SAME module
          workflow_import imports the class from, so the explicit REF CHECK
          is exercised, not the dual-import-path class accident -- MUST be
          rejected loudly by import_workflow_result. Removing the ref check
          REDs here: pre-fix this exact handle closed cleanly and stamped a
          specific performer the harness never exposed.
      (9) USAGE KEY ALLOWLIST (importer re-review fix 0612, Medium): a usage
          key OUTSIDE the aggregate-metric allowlist (e.g. {"x_team": 3} -- a
          per-agent label under a neutral name the identity deny-list cannot
          enumerate) MUST be rejected loudly; allowlisted flat usage
          ({"input_tokens": 1000, "output_tokens": 234}, the happy path
          above) stays accepted and recorded. Widening the allowlist check to
          accept-all REDs here: {"x_team": 3} would then import cleanly
          (nothing downstream flags a neutral key name).

    Support evidence only: asserts recorded SHAPE/honesty, not workflow
    quality; the gate verdict over the imported result is the Link rule's
    COMPUTED output and is not asserted here.
    """

    items = rule_items(profile, "workflow_import_case")
    if not items:
        return 0
    from support.operator.workflow_import import (
        WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS,
        WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE,
        WORKFLOW_IMPORT_PACKET_KEY,
        import_workflow_result,
        open_workflow_recording,
    )
    from support.operator.composition_intent import LINEAR_COMPOSITION_MODE
    from support.checkers.check_building_declaration_integrity import (
        validate_building_root,
    )

    count = 0
    for item in items:
        mapping = require_mapping(item, "workflow_import_case item")
        label = require_string(
            mapping.get("label", "workflow-import"), "workflow_import_case.label"
        )
        slug = _case_slug(label)
        with tempfile.TemporaryDirectory(prefix=f"bp-workflow-import-{slug}-") as tmpdir:
            output_root = Path(tmpdir) / "buildings"
            result_text = (
                "observed_evidence: workflow produced the verbatim report\n"
                "not_proven: internal agent detail (workflow back door)"
            )
            envelope = {
                "status": "completed",
                "result": result_text,
                "agent_count": 3,
                "totalTokens": 1234,
                "usage": {"input_tokens": 1000, "output_tokens": 234},
                "totalDurationMs": 7777,
            }
            handle = open_workflow_recording(
                building_id=f"{slug}-imported",
                received_work=f"{label}: record a finished workflow's result",
                output_root=output_root,
                overwrite_existing=True,
            )
            record = import_workflow_result(
                handle,
                workflow_result=envelope,
                workflow_ref=f"workflow:{slug}",
                started_at="2026-06-12T01:00:00Z",
                finished_at="2026-06-12T01:30:00Z",
            )
            root = Path(str(record.get("building_root", "")))
            if not root.is_dir():
                raise ProfileError(
                    f"workflow_import_case rejected {label}: import did not produce "
                    f"a building_root directory (got {record.get('building_root')!r})"
                )

            # (1) the verbatim result text rides the existing agent-return raw stream.
            raw_path = root / "raw" / "agent-return.jsonl"
            if not raw_path.is_file():
                raise ProfileError(
                    f"workflow_import_case rejected {label}: raw/agent-return.jsonl "
                    "is missing -- the result did not ride the agent-return raw stream"
                )
            if "workflow produced the verbatim report" not in raw_path.read_text(
                encoding="utf-8"
            ):
                raise ProfileError(
                    f"workflow_import_case rejected {label}: raw/agent-return.jsonl "
                    "does not carry the verbatim workflow result text"
                )

            # (2) the honest packet on the on-disk work record.
            work = json.loads(
                (root / "work" / "building-work.json").read_text(encoding="utf-8")
            )
            packet = work.get(WORKFLOW_IMPORT_PACKET_KEY)
            if not isinstance(packet, Mapping):
                raise ProfileError(
                    f"workflow_import_case rejected {label}: work/building-work.json "
                    f"carries no {WORKFLOW_IMPORT_PACKET_KEY} packet (got {packet!r})"
                )
            recorded_note = packet.get("internal_agent_detail")
            if recorded_note != WORKFLOW_IMPORT_NOT_OBSERVABLE_NOTE:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: HONESTY NOTE LOST -- "
                    "the packet does not carry the verbatim not-observable note "
                    f"(got {recorded_note!r})"
                )
            # ANTI-TAUTOLOGY (operator gate 0612, hardened same day): the
            # equality above compares the packet against the SAME imported
            # constant the producer writes, so gutting the constant itself
            # would pass silently. This checker-side FULL literal is the
            # independent second place: changing the producer constant in ANY
            # way (not just dropping the old phrases -- a misleading future
            # rewording that still CONTAINS them would have slipped a
            # substring check) REDs here until this literal is deliberately
            # updated too. A two-place update is the point.
            expected_note_literal = (
                "internal agent detail not observable (workflow back door); "
                "recorded as one performer act"
            )
            if recorded_note != expected_note_literal:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: HONESTY NOTE CHANGED -- "
                    "the on-disk note must EQUAL the checker-side literal verbatim "
                    f"(expected {expected_note_literal!r}, got {recorded_note!r}); "
                    "if the note wording is deliberately changing, update producer "
                    "constant AND this literal together"
                )
            expected_values = {
                "workflow_ref": f"workflow:{slug}",
                "agent_count": 3,
                "total_tokens": 1234,
                "usage_totals": {"input_tokens": 1000, "output_tokens": 234},
                "recorded_performer_acts": 1,
                "started_at": "2026-06-12T01:00:00Z",
                "finished_at": "2026-06-12T01:30:00Z",
            }
            for key, expected in expected_values.items():
                if packet.get(key) != expected:
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: packet.{key} is "
                        f"{packet.get(key)!r}, expected {expected!r}"
                    )
            ignored = packet.get("envelope_keys_ignored")
            if not isinstance(ignored, list) or "status" not in ignored:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: packet."
                    "envelope_keys_ignored does not name the ignored harness "
                    f"'status' key (got {ignored!r})"
                )
            fabricated_keys = sorted(
                set(packet) & set(WORKFLOW_IMPORT_FORBIDDEN_PACKET_KEYS)
            )
            if fabricated_keys:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATION -- the "
                    "packet carries per-internal-agent identity key(s) the harness "
                    f"never exposed: {fabricated_keys}"
                )

            # (3) HONESTY PIN: exactly ONE recorded performer act.
            spine_path = root / "evidence" / "spine" / "spine.jsonl"
            spine_events = [
                json.loads(line)
                for line in spine_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            for event_type in ("AgentBinding", "AgentReceipt", "AgentReturn"):
                observed = sum(
                    1 for event in spine_events if event.get("event_type") == event_type
                )
                if observed != 1:
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: FABRICATION -- the "
                        f"spine records {observed} {event_type} event(s); an imported "
                        "workflow is exactly ONE recorded performer act (internal "
                        "agents are not observable)"
                    )
            # (6) PERFORMER REF VALUE pin (fabrication fix 0612): the count pin
            # alone admits ONE act under a FABRICATED specific identity, so pin
            # the WHO too. The spine.jsonl rows are the hash-chain INDEX; the
            # performer refs live in the event BODY files under event_ref.
            # Checker-side LITERALS, deliberately not the producer constant: a
            # re-introduced caller override (or a changed constant) that stamps
            # any other performer ref REDs here.
            expected_performer_ref = "agent-object:workflow"
            for event in spine_events:
                event_type = event.get("event_type")
                if event_type not in ("AgentBinding", "AgentReceipt", "AgentReturn"):
                    continue
                body = json.loads(
                    (root / str(event.get("event_ref"))).read_text(encoding="utf-8")
                )
                observed_ref = body.get("agent_object_ref")
                if observed_ref != expected_performer_ref:
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: FABRICATED "
                        f"PERFORMER -- spine {event_type} records "
                        f"agent_object_ref {observed_ref!r}; an imported workflow's "
                        "one performer act is ALWAYS the synthetic "
                        f"{expected_performer_ref!r} (specific performer identity "
                        "is not observable through the workflow back door)"
                    )
                if event_type == "AgentBinding":
                    observed_performer = body.get("agent_performer_ref")
                    if observed_performer != f"agent-performer:{expected_performer_ref}":
                        raise ProfileError(
                            f"workflow_import_case rejected {label}: FABRICATED "
                            "PERFORMER -- spine AgentBinding records "
                            f"agent_performer_ref {observed_performer!r}, expected "
                            f"'agent-performer:{expected_performer_ref}'"
                        )
            claims = json.loads(
                (root / "evidence" / "claim_trace" / "agent" / "returned_claims.json")
                .read_text(encoding="utf-8")
            )
            facts = claims.get("facts")
            if not isinstance(facts, list) or len(facts) != 1:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATION -- the agent "
                    f"claim trace carries {len(facts) if isinstance(facts, list) else facts!r} "
                    "returned fact(s); expected exactly ONE recorded performer act"
                )

            # (5) B4-REPAIR non-recurrence: composition_mode stamped + the REAL
            # declaration-law validator over the imported building.
            building_map = json.loads(
                (root / "work" / "building-map.json").read_text(encoding="utf-8")
            )
            provenance = building_map.get("declaration_provenance")
            stamped_mode = (
                provenance.get("composition_mode")
                if isinstance(provenance, Mapping)
                else None
            )
            if stamped_mode != LINEAR_COMPOSITION_MODE:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: imported building "
                    f"declaration_provenance.composition_mode is {stamped_mode!r}, "
                    f"expected the single-sourced {LINEAR_COMPOSITION_MODE!r}"
                )
            integrity_violations = validate_building_root(root)
            if integrity_violations:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: imported building fails "
                    f"the declaration-law validator: {integrity_violations}"
                )

            # (4) NO LAUNDERING through the import verb: a STRUCTURED workflow
            # return (a Mapping under the content key) smuggling 'status' must
            # STILL reject via the unchanged closed RETURNED_FORBIDDEN_KEYS set.
            handle_l = open_workflow_recording(
                building_id=f"{slug}-laundering",
                received_work=f"{label}: structured return smuggling status",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_l,
                    workflow_result={
                        "result": {"status": "completed", "observed_evidence": "x"}
                    },
                    workflow_ref=f"workflow:{slug}-laundering",
                )
            except ValueError as exc:
                if "forbidden key 'status'" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: structured return "
                        "with 'status' was rejected with an unexpected message: "
                        f"{exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: CLOSED KEY SET OPENED "
                    "-- the importer admitted a structured return carrying the "
                    "forbidden 'status' key"
                )

            # (6) FORCED PERFORMER: a caller-claimed SPECIFIC performer identity
            # must be rejected loudly at open. TypeError = the override
            # parameter stays removed (current design); ValueError = a compat
            # parameter returned WITH a loud guard. Anything else (the call
            # succeeding) is the High fabrication vector reopened.
            try:
                open_workflow_recording(
                    building_id=f"{slug}-fake-performer",
                    received_work=f"{label}: caller claims a specific performer",
                    output_root=output_root,
                    overwrite_existing=True,
                    agent_object_ref="agent:fake-specific-person",
                )
            except (TypeError, ValueError):
                pass
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATED PERFORMER "
                    "ADMITTED -- open_workflow_recording accepted a caller-supplied "
                    "agent_object_ref; the imported performer must ALWAYS be the "
                    "synthetic agent-object:workflow"
                )

            # (7a) NESTED usage via the EXPLICIT argument: a usage tally is
            # flat ints; a nested mapping is an identity smuggling vector.
            handle_u = open_workflow_recording(
                building_id=f"{slug}-nested-usage",
                received_work=f"{label}: nested usage smuggle (explicit arg)",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_u,
                    workflow_result="usage smuggle probe",
                    workflow_ref=f"workflow:{slug}-nested-usage",
                    usage={"input_tokens": {"agent_ids": ["fabricated-agent-1"]}},
                )
            except ValueError as exc:
                if "flat mapping" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: nested usage was "
                        f"rejected with an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- import_workflow_result accepted a non-flat usage "
                    "mapping carrying agent_ids under an admitted field"
                )

            # (7b) NESTED usage via the ENVELOPE lift: same guard on the lifted
            # path (the old code dict()-copied the envelope usage verbatim).
            handle_e = open_workflow_recording(
                building_id=f"{slug}-envelope-usage",
                received_work=f"{label}: nested usage smuggle (envelope lift)",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_e,
                    workflow_result={
                        "result": "envelope usage smuggle probe",
                        "usage": {"input_tokens": {"agent_ids": ["fabricated-agent-2"]}},
                    },
                    workflow_ref=f"workflow:{slug}-envelope-usage",
                )
            except ValueError as exc:
                if "flat mapping" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: nested envelope "
                        f"usage was rejected with an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- the envelope usage lift copied a nested mapping "
                    "carrying agent_ids into the packet"
                )

            # (7c) IDENTITY-SHAPED KEY NAME in usage with a FLAT int value:
            # passes the flat-shape check by construction. Since the re-review
            # allowlist fix, the usage-key ALLOWLIST rejects it FIRST
            # ("agent_ids" is not an aggregate metric key); the deep packet
            # scan stays behind it as defense in depth (pinned independently
            # on the structured-return path, 7d). Accept either guard's loud
            # rejection wording -- both close this vector.
            handle_k = open_workflow_recording(
                building_id=f"{slug}-identity-key",
                received_work=f"{label}: identity key name in flat usage",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_k,
                    workflow_result="identity key probe",
                    workflow_ref=f"workflow:{slug}-identity-key",
                    usage={"agent_ids": 3},
                )
            except ValueError as exc:
                if "non-allowlisted" not in str(exc) and "per-internal-agent" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: nested identity "
                        f"key was rejected with an unexpected message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- an identity-shaped key name in usage passed both "
                    "the usage-key allowlist and the deep packet scan"
                )

            # (7d) STRUCTURED RETURN carrying identity at depth: the return
            # rides the single Agent claim fact verbatim and the closed
            # RETURNED_FORBIDDEN_KEYS set names no identity keys, so the
            # importer must reject identity shapes in the structured return
            # itself (count pin stays 1 either way -- the WHO is the leak).
            handle_r = open_workflow_recording(
                building_id=f"{slug}-return-identity",
                received_work=f"{label}: structured return smuggling identity",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_r,
                    workflow_result={
                        "result": {
                            "observed_evidence": "x",
                            "detail": {"agent_ids": ["fabricated-agent-3"]},
                        }
                    },
                    workflow_ref=f"workflow:{slug}-return-identity",
                )
            except ValueError as exc:
                if "per-internal-agent" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: identity in the "
                        "structured return was rejected with an unexpected "
                        f"message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: NESTED IDENTITY "
                    "ADMITTED -- a structured workflow return carried agent_ids "
                    "at depth into the single Agent claim fact"
                )

            # (8) HANDLE PERFORMER-REF PIN (importer re-review fix 0612,
            # High): isinstance pins the handle CLASS, not the WHO it claims.
            # Build a fully CONSISTENT forged handle the most direct way that
            # yields the exact class import_workflow_result accepts: the
            # brick_protocol-path open_native_dispatch_brick -- the SAME
            # module workflow_import itself imports the class from. (The
            # support-path twin class is a dual-import accident, not a guard;
            # this construction goes around it, so the explicit REF CHECK is
            # what is exercised.) Pre-fix this exact handle rode through and
            # recorded a specific performer the harness never exposed; remove
            # the ref check and it closes cleanly again -- RED on the else.
            from brick_protocol.support.operator.native_dispatch import (  # noqa: PLC0415
                open_native_dispatch_brick as _bp_open_native_dispatch_brick,
            )

            forged = _bp_open_native_dispatch_brick(
                building_id=f"{slug}-forged-ref",
                received_work=f"{label}: handle claiming a specific performer",
                required_return_shape="",
                agent_object_ref="agent-object:fake-specific-person",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    forged,
                    workflow_result="forged performer-ref probe",
                    workflow_ref=f"workflow:{slug}-forged-ref",
                )
            except ValueError as exc:
                message = str(exc)
                if (
                    "refusing" not in message
                    or "agent-object:workflow" not in message
                ):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: forged "
                        "performer-ref handle was rejected with an unexpected "
                        f"message: {exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: FABRICATED "
                    "PERFORMER ADMITTED -- import_workflow_result accepted a "
                    "handle whose agent_object_ref is not the synthetic "
                    "agent-object:workflow; the performer-ref guard must hold "
                    "independent of class-identity accidents"
                )

            # (9) USAGE KEY ALLOWLIST (importer re-review fix 0612, Medium):
            # a per-agent LABEL under a NEUTRAL key name -- one the identity
            # deny-list does not flag and the deep scan cannot recognize --
            # must be rejected by the aggregate-metric allowlist. Widen the
            # allowlist check to accept-all and {"x_team": 3} imports cleanly
            # (no downstream guard knows the name) -- RED on the else branch.
            # Allowlisted-flat ACCEPTANCE is pinned by the happy path above
            # (usage_totals == {"input_tokens": 1000, "output_tokens": 234}).
            handle_a = open_workflow_recording(
                building_id=f"{slug}-usage-label",
                received_work=f"{label}: per-agent label under neutral usage key",
                output_root=output_root,
                overwrite_existing=True,
            )
            try:
                import_workflow_result(
                    handle_a,
                    workflow_result="neutral usage-label probe",
                    workflow_ref=f"workflow:{slug}-usage-label",
                    usage={"x_team": 3},
                )
            except ValueError as exc:
                if "non-allowlisted" not in str(exc):
                    raise ProfileError(
                        f"workflow_import_case rejected {label}: non-allowlisted "
                        "usage key was rejected with an unexpected message: "
                        f"{exc}"
                    ) from exc
            else:
                raise ProfileError(
                    f"workflow_import_case rejected {label}: PER-AGENT LABEL "
                    "ADMITTED -- import_workflow_result accepted usage key "
                    "'x_team' outside the aggregate-metric allowlist; an "
                    "arbitrary usage key name is recorded per-agent detail"
                )
        count += 1
    return count
