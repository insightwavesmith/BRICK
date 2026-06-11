#!/usr/bin/env python3
"""Codex CLI SubagentStart hook. CODEX CONFIG, NOT the Brick engine.

TRACKED MACHINE-NEUTRAL TEMPLATE (support/onboarding/): installed into
<repo>/.claude/hooks/ or <repo>/.codex/hooks/ by the onboard wizard's
opt-in recording step (support/operator/onboard.py --recording). It has NO
machine default: BRICK_REPO_ROOT is REQUIRED; unset -> logged no-op.


FORCED-WHEN-IN-A-BRICK recording, ported from the Claude-side
.claude/hooks/open-recording.py to the codex hooks seam
(https://developers.openai.com/codex/hooks). When the engine launches the
codex CLI and codex spawns its OWN subagent, this hook records that spawn as
a child native-dispatch Building -- the SAME seam as the Claude hooks:

  - NO brick context (support.operator.native_dispatch.read_brick_context
    returns None) -> NO-OP: write nothing, create no handle, open no
    Building. Ordinary codex subagents make no recording noise.
  - CONTEXT set -> FORCE-record THIS codex subagent spawn as a child
    native-dispatch Building. The child id is DETERMINISTIC:
    native_dispatch_child_building_id(parent_building_id, agent_id). codex's
    ``agent_id`` is a REAL correlation id shared by SubagentStart and
    SubagentStop (unlike the Claude Agent-tool hooks, which had to hash the
    prompt), so open and close agree on the child id from the payload alone.

Payload note: the SubagentStart payload carries session_id / turn_id /
agent_id / agent_type / permission_mode / cwd / hook_event_name -- it does
NOT carry the subagent's prompt. received_work records agent_type/agent_id
plus an explicit note that the prompt is not present in the payload.

Output discipline (mirrors the Claude hooks EXACTLY): writes NOTHING to
stdout; all diagnostics go to a logfile; every exception is swallowed; ALWAYS
exits 0. Exit 2 would BLOCK codex's subagent -- that must be impossible, so
no code path here can return anything but 0.
"""
from __future__ import annotations

import json
import os
import sys

_HANDLE_DIR = os.path.join("/tmp", "brick-native-dispatch-handles")
_LOG_PATH = os.path.join("/tmp", "brick-native-dispatch-hooks.log")


def _log(message: str) -> None:
    """Write a diagnostic to the logfile only. Never to stdout (codex consumes
    hook stdout). Logging failures are swallowed."""
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"[codex-open-recording] {message}\n")
    except Exception:
        pass


def main() -> int:
    # Silence stdout for the whole body: nothing this hook does may print to
    # codex's hook stream. Diagnostics go to the logfile via _log().
    sys.stdout = open(os.devnull, "w")  # noqa: SIM115
    try:
        try:
            payload = json.load(sys.stdin)
        except Exception as exc:  # malformed/empty stdin -> no-op, never block
            _log(f"stdin not JSON, no-op: {exc!r}")
            return 0

        repo = os.environ.get("BRICK_REPO_ROOT", "").strip()
        if not repo:
            # MACHINE-NEUTRAL TEMPLATE: there is NO default repo root. The
            # onboard recording step wires BRICK_REPO_ROOT into the hook
            # command; a missing env is a logged no-op, never a block.
            _log("BRICK_REPO_ROOT not set, no-op")
            return 0
        # The import path is `support.operator...`; brick_protocol lives under
        # support/import_identity. Both must be on sys.path, import_identity first.
        sys.path[:0] = [os.path.join(repo, "support", "import_identity"), repo]

        try:
            from support.operator.building_operation import (  # noqa: PLC0415
                native_dispatch_child_building_id,
                open_native_dispatch_brick,
                read_brick_context,
            )
        except Exception as exc:  # import failure must not block the subagent
            _log(f"import failed, no-op: {exc!r}")
            return 0

        agent_id = str(payload.get("agent_id", "") or "").strip()
        agent_type = str(payload.get("agent_type", "") or "").strip()

        context = read_brick_context()
        if context is None:
            # Not in a brick -> ordinary codex subagent -> NOT wrapped, NOT
            # recorded. Load-bearing no-op gate: write nothing, create no
            # handle. (One diagnostic line so the empirical seam stays
            # observable; the logfile is the only write.)
            _log(f"SubagentStart fired (agent_id={agent_id!r}), no brick context -> no-op")
            return 0

        if not agent_id:
            # agent_id is the open/close correlation key; without it the close
            # hook could never re-derive the same child id. Fail to NO-OP.
            _log("SubagentStart payload has no agent_id, no-op")
            return 0

        parent_building_id = context["building_id"]
        parent_step_ref = context.get("parent_step_ref", "")
        # Deterministic child id both hooks recompute from the payload alone:
        # codex's agent_id is shared by SubagentStart and SubagentStop.
        child_id = native_dispatch_child_building_id(parent_building_id, agent_id)

        received_work = (
            f"codex native subagent dispatch (agent_type={agent_type or 'unknown'}, "
            f"agent_id={agent_id}); the SubagentStart payload does not carry the "
            "subagent prompt, so the dispatched work text is not recorded here"
        )

        try:
            open_kwargs = dict(
                building_id=child_id,
                received_work=received_work,
                # FIELD LIST, not a JSON object (same as the Claude open hook).
                required_return_shape="observed_evidence, not_proven",
                agent_object_ref="agent-object:dev",
                declared_gate_refs=["link-gate:default-transition"],
                parent_building_id=parent_building_id,
                parent_step_ref=parent_step_ref,
                overwrite_existing=True,
            )
            # OPTIONAL testability seam (mirrors the Claude open hook): unset in
            # live use. Only a FIRE/probe harness sets it, to redirect the
            # produced building off the repo tree.
            output_root_override = os.environ.get("BRICK_NATIVE_DISPATCH_OUTPUT_ROOT")
            if output_root_override:
                open_kwargs["output_root"] = output_root_override
            handle = open_native_dispatch_brick(**open_kwargs)
        except Exception as exc:  # recording failure must not block the subagent
            _log(f"open_native_dispatch_brick failed for {child_id!r}: {exc!r}")
            return 0

        try:
            import dataclasses  # noqa: PLC0415

            os.makedirs(_HANDLE_DIR, exist_ok=True)
            handle_path = os.path.join(_HANDLE_DIR, child_id + ".json")
            with open(handle_path, "w", encoding="utf-8") as fh:
                json.dump(dataclasses.asdict(handle), fh)
            _log(
                f"opened child building {child_id!r} "
                f"(parent {parent_building_id!r}/{parent_step_ref!r}, "
                f"agent_id={agent_id!r}); handle -> {handle_path}"
            )
        except Exception as exc:
            _log(f"failed to persist handle for {child_id!r}: {exc!r}")
            return 0

        return 0
    finally:
        try:
            sys.stdout.close()
        except Exception:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
