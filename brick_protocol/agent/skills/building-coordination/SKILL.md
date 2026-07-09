---
name: building-coordination
description: Use when coordinating a Brick Protocol Building sequence without becoming a runtime engine or Link authority.
---

Keep the active sequence:

```text
Brick -> Agent -> Brick -> Link -> Brick
```

A Building is not always the same six-step line. Select the smallest shape that
preserves Brick / Agent / Link ownership, declared Link Movement, verification
evidence, repair routing, and evidence accumulation.

For current COO judgment, use the active MOVEMENT-BINARY-0 language:

```text
forward = continue on the current declared road
reroute = move to any other declared Brick boundary
replay = route_replay_plan.replay_segment_refs inside reroute
return = superseded shorthand for nearby reroute
hold / stop = Building lifecycle or review/close state, not Link Movement
```

Older historical docs or evidence may still show wider Movement vocabulary;
mark that as superseded wording instead of copying it into new Building plans.

Building trigger rule:

```text
If the user asks to run a Building, assign a project, use a preset, move from
task to plan to run, or otherwise starts Brick / Building work, open COO intake
questions before implementation.
```

Smith shorthand examples that must trigger this rule:

```text
빌딩 만들자
빌딩 구성하자
빌딩 기획하자
빌딩 플랜 잡자
이걸 빌딩으로 하자
브릭으로 굴리자
task intake 하자
task.md 만들자
```

Meaning split:

```text
task intake 하자 = ask COO intake questions and draft task source evidence.
빌딩 구성하자 / 빌딩 기획하자 / 빌딩 만들자 = intake, catalog scope, preset or no-preset fallback, shape, and plan/intent declaration.
빌딩 굴려 / 빌딩 실행하자 = verify declared task and plan first; if missing, return to intake.
```

Composition-first dogfood policy: do not reduce every Building to a fixed
"launch -> Agent work -> QA -> closure -> disposition" line. For each task, the
COO composes the LLM(s) = brain, Brick KIND(s) = hands, and graph shape =
nervous system. If that cannot be expressed clearly, update this skill chain
instead of forcing the stale pipeline.

Skill-as-diagnostic rule: if a task cannot be drawn as LLM + Brick KIND + graph
composition, treat that as a gap in this skill chain
(building-coordination, brick-task-author, building-sizing-method, task_intake).
Extend these skills; do not create a new skill or force the fixed pipeline.

Fan barrier discipline: do not declare fan-in and fan-out as the same event.
Fan-in collects required branch bodies for synthesis/confirmation; fan-out
launches multiple next Bricks from a confirmed boundary. If fan-in is followed
by another fan-out, insert an explicit barrier Brick (`lane-qa-fanin-confirm`,
`design-synthesis`, `plan-confirm`) and fan out from it. Avoid complete-bipartite
shortcuts; if fan-outs share a source event, collapse them unless a barrier
explains the split.

P3 zero-ritual launch policy: once task source and graph shape are declared,
execution is compact drawing (`build` / `fan`) followed by operator-facing
`build()`. `fire()` is internal/debug wording; raw packet handoff through
`brick build --graph <packet>` is retired from the customer CLI surface.

Compact write-hand policy: file-modifying graph nodes need two declarations:
write need (`write=True` or `requires_brick_write_scope: true`) and bounded
launch `write_scope`. Passing only `write_scope` is intentionally read-only and
should report `made_changes=false`.

Open COO intake questions before implementation. Ask core questions, inspect
extracted fields, and ask follow-ups until missing task fields are named.

Run intake as a conversational loop:

```text
ask one core question
wait for Smith's answer
extract candidate task fields from that answer
state the interpretation back to Smith
ask "이 뜻 맞나?"
ask the next question only after confirmation or correction
```

Follow-ups must be answer-derived. Do not ask a batch checklist of intake
questions by default, and do not advance until interpretation is confirmed or
ambiguity is named.

Do not edit protocol, code, Agent resources, Link resources, support resources,
or project status files before the Building is declared.
Do not run the Building.
Do not select Link Movement by inference.

Use the active startup order:

```text
1. 사용자 요청 해석.
2. 프로젝트 체크 (project check first): "어느 프로젝트의 일인가?" — ask before task
   questions. If no declared vessel exists, guide to project-creation FIRST;
   do not silently invent one or default NEW work into project #1.
3. Ask task intake questions.
4. Draft `task.md` candidate evidence.
5. Confirm `task.md` as Brick-owned task source evidence.
6. Name `catalog_scope` candidate: `common` or `brick_protocol_dogfood`.
7. Name `preset vs manual` candidate: a `chain_preset_ref` candidate or
   explicit `no_preset_fallback` / manual graph candidate.
8. Write `route_family_case_analysis`:
   existing_declared_plan, linear_chain_preset, preset_guided_graph,
   full_manual_graph, declared_portfolio, or declared_repair_replay.
9. Write `graph_movement_case_analysis` before plan/startup when graph,
   fan-out/fan-in, portfolio, repair, replay, or parallel QA is implied.
10. If multiple verification lanes exist, declare `fan_in_first_candidate` as
   the default analysis policy before closure-synthesis.
11. Name the startup path candidate only after the prior candidate/declaration
    chain is present.
```

Claude master-sequence and engine detail are support evidence only. They may
review a candidate chain but are not the center, source truth, success judgment,
quality judgment, Movement authority, or a reason to skip intake/route ladder.

Support, model output, checker output, and reporter output are evidence only;
they must not decide task meaning, route family, Movement, success, or quality.

COO must not jump from `task.md` directly to `run_building_plan`. A confirmed
`task.md` is input evidence; catalog scope, preset/manual grammar, route family,
graph movement case, fan-in-first policy, and startup path remain separate
candidates until caller / COO declaration. Once `task.md` AND `chain_preset_ref`
are confirmed and declared, `run_building_intake` is the single seam from
confirmed intent to running Building; it sequences materialize -> run and does
not select the preset.

Chain presets live under `brick_protocol/brick/templates/presets/`; each `presets/<name>.md`
declares route structure in frontmatter and route-intent prose in `## Route`.
`brick_protocol_dogfood` presets are local Brick Protocol development
candidates; common presets carry `catalog_scope: common`. The set is indexed by
`brick_protocol/brick/templates/shapes/catalog.yaml`.

Startup / handoff path candidates:

```text
A: brick_protocol.support.operator.composition_intent.materialize_building_intent
B: brick_protocol.support.operator.composition_intent.render_declared_step_template_plan
C: brick_protocol.support.operator.composition_compose.compose_building
D: brick_protocol.support.operator.run.run_building_plan
E: brick_protocol.support.operator.driver.run_declared_portfolio
F: brick_protocol.support.operator.auto_repair_replay.run_declared_auto_repair_replay_case
```

Single confirmed-intent -> running-Building seam (task.md + chain preset -> run):

```text
SEAM: brick_protocol.support.operator.driver.run_building_intake
```

For confirmed `task.md` + selected `chain_preset_ref`, `run_building_intake`
calls `materialize_building_intent` (A), writes the plan, admits only
`plan_shape: graph`, dispatches the dynamic graph walker, then calls
`run_building_plan` (D). It selects no preset, chooses no Movement, picks no
agent outside NEED<->CAPABILITY, and judges no success / sufficiency / quality.

Confirmed intent may carry optional `project_ref` (`project:<id>`). When
declared, output root derives through `buildings_root_for`; undeclared /
charterless vessels are refused at intake. Absence lands in project #1 by
mechanical compat default, not as a NEW-work intake answer.

Do not claim CLI startup. Do not present native_dispatch or
building_operation as the runner. Do not present `target_word` as Link
Movement. Do not present `selected_preset_ref` as canonical proof.

Pre-run declaration / evidence refs, when caller / COO or an admitted composer
materializes them, are:

```text
work/task.md
work/building-intake.json
work/preset-expansion.json
work/declared-building-plan.json
work/link-launch-policy.json
```

These refs are brick_protocol/support/declaration evidence for a future Building, not
permission for `task_intake` to write them. They are not a run, source truth,
success/quality judgment, Movement, or target choice.

Use this coordination order:

```text
1. Read AGENTS.md, the project PROGRESS.md projection, and the active slice spec.
2. Run `task_intake` as the first active work step for the user's trigger.
3. Confirm `task_source_draft`, missing fields, not_proven, and remaining gaps.
4. Let caller / COO declaration confirm `task_source_ref` only after that
   confirmation; support records `work/task.md` as declaration evidence, and
   `task_intake` itself must not write the file.
5. Select `catalog_scope` and name a `chain_preset_ref` candidate, or explicitly
   mark `no_preset_fallback`.
6. Declare `selected_shape_ref` as an optional tag after task-source and preset
   evidence exist (it no longer has to match the preset or the caller / COO shape).
7. Name `route_family_candidate` and `preset_vs_manual_case_analysis`.
8. If the route family is graph, portfolio, repair/replay, or a preset with
   `parallel_qa`, `hard_parallel_qa`, or `fan_in_final_gate`, write
   `graph_movement_case_analysis` before plan/startup.
9. Use fan-in-first for multiple verification lanes: collect all declared QA bodies
   before closure-synthesis unless a later declared freshness / Work Packet
   Building proves partial QA reuse.
10. Do not make fan-in and fan-out the same event. When one cohort must be
   collected and then another cohort launched, declare an explicit barrier Brick
   first (for example `lane-qa-fanin-confirm`), then declare the next fan-out from
   that barrier. Do not model this as each upstream QA lane pointing to every
   final QA lane; that hides the fan-in boundary and can serialize or confuse the
   final QA cohort.
11. For confirmed chain presets, use the Builder materializer handoff
   (`task_source_ref + chain_preset_ref -> declared rows` for single-lane,
   row-shaped presets — which still materialize to a `plan_shape: graph` plan —
   or declared nodes / edges / groups for graph routes) before Runner.
   For manual paths, keep explicit declared nodes / edges / groups.
12. Declare `active_plan_ref` or fully declared intent only after task-source,
   preset/no-preset, shape, route-family, and graph-case evidence exist.
13. After those declarations, name the Brick work contract and Building Plan
   boundary before resource changes.
14. Name the Agent Object refs that will receive work; do not inline prompt,
   skill, hook, tool-policy, adapter, or discipline bodies in the plan.
15. Name the Link Movement and target for each step. One Link row has one
   Movement and one target.
16. For every Brick, name the required return shape. A returned output can be a
   handoff, report, classification, synthesis, delete manifest, closure note,
   QA observation, code diff, documentation patch, or another required return
   shape.
17. For every Brick, name the Agent Object that performs and returns that output.
   No output type is hard-coded to COO, CTO, DEV, QA, or any other role; the
   performer is the Agent row for that Brick.
18. For implementation work, keep Design, Development, and Verification as
   Building work.
19. If the Building declares multiple verification lanes, collect all declared QA bodies
   before closure-synthesis or integration.
20. If repair is needed, record `reroute_replay_candidate`, create a reroute
   Link transition to the right Brick boundary, and preserve handoff refs. For
   dogfood policy, reroute_to_work_full_replay replays work plus declared QA
   lanes plus closure-synthesis; partial QA reuse remains not_proven until a
   later freshness / Work Packet Building admits it.
21. Inspect the Building evidence root: capture, raw, claim_trace, and
   building-map projection.
```

Do not let support pick a route, create a default GateFact, classify the Agent
return, choose Movement, replace a Brick's returned output, or turn graph into
source truth. Support may walk the declared road and record support evidence
only.

Graph movement cases are analysis inputs, not Movement choices:

```text
all_forward
single_reroute_concern
same_target_duplicate_reroute_concerns
conflicting_reroute_targets
insufficient_evidence_hold
reroute_to_work_full_replay
```
G1 no-link/default-forward distinction: compact authoring can hide Link rows
from the user, but reroute is not default Movement. Support materializes forward
edges unless `route=`, declared route policy, or adopted closure concern gives
Link/COO a reroute/HOLD basis. For hard fan-in QA, QA lanes return observations;
closure-synthesis is the sole Link-facing concern source.

Ordinary graph branches may return non-binding concerns only when their Brick
return shape declares `transition_concern_evidence`. In hard fan-in QA cohorts,
QA lanes return their own Brick fields without Link-facing `transition_concern_evidence`;
closure-synthesis is the only Link-facing `transition_concern_evidence` source.
Link / COO disposition adopts one declared Movement at the transition boundary.

Hold disposition vocabulary reference: when a walk stops at a HOLD, read the
committed self-description before choosing a disposition. It maps each measured
`hold_reason` literal to its legal disposition class, the real meaning of each
disposition action (notably `forward` = continue the declared road, NOT an
adoption or auto-approval; `raise` = bump budget so the held landing adopts
naturally; `stop` = lifecycle/close; `reroute` = move to another declared
boundary), and mispatch case references (0702 raise/forward confusion, 0703
reroute-suggestion HOLD mis-forwarded, 0704 route-policy over-adopting a
design-question concern):

```text
project/brick-protocol/status/kernel/hold-disposition-vocabulary-0704.md
```

That doc also records the distinct resume seed-build integrity refusal (a
fail-closed ValueError, NOT a `hold_reason` disposition; legal recovery = a
FRESH re-launch) per `resume-ledger-mismatch-recovery-0704.md`. It is committed
support evidence only: it does not choose the disposition, judge success or
quality, or select Link Movement — Link / COO adopts one declared Movement at
the boundary.

## Ship-copy land

This section carries the hold disposition vocabulary reference above:

```text
project/brick-protocol/status/kernel/hold-disposition-vocabulary-0704.md
pure-dev-d4-r4-product-land-0709b ship-copy land
```
