#!/usr/bin/env python3
"""Claude Code PreToolUse hook (Agent tool). CLAUDE CONFIG, NOT the Brick engine.

TRACKED MACHINE-NEUTRAL TEMPLATE (support/onboarding/): installed into
<repo>/.claude/hooks/ or <repo>/.codex/hooks/ by the onboard wizard's
opt-in recording step (support/operator/onboard.py --recording). It has NO
machine default: BRICK_REPO_ROOT is REQUIRED; unset -> logged no-op.


FORCED-WHEN-IN-A-BRICK recording. B1 keyed recording on a voluntary per-prompt
``BRICK-TRACK:<id>`` marker the agent had to type. This hook instead reads the
single active BRICK CONTEXT (support.operator.native_dispatch.read_brick_context,
a fixed-path JSON record set when a brick is explicitly entered):

  - NO context (not in a brick) -> NO-OP: write nothing, create no handle,
    open no Building. Ordinary dev subagents make no recording noise.
  - CONTEXT set (in a brick) -> FORCE-record THIS child Agent-tool spawn as a
    child native-dispatch Building, with NO voluntary marker needed. The child
    id is DETERMINISTIC (sha256 of parent building_id + tool_input.prompt) so
    the PostToolUse close hook recomputes the SAME id without shared state. The
    child carries a PLAIN parent_orchestration_ref to the brick context's
    {building_id, parent_step_ref}.

Output discipline: a PreToolUse hook's STDOUT can be fed back into the agent's
tool context and corrupt the subagent's input. This hook writes NOTHING to
stdout; all diagnostics go to a logfile. It always exits 0 so a recording
failure can never block the actual dispatch.
"""
from __future__ import annotations

import json
import os
import sys

_HANDLE_DIR = os.path.join("/tmp", "brick-native-dispatch-handles")
_LOG_PATH = os.path.join("/tmp", "brick-native-dispatch-hooks.log")


def _log(message: str) -> None:
    """Write a diagnostic to the logfile only. Never to stdout (would corrupt
    the agent tool stream). Logging failures are swallowed."""
    try:
        with open(_LOG_PATH, "a", encoding="utf-8") as fh:
            fh.write(f"[open-recording] {message}\n")
    except Exception:
        pass


def main() -> int:
    # Silence stdout for the whole body: nothing this hook does may print to the
    # agent's tool stream. Diagnostics go to the logfile via _log().
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
        except Exception as exc:  # import failure must not block dispatch
            _log(f"import failed, no-op: {exc!r}")
            return 0

        context = read_brick_context()
        if context is None:
            # Not in a brick -> ordinary dev subagent -> NOT wrapped, NOT
            # recorded. Load-bearing no-op gate: write nothing, create no handle.
            return 0

        tool_input = payload.get("tool_input", {}) or {}
        prompt = str(tool_input.get("prompt", ""))
        parent_building_id = context["building_id"]
        parent_step_ref = context.get("parent_step_ref", "")
        # Deterministic child id both hooks recompute from inputs alone (no
        # random/time, no shared per-call correlation id exists).
        child_id = native_dispatch_child_building_id(parent_building_id, prompt)

        try:
            open_kwargs = dict(
                building_id=child_id,
                received_work=prompt,
                # FIELD LIST, not a JSON object. Stored verbatim at open(); the
                # JSON-object rejection fires later at the parse step.
                required_return_shape="observed_evidence, not_proven",
                agent_object_ref="agent-object:dev",
                declared_gate_refs=["link-gate:default-transition"],
                parent_building_id=parent_building_id,
                parent_step_ref=parent_step_ref,
                overwrite_existing=True,
            )
            # OPTIONAL testability seam: unset in live use (defaults to the seam's
            # repo buildings root). Only the FIRE harness sets it, to redirect the
            # produced building to /tmp instead of the repo tree.
            output_root_override = os.environ.get("BRICK_NATIVE_DISPATCH_OUTPUT_ROOT")
            if output_root_override:
                open_kwargs["output_root"] = output_root_override
            handle = open_native_dispatch_brick(**open_kwargs)
        except Exception as exc:  # recording failure must not block dispatch
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
                f"(parent {parent_building_id!r}/{parent_step_ref!r}); handle -> {handle_path}"
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
