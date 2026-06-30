# BRICK 6 P1 Raw Evidence Scrub — Closure Evidence (0701)

Status: support evidence for P1 (raw evidence secret/PII/provider-session scrub). Not source truth, not success/quality judgment, not Movement authority, not whole-goal completion.

## Objective context

P1 of the BRICK 6-surface audit repair goal = raw evidence secret/PII scrub, closed through an official build()/brick build declared graph Building. Prior route-proof detours (0701a/b/c) and the route-concern address guard (brick-6-route-concern-address-guard-0701a) landed first; this doc records the P1 deliverable itself.

## Observed evidence

- An independent audit found P1's named artifacts ABSENT from main before this turn: support/checkers/profiles/raw_evidence_stream_scrub.yaml missing, not in support/checkers/profiles/core.yaml path_allowlist, and run_raw_evidence_stream_scrub absent from support/checkers/lib/kernel_checks.py. The earlier P1d sandbox commit 86be1ef was unmerged and its closure left broad proof as verification_gap.
- The prior P1c/P1d broad blocker read_side_projection_boundary now passes on current main.
- A rebased graph was declared (project/brick-protocol/status/kernel/GOAL/brick-6-p1-raw-evidence-scrub-0701e.json) and run via official build on base 52a74d1.
- Build brick-6-p1-raw-evidence-scrub-0701e: frontier_kind=complete, all link movements forward (12/12), code-qa/axis-qa/evidence-qa/closure all returned transition_concern_evidence=None, sandbox commit 24f829e.
- Adopted via cherry-pick into main as 2cb942d, touching exactly: support/checkers/check_profile.py, support/checkers/lib/kernel_checks.py, support/checkers/profiles/core.yaml, support/checkers/profiles/raw_evidence_stream_scrub.yaml, support/recording/raw_claim_trace.py.
- Post-adopt on main: raw_evidence_stream_scrub.yaml present, admitted in core.yaml, run_raw_evidence_stream_scrub present; py_compile + git diff --check clean; check_profile.py --all green (core + raw-evidence-stream-scrub profiles passed).

## Narrowly proven

- P1's raw scrub implementation + focused checker + core admission now exist on main and pass focused and broad checker gates as support evidence.
- The P1 deliverable was produced and adopted through the official build route with hard fan-in QA + closure returning no implementation/boundary/evidence concern.

## Not proven

- Whole goal completion (P2-P8 remain).
- Semantic completeness of scrub for all future sensitive payload classes (focused checker covers selected synthetic credential/PII/provider-session classes only).
- Provider reliability, real-provider fresh-machine readiness, customer comprehension.
- Smith approval and push to origin/main.

## Next Movement candidate

Proceed to P2 (post-HOLD resume isolation + explicit disposition) as the next declared graph Building, keeping P1 closure as support evidence only. Hold whole-goal completion until P2-P8 close and Smith approves push.
