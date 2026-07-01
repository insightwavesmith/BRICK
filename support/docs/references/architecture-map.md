# Architecture map (current tree)

Date: 2026-06-24.
Status: support record / navigational reference only. NOT source truth, NOT
success judgment, NOT quality judgment, NOT Movement authority.
Supersedes the 0529 engine blueprint (the 34-checker era) as the CURRENT
architecture reference; that blueprint moved to the frozen HISTORY repo with the
rest of the unpinned historical spec and no longer resolves on this tree.

This page answers two fresh-clone questions: "which module does what?" and
"how does one run flow end to end?". Every module named here exists on the
current tree. The authoritative census is `support/checkers/module_registry.yaml`
(the count drifts as modules split/merge — read it from the registry, do not
trust a number copied here); this page is the human-readable map of the
`support/operator/` families plus the surrounding layers.

## Module families (support/operator, one folder)

builder — materialize a declared plan:

```text
plan_rendering.py              the BUILDER surface; auto-fills template nodes from a
                               work_statement ("rendering" name is historical)
composition_intent.py         materialize_building_intent: task/preset intent ->
                               declared Building Plan evidence
composition_compose.py        compose_building: final declared-plan assembly seam
composition_common.py         shared composition support primitives
composition_kinds.py          kind / role / template resolution helpers
composition_route_policy.py   route-policy derivation helpers
composition_gate_translation.py gate-stamping translation helpers
composition_graph_emit.py     graph row emission helpers
composition_graph_validate.py graph validation helpers
composition_problem.py        composition error / problem helpers
plan_graph.py                 declared plan graph projection helpers (graph -> walk order)
route_materialization.py      literal route-request matching + route Link row
                               materialization
```

engine — walk the declared plan, record evidence:

```text
run.py                       single public Building run surface (run_building_plan;
                             thin facade)
dynamic_walker.py            bounded, agent-proposed, gate-adopted dynamic graph
                             walker (thin facade)
walker_kernel.py             forward step-walk kernel
walker_step_fixture.py       per-step Brick/Link row readers + gate disposition
walker_fan_in.py             fan-out scheduling + fan-in wait-all observation/HOLD
walker_reroute_budget.py     per-target-node reroute budget + carry-budget
                             evidence refs
walker_transition_concern.py Agent non-binding transition-concern adoption
walker_hold.py               HOLD construction + paused-lifecycle injection
walker_frontier.py           adapter-error frontier write-plan + writer
walker_resume.py             resume-after-HOLD verb
walker_common.py             shared proof-limit / not-proven constants
gate_sequence.py             shared gate-sequence policy reader
native_dispatch.py           POSITION-A native-dispatch open/close recording seam
```

operator surface — entry points + operator observation:

```text
assembly.py              refined 3-axis assemble() customer front door
driver.py                bounded declared multi-Building driver + task intake
                         (run_building_intake)
onboard.py               friendly never-raising onboarding wizard flow
building_operation.py    Building operation helper mechanics (thin facade)
coo_operating_chain.py   COO operator-loop / closure read projection (closure_draft)
frontier_observation.py  Building frontier observation
evidence_status.py       evidence presence/analysis read projection
orchestration_packet.py  coo_run_orchestration read packet
checker_runner.py        allowlisted checker-profile subprocess invocation
workflow_import.py       post-hoc workflow-result recording channel (records
                         work done inside a harness Workflow the hooks can't see)
worktree_sandbox.py      disposable git-worktree sandbox for customer-facing
                         dispatch (pinned base SHA; live tree never written)
```

read-side projection — observe + project written evidence, never judge:

```text
ledger_projection.py    per-vessel orchestration-ledger packet + read-only view
progress_projection.py  per-vessel machine PROGRESS.md projection (truth layer only)
dashboard_export.py     dashboard read-side projection; delta keyed by the
                        composite (project_ref, building_id)
reporter.py             support-only report packet renderer for admitted
                        report sinks
report_sinks.py         one-shot report sink fan-out for support-only report
                        packets: local inbox, operator wake, Slack, dashboard
```

vessel declaration — project vessel declaration record + creation verb:

```text
project_declaration.py  project declaration record loader (closed key set,
                        judgment keys rejected)
project_creation.py     project creation verb (charter-first; writes the vessel
                        skeleton)
```

shared mechanics — carriers, validators, packet assembly, repair/replay:

```text
contracts.py                  support-only typed contracts for the walker (carrier)
primitives.py                 shared support primitives for the operator split
building_operation_common.py  shared primitives for Building-operation collaborators
plan_validation.py            plan row + Link declaration validation (before the
                              walk; chooses no movement)
evidence_assembly.py          evidence packet assembly for the walker (thin facade)
write_observation.py          write-scope observation for effective-write adapter
                              results
auto_repair_replay.py         executes declared repair/replay Building Plans after
                              literal route materialization
child_building_generation.py  prepares child Building Plan candidates from declared
                              remaining_delta evidence
```

Surrounding layers (census + per-row notes in `module_registry.yaml`):

```text
support/recording/    deterministic evidence writers (capture, raw, claims, spine)
support/connection/   Agent-brain / adapter / MCP / sync connection surfaces
support/checkers/     profile runner + kernel checks + declarative profiles
support/onboarding/   install script + provider-native open/close hooks
```

## Flow (a): task -> building

```text
task.md / inline statement (+ optional project_ref)
        |
        v
run_building_intake                support/operator/driver.py
  read task, confirm declared intent
        |
        v
materialize_building_intent        support/operator/composition_intent.py
  chain preset -> declared steps (preset translation)
  gate stamping (declared gate refs)
  project_ref fail-close: referenced vessel must exist and load
  writes work/declared-building-plan.json under the building root
        |
        v
run_building_plan                  support/operator/run.py
  walker walks the declared steps (dynamic_walker + walker_* kernel)
  gates measure sufficiency (gate_sequence)
  evidence spine recorded (support/recording/*)
        |
        v
closed Building boundary
  evidence under project/<id>/buildings/<building_id>/
```

For bigger Easy Building work, the official authoring/launch interface is the
`assemble()` / `build()` / `fan()` Python DSL (`support/operator/assembly.py`)
plus `run_building_plan()`. A clear task may enter as `preset_task`; design-first
or multi-lane work is constructed with the DSL, which auto-derives node/edge/
group wiring:

```text
make X
        |
        v
task intake
        |
        v
design fan-out / review
        |
        v
plan confirm
        |
        v
parallel dev lanes -> lane QA
        |
        v
final QA -> closure
        |
        v
assemble() / build() / fan()  ->  run_building_plan()
```

`brick build --graph <declared-graph-packet.json>` (hand-authored `graph_packet`
JSON) is a low-level escape hatch, headed for retirement per Global Operating
Rule 10 (`brick-6-surface-audit-repair-goal-0630.md`) — not yet fully
removable: `sibling_independence` and per-node `write_scope` narrowing are
still DSL gaps that only `--graph` covers. `run_building_intake` and
`launch_assembled_building` remain support/operator helper or advanced/internal
surfaces in this map. None of these become separate customer target selectors,
Movement authority, source truth, success judgment, or quality judgment.

## Flow (b): read side

```text
building evidence (capture/ raw/ evidence/ work/)
        |
        v
ledger_projection.py    per-vessel orchestration-ledger packet + view
progress_projection.py  per-vessel machine PROGRESS.md
dashboard_export.py     dashboard delta, composite key (project_ref, building_id)
        |
        v
reporter.py             stateless report packet render
        |
        v
report_sinks.py         one-shot fan-out to admitted sinks (local inbox first)
```

The read side observes and projects evidence already written. It never judges
success or quality and never chooses Movement.

## Where is the truth

```text
module census        support/checkers/module_registry.yaml
axis law             AGENTS.md (the constitution)
vessel declaration   project/<id>/project.json (+ README.md charter)
building plan        GENERATED artifact: work/declared-building-plan.json inside
                     each building root; chain presets are the current single
                     entry (brick/building_plans/ is the dogfood-era hand-declared
                     library, kept as history and profile pins)
split plan           project/brick-protocol/status/kernel/checker-split-map-0611.md
```
