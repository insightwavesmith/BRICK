# BRICK 6-Surface Audit Repair - phase:P0 Audit adoption and baseline - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P0
phase_title: Audit adoption and baseline
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

감사 9문서와 support review 3문서를 repair programme의 routing context로 채택하고, repair 시작 전 기준선을 잠근다.

## Audit References To Keep Open

- `project/brick-protocol/status/kernel/brick-6-surface-audit-s1-brick-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s2-agent-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s3-link-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-readiness-tuples-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-report-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-review-addenda-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-claude-opinion-0630.md`

## Must Preserve / 절대 지킬 것

1. 감사 문서는 source truth가 아니라 support/audit evidence로만 채택한다.
2. flat ISSUE는 readiness grade가 아니라 findings-inventory label로 해석한다.
3. P1~P8 구현 전 active priority order(protocol-live vs ship-imminent)를 명시한다.
4. audit docs/Claude packets가 untracked이면 채택 commit 또는 explicit park 중 하나로 처분한다.

## Building Graph Shape Candidate

```text
review-audit-packets -> baseline-verify -> adoption-record -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- 감사 문서와 Claude packets를 함께 commit할 것인가, 아니면 Claude packets는 review-evidence appendix로만 둘 것인가?
- 현재 목표는 protocol-live correctness인가, public ship-imminent hardening인가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

audit packets are committed/parked, baseline commands recorded, and P1 start condition is declared.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
