# BRICK 6 P5 Link declaration / concern target safety closure evidence - 2026-07-01

## Scope

- Phase: P5 - Link declaration law and invalid concern target safety.
- Repo: `/Users/smith/projects/BRICK`.
- Base before P5 sequence: `a10d2f6`.
- Current adopted HEAD after P5 sequence: `5b2a79d`.
- P5 evidence roots:
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p5-link-declaration-concern-safety-0701a` — multi-adapter design path, interrupted before implementation.
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p5-link-declaration-concern-safety-0701b` — rerun design path, interrupted before implementation.
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p5-link-declaration-concern-safety-0701c` — narrow implementation Building; `frontier_kind=complete`, with a closure concern for broad-profile fixture fallout.
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p5-link-gate-fixture-consolidation-0701d` — fixture follow-up Building; `frontier_kind=link_paused` after discovering additional fixture fallout.
  - `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p5-checker-fixture-gate-consolidation-0701e` — broader fixture follow-up attempt; `frontier_kind=agent_incomplete` due local CLI timeout before an AgentFact return.

## Adopted commits

```text
fb4c4df P5: declare Link gate concern safety graph
f049cb7 P5: declare Link gate concern safety rerun graph
6ded4f1 P5: declare narrow Link gate safety implementation graph
8221872 BRICK building output: brick-6-p5-link-declaration-concern-safety-0701c
ad9fc80 P5: declare Link gate fixture consolidation graph
ad2374b P5: declare checker fixture gate consolidation graph
5b2a79d P5: consolidate checker fixture gate declarations
```

## Observed evidence

- P5c Building result: `frontier_kind=complete`.
- P5c sandbox commit: `5baa781e5edae95e2449ca576464204c7cab9b41`, adopted to main as `8221872`.
- P5c changed files:
  - `support/operator/plan_validation.py`
  - `support/operator/walker_transition_concern.py`
  - `support/checkers/check_bounded_agent_proposed_routing_loop0.py`
  - `support/checkers/profiles/bounded_agent_proposed_routing_loop.yaml`
- P5c closure recorded one implementation-gap concern: `check_profile.py --all` reached an adjacent checker fixture ordering gap after mandatory `declared_gate_refs` validation.
- P5d/P5e attempted to close the fixture fallout through additional official Building routes, but P5d paused and P5e timed out before a usable AgentFact return.
- Final fixture consolidation changed only checker fixtures/profiles:
  - `support/checkers/lib/adapter_capability_checks.py`
  - `support/checkers/lib/case_runners.py`
  - `support/checkers/lib/kernel_checks.py`
  - `support/checkers/profiles/structure_template_integrity.yaml`
- Final verification on main after `5b2a79d` observed:
  - `py_compile` of changed Python: PASS
  - `bounded_agent_proposed_routing_loop` profile: PASS
  - `link_routing_behavioral` profile: PASS
  - `agent_axis_behavioral` profile: PASS
  - `building_automation` profile: PASS
  - `git diff --check`: PASS
  - `check_profile.py --all`: PASS (`RC=0`)

## Narrowly proven

- Active Building Plan Link rows must now declare `declared_gate_refs`; absence is rejected at the validation boundary instead of silently becoming runtime default-transition behavior.
- Explicit `link-gate:default-transition` remains the accepted default materialization path for ordinary forward Link rows.
- Invalid `transition_concern_evidence` no longer shapes a HOLD target from raw proposed refs; invalid concern HOLD construction anchors to `source_brick_ref`.
- Focused P5 probes cover:
  - missing `declared_gate_refs` RED,
  - explicit default-transition GREEN,
  - invalid concern with resolvable proposed target does not populate `immediate_target_ref`, `target_brick`, or `pending_target_ref` with the proposed target.
- Fixture consolidation is checker-fixture only; production P5 semantics remain in `plan_validation.py` and `walker_transition_concern.py`.
- Full local profile sweep is green on current main.

## Not proven / proof limits

- P5 does not prove P6-P9 or whole customer-ready closeout.
- P5 does not prove real-provider reliability, fresh-machine install, product comprehension, release/dashboard hardening, or customer dogfood.
- P5c used a single-adapter narrow implementation path after P5a/P5b collected multi-adapter design evidence but stalled before implementation; Gemini/Claude implementation QA is not proven for the final fixture consolidation.
- P5d/P5e did not close through complete official Building frontiers; their evidence is retained as support evidence for why fixture fallout was consolidated.
- Checker/profile green is support evidence only, not source truth, success judgment, quality judgment, or Movement authority.

## Next Movement candidate

Proceed to P6: verification-surface honesty / product route readiness, unless Smith requests a separate follow-up Building to re-run P5 fixture consolidation entirely through a smaller official route.
