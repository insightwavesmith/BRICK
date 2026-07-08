# ⑩e COO Order-Chain Skill / Prompt / Hook Consistency Map — 0709

Status: support evidence only. This document does not edit prompts, skills,
hooks, projections, Building Call code, Agent Objects, or Link resources. It
maps the current COO order-chain consistency after Building Call v1.1 and marks
what a later declared Building must repair or verify. It is not source truth,
success judgment, quality judgment, or Movement authority.

## 0. Scope

This is phase ⑩e from:

```text
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

It follows:

```text
⑩a cleanup-scope-invariants-0709.md
⑩b blocks-retained-map-0709.md
⑩d skills-ship-copy-drift-map-0709.md
```

The requested consistency target is:

```text
small work -> direct_preset candidate only after proof and fast_confirm
normal / ambiguous / multi-surface work -> order_authoring Building
critical / destructive / credential / high-impact boundary -> human_gate_first
```

## 1. Active policy that must be reflected everywhere

```text
Default route: order_authoring
Direct escape hatch: quick_check | quick_fix only
Direct preconditions: direct_preset_admission + fast_confirm
Standard delivery or ambiguous work: order_authoring
Critical red flag: human_gate_first
Order-authoring Agent: draft only; no confirmation, launch, success/quality, or
Movement judgment
Brick-facing authoring: no adapter/model/provider/selected_* selection
Movement literals: forward | reroute only
hold/paused/held_for_coo_review: gate/lifecycle states only
```

## 2. Surfaces inspected

```text
Agent skill source:
  brick_protocol/agent/skills/brick-task-author/SKILL.md
  brick_protocol/agent/skills/building-call-authoring/SKILL.md
  brick_protocol/agent/skills/task_intake/SKILL.md
  brick_protocol/agent/skills/building-coordination/SKILL.md

Brick ship-copy skill surface:
  brick_protocol/brick/templates/skills/brick-task-author/SKILL.md
  brick_protocol/brick/templates/skills/task_intake/SKILL.md
  brick_protocol/brick/templates/skills/building-coordination/SKILL.md

Support code/menu surfaces:
  brick_protocol/support/operator/building_call.py
  brick_protocol/support/operator/building_call_authoring.py
  brick_protocol/support/operator/building_call_menus.py

Control/status surface:
  project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

## 3. Consistency observations

### 3.1 Positive alignment observed

`brick-task-author` Agent source and ship-copy both contain the Quick Path
labels and four examples:

```text
direct quick_check
direct quick_fix
order_authoring
human_gate_first / forbidden direct
```

They also state:

```text
- direct_preset is only an escape hatch for direct quick_check / quick_fix.
- direct_preset admission + fast_confirm are required.
- direct_preset admission is not launch authorization.
- route_target authority and adapter/model/provider/selected_* exposure must not
  be created in authoring.
```

`building-call-authoring` Agent source states equivalent labels:

```text
direct quick_check
direct quick_fix
order_authoring
human_gate_first / forbidden direct
```

and clarifies:

```text
- direct quick_* needs admission plus fast_confirm.
- order_authoring is the standard draft path for normal/unclear/multi-file work.
- human_gate_first covers credential/secret, destructive/irreversible, and
  high-impact boundary changes.
```

`building_call.py` enforces the core policy:

```text
DIRECT_PRESET_CASES = {quick_check, quick_fix}
standard_delivery -> order_authoring unless separately confirmed as non-direct
red flags -> order_authoring
critical red flags -> human_gate_first
fast_confirm required before direct lowering
```

`building_call_authoring.py` rejects authoring exposure of forbidden authority
terms, including:

```text
movement_choice
route_target
selected_adapter_ref
selected_model_ref
```

`building_call_menus.py` exposes routing modes:

```text
direct_quick_check
direct_quick_fix
order_authoring
human_gate_first
```

### 3.2 Watch items / potential drift

#### Watch A — `building-coordination` ship-copy drift

From ⑩d:

```text
brick_protocol/agent/skills/building-coordination/SKILL.md
  contains hold-disposition vocabulary reference.

brick_protocol/brick/templates/skills/building-coordination/SKILL.md
  lacks that section.
```

Impact on ⑩e:

```text
COO order-chain consistency should not rely on an outdated ship-copy that lacks
hold/lifecycle disposition guidance. This is the strongest ⑩d-repair-1 candidate.
```

#### Watch B — `brick-task-author` selected_* code block

`brick-task-author` Agent and ship-copy both contain literal strings:

```text
selected_adapter_ref
selected_model_ref
```

Context observed:

```text
They appear in a code-block / intent-style example area, while the same Quick
Path section says Brick-facing authoring must not expose adapter/model/provider
or selected_* authority.
```

Disposition:

```text
Do not call this a defect without a focused review. It may be compiled/runtime
intent evidence rather than external authoring. A later ⑩e repair Building
should classify this exact occurrence as one of:
  - allowed internal/lowering example with clear label; or
  - confusing external authoring exposure that needs rewrite.
```

#### Watch C — `building-sizing-method` ship-copy overlay

From ⑩d:

```text
building-sizing-method template differs intentionally or semi-intentionally for
checker compatibility text.
```

Impact on ⑩e:

```text
Do not blind-sync. If order-chain wording is updated, preserve the checker pin
or update the checker/profile in the same declared Building.
```

#### Watch D — agent-only skills possibly needed for ship/customer UX

From ⑩d, maybe-ship candidates:

```text
building-call-authoring
evidence-verification
protocol-boundary-watch
project-creation
```

Impact on ⑩e/⑩f:

```text
COO order-chain and customer UX may need these skills packaged, but no copy is
approved by this map. Decide via a declared Building with source/ship/live sync
rules and checker evidence.
```

## 4. Required sequence for a future ⑩e repair Building

A ⑩e repair Building must not start by editing a prompt. It must proceed in this
order:

```text
1. Confirm source surfaces and exact write_scope.
2. Classify each inconsistency as Brick / Agent / Link / Support.
3. Repair Agent-source skill wording first when the Agent source is wrong.
4. Sync ship-copy only after source wording is correct and APPLY-LIST allows it.
5. Update checker/profile text pins only when the pinned compatibility wording is
   intentionally retired or replaced.
6. Regenerate/provider projection surfaces only if the source/ship contract says
   to do so; do not store credentials/session bodies.
7. Update GOAL/status with changed_files, proof, not_proven, and remaining_delta.
```

## 5. ⑩e candidate repair plan

Recommended first repair Building:

```text
building_id_candidate: cleanup-10e-order-chain-consistency-0709a
primary goal:
  Repair and/or explicitly classify order-chain wording drift without changing
  route/walker or Building Call runtime semantics.

candidate write_scope:
  - brick_protocol/agent/skills/building-coordination/SKILL.md
  - brick_protocol/brick/templates/skills/building-coordination/SKILL.md
  - brick_protocol/agent/skills/brick-task-author/SKILL.md        (review/repair only if selected_* example is confusing)
  - brick_protocol/brick/templates/skills/brick-task-author/SKILL.md (ship-copy mirror if repaired)
  - brick_protocol/support/checkers/profiles/coo_operating_chain.yaml
  - brick_protocol/support/checkers/profiles/building_skill_preset_builder_composition.yaml
  - brick_protocol/support/checkers/profiles/building_call_menus.yaml
  - project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
  - follow-up support note

forbidden_scope:
  - route_materialization.py
  - walker_kernel.py / walker_resume.py
  - brick_protocol/link/**
  - brick_protocol/agent/return_fact.py
  - provider/adapter/model runtime code unless a new human gate admits it
```

Minimal repair candidates:

```text
A. Sync building-coordination hold-disposition section from agent source to ship-copy.
B. Add an explicit label around brick-task-author selected_* example if it is an
   internal/lowering fixture, or rewrite it if it reads as external authoring.
C. Leave building-sizing-method drift untouched unless the checker compatibility
   pin is updated in the same Building.
```

## 6. Required proof for ⑩e repair Building

```text
- changed_files
- deleted_files or explicit none
- copied/synced skill names
- exact classification of selected_* occurrences in brick-task-author
- checker/profile commands:
  python3 -m compileall -q brick_protocol
  python3 brick_protocol/support/checkers/check_profile.py --profile coo_operating_chain
  python3 brick_protocol/support/checkers/check_profile.py --profile building_skill_preset_builder_composition
  python3 brick_protocol/support/checkers/check_profile.py --profile building_call_menus
  clean detached worktree: python3 brick_protocol/support/checkers/check_profile.py --all
  git diff --check
- GOAL/status update with remaining_delta
```

## 7. Not proven by this ⑩e map

```text
- No skill wording has been repaired.
- No ship-copy has been synced.
- No projection/live installed skill has been inspected or regenerated.
- No selected_* occurrence has been conclusively reclassified as allowed or a
  defect.
- No ⑥d/⑥e Route V2 implementation is approved.
```

## 8. Next operational candidate

```text
next_candidate: cleanup-10e-order-chain-consistency-0709a declared Building
recommended first patch: building-coordination ship-copy sync, plus focused
  review of brick-task-author selected_* example context
route_v2_gate_state: ⑥d/⑥e remain held_for_human_gate until Smith/human approval
```
