# ⑩a Cleanup Scope / Invariants — 0709

Status: support evidence only. This document does not delete, move, archive,
rename, implement, approve success/quality, choose Movement, or create source
truth. It defines the cleanup/customer-UX scope and invariants for later declared
Buildings under the 0708 unified GOAL.

## 0. Purpose

This is phase ⑩a from:

```text
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

The user request behind ⑩ is to clean up the COO order chain, skills/prompts,
directory duplication, project vessel separation, and customer-facing UX after
⑤ Building Call and ⑥ Route V2 R0/R1/R2 closure. This phase is only a scope and
invariants record so later Buildings do not delete or move load-bearing surfaces
by assumption.

## 1. Three-axis frame

```text
Brick:
  Owns task sources, work contracts, Building Plans, templates, presets,
  required returns, and cleanup work definitions.

Agent:
  Owns Agent Objects, prompts, skills, hooks, tool-policy refs, disciplines,
  and closed AgentFact(received_work, returned). Agent skills are the operating
  source for performer behavior.

Link:
  Owns transfer/carry/gate/Movement/route policy and route replay facts.
  Movement remains forward | reroute only. hold/paused/blocked/waiting are
  lifecycle or gate states, not Movement.

Support / project evidence:
  Support records and projects evidence; it is not a fourth axis. project/ is a
  project-local evidence/status destination and not source truth.
```

## 2. Live tree measurement snapshot

Observed on live repo at HEAD `a1cbad348` before this ⑩a document:

```text
brick_protocol/brick/building_plans/         exists=true files=4
brick_protocol/brick/templates/blocks/       exists=true files=8
brick_protocol/brick/templates/shapes/       exists=true files=2
brick_protocol/brick/templates/tasks/        exists=true files=2
brick_protocol/brick/templates/skills/       exists=true files=8
brick_protocol/agent/skills/                 exists=true files=19
project/brick-protocol/                      exists=true files=6851
```

Reference scan summary:

```text
building_plans hits: 35
  observed refs include AGENTS.md, check_package_path_admission.py,
  check_profile.py, adapter_capability checks, and fixture plans.

templates/blocks hits: 10
  current direct support/operator runtime refs were not observed in the scan,
  but status/planning docs preserve block/motif meaning. Treat as cleanup /
  archive candidate, not deletion proof.

templates/shapes hits: 90
  observed refs include AGENTS.md, task_intake, template catalog readers,
  shape catalog/profile/checker surfaces. Load-bearing; do not delete.

templates/tasks hits: 79
  observed refs include task_intake and catalog entries. Brick-owned task-source
  template surface; keep unless a later Building proves a replacement.

templates/skills hits: 64
  observed refs include agent README, brick README, APPLY-LIST, and ship-copy
  skill surfaces. This is an intentional sync/ship-copy surface, not blind dup.

agent/skills hits: 186
  Agent-axis operating skill source. Later cleanup may repair drift, not delete.

project-creation hits: 44
  project creation skill/support already exist.

progress_projection hits: 30
  progress projection support already exists.
```

Measurement command pattern:

```text
python3 one-off pathlib/git-grep scan over AGENTS.md, README.md,
brick_protocol/**, project/**
```

Proof limit: counts are a 0709 snapshot, not a permanent dependency graph or a
source-truth classification.

## 3. Surface classification and cleanup invariant

| Surface | Current classification | ⑩ invariant | Later phase |
|---|---|---|---|
| `brick_protocol/brick/building_plans/` | Brick-owned execution-plan fixtures/plans; load-bearing refs observed | No simple move/git-mv. Any relocation needs reader/checker/admission migration in one declared Building. | ⑩c |
| `brick_protocol/brick/templates/blocks/` | Brick template/motif corpus candidate; direct runtime load not proven | Do not delete. First create retained/archive/superseded map and prove no load-bearing refs. | ⑩b |
| `brick_protocol/brick/templates/shapes/` | Brick template catalog; load-bearing | Keep. Deletion/replacement forbidden without dedicated replacement design + checker. | guard for all ⑩ |
| `brick_protocol/brick/templates/tasks/` | Brick task-source template surface | Keep unless later Building proves better naming/placement. | guard for all ⑩ |
| `brick_protocol/brick/templates/skills/` | Ship-copy / distribution surface tied to APPLY-LIST | No blind delete. Treat as source-vs-ship-copy sync/packaging issue. | ⑩d |
| `brick_protocol/agent/skills/` | Agent-axis operating source | Source for skills. Drift repair starts here and syncs outward. | ⑩d/⑩e |
| COO order chain prompts/skills/hooks | Agent/support projection surfaces | Reflect direct_preset escape hatch and order_authoring default without concrete adapter/model exposure. | ⑩e |
| project creation/progress UX | Existing project-creation + progress projection support | Add customer UX layer only by design-first Building; no scheduler/queue/runtime platform. | ⑩f |
| `project/brick-protocol/` | Current dogfood evidence/status vessel | Do not remove/move while active GOAL/status/building evidence lives here. Vessel separation needs human gate. | ⑩g |

## 4. Global no-delete / no-move rules

```text
- No directory deletion based only on a human sense of duplication.
- No `git mv` of building_plans without simultaneous reader/checker/admission
  proof.
- No templates/skills deletion without APPLY-LIST / ship-copy contract decision.
- No shapes deletion; shapes/catalog are load-bearing.
- No project/brick-protocol vessel move while it carries active GOAL/status and
  evidence.
- No cleanup mixed into Route V2 ⑥d/⑥e or Building Call lowering/direct path
  implementation.
- No concrete adapter/model/provider selection introduced in Brick-facing or
  order-authoring docs while cleaning COO skills.
- No new runtime scheduler, queue, retry service, storage platform, or source
  truth layer as part of cleanup UX.
```

## 5. Direct preset vs Building routing for cleanup

Direct preset candidate only when all are true:

```text
- docs-only or exact single-file correction.
- no directory move.
- no package path admission change.
- no checker/profile/fixture/module_registry change.
- no Agent source vs ship-copy sync issue.
- no human gate / root / project vessel migration.
- direct_preset_admission + fast_confirm are recorded.
```

Building required when any are true:

```text
- directory move, archive, or deletion.
- building_plans path migration.
- shape/catalog replacement.
- Agent skill source ↔ ship-copy synchronization.
- COO prompt/skill/hook/projection multi-surface consistency.
- customer UX / first-run / project-creation flow.
- project vessel separation or active evidence/status migration.
- new checker/profile/fixture/module_registry coverage.
```

## 6. Phase map after ⑩a

```text
⑩b blocks map:
  Produce retained/archive/superseded map for templates/blocks before any file
  operation. Prefer archive/superseded labels over deletion.

⑩c building_plans decision:
  Decide keep vs move. If move, declare a Building that updates all readers,
  checkers, admissions, fixtures, and docs together.

⑩d skills ship-copy cleanup:
  Define source-of-truth and sync direction: agent/skills source ->
  templates/skills ship-copy -> installed/projection surface. Repair drift only
  with checker evidence.

⑩e COO order-chain skill/prompt/hook consistency:
  Align COO ordering prompt, building-call-authoring skill, task_intake /
  building-coordination, and projections with the final policy: small work is a
  direct_preset candidate only after proof; otherwise order_authoring Building.
  Keep adapter/model/provider hidden from Brick-facing authoring.

⑩f customer UX layer:
  Design install -> project creation -> buildings/status/progress board ->
  project definition flow. Reuse project_creation and progress_projection where
  possible. Do not create scheduler/queue/runtime ownership.

⑩g dogfood vessel separation:
  Separate `project/brick-protocol` dogfood evidence/status from product source
  only after active GOAL/status is closed or explicitly migrated through a human
  gate Building.
```

## 7. Required proof shape for later ⑩ Buildings

Every ⑩b~⑩g Building must return at least:

```text
- changed_files
- deleted_files or explicit none
- moved_files or explicit none
- source_facts used
- allowed_scope
- forbidden_scope respected
- checker/profile commands and rc
- clean detached worktree --all rc when landing code/resource changes
- git diff --check rc
- not_proven
- remaining_delta
- GOAL/status update
```

## 8. Not proven by this ⑩a document

```text
- No cleanup implementation is complete.
- No directory is safe to delete.
- No directory is approved to move.
- No skills ship-copy drift is repaired.
- No customer UX layer is implemented.
- No dogfood vessel separation is approved.
- No Route V2 ⑥d/⑥e work is approved by this document.
```

## 9. Next operational gate

```text
next_cleanup_phase_candidate: ⑩b blocks retained/archive/superseded map
alternate_candidate: ⑩d skills ship-copy drift map if Smith prioritizes COO order-chain skill consistency
route_v2_gate_state: ⑥d/⑥e remain held_for_human_gate until Smith/human approval
```
