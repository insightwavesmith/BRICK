# BRICK 6-Surface Audit Repair - phase:P3 Brick return-shape truth and Link carry filtering - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P3
phase_title: Brick return-shape truth and Link carry filtering
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

fan-in source Brick return shape를 return.yaml full truth로 복원하고, downstream filtering을 Link carry/closure 정책으로 이동한다.

## Audit References To Keep Open

- `final C1`
- `S1-F1`
- `S1-F2`
- `S5-F1`
- `memory: graph declaration must preserve template return shape/ref/carry fields`

## Must Preserve / 절대 지킬 것

1. Brick return shape는 brick/templates/bricks/<kind>/return.yaml에서 온 full shape여야 한다.
2. operator/customer graph packet이 required_return_shape를 author하지 못하게 한다.
3. transition_concern_evidence 제거는 Brick shape 축소가 아니라 Link carry/closure filtering에서만 일어난다.
4. assembly/easy graph checker는 old shrink behavior를 green으로 보존하면 안 된다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s1-brick-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
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
design-contract-seam -> work-return-shape-repair -> fan([code-attack-qa, axis-attack-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- Link carry filtering의 single source는 walker carry인가 closure synthesis인가?
- 기존 historical evidence의 shrunk shapes를 active failure로 볼지 historical support로 둘지?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

old observed_evidence,not_proven shrink path is RED; full template shape plus filtered carry is GREEN.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
