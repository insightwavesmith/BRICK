# P7 Evidence Root Location Policy Cleanup

## Question

Is this an engine code change?

No. Current evidence points to root selection and documentation clarity, not an
engine contract violation.

## Measurement

- `support/recording/capture.py` defines `BRICK_EVIDENCE_HOME()` as `$BRICK_HOME`
  when set, otherwise `Path.home() / ".brick"`.
- `default_buildings_root()` and lazy `DEFAULT_BUILDINGS_ROOT` resolve the
  ref-less default to `BRICK_EVIDENCE_HOME()/project/brick-protocol/buildings`.
- `buildings_root_for("project:brick-protocol")` resolves the declared project
  vessel to the active checkout's `project/brick-protocol/buildings`.
- `support/operator/driver.py::run_building_intake` rejects ambiguous
  `project_ref` plus explicit `output_root`; then chooses, in order:
  declared `project_ref` via `buildings_root_for`, explicit `output_root`, or
  ref-less `DEFAULT_BUILDINGS_ROOT`.
- In this measured process, `BRICK_HOME` was unset, `Path.home()` was the local
  Codex sandbox home, and the ref-less default resolved under that `.brick`
  evidence home. A declared `project_ref: "project:brick-protocol"` resolved to
  this worktree's `project/brick-protocol/buildings`.
- `support/operator/reporter.py` already contains EVROOT2 handling for evidence
  roots under either the source repo root or the `$BRICK_HOME` / `~/.brick`
  evidence home, with declared-spine checks before external delivery.
- `support/checkers/check_building_root_anchor.py` explicitly admits the
  home evidence root anchor (`BRICK_EVIDENCE_HOME`) and the single
  `buildings_root_for(project_ref)` derivation seam.

## Minimal Fix Category

A. No engine code. Use declared `project_ref` or explicit `output_root` when a
repo-local dogfood Building root is intended, and document the ref-less default
as caller-local evidence home rather than repo-local.

## Changes Made

- Clarified `support/docs/references/setup.md` so `DEFAULT_BUILDINGS_ROOT` is
  described as `$BRICK_HOME/project/brick-protocol/buildings` or
  `~/.brick/project/brick-protocol/buildings`, while declared `project_ref`
  resolves to the repo-local project vessel.
- Clarified `support/docs/references/quickstart.md` with the same split in the
  customer-entry matrix and Evidence location section.

## Proof Limits

- This is support evidence and documentation only.
- It does not change Brick, Agent, or Link semantics.
- It does not choose Movement, judge success, judge quality, or create a source
  truth surface.
- It does not prove future dogfood launch commands will always declare the
  intended root; it only records the observed root policy and documents the
  operator choice.
