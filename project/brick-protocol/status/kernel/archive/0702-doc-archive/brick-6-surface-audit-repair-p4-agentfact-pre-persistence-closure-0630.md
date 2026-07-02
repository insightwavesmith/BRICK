# BRICK 6-Surface Audit Repair - phase:P4 AgentFact pre-persistence closure - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P4
phase_title: AgentFact pre-persistence closure
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

chat-session/submission intake가 AgentFact-forbidden top-level authority keys를 디스크 저장 전에 reject하도록 한다.

## Audit References To Keep Open

- `final C2`
- `S2-F1`
- `S5-F2`
- `coverage matrix ADD-7 ADD-8`

## Must Preserve / 절대 지킬 것

1. top-level movement/status/success/target/verdict/result 등 AgentFact authority keys는 pre-persistence에서 reject한다.
2. nested evidence 안의 status/result 같은 일반 데이터는 무작정 recursive ban하지 않는다.
3. poisoned submission.json이 write-exclusive로 wedge를 만들기 전에 깨끗한 HOLD/reject로 끝난다.
4. AgentFact shape remains received_work + returned; support는 verdict를 만들지 않는다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s2-agent-axis-0630.md`
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
design-agentfact-boundary -> work-prepersist-validator -> fan([code-attack-qa, axis-attack-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- bad submission은 hard reject인가, parked-with-reason HOLD인가?
- chat-session human handoff UX에 어떤 error packet을 보여줄 것인가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

top-level forbidden payload cannot persist; nested ordinary evidence remains legal; replay wedge probe green.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
