# BRICK 6-Surface Audit Repair - phase:P8 Final dynamic proof and customer-ready replay - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P8
phase_title: Final dynamic proof and customer-ready replay
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

static audit/repair 이후 current-main에서 official build() route로 dynamic/customer proof를 다시 닫는다.

## Audit References To Keep Open

- `final C8`
- `final C19`
- `S6-F8`
- `readiness tuples Final Readiness Judgment`
- `current-origin dogfood onebrick artifact`

## Must Preserve / 절대 지킬 것

1. official build() route만 사용한다; internal/debug helper를 고객 route처럼 말하지 않는다.
2. frontier_kind=complete, real artifact, evidence root, commit/adoption proof가 있어야 한다.
3. HOLD/resume, fan-in, report/dashboard projection 중 scope로 선언한 dynamic behavior는 current evidence로 증명해야 한다.
4. customer comprehension은 fresh reader/Smith validation 없이는 not_proven 또는 waived로 남긴다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-readiness-tuples-0630.md`
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
design-proof-scope -> work-customer-run -> fan([technical-qa, comprehension-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- final proof는 real provider-backed인가, provider-stubbed인가, 둘 다 필요한가?
- fresh-machine proof를 실제 clean machine으로 할지 current-machine fresh clone으로 제한할지?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

current-main dynamic proof completes, --all green, main=origin/main, remaining customer comprehension status explicit.

## Phase Number Note

Per the goal-doc P0..P9 revision (Smith/Codex 0701), final dynamic proof is now
`phase:P9`. The filename keeps `p8`; the goal doc mapping wins.

## Scope Addition (Smith/Codex review 0701)

- stub vs real-provider split is mandatory in the done condition:
  - stubbed proof closes the protocol path ONLY.
  - real-provider / fresh-machine customer-ready claim remains `not_proven` unless a
    separate real-provider run is performed and recorded.
- Replace the ambiguous `main = origin/main` close criterion with: repair branch /
  main is clean, pushed or explicitly parked, and `git status` / `HEAD` / upstream
  delta are recorded (P0 audit commits can legitimately put local main ahead of
  origin, so equality is not the right test).

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
