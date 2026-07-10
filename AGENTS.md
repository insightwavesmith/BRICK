# Brick Protocol Project Instructions

This repository is the clean-room home for Brick Protocol. Read this file before
changing protocol, kernel, checker, module, contract, runner, Agent resource,
Link gate, projection, evidence, or status surfaces.

Law (the invariant rules) lives in root `BRICK-CONSTITUTION.md` (three axes,
support records facts and never judges, minimal graph, Rules 1-13; ratified by
Smith 0702, amended 0705/0706/0708). This file carries operating detail —
identity, paths, procedures, contract surfaces. Where the two conflict, the
constitution wins.

If this operating instruction set conflicts with older detailed prose, this file
plus the current operating packet's AGENTS-governed operating context controls
active operation. The packet is not independent constitutional authority.
Historical records remain evidence; they do not rewrite current law by
implication.

## Fixed Identity

```text
Project name: Brick Protocol
Repo slug: brick-protocol
Python namespace: brick_protocol
```

Brick Protocol defines the three-axis work protocol. Brick Protocol is not a
runtime engine. Brick Engine remains legacy/reference runtime evidence, not the
source of truth. Protocol is the project name, not a fourth axis.

## Three Axes

The only meaning axes are:

```text
Brick = work
Agent = performer
Link = transfer / carry / movement
```

Everything else is an axis-owned fact/contract, expression/projection, crossing
result, residual support mechanic, legacy evidence, or not admitted / held.

Support is not a fourth axis.

Runtime, engine, storage, wiki, docs, tests, checkers, memory, tools, Claude,
Gemini, Codex, generated output, dashboards, reporters, projections, and
project records are brick_protocol/support/evidence/projection surfaces only. They must not
become source truth, success judgment, quality judgment, Movement authority,
target selector, route inventor, or fourth axis.

Current public run relationship:

```text
Building Plan defines the road.
brick_protocol/support/operator/run.py walks one Building road.
brick_protocol/support/operator/driver.py walks declared multi-Building portfolios only.
Agent Object defines the performer.
Agent Adapter connects the brain.
Link owns Movement.
```

Customer/startup authority is narrower than the internal support call graph:

```text
Official customer execution entrances = brick build | brick resume --decl
brick init = bootstrap/example setup only; not Building execution
declared_portfolio = declared route-family plan kind
declared_repair_replay = declared route-family plan kind
```

`run_declared_portfolio` and `run_declared_auto_repair_replay_case` are
Builder-internal declared route-family executors, not customer/startup
entrances. `_coo_run_orchestration_packet`, lowering/materialization helpers,
and `fire()` are Builder-internal material as well. Their presence in the
support call graph does not create another public execution entrance.

Canonical public import:

```text
brick_protocol.support.operator.run
```

In compact authoring, support = expands declared compact authoring, records evidence, and walks;
it authors nothing. Support must not choose Movement,
invent route targets, create undeclared GateFacts, classify Agent returns as
success/failure, judge quality, store credential/session bodies, or open
scheduler/queue/retry runtime ownership.

## Physical Roots

Active physical roots:

```text
brick_protocol/brick/    = Brick axis physical surface
brick_protocol/agent/    = Agent axis physical surface
brick_protocol/link/     = Link axis physical surface
brick_protocol/support/  = support machine location only
project/  = project-local evidence / status destination only
```

The Python package root is now the physical `brick_protocol/` tree.
The namespace remains `brick_protocol`; legacy top-level `brick/`, `agent/`,
`link/`, and `support/` roots are no longer active import roots.

Active path rebases:

```text
docs/              -> brick_protocol/support/docs/
.status/           -> project/brick-protocol/status/
brick_protocol/support/status/    -> project/brick-protocol/status/
tests/checkers/    -> brick_protocol/support/checkers/
building-evidence/ -> project/brick-protocol/building-evidence/
```

Historical records may retain older path wording as historical evidence. Active
status/control references use `project/brick-protocol/status/`.

## Brick Axis

Brick owns work contracts, Building Plans, Building templates, required return
shape, comparison facts, and work composition. Active Brick surfaces include
`brick_protocol/brick/work.py`, `brick_protocol/brick/building.py`, `brick_protocol/brick/comparison.py`,
`brick_protocol/brick/templates/**`, and `brick_protocol/brick/building_plans/**`.

Current template catalog:

```text
brick_protocol/brick/templates/shapes/catalog.yaml
brick_protocol/brick/templates/shapes/shapes.yaml
brick_protocol/brick/templates/presets/*.md
```

`development` is CTO assignment planning and writes no code. `work` is the
coding Brick and requires a dev lane write-scope NEED. `step_template_ref` is a
legacy-named key resolving to `brick_protocol/brick/templates/bricks/<kind>/brick.md`.

P7 admits the matrix direction as current post-D operating policy:

```text
task-first presets are preferred when the task is clear
plan/design shaping is reserved for ambiguity, portfolio split, or admission risk
Codex builder, Opus attack-review, and Gemini broad-review are routing hints
parallel attack-QA is Building work, not reviewer judgment authority
fan-in-wait-all -> declared graph fan-in observation/frontier
portfolio-policy -> brick_protocol/support/operator/driver.py declared portfolio policy
```

## Agent Axis

Agent owns performer identity, receipt, and the closed returned fact:

```text
AgentFact(received_work, returned)
```

Agent does not self-classify success, failure, done, not_done, failed, result,
FailureFact, SuccessResult, or FailureResult.

Agent Object is a provider-neutral contract data resource. It must contain only provider-neutral references:

```text
object_ref
name
lane
callable_performer_refs
prompt_refs
skill_refs
hook_refs
tool_policy_refs
discipline_refs
adapter_refs
preferred_adapter_ref
preferred_model_ref
preferred_reasoning_effort_ref
```

`hook_refs` are advisory intents only; registry entries carry
`execution_opened: false`. Executing hooks are machine config wired by
`brick_protocol/support/operator/onboard.py --recording`, not by Agent-axis records.

Current Agent Object roles:

```text
coo
pm-lead
design-lead
cto-lead
dev
qa-lead
qa
inspector
```

Current provider-neutral adapter refs:

```text
adapter:local
adapter:codex-local
adapter:codex-fugu-local
adapter:claude-local
adapter:gemini-local
adapter:chat-session
```

Write capability is not owned by the adapter name or by `dev` alone. Effective
write requires Brick-declared write scope, Agent tool policy, adapter support,
adapter capability, and write observation checks; not adapter identity alone.
Adapter refs expose technical capability only. A selected adapter ref is a
brain/capability connection; selected adapter ref is a brain/capability
connection: the request remains read-only even if that adapter
can write unless the Brick declares `write_scope`; with Brick `write_scope`, the write attempt must still
pass Agent policy, adapter capability, and write observation checks.

`selected_model_ref` is a Building Plan / step selection, not Agent identity,
credential proof, or model availability proof. `preferred_model_ref` is a soft
lane-preferred default and must match the provider of `preferred_adapter_ref`.
Model-specific adapter refs are not admitted.

Projection sync terms:

```text
sync-out = brick_protocol/agent/ -> rendered projection seed -> exact provider-native projection file
sync-in observation = provider-native projection file -> hash / presence / field observation -> drift evidence
```

Sync-in observation must not automatically write `brick_protocol/agent/`.
AGENT-PROJECTION-SYNC-0 is an Agent resource/projection admission family.

Setup token, auth, credential body, provider runtime state, provider call state,
and provider-specific session ids must not be stored in Agent resources,
adapter refs, AgentFact, Building Plans, Link facts, graph packets, capture
packets, raw evidence, support records, fixtures, or projections.

## Link Axis

Link owns transfer, carry, gate sufficiency, movement, transition, route policy,
fan-out/fan-in transition meaning, and portfolio adoption policy. Active
Movement literals:

```text
forward
reroute
```

`forward` continues on the current declared road. `reroute` moves to another
declared Brick boundary. `return` is historical shorthand for reroute. `hold`,
`stop`, `pass`, `complete`, and `paused` are lifecycle or judgment words, not
Movement.

GateFact records Link-side sufficiency only:

```text
stage
sufficiency
checked_public_fact
required_public_facts
missing_required_facts
reason
evidence_reference
```

GateFact does not choose Movement, route, destination, rollback, retry, hold
state, next target, quality, success, failure, outcome, runtime execution, or
storage truth.

Declared gate refs:

```text
link-gate:default-transition
link-gate:strict
link-gate:human
link-gate:coo
link-gate:expansion-approval
```

LINK-DECISION-DISPOSITION-0 and LINK-OWNED-AUTOMATION-0 remain Link/routing
admissions. Agent `transition_concern_evidence` is non-binding evidence; it may
describe a concern or proposed transition, but it does not choose Movement,
route target, sufficiency, quality, success, failure, or source truth.

## Building And Portfolio Boundaries

Building Plan is Brick-owned work composition. Each step carries a Brick row,
an Agent row, and a Link row with exactly one Movement and one target.

Active crossing:

```text
BrickWork boundary
-> ReceiptFact / AgentFact.returned inside that Brick work
-> optional BrickComparisonFact contract observation when comparison evidence exists
-> TransferFact / CarryFact / GateFact / MovementFact / TransitionFact between Brick boundaries
-> next BrickWork boundary
```

`brick_protocol/support/operator/run.py` is the only active public single-Building run surface.
It may walk caller-supplied Building Plans and preserve declared rows. It does
not choose next steps, invent routes, create default GateFacts, classify
returns, treat BrickComparisonFact as a verdict, execute tools/hooks outside
admission, store secrets, or use Agent/provider identity as a Link endpoint.

`brick_protocol/support/operator/dynamic_walker.py` walks declared graph Buildings under
BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0. Agent may propose non-binding
transition concerns; declared Link gate/policy adopts or pauses; support walks
and records. Per-node budgets and HOLD/frontier evidence bound the route.
Support authors no route or Movement.

Fan-out sibling-evidence independence: same-parent fan-out siblings must each
hold their own independent evidence body. Sequential/chain Bricks share
carry/spine by design.

Runtime mail delivers only recorded row addresses through
`link_handoff_refs.runtime_handoffs`. A redo step scheduled by an adopted
runtime reroute receives the eligible runtime rows' addresses, not bodies. An
address that does not resolve in the ledger causes a HOLD through existing
machinery. AgentReceipt records delivered addresses as
`received_handoff_refs`.

AUTO-REPAIR-REPLAY-0 admits `brick_protocol/support/operator/auto_repair_replay.py` only for
predeclared repair/replay Building Plan execution after literal route
materialization. It may check and walk the declared repair/replay Building Plan;
it must not invent repair work, route targets, Movement, or sufficiency.

BUILDING-OPERATOR-DRIVER-0 admits `brick_protocol/support/operator/driver.py::run_declared_portfolio`
as the bounded declared multi-Building driver. It composes existing
`run_building_plan()` once per adopted Building over a finite caller/COO-declared
candidate set. It must not discover, invent, or choose Buildings; author
Building Plans, Movement, targets, or adoption; judge success or quality; or
open scheduler/queue/retry.

Nested/child Building candidate records inside a Brick are not active Buildings
until caller/COO declaration. `brick_protocol/support/operator/child_building_generation.py`
may support candidate generation only inside its admitted boundary.

## Support And Projection Boundaries

Support connection surfaces include `brick_protocol/support/connection/agent_adapter.py`,
`brick_protocol/support/connection/agent_resources.py`,
`brick_protocol/support/connection/building_design_toolkit.py`,
`brick_protocol/support/connection/coo_sync.py`, and `brick_protocol/support/connection/mcp_projection.py`.

Support operator surfaces include `brick_protocol/support/operator/driver.py`,
`brick_protocol/support/operator/run.py`, `brick_protocol/support/operator/dynamic_walker.py`,
`brick_protocol/support/operator/building_operation.py`, `brick_protocol/support/operator/plan_validation.py`,
`brick_protocol/support/operator/evidence_assembly.py`, `brick_protocol/support/operator/contracts.py`,
`brick_protocol/support/operator/plan_graph.py`, `brick_protocol/support/operator/primitives.py`,
`brick_protocol/support/operator/route_materialization.py`,
`brick_protocol/support/operator/write_observation.py`,
`brick_protocol/support/operator/auto_repair_replay.py`,
`brick_protocol/support/operator/child_building_generation.py`,
`brick_protocol/support/operator/reporter.py`, and `brick_protocol/support/operator/report_sinks.py`.

Recording-folder glossary inside every Building root:

```text
capture/   passive lifecycle EVENTS (events.jsonl)
raw/       VERBATIM streams (brick work, agent returns, link records)
evidence/  DERIVED claims (claim_trace/, manifests) + the spine projection
work/      run INPUTS (task/intake/plan packets) + per-step outputs
```

Claude, Gemini, Codex subagents, reviewer output, checker output, dashboards,
reporters, memories, and generated files are support evidence only. They do
not decide Movement or project success.

DASHBOARD-READ-SIDE-VIEW and PROJECT-ORCHESTRATION-LEDGER-0 are read-side
projection admissions over already-written evidence. They are not ledger owner,
dashboard runtime, Movement authority, source truth, success judgment, or
quality judgment.

REPORTER-NOTIFICATION-PROJECTION-0 four support-only report sinks:

```text
brick_protocol/support/operator/reporter.py
brick_protocol/support/operator/report_sinks.py
project/brick-protocol/status/inbox/
report-sink:local-inbox
report-sink:operator-wake-local
report-sink:slack
report-sink:dashboard
```

The admitted slice may read persisted Building / portfolio evidence, render
report packets, and fan out one packet to admitted sinks. Slack and dashboard
real delivery are gated by environment credentials plus the caller-declared
`allow_real_slack_delivery` / `allow_real_dashboard_delivery` flags. Dry-run /
non-delivery remains the default. Observations record only environment presence
and status classes, never credentials or response bodies. It must not become
source truth, success judgment, quality judgment, Movement authority, target
selector, route input, scheduler / queue / retry runtime; target selector, route input, scheduler / queue / retry runtime, provider runtime,
webhook delivery, database, source-truth write-back, or any fifth sink. The
reporter remains stateless synchronous render -> sink support projection with a
four-sink ceiling.

## Checker And Verifier Rule

Checker/profile pass is support evidence only. It is not source truth, success
judgment, quality judgment, Movement authority, provider proof, or complete
coverage proof.

Before code, contract, checker, template, gate, Agent resource, projection, or
AGENTS.md mutation:

```text
checker-first / verifier-first:
  Which checker/verifier covers the invariant, or what admitted checker/profile
  change must come first?

implementation-closed:
  Does this edit avoid opening a new BAL fact class, module family, Movement
  literal, scheduler/queue/retry runtime, provider runtime, source truth surface,
  success/quality judge, or hidden target selector?
```

Prefer `brick_protocol/support/checkers/check_profile.py` + profile YAML + kernel helpers.
Avoid new standalone `check_*.py` unless separately admitted. Negative probes
are required for high-risk boundaries.

Checker-companion development principle / 체커-동반 개발 원칙: every new
feature or declaration surface lands with the checker or mutation-RED probe
that gates that surface. If the checker/probe cannot land in the same slice,
the gap must be named as support evidence and not treated as enforcement. This
principle aligns with the existing make-a-brick and make-a-gate procedures; it
does not admit a new checker family or gate by itself.

Ask six questions: Brick, Agent, Link, Support, Evidence, Admission.

## Binding Safety Schemas

Agent transition concerns use the closed `concern_kind` vocabulary:

```text
upstream_gap
boundary_mismatch
insufficient_input
replay_needed
unknown
design_gap
implementation_gap
verification_gap
```

Link transition lifecycle evidence uses only this active shape:

```text
transition_lifecycle:
  state: paused | resumed
  progress_state: in_progress
  required_disposition_owner: caller | coo | caller-or-coo
  pending_target_ref: <declared Brick boundary ref>
  disposition_action: raise | forward | stop | reroute
  budget_increment: <finite positive integer, required only for raise>
```

`paused` and `resumed` are lifecycle states, not Movement literals.
`disposition_action` may appear only on a human:/coo:-authored disposition row.
`human:/coo:/caller:` are author prefixes, not owner values; current validation
admits `human:` and `coo:` author prefixes only. `raise` extends only the
declared bounded budget and requires finite positive `budget_increment`.
`forward` and `stop` must not carry `budget_increment`.

Human gate MUST-HALT conditions:

```text
credential / secret exposure risk
destructive or irreversible filesystem / git / external action
no declared Brick / Agent / Link basis for the next Movement
new module, folder, surface, fact class, Movement literal, provider runtime,
  scheduler / queue / retry runtime, source truth, success judge, quality judge,
  or target selector admission
AGENTS.md constitutional wording or current operating packet mutation
```

Impact tiers:

```text
low = wording or support-record clarification that cannot change operation
medium = checker/profile/status/projection wording that can affect future agents
high = AGENTS.md/current-packet constitutional wording, active contract,
       module/surface admission, fact-class shape, Movement/gate/routing rule,
       destructive action, credential exposure, or irreversible external effect
```

High-impact work requires explicit Smith/human disposition before it is treated
as closed. Model review, checker green, dashboard rendering, projection
freshness, and support records are evidence only; they do not replace the human
gate.

## Active Admission Index

Core: FSR-0 Physical Root Layout, ACA-0 Axis Clarity Amendment, CA-0
Classification Authority, MAG-0 Module Admission Gate, MOVEMENT-BINARY-0,
SIMPLE-RUN-0, CONNECTION-SURFACE-0.

Agent/projection: AGENT-STRUCTURE-AUTO-0, AGENT-RESOURCE-0,
AGENT-RESOURCE-TOOLKIT-0, COO-SYNC-0, MCP-PROJECTION-0,
CONNECTION-INSTALL-SYNC-0, AGENT-PROJECTION-SYNC-0,
LEGACY-AGENT-HARNESS-SYSTEM-0,
BUILDING-SKILL-PRESET-AGENT-TOOL-HARDENING-0,
PROVIDER-LANE-EXPANSION-0.

BUILDING-SKILL-PRESET-AGENT-TOOL-HARDENING-0 chain:
Building skill -> chain preset -> step template -> Agent Object -> tool / hook guardrail.

Building/run: Building Plan Boundary, BUILDING-METHOD-0,
BUILDING-ACCUMULATION-0, DEVELOPMENT-AGENT-TOOL-USE-0,
BUILDING-AUTOMATION-ROADMAP-0, BUILDING-AUTOMATION-LEVEL-0,
LINK-REROUTE-REPLAY-LOOP-0, BUILDING-OPERATOR-LOOP-0,
BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0, BUILDING-OPERATOR-DRIVER-0,
BUILDING-AUTOMATION-COMPLETE-0.

Evidence/projection: PROJECT-ORCHESTRATION-LEDGER-0,
DASHBOARD-READ-SIDE-VIEW, DASHBOARD-WEB-PROJECTION-0,
REPORTER-NOTIFICATION-PROJECTION-0 four support-only report sinks, PRH-B
automatic Building evidence recording, raw structured BAL evidence minimum.

Link/routing: LINK-ROUTE-REPLAY-0, TRUTH-PRESERVING-REROUTE-0,
LINK-RETURN-REROUTE-DOGFOOD-0, LINK-DECISION-DISPOSITION-0,
LINK-OWNED-AUTOMATION-0, LINK-TRANSITION-AUTHORING-1,
BUILDING-PLAN-AUTHORING-2, LINK-CONNECTION-ROUTE-0,
LINK-ROUTE-POLICY-RESOURCE-0, ROUTE-MATCH-AND-MATERIALIZATION-0,
AUTO-REPAIR-REPLAY-0, AUTO-CHILD-BUILDING-GENERATION-0.

Checker/validation: CHECKER-COMMON-LIB-0, CHECKER-KERNEL-0,
CHECKER-STRICT-VALIDATION-0, STEP-ROWS-THREE-AXIS-CONTRACT-REPAIR-0,
OBJECTIVE-PRESERVATION-ROOT-0, HUMAN-GATE-TIER-AND-RECOVERY-0,
WRITE-SCOPE-DEFAULT-EXCLUDE-0, STEP-OUTPUT-AND-ROUTE-REQUEST-0,
TASK-SHAPE-AND-DESIGN-CONTRACT-0.

Cleanup/status/history: REPO-CLEANUP-AND-BOUNDARY-AUDIT-0,
AXIS-RECOLLAPSE-MASS-DELETE-0, BUILDING-NEXT-WAVE-AUDIT-0,
SESSION-LIFECYCLE-NEXT-REPAIR-0, PROVIDER-PROJECTION-NEXT-REPAIR-0,
LINK-LIFECYCLE-NEXT-AUDIT-0, CASCADE-SWEEP-0,
BAR-V2-END-TO-END-DOGFOOD-0, legacy v0.1 / v0.2 / v0.3 records.

Current not proven remains status evidence only:

```text
safe deletion of P6 delete candidates
reporter admission need
notification / thread wake delivery reliability
report sink shape
repeated provider reliability
provider process integrity
semantic correctness of Agent transition_concern_evidence
```
