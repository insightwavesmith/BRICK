#!/usr/bin/env python3
"""Codex CLI SubagentStop hook. CODEX CONFIG, NOT the Brick engine.

TRACKED MACHINE-NEUTRAL TEMPLATE (brick_protocol/support/onboarding/): installed into
<repo>/.claude/hooks/ or <repo>/.codex/hooks/ by the onboard wizard's
opt-in recording step (brick_protocol/support/operator/onboard.py --recording). It has NO
machine default: BRICK_REPO_ROOT is REQUIRED; unset -> logged no-op.


FORCED-WHEN-IN-A-BRICK recording (close half), ported from the Claude-side
.claude/hooks/close-recording.py to the codex hooks seam:

  - NO brick context -> NO-OP.
  - CONTEXT set -> re-derive the SAME deterministic child id the open hook
    used (native_dispatch_child_building_id(parent_building_id, agent_id) --
    codex's agent_id is a REAL correlation id shared by SubagentStart and
    SubagentStop), load the open handle, and close the child native-dispatch
    Building with the subagent's last_assistant_message (fallback: a note
    naming agent_transcript_path), then remove the handle (idempotent). No
    open handle found -> no-op.

It NEVER passes comparison_observation (the gate is COMPUTED; a caller
observation is rejected fail-closed) and NEVER passes a movement other than
"forward" (reroute is CoO-only).

Output discipline (mirrors the Claude hooks EXACTLY): writes NOTHING to
stdout; diagnostics go to a logfile; every exception is swallowed; ALWAYS
exits 0. Exit 2 would surface as a block to codex -- impossible here.
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
            fh.write(f"[codex-close-recording] {message}\n")
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
            )
        except Exception as exc:  # import failure must not affect codex
            _log(f"import failed, no-op: {exc!r}")
            return 0

        agent_id = str(payload.get("agent_id", "") or "").strip()

        context = read_brick_context()
        if context is None:
            # Not in a brick -> ordinary codex subagent -> not wrapped -> no-op.
            _log(f"SubagentStop fired (agent_id={agent_id!r}), no brick context -> no-op")
            return 0

        if not agent_id:
            _log("SubagentStop payload has no agent_id, no-op")
            return 0

        parent_building_id = context["building_id"]
        # Re-derive the SAME child id the open hook wrote (same agent_id, same hash).
        child_id = native_dispatch_child_building_id(parent_building_id, agent_id)

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
            # The codex subagent's final message is the returned value; the
            # SubagentStop payload carries it as last_assistant_message. When it
            # is absent/empty, record an honest pointer to the transcript path
            # instead of inventing content.
            last_message = payload.get("last_assistant_message")
            if isinstance(last_message, str) and last_message.strip():
                returned = last_message
            else:
                transcript = str(payload.get("agent_transcript_path", "") or "")
                returned = (
                    "codex SubagentStop carried no last_assistant_message; "
                    f"agent transcript path: {transcript or 'unknown'}"
                )
            close_native_dispatch_brick(
                handle,
                returned=returned,
                movement="forward",  # reroute is CoO-only; never pass it here.
                # Do NOT pass comparison_observation: the gate is COMPUTED.
            )
            _log(f"closed child building {child_id!r} (parent {parent_building_id!r})")
        except Exception as exc:
            # A close failure must not affect codex. Leave the handle file in
            # place so a later retry can still find it; just log and exit 0.
            _log(f"close_native_dispatch_brick failed for {child_id!r}: {exc!r}")
            return 0

        try:
            os.remove(handle_path)
        except Exception as exc:
            _log(f"failed to remove handle {handle_path!r}: {exc!r}")

        # B-DASH-WIRE (same as the Claude close hook): best-effort dashboard
        # delta publish AFTER a successful close. GATED on dashboard env
        # (absent -> not_attempted, no POST); BEST-EFFORT: every failure is
        # swallowed -- a publish problem must never affect codex or the close.
        try:
            from brick_protocol.support.operator.report_sinks import (  # noqa: PLC0415
                send_dashboard_building_delta,
            )
            from brick_protocol.support.recording.capture import (  # noqa: PLC0415
                project_ref_for_building_root,
            )

            # DECISIONS-WIRE AUTO-ON (Smith 0611): the vessel is a PATH fact --
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
