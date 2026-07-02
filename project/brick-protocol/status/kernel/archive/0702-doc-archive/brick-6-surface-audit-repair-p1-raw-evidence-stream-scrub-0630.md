# BRICK 6-Surface Audit Repair - phase:P1 Raw evidence stream secret/PII scrub - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P1
phase_title: Raw evidence stream secret/PII scrub
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

raw BRICK JSONL stream에 secret/PII-looking payload가 조용히 저장되지 않도록 evidence integrity seam을 수리한다.

## Audit References To Keep Open

- `final C15`
- `S4 Support F11/raw stream addenda`
- `S5 Checker F13`
- `S6 Product ship-safety refs`

## Must Preserve / 절대 지킬 것

1. 이 phase는 Support/evidence integrity 수리이며 Brick/Agent/Link authority를 새로 만들지 않는다.
2. raw/brick-work, raw/agent-received, raw/agent-return, raw/adapter-error 계열 writer를 대상으로 한다.
3. credential/token/private-key/session-body-looking fixture가 raw stream에 원문 저장되면 RED여야 한다.
4. redaction/block/mark 정책은 evidence refs와 proof_limits를 보존해야 한다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
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
design-evidence-surfaces -> work-guard-redaction -> fan([code-attack-qa, axis-attack-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- 차단(block)과 redaction 중 어느 policy가 replay/evidence 재현성을 덜 손상하는가?
- PII-looking text의 false positive를 not_proven으로 남길 threshold는 무엇인가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

negative probes prove raw secret/PII fixtures cannot silently persist; focused checkers and --all are green.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
