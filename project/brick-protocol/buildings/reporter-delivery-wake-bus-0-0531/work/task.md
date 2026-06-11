# REPORTER-DELIVERY-WAKE-BUS-0 Task Source

## Objective

Implement and dogfood a support-only reporter delivery / wake bus for Brick
Protocol Building frontiers. The bus must report Building state changes to
local inbox first, then admit provider-neutral operator wake targets, with Slack
as a later delivery sink candidate only when credential references and external
side effects are gated.

## First-Line Contract

Run this work through the admitted Brick Protocol automation path:

```text
task.md -> caller/COO-declared preset + shape -> compose_building()
-> run_building_plan(..., walker_mode="dynamic") -> evidence root
```

Do not hand-author a durable Building Plan YAML for this task.

## Context / Why Now

REPORTER-NOTIFICATION-PROJECTION-0 already admits a support-only local inbox
projection. It does not admit Slack, webhook delivery, thread wake delivery,
scheduler, queue, retry runtime, source truth, success judgment, quality
judgment, Movement authority, route input, or target selection.

The next required capability is a generic delivery / wake bus so an active
operator endpoint can be notified when a Building closes, pauses, needs a human
or COO gate, hits a checker failure, or exposes incomplete evidence.

## Deep Intake Result

Trigger Event: Smith reopened the preserved reporter / notification work after
axis-vocab cleanup and requested that the automation engine run the work through
the admitted preset / composer / run path.

User Context: Smith may be on phone and wants operator wake to reach the active
operator, which can be Codex, Claude, local inbox, or later Slack.

Desired Information / Outcome: A support-only delivery / wake bus that can
surface Building frontier evidence to a configured operator endpoint without
becoming Link Movement or source truth.

Current Workaround: Local inbox packets exist under
project/brick-protocol/status/inbox, but there is no generic operator wake sink
or external sink admission.

Pain Points: Building automation can run for a long time; without a wake/report
bus the operator must manually poll or rely on chat memory.

Blocked Decisions: Real Slack delivery and real Codex/Claude wake side effects
must remain gated unless the implementation proves a provider-neutral,
support-only sink contract and redacted setup-token reference boundary.

Primary Signals: Building frontier kind, lifecycle state, checker summary ref,
evidence root refs, required disposition owner, proof limits, not_proven, and
delivery observation.

Status Vocabulary: observed_started, observed_running, observed_closed_boundary,
observed_paused, observed_human_gate, needs_disposition,
observed_checker_failed, observed_reporter_delivery_failed.

Required Actions: Design, implement, inspect, dogfood, and close the delivery /
wake bus through declared Brick / Agent / Link rows.

Forbidden Actions: Do not let a report packet, Slack message, wake event,
checker result, dashboard projection, model review, support helper, or memory
become source truth, success judgment, quality judgment, route input, target
selection, or Movement authority.

## Required Sources

- AGENTS.md
- project/brick-protocol/status/kernel/current-working-context.md
- project/brick-protocol/status/kernel/current-brick-operating-packet-0531.md
- project/brick-protocol/status/kernel/brick-protocol-reporter-notification-projection-0-support-record-0531.md
- project/brick-protocol/status/kernel/brick-protocol-post-d-surface-recompile-0-p8-reporter-candidate-admission-plan-0531.md
- brick/templates/shapes/registry.yaml
- link/gate.yaml
- link/movement.yaml
- support/operator/reporter.py
- support/operator/report_sinks.py
- support/operator/building_operation.py
- support/operator/run.py
- support/operator/dynamic_walker.py
- support/checkers/profiles/reporter_notification_projection.yaml

## Desired Output

The Building should return implementation and verification evidence for:

- a generic delivery sink contract
- a provider-neutral operator wake target contract
- local inbox compatibility
- optional Slack sink admission boundary or explicit deferral
- negative probes proving no source truth, no Movement authority, no route input,
  no target selection, no scheduler / queue / retry runtime, and no raw secret
  persistence
- a dogfood observation that a Building frontier report can be emitted to local
  inbox and that operator wake / Slack side effects are either proven through an
  admitted fake/local sink or explicitly not_proven

## Brick / Agent / Link Boundary

Brick owns the work contracts and required return shapes.

Agent owns the performer return through the closed AgentFact shape:

```text
received_work
returned
```

Link owns Movement, target, declared gates, route replay, max_attempts, and
node_reroute_budgets.

Support may render report packets and deliver them to admitted sinks. Support
must not choose Movement, choose target, resume a route, call a driver, dispatch
new Agents, judge success, judge quality, or claim source truth.

## Read Scope / Write Scope

Read scope:

- Brick / Agent / Link contracts named in Required Sources
- admitted reporter, sink, checker, and operator support surfaces
- local Building evidence roots and inbox packets needed for dogfood

Write scope:

- support/operator/reporter.py
- support/operator/report_sinks.py
- support/checkers/check_profile.py
- support/checkers/check_package_path_admission.py
- support/checkers/profiles/reporter_notification_projection.yaml
- project/brick-protocol/status/kernel/*reporter*delivery*wake*0531*.md
- project/brick-protocol/status/inbox/*.json
- project/brick-protocol/buildings/reporter-delivery-wake-bus-0-0531/**

No commit, push, credential, token, secret, provider-native config, scheduler,
queue, retry daemon, dashboard server, or driver mutation is allowed inside the
Building run.

## Constraints / Out of Scope

- Gemini is not used for this Building.
- Real Slack delivery is out of scope unless represented by an admitted
  setup-token reference and a no-network fake/local dogfood sink.
- Real Codex or Claude thread mutation is out of scope unless represented by an
  admitted provider-neutral operator wake packet and a no-resume observation.
- Scheduler, queue, retry daemon, dashboard server, database, provider SDK/API,
  and automatic route resume are out of scope.

## Human / Review Gate

Use strict evidence gates for design, implementation, code QA, axis QA, evidence
QA, and closure. Any external side effect, raw credential requirement, or wake
behavior that could resume work must pause for caller/COO disposition instead of
running automatically.

## Honest Report Contract

Each Agent return should include the relevant subset of:

```text
observed_evidence
made_changes
blocked_or_missing_evidence
open_questions
not_proven
remaining_delta
review_needed
transition_concern_evidence
```

Agents must not return source-truth claims, success/failure verdicts, quality
judgments, Movement choices, route targets, or driver inputs.

## Done Criteria

- The Building was launched from this task source through the admitted
  preset/composer/run path.
- work/building-intake.json, work/preset-expansion.json,
  work/declared-building-plan.json, work/link-launch-policy.json, and
  work/building-map.json exist in the evidence root.
- The implementation preserves REPORTER-NOTIFICATION-PROJECTION-0 local inbox
  behavior.
- The delivery / wake bus has negative probes proving forbidden authority is
  rejected.
- Full checker profile passes after the run.
- compileall and git diff checks pass.
- Proof limits and not_proven explicitly separate local inbox, operator wake,
  Slack, and delivery reliability.

## Risk

The main risk is treating wake/report delivery as Link Movement or route resume.
The second risk is storing provider setup tokens or Slack credentials in repo
evidence. The third risk is reintroducing a declaration gap by running from a
task without persisted preset, shape, Link policy, and building-map evidence.

## Proof Limits

This task does not prove production notification reliability, real Slack
delivery, real provider thread wake behavior, external network side effects,
semantic usefulness for every future Building type, or repeated provider
reliability.
