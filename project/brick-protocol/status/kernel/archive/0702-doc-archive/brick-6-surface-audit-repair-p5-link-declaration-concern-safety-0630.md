# BRICK 6-Surface Audit Repair - phase:P5 Link declaration law and invalid concern target safety - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P5
phase_title: Link declaration law and invalid concern target safety
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

declared_gate_refs absence/default materialization과 invalid transition_concern pending target 문제를 Link 법으로 닫는다.

## Audit References To Keep Open

- `final C3`
- `final C4`
- `S3-F1`
- `S3-F2`
- `S3-F3`
- `S5-F3`
- `coverage matrix ADD-5 ADD-14 ADD-20`

## Must Preserve / 절대 지킬 것

1. missing declared_gate_refs는 reject하거나 materialization boundary에서 explicit default-transition으로 기록한다.
2. invalid transition_concern_evidence는 pending target을 만들 수 없다.
3. pending target은 declared plan + valid concern + adopted disposition basis가 있을 때만 보여준다.
4. HOLD/pause를 reroute로 말하지 않는다; invalid concern은 source boundary HOLD가 기본이다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s3-link-axis-0630.md`
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
design-link-law -> work-gate-concern-repair -> fan([code-attack-qa, axis-attack-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- default-transition을 raw row absence에서 금지할 것인가, explicit materialized default로 허용할 것인가?
- portfolio adoption과 single-Building gate law를 같은 checker로 묶을 수 있는가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

absence/default and invalid concern negative probes green; carry/portfolio coverage gap closed or explicitly not_proven.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
