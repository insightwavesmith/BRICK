# Customer-Ready P3 C6 QA Semantics Recast - 0627

Status: support evidence only.

This record is not source truth, success judgment, quality judgment, or Movement
authority. It records the operator observation from the first official P3 C6 run
after the QA semantics amendment.

## Live Boundary

Live checkout:

```text
/Users/smith/.brick/worktrees/struct-surgery-0623
```

Evidence root:

```text
project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-5
```

Base commit observed by the customer-facing sandbox wrapper:

```text
5f95466dd0b5ed8ca30bc727662104315ba7c50a
```

## Declared Route

The run used the customer-facing CLI wrapper, which routes through the admitted
Building intake seam:

```text
support/operator/cli.py build
-> support/operator/driver.py run_customer_building_in_sandbox
-> support/operator/driver.py run_building_intake
-> materialize_building_intent
-> support/operator/run.py run_building_plan
```

Command shape:

```text
python3 -m support.operator.cli build --json --non-interactive
  --repo /Users/smith/.brick/worktrees/struct-surgery-0623
  --task <C6 one-call customer launch proof reroute statement>
  --preset building-chain-preset:four-llm-standard-graph
  --adapter adapter:codex-local
  --real-provider
  --building-id c6-one-call-launch-0627-weekend-recast-5
  --declared-by "coo codex"
  --output-root project/brick-protocol/buildings
  --timeout 300
```

Materialized plan shape:

```text
plan_shape = graph

c6-one-call-launch-0627-weekend-recast-5-work
  building-step-template:work
  adapter:codex-local

c6-one-call-launch-0627-weekend-recast-5-codex-code-attack-qa
  building-step-template:code-attack-qa
  adapter:codex-local

c6-one-call-launch-0627-weekend-recast-5-gemini-axis-attack-qa
  building-step-template:axis-attack-qa
  adapter:gemini-local

c6-one-call-launch-0627-weekend-recast-5-closure
  building-step-template:closure
  adapter:codex-local
```

Declared Link edges:

```text
work -> codex-code-attack-qa
work -> gemini-axis-attack-qa
codex-code-attack-qa -> closure
gemini-axis-attack-qa -> closure
closure -> building boundary
```

## Raw Result

The CLI returned:

```text
frontier_kind = agent_incomplete
customer_visible_frontier_state = not_ready
customer_visible_not_ready = true
customer_visible_frontier_message =
  not ready: Building frontier is agent_incomplete; inspect evidence_root before
  treating output as customer-ready.
```

Raw evidence:

```text
raw/brick-work.jsonl
raw/agent-received.jsonl
raw/adapter-error.jsonl
raw/link.jsonl
raw/raw-manifest.json
work/step-outputs/c6-one-call-launch-0627-weekend-recast-5-work-attempt-1/adapter-error.json
evidence/claim_trace/agent/receipt_trace.json
evidence/claim_trace/link/frontier_trace.json
evidence/evidence-manifest.json
```

Observed adapter error:

```text
step_ref = c6-one-call-launch-0627-weekend-recast-5-work
adapter_ref = adapter:codex-local
agent_object_ref = agent-object:dev
error_kind = local_cli_timeout
exception_type = TimeoutExpired
agent_fact_created = false
```

No `raw/agent-return.jsonl` exists for this run.

No `raw/adapter-usage.jsonl` exists for this run.

Gemini was not reached. This run does not prove or disprove live
`adapter:gemini-local` behavior.

## Three-Axis Attribution

Evidence first:

```text
The declared graph and adapters materialized correctly, but the first work node
did not produce a returned AgentFact before the adapter timeout.
```

Brick candidate:

```text
The Brick plan shape is not the observed blocker. The updated work, Codex
code-attack QA, Gemini axis-attack QA, and Codex closure route is present in the
declared plan.
```

Agent candidate:

```text
Agent receipt exists for agent-object:dev on adapter:codex-local. A closed
AgentFact is absent because the adapter call timed out before returned payload.
```

Link candidate:

```text
Declared Link edges exist, but Link transition to the QA fan-out did not happen
because the work Agent return was absent. The observed frontier is
agent_incomplete at the work boundary.
```

Support surface:

```text
The observed blocker is on the support adapter/CLI execution surface:
adapter:codex-local through local Codex CLI timed out at the first work node.
```

Rejected one-axis shortcut:

```text
Do not classify this as a Gemini key/API failure. Gemini was never called.
Do not classify this as a QA semantics failure. The new QA graph materialized.
Do not classify this as Link route failure. Link did not receive an Agent return
to carry.
```

Chosen repair surface:

```text
Investigate adapter:codex-local local CLI timeout behavior before rerunning P3,
or declare a narrower C6 work statement/timeout policy if the caller/COO wants a
different work boundary.
```

Verification before movement:

```text
1. Inspect adapter_local_cli timeout handling and Codex command stderr/stdout
   preservation.
2. Prove Codex work step can return a closed AgentFact under the official
   customer-facing route.
3. Rerun P3 C6 and confirm the fan-out reaches both Codex code-attack QA and
   Gemini axis-attack QA.
```

## Timeout Diagnostic Follow-Up

After this HOLD, the operator added a narrow support patch so future timed-out
local CLI adapter calls preserve redacted partial stdout/stderr excerpts in the
adapter-error mapping.

Changed support surfaces:

```text
support/connection/adapter_subprocess.py
support/operator/run.py
```

Behavioral intent:

```text
Timeout still raises TimeoutExpired.
Timeout still routes to adapter-error HOLD.
No retry, scheduler, queue, Movement, route, or quality judgment is introduced.
If the subprocess wrote partial stdout/stderr before timeout, support attaches
that text to the TimeoutExpired object and run.py records redacted excerpts.
```

Verifier evidence:

```text
direct verifier:
  temp codex executable wrote partial stdout/stderr then slept
  _run_command(timeout_seconds=1) raised TimeoutExpired
  _timeout_expired_partial_output returned both streams

adapter-error mapping verifier:
  timeout_reap_reason = timeout
  timeout_stdout_excerpt redacted credential-looking text
  timeout_stderr_excerpt redacted session-looking text

targeted checks:
  check_building_lifecycle_path_shape --target c6-one-call-launch-0627-weekend-recast-5 = green
  check_building_map_graph --target c6-one-call-launch-0627-weekend-recast-5/work/building-map.json = green
  check_cli_runner_stdin_devnull = green
  compileall support/connection support/operator = green
  git diff --check for touched timeout/status files = green
```

Profile caveat:

```text
agent_axis_behavioral and building_automation profile sweeps are not clean in
this dirty checkout because of pre-existing untracked/stale evidence roots:
  project/brick-protocol/buildings/c6-one-call-launch-0627-weekend-recast-3-composed-plan.json
  project/brick-protocol/buildings/gemini-adapter-fileread-0626/work/building-map.json

Those failures are support evidence about the checkout state, not proof that the
timeout diagnostic patch failed.
```

## Movement

Current P3 Movement:

```text
HOLD
```

Reason:

```text
The updated C6 graph was declared through the official Building route, but the
first Codex work step ended at agent_incomplete due local_cli_timeout. No
customer-ready claim is proven.
```

Next admissible move:

```text
REROUTE to adapter-local timeout diagnosis, then rerun P3 C6 after the first
work step can return AgentFact evidence.
```

## Not Proven

```text
P3 C6 closure
Gemini-local live provider success
dual QA execution
Codex closure execution
fresh-machine install/onboard
customer-ready self-dogfood proof
provider reliability
semantic quality of any Agent work
```
