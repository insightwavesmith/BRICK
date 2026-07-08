---
name: native-dispatch-recording
description: Use when recording a native (main-agent-launched) subagent dispatch as a Brick Building via the support seam, and when wiring the Claude Code Pre/PostToolUse hooks that auto-record every child spawn while a brick context is active.
---

A native dispatch is a subagent the MAIN AGENT launches directly (Claude Code's
own `Agent` tool), not through `brick_protocol/support/operator/run.py`'s Building Plan walk.
This skill records ONE such dispatch as a Brick Building, reusing the existing
evidence writers, so the produced evidence has the same shape as a run.py
Building plus a `native-dispatch` marker.

## The operating model: the CHOICE is free, only RECORDING is forced

An agent working inside a Brick FREELY CHOOSES what to do with its work. It is
NOT forced to spawn anything. It can:

```text
- do the work itself
- research
- spawn a subagent (native Agent tool)
- spawn a workflow
```

That choice stays the agent's own. What is forced is only the RECORDING: while
the agent is inside a brick, EVERY native child spawn is recorded as a child
native-dispatch Building. The agent cannot opt out of recording, but it is never
told what to spawn.

Slogan: **"브릭은 브릭을 부를 때만 진행"** — recording proceeds only when a
brick is calling. Outside a brick, nothing records.

## How recording is triggered: the single active brick context

Recording is CONTEXT-driven, not marker-driven. There is one active "brick
context" persisted at a fixed path (`/tmp/brick-native-dispatch-context.json`,
env-overridable via `BRICK_NATIVE_DISPATCH_CONTEXT_PATH` for tests only):

```text
set_brick_context(building_id, parent_step_ref="")  enter a brick: recording ON
clear_brick_context()                               leave a brick: recording OFF
read_brick_context() -> {building_id, parent_step_ref} | None
```

While the context is SET, EVERY native Agent-tool child spawn auto-records as a
child native-dispatch Building (the Pre/PostToolUse hooks read the context). When
the context is `None` (not in a brick) the hooks are a hard NO-OP — no recording,
no handle, no noise from ordinary dev subagents.

```text
context set    -> in a brick: open() at spawn, close() when the child returns.
context None   -> not in a brick: no-op. NOT wrapped, NOT recorded.
```

Single active context only: a second `set_brick_context` overwrites the first
(nested brick contexts are out of scope — they would need a stack, not one file).
A malformed/`building_id`-less record reads as `None` (fail to NO-OP, never to a
forged recording).

> Superseded: 구 "B1 voluntary"의 `BRICK-TRACK:<building_id>` 마커 타이핑 방식은 폐기 — brick context가 유일한 드라이버다.

## Convention: open -> dispatch -> gate -> close

```text
open    support records received_work + the Brick work contract + open
        capture events (building_opened, brick_opened) and writes
        execution_path="native-dispatch". Returns a handle.
dispatch the MAIN AGENT launches the subagent NATIVELY and collects its
        returned value. Support does NOT launch it, call the adapter, or run
        any CLI.
gate    close() computes the ζ1 BrickComparisonFact and the ζ2 Link movement
        GateFact (sufficiency verdict) from the supplied return. The gate is
        COMPUTED by the Link rule, never a hardcoded pass and never a
        caller-supplied observation.
close   support writes claim_trace + step-output + closure + building-map by
        reusing write_accumulated_building_evidence.
```

## The Brick seam is the engine API

The engine surface is the support functions in
`brick_protocol/support/operator/building_operation.py` (re-exported from
`brick_protocol/support/operator/native_dispatch.py`):

```python
from brick_protocol.support.operator.building_operation import (
    set_brick_context,
    clear_brick_context,
    read_brick_context,
    native_dispatch_child_building_id,
    open_native_dispatch_brick,
    close_native_dispatch_brick,
)

# Enter the brick: every native child spawn now records until cleared.
set_brick_context("my-parent-building-id", parent_step_ref="step-3")

handle = open_native_dispatch_brick(
    building_id="my-native-building-id",
    received_work="<the work the subagent will receive>",
    # required_return_shape is a comma/slash-separated FIELD LIST, NOT a JSON
    # object. open() stores this string VERBATIM in the Brick work contract; it
    # does not parse or reject it here. The split + JSON-object rejection happens
    # later, when brick_protocol/brick/work.py parse_required_return_shape is called at the gate
    # comparison / plan-validation / adapter step. Passing a '{...}' string would
    # therefore raise ValueError at that parse step (not at open), which is what
    # prevents the comma/slash split from shredding it into garbage field names
    # and producing a false-negative gate.
    required_return_shape="observed_evidence, not_proven",
    agent_object_ref="agent-object:dev",
    declared_gate_refs=["link-gate:default-transition"],
)
# ... main agent dispatches the subagent natively, collects `returned` ...
result = close_native_dispatch_brick(
    handle,
    returned=returned,            # the native subagent's output
    movement="forward",           # forward only here (reroute is CoO-only)
)

# Leave the brick: recording stops; later dev subagents are no-ops again.
clear_brick_context()
```

`close()` returns `execution_path`, `gate_stage`, `gate_sufficiency` (COMPUTED),
`observed_match_kind` (COMPUTED), and the written file list. The seam records
only; it does not judge success/quality, choose Movement, walk a plan, call the
agent_adapter, or run any CLI. A caller-supplied `comparison_observation` is
REJECTED fail-closed (so no caller can forge a sufficiency verdict), and a
non-forward Movement (reroute) requires both a `route_decision_basis` and that
the originating ref is `agent-object:coo`.

Provider note: codex is just another adapter (`adapter:codex-local`). The seam
itself records only; it does not depend on which provider produced `returned`.

## The deterministic child id

The Pre/PostToolUse hooks share NO per-call correlation id, so both must compute
the child Building id from the same inputs:

```python
child_id = native_dispatch_child_building_id(parent_building_id, prompt)
# = "<parent_building_id>-child-<sha256(parent_building_id + prompt)[:16]>"
```

Same context + same prompt -> same child id, so the open and close hooks agree
without shared state.

## Integration: Claude Code Pre/PostToolUse hooks

The live hooks are Claude Code config, not the Brick engine:

```text
.claude/hooks/open-recording.py    PreToolUse  (Agent)
.claude/hooks/close-recording.py   PostToolUse (Agent)
```

On each `Agent` dispatch, Claude Code feeds the hook JSON on stdin. Each hook:

```text
- reads read_brick_context();
- context None  -> hard NO-OP (return 0, write nothing);
- context set   -> derive the deterministic child id, then
                   open-recording:  open_native_dispatch_brick(...), persist the
                                    handle under /tmp/brick-native-dispatch-handles/
                   close-recording: reload the handle, close_native_dispatch_brick(
                                    returned, movement="forward"), remove the
                                    handle (idempotent), then best-effort publish
                                    a dashboard delta.
```

The hooks NEVER pass a caller `comparison_observation` (the gate is COMPUTED) and
always pass `movement="forward"` (reroute is CoO-only and not done here). Both
hooks write NOTHING to stdout (a hook's stdout can corrupt the agent tool stream)
and always exit 0, so a recording failure can never block the actual dispatch.
The child carries a PLAIN `parent_orchestration_ref` to the context's
`{building_id, parent_step_ref}` (record-only: no Movement, no success/quality).

### Activation: the onboard recording step wires the config

The hook FILES and their settings entries are generated by the onboard
recording step — `python3 -m brick_protocol.support.operator.onboard <host>
--recording` — which copies the TRACKED machine-neutral templates
(`brick_protocol/support/onboarding/claude-hooks/`, `brick_protocol/support/onboarding/codex-hooks/`) into
this checkout's `.claude/hooks/` + `.codex/hooks/` and merges the entries
below into `.claude/settings.local.json` / `.codex/hooks.json`, with
`BRICK_REPO_ROOT` and the hook paths computed from the ACTUAL repo root
(idempotent; a user-modified file is compared, skipped, and warned about,
never silently overwritten). 구체 JSON: PreToolUse/PostToolUse의 `Agent` matcher가 `BRICK_REPO_ROOT=<repo>`와 함께 open/close-recording.py를 호출하는 두 항목 — 원형은 `brick_protocol/support/onboarding/claude-hooks/` 템플릿 참조.

Until the onboard recording step (or an equivalent manual merge) has wired
this config, NO recording happens — on a fresh clone auto-recording is OFF.
Even once wired, the context gate keeps every not-in-a-brick spawn a no-op.
(codex side: codex additionally asks ONCE to trust this repo's
`.codex/hooks.json`; recording on the codex seam starts only after that
trust grant.)

## Honest limitations (do not over-promise)

```text
- OPT-IN ACTIVATION: the hooks do nothing until the onboard recording step
  (`brick_protocol/support/operator/onboard.py --recording`) — or an equivalent manual merge —
  has wired them into this checkout's machine config. Before that, no recording
  happens at all — the seam still works when called directly, but nothing calls
  it. A fresh clone starts with auto-recording OFF.

- HOST-SESSION ONLY: auto-recording is driven by the HOST Claude Code session's
  Agent-tool hooks. They can only see the host's own Agent-tool spawns.

- CODEX-AS-SUBPROCESS NOT-PROVEN: a provider that runs as a SEPARATE CLI
  subprocess (e.g. codex launched by the engine walker) runs in a different
  process the host cannot observe. The host's Agent-tool hooks do NOT see that
  subprocess's internal Agent-tool spawns, so "codex subagents record the same
  way" is currently NOT-PROVEN for the codex-as-subprocess path. Recording it
  would require codex-side hook wiring. State this plainly; do not claim it.
```

## Boundary

```text
Brick seam (brick_protocol/support/operator/building_operation.py)  = the engine API.
Claude Pre/PostToolUse hooks (.claude/hooks/...)      = optional Claude config,
                                                        active only once merged.
native_dispatch_brick_backstop checker profile       = the enforcement surface.
```

훅은 편의 호출자일 뿐 증명이 아니다 — the checker backstop is the enforcement surface;
the hooks are only a convenience caller.
