# BRICK 6-Surface Audit Repair - phase:P2 Resume/post-HOLD isolation and explicit disposition - 2026-06-30

## Phase Symbol

```yaml
phase_ref: phase:P2
phase_title: Resume/post-HOLD isolation and explicit disposition
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
```

## Mission

post-HOLD approve/resume가 fresh customer run과 동등한 live-tree isolation 및 명시 disposition을 갖도록 한다.

## Audit References To Keep Open

- `final C16`
- `S4-F1`
- `S4-F11`
- `S3 lifecycle controls`
- `coverage matrix ADD-1`

## Must Preserve / 절대 지킬 것

1. support가 action/author를 silently default하지 않는다; Link/caller/COO disposition은 명시되어야 한다.
2. resume path는 live checkout을 직접 mutate하지 않음을 증명해야 한다.
3. HOLD는 lifecycle이고 Movement가 아니다; Movement는 forward/reroute만 쓴다.
4. adapter_cwd/output_root isolation contract가 없으면 fail-closed 또는 HOLD로 남긴다.

## Source Audit Documents (open these)

The finding shorthand above resolves inside these adopted audit files; open them before repair and treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s4-support-machine-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s3-link-axis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s6-product-surface-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-coverage-matrix-0630.md`

## Building Graph Shape Candidate

```text
design-resume-paths -> work-isolation-disposition -> fan([code-attack-qa, axis-attack-qa, evidence-integrity]) -> closure
```

This is an orchestration graph candidate, not a preset-only instruction. A later COO declaration may use a preset only when it exactly preserves the phase contract. Otherwise the phase must be declared as a manual graph over the official `build()` / `brick build` route.

## Operator Questions If Evidence Conflicts Or Scope Breaks

- resume을 fresh worktree wrapper로 강제할 것인가, 기존 adapter_cwd 계약을 fail-closed로 강화할 것인가?
- 기존 goal-runs/onboard approve UX를 얼마나 보존해야 하는가?
- Is this a Brick work-contract problem, an Agent return/performer problem, a Link carry/gate/Movement problem, or only a Support/Product projection problem?
- Which evidence row is missing before repair: Brick evidence, Agent evidence, or Link evidence?
- Should the Building HOLD and ask Smith/COO disposition instead of patching around the gap?

## Done Condition

approve/resume without explicit disposition or isolation cannot mutate live tree; negative probes green.

## Proof Limits

- This phase document is planning/support evidence only.
- It is not source truth, success judgment, quality judgment, or Movement authority.
- Implementation must run later through a declared Building using official `build()` / `brick build` route.
- Checker green is support evidence only; every load-bearing claim needs current evidence.
