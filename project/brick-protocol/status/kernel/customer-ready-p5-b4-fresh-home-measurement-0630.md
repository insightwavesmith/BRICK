# Customer-Ready P5-B4 Fresh-HOME Measurement — 0630

Status: support evidence only. Not source truth / success judgment / quality judgment / Movement authority / P7 PASS.

## Measurement

Before launching `p5-b4-fresh-machine-prep-0630`, the operator measured the previously documented P7 hazard with an empty HOME and BRICK_HOME:

```bash
cd /Users/smith/projects/BRICK
tmp=$(mktemp -d)
HOME="$tmp" BRICK_HOME="$tmp/.brick" \
  PYTHONPATH=support/import_identity:. \
  python3 support/checkers/check_profile.py --profile read-side-projection-boundary
```

Observed result in the live terminal: exit 0; `read-side-projection-boundary` passed, including `intake_evidence_projection_case` and the read-side projection kernel checks.

## Narrow meaning

This means the former empty-HOME `intake_evidence_projection_case` item should not be carried as an unmeasured active blocker in this checkout.

## Proof limits

This does **not** prove P7. P7 still requires a real `origin/main` fresh clone, install, init/doctor/auth/onboard, official `brick build` / `brick fire`, and evidence/frontier inspection using documented steps only.

The P5-B4 Building closure also records that this standalone measurement was not persisted as raw command transcript inside the Building evidence root; this note preserves the operator-observed command and limits for handoff.
