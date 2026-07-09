# Deku G1–G4 verification Building (project:deku)

## Objective
Run official vessel verification for G1 Conduct through G4 Dominate on code already under /Users/smith/projects/deku. G0 already has deku-g0-face-official-0709.

## Deliverables
1. Run full unittest suite: `cd /Users/smith/projects/deku && python3 -m unittest discover -s tests -v` (expect green).
2. Confirm G1 surfaces: CallBudget, memory pins, assembler, timeout graceful tests pass.
3. Confirm G2: access/grounding/verify replan≤1 tests pass; free-form plan OFF.
4. Confirm G3-P/K: policy rollback restore + wiki adopt map + hermes forbidden.
5. Confirm G4: pin_loss@50 measured, call_cap violations counted honestly, suite passes on mock personal path.
6. Closure: list remaining_not_proven (paid soak, Nemotron-loaded 50×, multi-provider worktree merge).

## Hard constraints
Prefer verify-over-rewrite: if already green, made_changes=false with no_changes_reason.
Write scope only if a real test gap requires a fix under deku paths.
Vessel: project/deku/buildings.

## Evidence
commands_run, observed_evidence paths, not_proven honest.
