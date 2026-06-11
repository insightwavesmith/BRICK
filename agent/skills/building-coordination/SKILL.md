---
name: building-coordination
description: Use when coordinating a Brick Protocol Building sequence without becoming a runtime engine or Link authority.
---

Keep the active sequence:

```text
Brick -> Agent -> Brick -> Link -> Brick
```

A Building is not always the same six-step line. Select the smallest Building
shape that preserves Brick / Agent / Link ownership, declared Link Movement,
verification evidence, repair routing, and evidence accumulation.

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

Open COO intake questions before implementation. Ask core questions, inspect
which task fields they extract, and ask follow-up questions until the missing
task fields are named.

Run intake as a conversational loop:

```text
ask one core question
wait for Smith's answer
extract candidate task fields from that answer
state the interpretation back to Smith
ask "이 뜻 맞나?"
ask the next question only after confirmation or correction
```

Follow-up questions must be answer-derived. Do not ask a batch checklist of
intake questions by default, and do not advance to shape, preset, active plan,
or execution until the current interpretation is confirmed or the ambiguity is
explicitly named.

Do not edit protocol, code, Agent resources, Link resources, support resources,
or project status files before the Building is declared.
Do not run the Building.
Do not select Link Movement by inference.

Use the active startup order:

```text
1. 사용자 요청 해석.
2. 프로젝트 체크 (project check first): "어느 프로젝트의 일인가?" — the project
   question comes BEFORE the task questions. If the human names no vessel or
   the named vessel does not exist under project/<id>/, guide to the
   project-creation skill FIRST; do not invent a vessel silently and do not
   silently default a NEW work conversation into project #1 (the ref-less
   project #1 root is a mechanical compat default in support, not an intake
   answer).
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
help review a candidate chain, but they are not the center, source truth,
success judgment, quality judgment, Movement authority, or the reason to skip
task intake and route ladder.

Support, model output, checker output, and reporter output are evidence only;
they must not decide task meaning, route family, Movement, success, or quality.

COO must not jump from `task.md` directly to `run_building_plan`. A confirmed
`task.md` is input evidence; catalog scope, preset/manual grammar, route family,
graph movement case, fan-in-first policy, and startup path remain separate
candidates until caller / COO declaration. Once `task.md` AND the
`chain_preset_ref` are confirmed and declared, `run_building_intake` is the single
seam from that confirmed intent to a running Building (it sequences
materialize -> run; it does not select the preset or skip the prior confirmations).

Chain presets are one file per preset under `brick/templates/presets/` —
each `presets/<name>.md` is a "Building route 설명서" whose frontmatter declares
the route structure (steps with `step_template_ref` + `brick_spec_ref`, gate
hints) and whose `## Route` body is author route-intent prose the engine does
not parse. `brick_protocol_dogfood` presets
(those with `catalog_scope: brick_protocol_dogfood`) are local Brick Protocol
development candidates, not common export; common presets carry
`catalog_scope: common`. The whole set is indexed by
`brick/templates/shapes/catalog.yaml`.

Startup / handoff path candidates:

```text
A: brick_protocol.support.operator.composition.materialize_building_intent
B: brick_protocol.support.operator.composition.render_declared_step_template_plan
C: brick_protocol.support.operator.composition.compose_building
D: brick_protocol.support.operator.run.run_building_plan
E: brick_protocol.support.operator.driver.run_declared_portfolio
F: brick_protocol.support.operator.auto_repair_replay.run_declared_auto_repair_replay_case
```

Single confirmed-intent -> running-Building seam (task.md + chain preset -> run):

```text
SEAM: brick_protocol.support.operator.driver.run_building_intake
```

For a confirmed `task.md` + selected `chain_preset_ref`, `run_building_intake` is
the single entry from a declared intent to a running Building. It is pure support
sequencing: it calls `materialize_building_intent` (A), writes the materialized
plan to disk, maps `plan_shape -> walker_mode` mechanically (`linear -> linear`,
`graph -> dynamic`, forced by `run_building_plan`'s own contract, NOT a Movement
choice), then calls `run_building_plan` (D). It selects no preset (the preset comes
from the confirmed intent; an intent with no registry preset hard-fails), chooses
no Movement, picks no agent outside the NEED<->CAPABILITY match, and judges no
success / sufficiency / quality. The underlying A..F verbs remain available for
manual graph paths, portfolios, repair/replay, and step-by-step composition.

The confirmed intent may carry an OPTIONAL `project_ref` (`project:<id>`) —
the project vessel the building belongs to (membership is the path:
`project/<id>/buildings/`). When declared, the output root derives through
`buildings_root_for` (the single derivation seam in
`support/recording/capture.py`) and an undeclared / charterless vessel is
refused loudly at intake, before any run. When absent, the building lands in
the project #1 root — a mechanical compat default routed through the SAME
seam, not an intake answer: the project check in the startup order above still
asks for NEW work conversations.

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

These refs are support/declaration evidence for the future Building, not
permission for `task_intake` to write them. They are not protocol, code, or
resource editing; not a Building run; not source truth; not success or quality
judgment; and not Movement or target choice. `task_intake` may draft candidate
content, but `task_intake` must not write files.

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
10. For confirmed chain presets, use the Builder materializer handoff
   (`task_source_ref + chain_preset_ref -> declared rows` for linear routes,
   or declared nodes / edges / groups for graph routes) before Runner.
   For manual paths, keep explicit declared nodes / edges / groups.
11. Declare `active_plan_ref` or fully declared intent only after task-source,
   preset/no-preset, shape, route-family, and graph-case evidence exist.
12. After those declarations, name the Brick work contract and Building Plan
   boundary before resource changes.
13. Name the Agent Object refs that will receive work; do not inline prompt,
   skill, hook, tool-policy, adapter, or discipline bodies in the plan.
14. Name the Link Movement and target for each step. One Link row has one
   Movement and one target.
15. For every Brick, name the required return shape. A returned output can be a
   handoff, report, classification, synthesis, delete manifest, closure note,
   QA observation, code diff, documentation patch, or another required return
   shape.
16. For every Brick, name the Agent Object that performs and returns that output.
   No output type is hard-coded to COO, CTO, DEV, QA, or any other role; the
   performer is the Agent row for that Brick.
17. For implementation work, keep Design, Development, and Verification as
   Building work.
18. If the Building declares multiple verification lanes, collect all declared QA bodies
   before closure-synthesis or integration.
19. If repair is needed, record `reroute_replay_candidate`, create a reroute
   Link transition to the right Brick
   boundary and preserve handoff refs for replay verification. For this dogfood
   policy, reroute to work replays work plus all declared QA lanes plus
   closure-synthesis; partial QA reuse remains not_proven until a later
   freshness / Work Packet Building admits it.
20. Inspect the Building evidence root: capture, raw, claim_trace, and
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

Ordinary non-hard graph branches may return non-binding transition concerns only
when their Brick return shape declares `transition_concern_evidence`. In hard fan-in QA cohorts,
QA lanes return their own Brick fields without Link-facing `transition_concern_evidence`; closure-synthesis is the only Link-facing `transition_concern_evidence` source. Closure-synthesis may
summarize branch evidence, branch observations, and remaining_delta. Link / COO
disposition adopts one declared Movement at the transition boundary.
