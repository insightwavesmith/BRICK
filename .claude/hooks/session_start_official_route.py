#!/usr/bin/env python3
"""Claude SessionStart hook: inject official Brick launch route context."""

from __future__ import annotations

import json
import os
import sys


FIXED_CONTEXT = """Brick Protocol official launch route for this repository:

- Use only the official launch verbs: `brick build` or `brick resume`.
- Equivalent official module form is allowed: `python -m brick_protocol.support.operator.cli build` or `python -m brick_protocol.support.operator.cli resume`.
- Do not directly import or call operator internals to launch work: `_run_dynamic_graph_walker`, `_resume_dynamic_graph_walker`, `run_building_plan`, `run_building_once`, `resume_building_plan`, `launch_assembled_building`, or `run_customer_graph_building_in_sandbox`.
- Do not use launcher scripts or subprocess/os.system wrappers to invoke those internals.
- Before any Building launch, state the exact official command line you will run and confirm no operator submodule is being imported or called directly.
- Layer 1/2 hooks prime and block common Bash launches only. Layer 3 walker provenance gating is outside this Building and remains a separate verification target.
"""


def _load_event() -> dict[str, object]:
    raw = sys.stdin.read()
    if not raw.strip():
        return {}
    loaded = json.loads(raw)
    if isinstance(loaded, dict):
        return loaded
    return {}


def _build_output() -> dict[str, object]:
    event = _load_event()
    source = str(event.get("source", "unknown")).strip().lower()

    # Re-inject on startup/resume/clear/compact and on future unknown sources.
    if source in {"startup", "resume", "clear", "compact"} or source:
        context = FIXED_CONTEXT
    else:
        context = FIXED_CONTEXT

    return {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
            "initialUserMessage": (
                "Before launching Brick work, use only `brick build`/`brick resume` "
                "or `python -m brick_protocol.support.operator.cli build|resume`; "
                "declare the exact official command first."
            ),
        }
    }


def main() -> int:
    try:
        if os.environ.get("BRICK_HOOK_FORCE_ERROR") == "1":
            raise RuntimeError("forced hook error")
        print(json.dumps(_build_output(), ensure_ascii=False))
    except Exception:
        # Fail open: a hook bug must not block session startup.
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
