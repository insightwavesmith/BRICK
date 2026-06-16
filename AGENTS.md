# Brick Protocol Project Instructions

This repository is the clean-room home for Brick Protocol.

Read this file before changing protocol, kernel, checker, module, contract,
runner, Agent resource, Link gate, projection, evidence, or status surfaces.
For current post-D operation also read:

```text
archive/status-kernel/current-brick-operating-packet-0531.md
archive/status-kernel/brick-protocol-post-d-surface-recompile-0-plan-0530.md
```

Detailed pre-compression admission prose is preserved as reference evidence at:

```text
archive/docs-spec/brick-protocol-agents-active-admission-history-0531.md
```

If this short constitution conflicts with older detailed prose, this file plus
the current operating packet's AGENTS-governed operating context controls active
operation. The packet is not independent constitutional authority. Historical
records remain evidence; they do not rewrite current law by implication.

## Fixed Identity

```text
Project name: Brick Protocol
Repo slug: brick-protocol
Python namespace: brick_protocol
```

Brick Protocol defines the three-axis work protocol.

Brick Protocol is not a runtime engine.

Brick Engine remains legacy/reference runtime evidence, not the source of truth.

Protocol is the project name, not a fourth axis.

## Three Axes

The only meaning axes are:

```text
Brick = work
Agent = performer
Link = transfer / carry / movement
```

Everything else is one of:

```text
axis-owned fact
axis-owned contract
expression/projection
crossing result
residual support mechanics
legacy evidence
not admitted / held
```

Support is not a fourth axis.

Runtime, engine, storage, wiki, docs, tests, checkers, memory, tools, Claude,
Gemini, Codex, generated output, dashboards, reporters, projections, and
project records are support/evidence/projection surfaces only.

They must not become:

```text
source truth
success judgment
quality judgment
Movement authority
target selector
route inventor
fourth axis
```

## Current Operating Rule

Current public run relationship:

```text
Building Plan defines the road.
support/operator/run.py walks one Building road.
support/operator/driver.py walks declared multi-Building portfolios only.
Agent Object defines the performer.
Agent Adapter connects the brain.
Link owns Movement.
```

Canonical public import:

```text
brick_protocol.support.operator.run
```

Support may walk, validate shape, record evidence, render projections, and
observe frontiers. In compact authoring,
support = expands declared compact authoring, records evidence, and walks;
it authors nothing. Support must not
choose Movement, invent route targets, create undeclared GateFacts, classify
Agent returns as success/failure, judge quality, store credential/session
bodies, or open scheduler/queue/retry runtime ownership.

## Agent Operating Model

Inside a Brick, the performing Agent freely chooses how the work gets done:

```text
do the work itself
research
spawn a native subagent
spawn a workflow
```

No role is forced to orchestrate. Only the recording is forced, and only while
a brick context is active ("브릭은 브릭을 부를 때만 진행"): while
`set_brick_context` (`support/operator/native_dispatch.py`) is set, every
native Agent-tool child spawn auto-records as a child native-dispatch Building
through the Pre/PostToolUse hooks; with the brick context cleared, child spawns
are not recorded. See `agent/skills/native-dispatch-recording/SKILL.md`
(skill:native-dispatch-recording). Auto-recording is active only once the
onboard recording step (`support/operator/onboard.py --recording`) has wired
the tracked hook templates (`support/onboarding/{claude,codex}-hooks/`) into
this checkout's `.claude`/`.codex` machine config; on a fresh clone, before
that step, nothing auto-records (the seam + checker backstop still hold).

Write capability is `tool-policy:read-write-scoped` plus an observed-write
adapter. It is admissible for worker and leader lanes — the four team leads
(pm-lead, design-lead, cto-lead, qa-lead) carry it alongside dev; the COO
stays read-only (the Movement/judgment authority carries no write tools);
reviewer lanes stay read-only. Capability is not authority. Effective write
opens only where the Brick declares its write NEED:

```text
effective_write = Brick write_scope NEED
                AND tool-policy:read-write-scoped
                AND observed-write adapter
```

The Agent match is capability >= need: a write-capable Agent may serve a
read-only Brick; lane must still equal the Brick `performer_lane_need`; only
the write NEED filters out non-writers. The provider's physical sandbox and
tool set are gated per step by the Brick write NEED — a read-only Brick yields
a read-only sandbox even for a write-capable leader.

There is no silent write grant. At live run admission (`run_building_plan`,
the dynamic walker/resume, `run_building_once`), a brick row carrying
`write_scope` must explicitly declare `requires_brick_write_scope: true` or
the run is rejected.

## FSR-0 Physical Root Layout

The active physical roots are:

```text
brick/    = Brick axis physical surface
agent/    = Agent axis physical surface
link/     = Link axis physical surface
support/  = support machine location only
project/  = project-local evidence / status destination only
```

The Python import identity router lives under:

```text
support/import_identity/brick_protocol/
```

`support/import_identity` is support mechanics only. It may route package lookup
to the active surfaces, but it must not re-export axis classes as authority, run
support mechanics, judge success or quality, choose Movement, or import
provider/runtime/storage/wiki code.

Root-level `brick_protocol/` is not an active root. The namespace remains
`brick_protocol`.

`support/` is not an axis, not a module family, not source truth, not success
judgment, not quality judgment, not Movement authority, not runtime, not
storage, and not wiki.

`project/` is the local evidence and active status destination for this
repository only. It is not source truth, not a ledger owner, not success
judgment, and not Movement authority.

Active path rebases:

```text
docs/              -> support/docs/
.status/           -> project/brick-protocol/status/
support/status/    -> project/brick-protocol/status/
tests/checkers/    -> support/checkers/
building-evidence/ -> project/brick-protocol/building-evidence/
```

Historical records may retain older path wording as historical evidence. Active
status/control references use `project/brick-protocol/status/`.

## Brick Axis

Brick owns work contracts, Building Plans, Building templates, required return
shape, comparison facts, and work composition.

Active Brick surfaces include:

```text
brick/work.py
brick/building.py
brick/comparison.py
brick/templates/**
brick/building_plans/**
```

Current template catalog:

```text
brick/templates/shapes/catalog.yaml
brick/templates/shapes/shapes.yaml
brick/templates/presets/*.md
```

The old compact registry path was removed by BRICK-TEMPLATE-CATALOG-RESTRUCTURE-0
P10. Historical evidence may mention it, but active operation uses the split
catalog above.

Brick kind vocabulary (brick/templates/bricks/<kind>/brick.md):
`development` = CTO assignment planning step; the coding step is `work` —
`development` creates worker assignments and engineering risk boundaries, and
writes NO code; `work` is THE coding brick (dev lane, write-scope NEED). (The
0610 `cto-assignment` rename was reverted 0611 by Smith ruling — a role in the
kind name is an axis smell; the short-lived name now loud-rejects naming
`building-step-template:development`.) `step_template_ref` is a legacy-named
key: it resolves to `brick/templates/bricks/<kind>/brick.md` frontmatter (the
former step-templates.yaml registry is retired).

Shape and preset selection is caller/COO declared only. The Brick template menu
is not automatic shape selection, source truth, success judgment, quality
judgment, or Movement authority.

Current post-D direction:

```text
Prefer task-first presets where the task is clear.
Reserve planning/shape steps for ambiguity, portfolio split, or admission risk.
Treat attack-QA and axis-QA as Building work, not reviewer authority.
```

Candidate matrix:

```text
archive/status-kernel/brick-protocol-agent-brick-link-preset-matrix-0-candidate-0530.md
```

P7 admits the matrix direction as current post-D operating policy:

```text
task-first presets are preferred when the task is clear
plan/design shaping is reserved for ambiguity, portfolio split, or admission risk
Codex builder, Opus attack-review, and Gemini broad-review are routing hints,
not Agent identities or authority
parallel attack-QA is Building work, not reviewer judgment authority
```

The admitted P7 status record is:

```text
archive/status-kernel/brick-protocol-post-d-surface-recompile-0-p7-agent-template-gate-preset-recompile-0531.md
```

## Agent Axis

Agent owns performer identity, receipt, and the closed returned fact.

The closed AgentFact shape is:

```text
received_work
returned
```

Agent does not self-classify:

```text
success
failure
done
not_done
failed
result
FailureFact
SuccessResult
FailureResult
```

Agent Object is an Agent-axis provider-neutral contract data resource. It may
contain only provider-neutral references:

```text
prompt_refs
skill_refs
hook_refs
tool_policy_refs
discipline_refs
adapter_refs
callable_performer_refs
```

`hook_refs` name advisory intents (never executed; every registry entry
carries `execution_opened: false`); the EXECUTING hooks are machine config
wired by the onboard recording step, not these Agent-axis records.

`callable_performer_refs` is Agent performer-callability metadata for support
adapter connection. It is not provider identity, tool execution authority,
Movement authority, success judgment, or quality judgment.

Agent Object is not a BAL fact class, not a fourth axis, not a provider runtime,
not a setup pack, not credential owner, not tool/hook executor, not source
truth, not success judgment, not quality judgment, and not Movement authority.

Active Agent resource surfaces include:

```text
agent/objects/*.yaml
agent/prompts/*.md
agent/skills/*/SKILL.md
agent/hooks/registry.yaml
agent/hooks/bindings.yaml
agent/tool_policies/*.yaml
agent/disciplines/*.md
agent/performance.py
agent/receipt.py
agent/return_fact.py
```

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
adapter:claude-local
adapter:gemini-local
```

Write capability is not owned by the adapter name or by `dev` alone. Effective
write requires Brick-declared write scope, Agent tool policy, adapter support,
and write observation; not adapter identity alone. Adapter refs expose technical
capability only. A selected adapter ref is a brain/capability connection:
without Brick `write_scope`, the request remains read-only even if that adapter
can technically write; with Brick `write_scope`, the write attempt must still
pass Agent tool policy, adapter capability, and write observation checks.
`adapter:codex-write-local` is retired from active provider-neutral adapter refs
and active Agent Objects. Adapter support remains provider-neutral, is not a
generic tool executor, and must reject forbidden commit/push side effects.

`selected_model_ref` is a Building Plan / step selection, not Agent identity,
credential proof, or model availability proof. Model-specific adapter refs are
not admitted.

Setup token, auth, credential body, provider runtime state, provider call state,
and provider-specific session ids must not be stored in Agent resources,
adapter refs, AgentFact, Building Plans, Link facts, graph packets, capture
packets, raw evidence, support records, fixtures, or projections.

## Link Axis

Link owns transfer, carry, gate sufficiency, movement, transition, route policy,
fan-out/fan-in transition meaning, and portfolio adoption policy.

Active Link surfaces include:

```text
link/movement.py
link/transfer.py
link/carry.py
link/gate.py
link/transition.py
link/route_policies/*.yaml
```

Active Movement literals:

```text
forward
reroute
```

Meaning:

```text
forward = continue on the current declared road
reroute = move to another declared Brick boundary
```

Superseded or non-Movement words:

```text
return = historical shorthand for reroute
hold = Building lifecycle / review-wait / frontier state
stop = Building lifecycle close state or disposition action
pass = judgment wording
complete / paused = lifecycle or frontier state
```

GateFact records Link-side sufficiency for public facts:

```text
stage
sufficiency
checked_public_fact
required_public_facts
missing_required_facts
reason
evidence_reference
```

GateFact reports sufficiency only. It does not choose Movement, route,
destination, rollback, retry, hold state, next target, quality, success,
failure, outcome, runtime execution, or storage truth.

Current declared gate refs:

```text
link-gate:default-transition
link-gate:strict
link-gate:human
link-gate:coo
```

`default-transition` is structural honest-return sufficiency. It may advance a
static order or exactly-one eligible next target. It must not select among
multiple candidate Buildings.

P7 base gate concepts map onto current live surfaces instead of adding hidden
gate authority:

```text
default-transition -> link-gate:default-transition
strict-evidence -> link-gate:strict
coo-review -> link-gate:coo
fan-in-wait-all -> declared graph fan-in observation/frontier, not a new GateFact literal
portfolio-policy -> support/operator/driver.py declared portfolio policy, not a new GateFact literal
human-review -> link-gate:human, exceptional only, not a base default
```

Agent `transition_concern_evidence` is non-binding evidence. Link/caller/COO may
adopt, not adopt, or pause according to declared policy. Agent does not choose
route, Movement, success, or quality.

## Building / Portfolio Boundaries

Building Plan is Brick-owned work composition. Each step carries a Brick row, an
Agent row, and a Link row with exactly one Movement and one target.

Active SEQ-0 crossing:

```text
BrickWork boundary
-> ReceiptFact / AgentFact.returned inside that Brick work
-> optional BrickComparisonFact contract observation when comparison evidence exists
-> TransferFact / CarryFact / GateFact / MovementFact / TransitionFact between Brick boundaries
-> next BrickWork boundary
```

`support/operator/run.py` is the only active public single-Building run surface.
It may walk caller-supplied Building Plans and preserve declared rows. It does
not choose next steps, invent routes, create default GateFacts, classify returns,
treat BrickComparisonFact as a verdict, execute tools/hooks outside admission,
store secrets, or use Agent/provider identity as a Link endpoint.

`support/operator/dynamic_walker.py` walks declared graph Buildings. Agent may
propose non-binding transition concerns; declared Link gate/policy adopts or
pauses; support walks and records. Per-node budgets and HOLD/frontier evidence
bound the route. Support authors no route or Movement.

Runtime mail (MAIL-REPAIR, Smith rulings 0611): a redo step scheduled by an
ADOPTED runtime reroute receives, in its Link handoff packet
(`link_handoff_refs.runtime_handoffs`), the eligible runtime rows' ADDRESSES —
narrowly (B3) the gate-adopted transition concern's `reason_refs` and, on a
raise resume, that resume's human/COO disposition row `reason_refs`. Nothing
else rides. Delivery reads the RECORDED row back from the Building ledger
(the written transition-concern step-output document / `raw/link.jsonl`),
never memory, and each entry stamps provenance as data (runtime row ref +
row kind + recorded residence). Addresses only — bodies never ride. An
address that does not resolve in the ledger is a broken ticket (B1): the walk
HOLDs loudly via the existing hold machinery; no silent delivery. The
AgentReceipt records the delivered handoff addresses as fact (B2,
`received_handoff_refs`). Plans with no eligible runtime rows keep a
byte-identical declared-refs handoff packet.

AUTO-REPAIR-REPLAY-0 admits `support/operator/auto_repair_replay.py` only for
predeclared repair/replay Building Plan execution after literal route
materialization. It may check and walk the declared repair/replay plan; it must
not invent repair work, route targets, Movement, or sufficiency.

`support/operator/driver.py::run_declared_portfolio` is the admitted bounded
declared multi-Building driver. It composes existing `run_building_plan()` once
per adopted Building over a finite caller/COO-declared candidate set. It must
not discover, invent, or choose Buildings; author Building Plans, Movement,
targets, or adoption; judge success or quality; or open scheduler/queue/retry.

Nested/child Building candidates inside a Brick are not the same as the
inter-Building portfolio driver. Child candidates are not active Buildings until
caller/COO declares them. The portfolio driver may only walk declared Building
refs under declared Link/portfolio policy.

## Support / Projection / Review Boundaries

Support connection surfaces:

```text
support/connection/agent_adapter.py
support/connection/agent_resources.py
support/connection/building_design_toolkit.py
support/connection/coo_sync.py
support/connection/mcp_projection.py
```

Support operator surfaces:

```text
support/operator/driver.py
support/operator/run.py
support/operator/dynamic_walker.py
support/operator/building_operation.py
support/operator/plan_validation.py
support/operator/evidence_assembly.py
support/operator/contracts.py
support/operator/plan_graph.py
support/operator/primitives.py
support/operator/route_materialization.py
support/operator/write_observation.py
support/operator/auto_repair_replay.py
support/operator/child_building_generation.py
support/operator/reporter.py
support/operator/report_sinks.py
```

These are support mechanics. They must not own Brick / Agent / Link meaning.

support/operator module map (vocabulary; five families, one folder):

```text
builder (materialize a declared plan):
  plan_rendering.py  composition.py  plan_graph.py  route_materialization.py
engine (walk the declared plan, record evidence):
  run.py  dynamic_walker.py  walker_*.py  gate_sequence.py  native_dispatch.py
operator surface (entry points + read-side observation):
  driver.py  onboard.py  building_operation.py  coo_operating_chain.py
  frontier_observation.py  evidence_status.py  dashboard_export.py
read-side projection (observe + project written evidence, never judge):
  ledger_projection.py  progress_projection.py  dashboard_export.py
  report_sinks.py  reporter.py
vessel declaration (project vessel declaration record + creation verb):
  project_declaration.py  project_creation.py
```

The authoritative module census is `support/checkers/module_registry.yaml`; this
map is shared vocabulary only, not the census.

Recording-folder glossary (inside every Building root):

```text
capture/   passive lifecycle EVENTS (events.jsonl)
raw/       VERBATIM streams (brick work, agent returns, link records)
evidence/  DERIVED claims (claim_trace/, manifests) + the spine projection
work/      run INPUTS (task/intake/plan packets) + per-step outputs
```

Provider-native Codex/Claude/MCP files and local skills are projections unless
explicitly admitted as Agent resources. If a projection differs from `agent/`,
`agent/` remains authoritative for Agent resources and the projection is
regenerated or reviewed as support evidence.

Projection sync terms:

```text
sync-out = agent/ -> rendered projection seed -> exact provider-native projection file
sync-in observation = provider-native projection file -> hash / presence / field observation -> drift evidence
```

Sync-in observation must not automatically write `agent/`. Useful
provider-native changes are candidate evidence for a later Building only; they
are not source truth until admitted through Brick / Agent / Link work.

Claude, Gemini, Codex subagents, reviewer output, checker output, dashboards,
reporters, memories, and generated files are support evidence only. They do not
decide Movement or project success.

## Checker / Verifier Rule

Checker/profile pass is support evidence only. It is not source truth, success
judgment, quality judgment, Movement authority, provider proof, or complete
coverage proof.

Current checker direction:

```text
prefer support/checkers/check_profile.py + profile YAML + kernel helpers
avoid new standalone check_*.py unless separately admitted
negative probes required for high-risk boundaries
```

Before any code, contract, checker, template, gate, Agent resource, projection,
or `AGENTS.md` mutation:

```text
checker-first / verifier-first:
  Which checker/verifier covers the invariant, or what admitted checker/profile
  change must come first?

implementation-closed:
  Does this edit avoid opening a new BAL fact class, module family, Movement
  literal, scheduler/queue/retry runtime, provider runtime, source truth surface,
  success/quality judge, or hidden target selector?
```

## Binding Safety Schemas

The compressed constitution keeps these safety schemas binding here. Detailed
history may explain them, but history does not replace this active contract.

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

`transition_concern_evidence` is non-binding Agent return evidence. It may
describe a concern or proposed transition, but it does not choose Movement,
route target, sufficiency, quality, success, failure, or source truth.

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

`paused` and `resumed` are lifecycle states, not Movement literals. Link
Movement remains `forward` / `reroute`. A `disposition_action` may appear only
on a human:/coo:-authored disposition row. `human:/coo:/caller:` are author prefixes, not owner values; current transition-lifecycle disposition validation
admits `human:` and `coo:` author prefixes only. `raise` extends only the
declared bounded budget for the paused boundary and requires finite positive
`budget_increment`; `forward` and `stop` must not carry `budget_increment`.
Support may observe and record the disposition, but it must not author the
disposition or choose the target.

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

Historical POST-D P1 baseline snapshot:

```text
40 profile files
check_profile.py --all green
compileall green
git diff --check green
```

Current closure at POST-D P9 and later closeout:

```text
P0-P8 committed through b3cc0da
42 profile files
check_profile.py --all green
compileall green
git diff --check green
import smoke green
reporter implementation remained absent at P9; REPORTER-NOTIFICATION-PROJECTION-0
later admits the local inbox projection slice only
```

## Current Post-D Goal

Active long goal:

```text
POST-D-SURFACE-RECOMPILE-0
```

Goal boundary:

```text
freeze feature work after D3
compress active constitution
consolidate checker/profile surfaces
re-verify and repair reaudit findings
audit support/operator and module boundaries
admit or explicitly defer Agent/Brick-template/Link-gate/preset matrix
classify active vs historical evidence
refresh projections only as support
finish with P9 strict gates and proof limits
```

P9 final strict-gate record:

```text
project/brick-protocol/status/kernel/brick-protocol-post-d-surface-recompile-0-p9-final-strict-gate-and-proof-limits-0531.md
```

Forbidden inside this goal unless a later explicit admission changes it:

```text
E features
reporter implementation
dashboard expansion
provider runtime
scheduler / queue / retry runtime
new automation behavior
```

Phase order:

```text
P0 Baseline Freeze
P1 Current Operator Packet
P2 Constitution Compression
P3 Checker/Profile Consolidation
P4 Reaudit Finding Repairs
P5 Module Boundary Audit
P6 Evidence And Status Compaction
P7 Agent / Brick Template / Link Gate / Preset / Projection Recompile
P8 Reporter Candidate Admission Plan
P9 Final Strict Gate + Proof Limits
```

Every phase uses:

```text
1. Ask six questions: Brick, Agent, Link, Support, Evidence, Admission.
2. Measure current repo evidence.
3. Delegate focused read-only review to Claude and Gemini.
4. Treat model reviews as support evidence only.
5. Main Codex reconciles findings against repo evidence.
6. Patch only when it moves the full goal closer to completion.
```

## Active Admission Index

This index points to active law families. Detailed pre-compression prose is
preserved in:

```text
archive/docs-spec/brick-protocol-agents-active-admission-history-0531.md
```

Current operator packet:

```text
archive/status-kernel/current-brick-operating-packet-0531.md
```

Core root / authority:

```text
FSR-0 Physical Root Layout
ACA-0 Axis Clarity Amendment
CA-0 Classification Authority
MAG-0 Module Admission Gate
MOVEMENT-BINARY-0
SIMPLE-RUN-0
CONNECTION-SURFACE-0
```

Agent resource / projection family:

```text
AGENT-STRUCTURE-AUTO-0
AGENT-RESOURCE-0
AGENT-RESOURCE-TOOLKIT-0
COO-SYNC-0
MCP-PROJECTION-0
CONNECTION-INSTALL-SYNC-0
AGENT-PROJECTION-SYNC-0
LEGACY-AGENT-HARNESS-SYSTEM-0
BUILDING-SKILL-PRESET-AGENT-TOOL-HARDENING-0
PROVIDER-LANE-EXPANSION-0
```

BUILDING-SKILL-PRESET-AGENT-TOOL-HARDENING-0 chain:
Building skill -> chain preset -> step template -> Agent Object -> tool / hook guardrail.

Building/run family:

```text
Building Plan Boundary
BUILDING-METHOD-0
BUILDING-ACCUMULATION-0
DEVELOPMENT-AGENT-TOOL-USE-0
BUILDING-AUTOMATION-ROADMAP-0
BUILDING-AUTOMATION-LEVEL-0
LINK-REROUTE-REPLAY-LOOP-0
BUILDING-OPERATOR-LOOP-0
BOUNDED-AGENT-PROPOSED-ROUTING-LOOP-0
BUILDING-OPERATOR-DRIVER-0
BUILDING-AUTOMATION-COMPLETE-0
```

Evidence / ledger / dashboard family:

```text
PROJECT-ORCHESTRATION-LEDGER-0
DASHBOARD-READ-SIDE-VIEW
DASHBOARD-WEB-PROJECTION-0
REPORTER-NOTIFICATION-PROJECTION-0 local inbox projection slice only
PRH-B automatic Building evidence recording
raw structured BAL evidence minimum
```

P8 records the reporter / notification candidate admission plan:

```text
project/brick-protocol/status/kernel/brick-protocol-post-d-surface-recompile-0-p8-reporter-candidate-admission-plan-0531.md
```

REPORTER-NOTIFICATION-PROJECTION-0 admits only the first support-only local
status inbox projection slice:

```text
support/operator/reporter.py
support/operator/report_sinks.py
project/brick-protocol/status/inbox/
project/brick-protocol/status/kernel/brick-protocol-reporter-notification-projection-0-support-record-0531.md
```

The admitted slice may read persisted Building / portfolio evidence, render
report packets, and fan out one packet to the local inbox sink. It must not
become source truth, success judgment, quality judgment, Movement authority,
target selector, route input, scheduler / queue / retry runtime, provider
runtime, Slack delivery, thread wake delivery, dashboard expansion, webhook
delivery, or database. The reporter profile executes negative probes for
authority-leaking report packets and unadmitted sinks; it does not merely
text-pin probe function names.

Link / routing / disposition family:

```text
LINK-ROUTE-REPLAY-0
TRUTH-PRESERVING-REROUTE-0
LINK-RETURN-REROUTE-DOGFOOD-0
LINK-DECISION-DISPOSITION-0
LINK-OWNED-AUTOMATION-0
LINK-TRANSITION-AUTHORING-1
BUILDING-PLAN-AUTHORING-2
LINK-CONNECTION-ROUTE-0
LINK-ROUTE-POLICY-RESOURCE-0
ROUTE-MATCH-AND-MATERIALIZATION-0
AUTO-REPAIR-REPLAY-0
AUTO-CHILD-BUILDING-GENERATION-0
```

Checker / validation family:

```text
CHECKER-COMMON-LIB-0
CHECKER-KERNEL-0
CHECKER-STRICT-VALIDATION-0
STEP-ROWS-THREE-AXIS-CONTRACT-REPAIR-0
OBJECTIVE-PRESERVATION-ROOT-0
HUMAN-GATE-TIER-AND-RECOVERY-0
WRITE-SCOPE-DEFAULT-EXCLUDE-0
STEP-OUTPUT-AND-ROUTE-REQUEST-0
TASK-SHAPE-AND-DESIGN-CONTRACT-0
```

Cleanup / status / historical families:

```text
REPO-CLEANUP-AND-BOUNDARY-AUDIT-0
AXIS-RECOLLAPSE-MASS-DELETE-0
BUILDING-NEXT-WAVE-AUDIT-0
SESSION-LIFECYCLE-NEXT-REPAIR-0
PROVIDER-PROJECTION-NEXT-REPAIR-0
LINK-LIFECYCLE-NEXT-AUDIT-0
CASCADE-SWEEP-0
BAR-V2-END-TO-END-DOGFOOD-0
legacy v0.1 / v0.2 / v0.3 records
```

## Current Not Proven

The following remain not proven unless later evidence closes them:

```text
safe deletion of P6 delete candidates
reporter admission need
notification / thread wake delivery reliability
report sink shape
repeated provider reliability
provider process integrity
semantic correctness of Agent transition_concern_evidence
caller/COO disposition after portfolio HOLD
production runtime
multi-human gates
fine-tuning data pipeline
complete absence of future support-authority leaks beyond audited current surfaces
Codex/Claude app reload behavior after projection refresh
Gemini-native projection shape
```

## Reporting

When reporting work, include:

```text
changed files
Building or support evidence root
commands run
narrowly proven
not_proven
review/model evidence disposition
next Movement recommendation
```

Do not describe checker green, model review, dashboard rendering, or projection
freshness as success, quality, or source truth.
