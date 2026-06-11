# Task

## Objective
Create the first project orchestration ledger/export for Brick Protocol Building roots so a later web dashboard can show project and Building progress.

## First-Line Contract
Render existing Building evidence roots into a support-only project operation ledger without creating source truth, Movement authority, or dashboard runtime.

## Context / Why Now
Smith wants to dogfood Brick Protocol with about six participants who use the same rules. The first useful surface is a board that shows which participant is working on which project and Building, then later supports shared project and shared Building collaboration.

## Deep Intake Result
Trigger Event: Smith asked to make a Building for project goals, active Buildings, and dashboard projection.
User Context: Human orchestration starts as six separate participants using the same protocol rules.
Desired Information / Outcome: A project-level ledger/export that a later dashboard can read.
Current Workaround: Existing Building roots and Building index projection show local evidence roots only.
Pain Points: There is no project operation ledger that joins participant, project, Building, frontier, and next-action observations.
Blocked Decisions: Web UI and shared collaboration should wait until the ledger/export is closed.
Primary Signals: Building root, current step, frontier kind, Link target, mechanical evidence gaps, and closure boundary.
Status Vocabulary: planned, observed_running, waiting_review, link_paused, rerouted, closed, evidence_incomplete, unknown.
Required Actions: Use existing support projection helpers where possible, keep project output under project status, and keep dashboard UI out of Phase 1.
Forbidden Actions: Do not make support source truth, do not create Movement authority, do not create dashboard runtime, and do not invent route targets.

## Required Sources
- AGENTS.md
- project/brick-protocol/status/kernel/current-working-context.md
- support/docs/spec/brick-protocol-building-index-1-root-projection-0526.md
- support/operator/building_operation.py
- brick/templates/shapes/registry.yaml

## Desired Output
- A support-only `project_orchestration_ledger_packet()` helper.
- A project-local ledger/export JSON under `project/brick-protocol/status/`.
- A profile that keeps the ledger projection inside existing support boundaries.
- A Building evidence root for `PROJECT-ORCHESTRATION-LEDGER-0`.

## Brick / Agent / Link Boundary
- Brick: declares this ledger/export work and the dashboard-readiness contract.
- Agent: returns observed evidence only through closed `received_work / returned`.
- Link: records only declared `forward` transitions in this phase.
- support: reads existing Building roots and renders a projection packet.

## Read Scope / Write Scope
- Read: `AGENTS.md`, current working context, Building evidence roots, existing support specs, existing operator helper.
- Write: `support/operator/building_operation.py`, `support/checkers/profiles/`, `support/docs/spec/`, `project/brick-protocol/status/`, this Building evidence root, and the declared Building Plan.
- Do not write: new dashboard runtime folder, new Link module, new checker file, new root storage/wiki surface.

## Constraints / Out of Scope
- Web dashboard UI is out of Phase 1.
- Multi-participant import is out of Phase 1.
- Shared project collaboration is out of Phase 1.
- No RoutePolicyFact or new BAL fact class.

## Human / Review Gate
Smith review is required before moving to Phase 2.

## Honest Report Contract
Agents and support reports may include `observed_evidence`, `made_changes`, `blocked_or_missing_evidence`, `open_questions`, `not_proven`, `remaining_delta`, `review_needed`, and `transition_concern_evidence`.
They must not return success, failure, approved, quality score, route_target, movement_choice, movement, or target_ref as Agent judgment.

## Done Criteria
- `project_orchestration_ledger_packet()` renders without writing.
- A ledger/export JSON exists under `project/brick-protocol/status/`.
- The new profile passes.
- `check_profile.py --all` passes.
- The declared Building Plan runs and writes evidence.

## Risk
- A ledger/export can look like source truth if proof limits are weak.
- A dashboard-readiness packet can accidentally become dashboard runtime.
- Static evidence cannot prove process liveness.

## Proof Limits
- This task does not prove dashboard UI readiness.
- This task does not prove cross-participant sync.
- This task does not prove semantic correctness of any Building.
- This task does not prove process liveness.
