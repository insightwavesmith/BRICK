# ⑩f Customer UX Implementation Building Request — 0709

Status: confirmed Building request candidate / COO order packet. This packet does
not implement code, does not run a Building, does not choose Link Movement,
does not judge success/quality, and does not make source truth. It exists so the
next ⑩f work can run through a declared Building/worktree rather than COO live
patching.

## 0. Source design and live evidence

```text
design: project/brick-protocol/status/kernel/customer-ux-layer-design-0709.md
GOAL: project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
current CLI: brick_protocol/support/operator/cli.py
project backend: brick_protocol/support/operator/project_creation.py
progress backend: brick_protocol/support/operator/progress_projection.py
project skill: brick_protocol/agent/skills/project-creation/SKILL.md
```

Live-code finding:

```text
pyproject.toml already exposes `brick` via [project.scripts].
cli.py currently has init/build/draft/draft-diff/resume/verify/doctor/status/auth/provider/sink.
cli.py has no project/progress subcommand and no references to create_project or generate_project_progress.
project_creation.py implements charter-first -> project.json shadow -> skeleton.
progress_projection.py implements deterministic PROGRESS.md rendering/writing.
```

Therefore the ⑩f implementation job is a thin customer-facing CLI tie over
existing verbs, not a new runtime or a reimplementation of vessel logic.

## 1. Building identity

```text
building_candidate: customer-ux-10f-cli-tie-0709
catalog_scope: brick_protocol_dogfood
recommended_chain_preset_ref: building-chain-preset:brick-protocol-engine-feature-hard
route_family_candidate: preset_guided_graph
startup_path_candidate: run_building_intake after task_source_ref + chain_preset_ref are confirmed
worktree_required: true
live_checkout_run_building_intake: forbidden
```

Why this preset:

```text
This is support-code + checker + docs work touching the public CLI and project
vessel UX. It needs design -> work -> code attack QA -> axis attack QA ->
evidence integrity -> closure, not a direct preset and not a quick_fix.
```

Direct preset admission:

```text
direct_preset: rejected
reason: multi-file support-code/checker/docs change, customer-facing CLI,
project vessel semantics, non-TTY safety, secret-masking/read-only behavior.
```

## 2. Work contract

Implement the ⑩f design in a declared worktree Building:

```text
Add customer-facing project/progress CLI surfaces that expose existing
project_creation and progress_projection verbs without reimplementing their
logic or adding scheduler/queue/runtime ownership.
```

Required user-facing commands:

```text
brick project new [--id <slug>] [--label <name>] [--non-interactive]
brick project list
brick project show [<id>]
brick progress [<id>] [--write]
```

Minimum expected behavior:

```text
brick project new:
  - TTY mode: ask/fill project-creation SKILL charter slots, then require explicit
    human confirmation before create_project(...).
  - non-TTY / --non-interactive: must NOT silently stamp a project. It should
    refuse with clear required slot guidance unless all required charter fields
    are supplied by explicit flags or a declared input file admitted by the
    Building. Default non-interactive auto-create is forbidden.

brick project list:
  - read-only enumerate declared project vessels under project/*/project.json.
  - no source truth / success / quality / Movement judgment.

brick project show:
  - read-only show charter/declaration fields for one declared project.
  - never print secrets or provider/session bodies.

brick progress:
  - default read-only render of render_project_progress(...).
  - --write calls generate_project_progress(...) and reports the PROGRESS.md path.
  - no live provider calls, no scheduler/queue, no Building run.
```

## 3. Allowed / forbidden scope

Allowed candidate write scope:

```text
brick_protocol/support/operator/cli.py
brick_protocol/support/checkers/**
brick_protocol/support/checkers/profiles/**
brick_protocol/support/docs/references/**
project/brick-protocol/status/kernel/customer-ux-10f-implementation-report-0709.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Prefer no changes to:

```text
brick_protocol/support/operator/project_creation.py
brick_protocol/support/operator/progress_projection.py
```

These modules are existing backends. Modify them only if the Building proves an
actual signature or safety gap that cannot be solved in the CLI wrapper.

Forbidden scope:

```text
agent/** except status references in docs (no Agent source mutation for ⑩f implementation)
link/**
brick_protocol/agent/return_fact.py
brick_protocol/link/**
project/brick-protocol/buildings/**
project/brick-protocol/status/inbox/**
project/brick-protocol/project.json
project/brick-protocol/README.md
credentials, secrets, provider config, tokens
new runtime/scheduler/queue/retry/storage platform
```

## 4. Required checker / proof plan

A ⑩f implementation Building is not accepted by CLI smoke alone. It must add or
extend checker coverage for:

```text
P1. CLI parser exposes `project` and `progress` subcommands.
P2. cli.py imports/calls create_project and render/generate project progress only
    through their existing support modules; it does not inline vessel creation or
    progress board computation.
P3. project new non-TTY default does not create a project silently.
P4. project new requires explicit charter confirmation before stamping.
P5. project list/show are read-only and do not mutate project vessels.
P6. progress default is read-only; progress --write matches generate_project_progress output.
P7. project/progress output contains no raw secret/session/provider credential values.
P8. existing project_declaration / intake_project_vessel_case /
    intake_evidence_projection_case kernel-check behavior stays green
    (these are kernel_check CASE names, not standalone --profile names; they run
    inside their host profiles, see the commands below).
P9. CLI import identity still works from outside repo (existing check_import_identity_modes guard).
P10. No new source truth, success/quality, or Movement fields are introduced.
```

Required commands before landing:

```text
python3 -m compileall -q brick_protocol
python3 brick_protocol/support/checkers/check_profile.py --profile core
python3 brick_protocol/support/checkers/check_profile.py --profile <focused-new-or-extended-profile>
# intake_project_vessel_case / intake_evidence_projection_case are kernel checks,
# not profiles. Run their host profiles instead (verified live 2026-07-09):
python3 brick_protocol/support/checkers/check_profile.py --profile building_skill_preset_intake_adapter_gate
python3 brick_protocol/support/checkers/check_profile.py --profile read_side_projection_boundary
# clean detached worktree when landing code/resource changes:
python3 brick_protocol/support/checkers/check_profile.py --all
git diff --check
```

If exact profile names differ, the Building must record the actual focused
profiles used and why they cover P1-P10.

## 5. Brick / Agent / Link rows candidate

Candidate route shape:

```text
Design Brick:
  return: observed current CLI/backend structure, implementation plan, checker plan,
  edge cases, reading_scope_map.

Work Brick:
  return: changed_files, made_changes, commands_run, observed_evidence,
  blocked_or_missing_evidence, not_proven.

Code-attack QA Brick:
  return: whether CLI behavior and checker coverage can be broken by simple misuse
  (non-TTY, missing fields, secret-looking strings, no project vessel present).

Axis-attack QA Brick:
  return: whether Brick/Agent/Link boundaries are preserved and no support surface
  authors Movement/success/quality/source truth.

Evidence-integrity Brick:
  return: whether proof commands cover P1-P10 and whether docs/status match code.

Closure Brick:
  return: narrowly_proven, not_proven, remaining_delta, next_target_candidates,
  transition_concern_evidence if any.
```

Agent candidate notes:

```text
Use normal preset Agent rows. Do not expose model/provider details in Brick rows.
If a single candidate is ambiguous, COO/Smith declaration chooses Agent/casting;
support must not rank by quality.
```

Link candidate notes:

```text
All default movement rows are forward unless a QA/closure Brick returns an
admitted non-binding transition_concern_evidence that warrants a later Link / COO
reroute. hold/paused/blocked are lifecycle/gate states, not Movement.
```

## 6. Edge cases the Building must handle

```text
- project id already exists -> fail closed, no partial overwrite.
- invalid project id / path traversal -> fail before filesystem touch.
- non-TTY without full explicit charter input -> refuse, no project created.
- project list when no projects exist -> read-only empty result, no error stack.
- project show unknown id -> typed/clear error, no traceback.
- progress unknown project -> loader rejection surfaced clearly.
- progress --write on unchanged evidence -> deterministic PROGRESS.md output.
- output containing strings shaped like secrets must be masked/rejected according
  to existing support secret discipline.
```

## 7. GOAL landing requirements

The implementation Building must update:

```text
project/brick-protocol/status/kernel/customer-ux-10f-implementation-report-0709.md
project/brick-protocol/status/kernel/GOAL/02-unified-continuous-build-goal-0708.md
```

Report must include:

```text
- changed_files
- deleted_files: none or explicit list
- moved_files: none or explicit list
- commands_run with rc
- checker coverage mapping P1-P10 -> command/evidence
- not_proven
- remaining_delta
- whether ⑩f implementation can be considered landed or needs a repair Building
```

## 8. Not proven by this request

```text
- No CLI implementation is complete.
- No checker has been added for project/progress subcommands.
- No customer smoke has run.
- No ⑩g vessel decision is closed.
- No ⑥e/⑦ route-walker implementation is opened.
```

## 9. Movement language

This request authors no Link Movement. It is a COO Building-order packet:

```text
gate_state: ready_for_declared_building_intake
movement_candidate: none supplied by this packet
```
