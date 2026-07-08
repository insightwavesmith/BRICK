#!/usr/bin/env python3
"""Claude Code PostToolUse hook (Agent tool). CLAUDE CONFIG, NOT the Brick engine.

TRACKED MACHINE-NEUTRAL TEMPLATE (brick_protocol/support/onboarding/): installed into
<repo>/.claude/hooks/ or <repo>/.codex/hooks/ by the onboard wizard's
opt-in recording step (brick_protocol/support/operator/onboard.py --recording). It has NO
machine default: BRICK_REPO_ROOT is REQUIRED; unset -> logged no-op.


FORCED-WHEN-IN-A-BRICK recording (close half). B1 keyed on a voluntary
``BRICK-TRACK:<id>`` marker. This hook instead reads the single active BRICK
CONTEXT (support.operator.native_dispatch.read_brick_context):

  - NO context (not in a brick) -> NO-OP.
  - CONTEXT set -> re-derive the SAME deterministic child id the open hook used
    (sha256 of parent building_id + tool_input.prompt), load the open handle,
    and close the child native-dispatch Building with the subagent's returned
    payload, then remove the handle (idempotent). No open handle found -> no-op.

It NEVER passes comparison_observation (the gate is COMPUTED; B0-GOV rejects a
caller observation) and NEVER passes a movement other than "forward" (reroute is
CoO-only now).

Output discipline: writes NOTHING to stdout (a PostToolUse hook's stdout can
corrupt the agent tool stream); diagnostics go to a logfile. Always exits 0 so a
recording failure can never affect the agent.
"""
from __future__ import annotations

import json
import os
import sys

_HANDLE_DIR = os.path.join("/tmp", "brick-native-dispatch-handles")
_LOG_PATH = os.path.join("/tmp", "brick-native-dispatch-hooks.log")

# Sequence fields the NativeDispatchBrickHandle dataclass declares as tuples;
# json.load gives lists, so re-coerce before reconstructing the frozen dataclass.
_TUPLE_FIELDS = ("source_facts", "declared_gate_refs", "proof_limits", "written_files")


def _log(message: str) -> None:
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"[close-recording] {message}\n")
    except Exception:
        pass


def main() -> int:
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115
    try:
        try:
            payload = json.load(sys.stdin)
        except Exception as exc:
            _log(f"stdin not JSON, no-op: {exc!r}")
            return 0

        repo = os.environ.get("BRICK_REPO_ROOT", "").strip()
        if not repo:
            # MACHINE-NEUTRAL TEMPLATE: there is NO default repo root. The
            # onboard recording step wires BRICK_REPO_ROOT into the hook
            # command; a missing env is a logged no-op, never a block.
            _log("BRICK_REPO_ROOT not set, no-op")
            return 0
        sys.path[:0] = [os.path.join(repo, "support", "import_identity"), repo]

        try:
            from brick_protocol.support.operator.building_operation import (  # noqa: PLC0415
                NativeDispatchBrickHandle,
                close_native_dispatch_brick,
                native_dispatch_child_building_id,
                read_brick_context,
                returned_value_from_harness_payload,
            )
        except Exception as exc:  # import failure must not affect the agent
            _log(f"import failed, no-op: {exc!r}")
            return 0

        context = read_brick_context()
        if context is None:
            # Not in a brick -> ordinary dev subagent -> not wrapped -> no-op.
            return 0

        tool_input = payload.get("tool_input", {}) or {}
        tool_result = payload.get("tool_result", payload.get("tool_response", {})) or {}
        prompt = str(tool_input.get("prompt", ""))
        parent_building_id = context["building_id"]
        # Re-derive the SAME child id the open hook wrote (same inputs, same hash).
        child_id = native_dispatch_child_building_id(parent_building_id, prompt)

        handle_path = os.path.join(_HANDLE_DIR, child_id + ".json")
        if not os.path.exists(handle_path):
            # Nothing opened for this id (or already closed) -> idempotent no-op.
            _log(f"no open handle for {child_id!r}, no-op")
            return 0

        try:
            with open(handle_path, encoding="utf-8") as fh:
                fields = json.load(fh)
            for key in _TUPLE_FIELDS:
                if key in fields and isinstance(fields[key], list):
                    fields[key] = tuple(fields[key])
            handle = NativeDispatchBrickHandle(**fields)
            # B4-REPAIR (0611): the live Agent tool_result is a TRANSPORT
            # ENVELOPE carrying harness metadata (e.g. 'status') alongside the
            # subagent's content; feeding it raw into close made every
            # hook-driven close fail on the closed RETURNED_FORBIDDEN_KEYS set.
            # The support seam extracts the content and ignores/preserves-as-raw
            # the envelope metadata; unconsumed key NAMES (never values) are
            # logged here. The closed return-record validation is unchanged.
            returned, unconsumed_keys = returned_value_from_harness_payload(tool_result)
            if unconsumed_keys:
                _log(
                    f"harness envelope keys not consumed for {child_id!r} "
                    f"(names only, ignored): {', '.join(unconsumed_keys)}"
                )
            close_native_dispatch_brick(
                handle,
                returned=returned,
                movement="forward",  # reroute is CoO-only; never pass it here.
                # Do NOT pass comparison_observation: the gate is COMPUTED.
            )
            _log(f"closed child building {child_id!r} (parent {parent_building_id!r})")
        except Exception as exc:
            # A close failure must not affect the agent. Leave the handle file in
            # place so a later retry can still find it; just log and exit 0.
            _log(f"close_native_dispatch_brick failed for {child_id!r}: {exc!r}")
            return 0

        try:
            os.remove(handle_path)
        except Exception as exc:
            _log(f"failed to remove handle {handle_path!r}: {exc!r}")

        # B-DASH-WIRE: best-effort dashboard delta publish AFTER a successful close.
        # The dashboard mirrors live building state via per-building EVENT-DELTAS
        # (not full-snapshot pushes); this is the live trigger. CLAUDE CONFIG glue,
        # NOT the engine:
        #   - GATED: send_dashboard_building_delta self-gates on dashboard env
        #     (BRICK_DASHBOARD_INGEST_URL / _SECRET). Absent -> not_attempted, no
        #     POST and no ledger projection. So "no env" -> silent no-op.
        #   - BEST-EFFORT: every failure (projection, network, import) is swallowed.
        #     A publish problem must NEVER affect the agent or the recording close,
        #     which has already succeeded by this point.
        try:
            from brick_protocol.support.operator.report_sinks import (  # noqa: PLC0415
                send_dashboard_building_delta,
            )
            from brick_protocol.support.recording.capture import (  # noqa: PLC0415
                project_ref_for_building_root,
            )

            # DECISIONS-WIRE AUTO-ON (Smith 0611): the vessel is a PATH fact —
            # derive project_ref from the handle's output root through THE
            # single inverse seam so a building_id living in 2+ vessels
            # narrows to ITS vessel. None (legacy/tmp root) keeps the legacy
            # un-narrowed call unchanged.
            project_ref = project_ref_for_building_root(handle.output_root)
            observation = send_dashboard_building_delta(
                child_id, project_ref=project_ref, allow_real_delivery=True
            )
            _log(
                f"dashboard delta for {child_id!r}: "
                f"{getattr(observation, 'delivery_status_class', 'unknown')}"
            )
        except Exception as exc:
            _log(f"dashboard delta publish failed for {child_id!r}, ignored: {exc!r}")
        return 0
    finally:
        try:
            sys.stdout.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
