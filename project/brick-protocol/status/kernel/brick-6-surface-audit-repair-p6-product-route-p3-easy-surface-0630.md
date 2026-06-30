# BRICK 6-Surface Audit Repair - phase:P6 Product route and P3 Easy Building surface - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P6
phase_title: Product route and P3 Easy Building surface
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

P3 Easy Building을 새 engine/--large가 아니라 official brick build 위의 declaration ergonomics로 제품화한다.

## Audit References To Keep Open

- `final C5`
- `final C6`
- `final C13`
- `final C14`
- `S6-F2/F3/F4/F10/F16/F17/F18`
- `S4-F4`

## Must Preserve / 절대 지킬 것

1. public first-use route는 brick init/status/doctor/build/build --graph로 좁힌다.
2. run_building_plan, assembly.fire, full Building Plan, onboard.py는 internal/advanced로 분리한다.
3. --large를 되살리지 않는다; task intake/sizing/graph packet이 official build()로 간다.
4. CLI/dashboard는 state, reason, next_action, decision_owner, evidence_root, proof_limits, not_proven을 보여주되 authority가 되지 않는다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`

## Common Phase Template Requirement (0701)

This phase MUST apply the goal document's mandatory per-phase common template:
`invariant`, `Brick / Agent / Link attribution`, `write_scope`, checker-first
negative probe, focused checker/profile, `check_profile.py --all`, evidence root,
changed files/diff, `observed_evidence` / `narrowly_proven` / `not_proven` /
`next Movement candidate`, and QA source-mutation ban (`probe_write` only). If a
phase Building or phase status cannot populate one of these fields, record the
gap explicitly under `not_proven` rather than treating the phase as closed.

## Building Graph Shape Candidate

```text
design-product-route -> work-doc-cli-projection -> fan([customer-comprehension-qa, axis-attack-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- ordinary customer run에서 checker detail을 어느 수준까지 숨기고 debug/evidence로 넘길 것인가?
- P3 Easy graph authoring은 CLI subcommand인가 skill/guide인가, 둘 다인가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

docs/CLI classify public vs internal routes; P3 Easy declaration graph reaches official build(); product-focused checks green.

## Phase Number Note

Per the goal-doc P0..P9 revision (Smith/Codex 0701), this product-route phase is
now `phase:P7`. The filename keeps `p6` for stability; the goal doc mapping wins.

## Scope Addition (Smith/Codex review 0701)

Named product observations and surface cleanups to include:

- Emit `readiness_blocker_observation` and `protocol_compliance_observation` as named
  product observations (support evidence, not Movement/quality authority).
- Use the shared failure attribution taxonomy (task_definition_gap,
  missing_source_evidence, brick_contract_gap, agent_return_shape_gap,
  provider_runtime_failure, link_gate_insufficient, human_disposition_required,
  write_scope_mismatch, checker_limit, dashboard_projection_stale).
- CLI raw `str(exc)` exposure cleanup: no raw traceback/exception text leaking to the
  operator surface.
- bare `brick` default behavior product decision: status vs help (decide and record).
- stale profile-count / `setup.md`-style docs cleanup at the product surface.

Easy Building big-work shape MUST be declared as the route (so large work never
escapes into a `--large` / hardcoded path):

```text
make X
-> task intake
-> design (Codex + Claude fan-out)
-> design QA / axis QA
-> closure plan-confirm
-> parallel dev lanes
-> lane QA
-> fan-in
-> Codex QA + axis QA
-> closure
```

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
