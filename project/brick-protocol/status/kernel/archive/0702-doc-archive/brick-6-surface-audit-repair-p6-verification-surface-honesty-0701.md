# BRICK 6-Surface Audit Repair - phase:P6 Verification surface honesty - 2026-07-01

## Phase Symbol

```yaml
phase_ref: phase:P6
phase_title: Verification surface honesty
source_audit_commit: 17eaade696998cd0de7bbd85ceb7525f349588e9
mode: future_implementation_by_official_build_route
operator_role: COO/operator handles routing, judgment, evidence synthesis, and Building graph declaration; performer lanes implement inside declared Buildings.
supersedes_note: Split out of the original P7 ship-safety bundle (Smith/Codex review 0701) so verification honesty closes on the internal dogfood path before product/ship/dynamic-proof phases.
```

## Mission

검증 표면이 정직한지 닫는다. test/checker가 실제 asserted behavior를 검증하지 않고
skip/stub/stale-archive로 green을 내는 경로를 제거하고, focused profile과
`check_profile.py --all`이 동일 결론을 내도록 한다. 이것은 ship-safety 이전에,
내부 dogfood 경로에서 먼저 닫아야 하는 "검증 정직성" 항목이다.

## Invariant

A passing verification surface means the asserted behavior actually held: no
false-green from skips, stubs that remove the assertion, stale `/tmp` git-archive
copies, focused-vs-`--all` divergence, or non-reentrant checker state.

## Brick / Agent / Link Attribution

- Brick: checker/profile work contracts and required return shape.
- Agent: performer implements probes/fixtures; QA/Inspector lanes probe_write only.
- Link: forward/reroute on declared boundaries; closure-synthesis is the only
  Link-facing transition_concern source in hard fan-in.
- Support/checker stays support evidence; it is not source truth, success, quality,
  or Movement authority.

## Must Preserve / 절대 지킬 것

1. pytest/test surface honesty: 테스트가 skip/xfail/stub로 핵심 assertion을 비우고
   통과하지 않는다.
2. checker reentrancy: 같은 입력에 대해 focused profile과 `--all`이 동일 결론.
   tempdir/archive divergence로 인한 false-green 금지.
3. `--all`은 worktree 자체에서 돌린다; 별도 `/tmp` git-archive 사본에서 돌려
   "변경이 포함 안 된 green"을 만들지 않는다.
4. profile-count / `setup.md` 류 stale doc drift를 관찰·정정한다.
5. checker green은 support evidence일 뿐, requirement 전체 완료가 아니다.

## Checker-First Negative Probe (required)

- Add a probe that REDs when a test/checker would pass while the asserted behavior
  is absent (skip/stub/stale-archive), then GREENs once the honest assertion runs.
- Record focused profile result AND `check_profile.py --all` result as support
  evidence; they must agree.

## Audit References To Keep Open

- `S5 checker-system findings`
- `final synthesis: protocol-live verification honesty`
- `coverage matrix: verification/test honesty rows`

## Source Audit Documents (open these)

Open these adopted audit files before repair; treat them as support evidence only.

- `project/brick-protocol/status/kernel/brick-6-surface-audit-final-synthesis-0630.md`
- `project/brick-protocol/status/kernel/brick-6-surface-audit-s5-checker-system-0630.md`
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

## Completion Definition

- The negative probe demonstrates no false-green path remains for the targeted
  verification surfaces.
- focused profile and `check_profile.py --all` agree and are recorded.
- stale profile-count / setup docs are corrected or the drift is recorded as
  `not_proven` / next work.
- Report separates `observed_evidence` / `narrowly_proven` / `not_proven` /
  `next Movement candidate`, with failure (if any) attributed via the shared
  failure attribution taxonomy (notably `checker_limit`).
- This phase is closed on the internal dogfood path, not deferred to ship-time.
