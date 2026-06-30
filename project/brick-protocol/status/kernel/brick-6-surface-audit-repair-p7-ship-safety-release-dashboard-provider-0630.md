# BRICK 6-Surface Audit Repair - phase:P7 Ship-safety release/dashboard/provider hardening - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P7
phase_title: Ship-safety release/dashboard/provider hardening
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

public release/customer install 직전 필요한 export, dashboard ingest, provider boundary, CI/release gate를 harden한다.

## Audit References To Keep Open

- `final C9`
- `final C10`
- `final C11`
- `final C12`
- `S4-F9/F10/F11/F12`
- `S5-F12/F13`
- `S6-F9/F11/F12/F13/F14/F15`

## Must Preserve / 절대 지킬 것

1. release export는 tracked-only default, dirty guard, secret/local denylist, explicit include-untracked opt-in을 가져야 한다.
2. dashboard ingest는 HMAC/body signature, timestamp skew, event id replay, sequence rollback rejection을 가져야 한다.
3. provider boundary matrix는 Codex/Claude/Gemini isolation strength 차이를 고객에게 숨기지 않는다.
4. sensitive path write는 complete commit 전에 block 또는 loud mark되어야 한다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`

## Building Graph Shape Candidate

```text
design-ship-threats -> work-hardening -> fan([security-negative-qa, product-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- GitHub Actions/branch protection을 실제로 admission할 것인가, release script local gate로 충분한가?
- dashboard viewer auth는 app 내부에서 할 것인가 deployment wall 전제로 문서화할 것인가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

release/dashboard/provider/sensitive-write negative probes green; release governance evidence exists or not_proven explicit.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
