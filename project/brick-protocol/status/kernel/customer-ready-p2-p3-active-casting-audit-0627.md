# Customer-Ready P2/P3 Active Casting Audit - 0627

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, or Movement
authority.

## Scope

Goal phases:

- P2 - Agent Casting And Preset Recast
- P3 - C6 One-Call Launch Close

Focused audit:

- Confirm whether the committed weekend Codex/Gemini recast is visible in the
  active rematerialized C6 Building root.
- Separate step-level adapter selection from plan-level default metadata.
- Confirm the current P3 frontier without treating the frontier as success or
  quality judgment.

## Live Checkout

- Worktree: `/Users/smith/.brick/worktrees/struct-surgery-0623`
- HEAD: `137f0e8 Recast weekend Codex Gemini building lanes`
- Active Building root:
  `project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-2`
- Building id: `c6-one-call-launch-0627-weekend-recast-2`

## Building Plan Evidence

Source:

- `project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-2/declared-building-plan.json`

Observed plan metadata:

- `plan_shape`: `graph`
- `chain_preset_ref`: `building-chain-preset:four-llm-standard-graph`
- plan-level `selected_adapter_ref`: `adapter:codex-local`
- plan-level `selected_model_ref`: `model:codex:default`

Step-level active casting:

```text
1. c6-one-call-launch-0627-weekend-recast-2-work
   template: building-step-template:work
   adapter: adapter:codex-local
   model: model:codex:default
   agent: agent-object:dev
   write_scope: true

2. c6-one-call-launch-0627-weekend-recast-2-codex-structure-qa
   template: building-step-template:review
   adapter: adapter:codex-local
   model: model:codex:default
   agent: agent-object:qa-lead
   write_scope: false

3. c6-one-call-launch-0627-weekend-recast-2-gemini-broad-review
   template: building-step-template:inspect
   adapter: adapter:gemini-local
   model: model:gemini:default
   agent: agent-object:inspector
   write_scope: false

4. c6-one-call-launch-0627-weekend-recast-2-closure
   template: building-step-template:closure
   adapter: adapter:codex-local
   model: model:codex:default
   agent: agent-object:coo
   write_scope: false
```

Step adapter counts:

```text
adapter:codex-local: 3
adapter:gemini-local: 1
```

Step model counts:

```text
model:codex:default: 3
model:gemini:default: 1
```

Active step values containing `claude`: 0.

Operator caveat:

- The plan also carries plan-level default `selected_adapter_ref` and
  `selected_model_ref` metadata for the primary Codex path. That metadata must
  not be mixed into step-level adapter counts.
- A prior support note may appear to count Codex four times if the plan-level
  default and the three Codex steps are added together. This audit uses the
  stricter step-level count for active execution casting.

## Raw Execution Evidence

Sources:

- `raw/agent-received.jsonl`
- `raw/agent-return.jsonl`
- `raw/adapter-usage.jsonl`
- `raw/adapter-error.jsonl`
- `raw/link.jsonl`

Observed raw facts:

- Agent receipts exist for:
  - Codex work
  - Codex structure QA
  - Gemini broad review
- Agent returns exist for:
  - Codex work
  - Codex structure QA
- Agent return does not exist for:
  - Gemini broad review
  - Codex closure
- Adapter usage records exist for:
  - Codex work
  - Codex structure QA
- Adapter error exists for:
  - Gemini broad review

Gemini adapter error:

```text
step_ref: c6-one-call-launch-0627-weekend-recast-2-gemini-broad-review
adapter_ref: adapter:gemini-local
agent_object_ref: agent-object:inspector
selected_model_ref: model:gemini:default
error_kind: local_cli_nonzero
message_excerpt contains: return_code=144
```

Frontier:

```text
frontier_kind: agent_incomplete
step_ref: c6-one-call-launch-0627-weekend-recast-2-gemini-broad-review
adapter_error_ref: adapter-error:c6-one-call-launch-0627-weekend-recast-2-gemini-broad-review:attempt-1
transition_lifecycle_state: paused
transition_lifecycle_required_disposition_owner: caller-or-coo
transition_lifecycle_pending_target_ref: brick-c6-one-call-launch-0627-weekend-recast-2-gemini-broad-review
```

## Three-Axis Attribution

Evidence first:

- The active C6 Building root exists and contains a graph plan.
- The plan includes Codex work, Codex QA, Gemini inspect/review, and Codex
  closure steps.
- Raw execution reached the Gemini Building Agent step and then paused on
  adapter error before AgentFact.returned for that step.

Brick candidate:

- The Brick plan composition is present and declares the intended weekend C6
  recast shape. The work statement explicitly asks for Codex work, Codex
  structure QA, Gemini broad review as a Building Agent step, and Codex closure.

Agent candidate:

- Agent rows bind `agent-object:dev`, `agent-object:qa-lead`,
  `agent-object:inspector`, and `agent-object:coo` to the four active steps.
  The Gemini inspector receipt exists, but its return is missing because the
  adapter failed.

Link candidate:

- Link did not choose a new route or Movement. The frontier records a paused
  lifecycle at the Gemini broad review boundary and requires caller/COO
  disposition.

Support surface:

- `support/operator/run.py` family Building evidence walked the declared road
  and recorded raw frontier evidence.
- `support/connection/adapter_local_cli.py` connected the Gemini-local brain
  surface and returned a nonzero adapter error.

Rejected one-axis shortcut:

- This is not evidenced as a hidden Claude dependency, stale C6 continuation,
  Link route invention, Slack delivery issue, or generic adapter-authority
  defect. The active plan has no Claude step selection, and execution paused at
  the Gemini-local provider/auth surface.

Chosen repair surface:

- No new code repair is selected by this audit. The current P3 blocker remains
  external Gemini-local provider/auth until credentials/client are fixed or the
  caller/COO declares a different non-Claude route.

Verification before movement:

- Re-run the rematerialized C6 Building after Gemini-local auth/client repair,
  or after an explicit caller/COO reroute.
- Require Gemini QA evidence inside the Building root before Codex closure can
  be counted as P3 closure evidence.

## Commands Run

```text
pwd && git rev-parse --show-toplevel && git status --short && git log -1 --oneline
python3 - <<'PY'
...parse declared-building-plan.json brick_steps and raw JSONL evidence...
PY
```

## Narrowly Proven

- The active P3 C6 Building root is a rematerialized graph plan, not a direct
  Gemini helper call.
- Step-level active casting is Codex work, Codex QA, Gemini Building inspect,
  Codex closure.
- Step-level active adapter counts are Codex 3, Gemini 1, Claude 0.
- The P3 frontier is `agent_incomplete` at the Gemini Building Agent step.
- The current P3 blocker is non-Claude: `adapter:gemini-local`
  `local_cli_nonzero`, with `return_code=144` carried inside the recorded
  `message_excerpt`.

## Not Proven

- Gemini Building QA returned evidence.
- Codex closure executed after Gemini QA.
- C6 one-call customer launch closed.
- Customer-ready proof.
- Fresh-machine proof.
- Full `check_profile.py --all`.
- Validity of the currently configured Gemini API key.

## Movement

P2 active casting audit: FORWARD as support evidence.

P3 active casting audit: FORWARD as support evidence.

Global customer-ready goal: HOLD until Gemini-local provider/auth is repaired or
caller/COO declares a different non-Claude route.
