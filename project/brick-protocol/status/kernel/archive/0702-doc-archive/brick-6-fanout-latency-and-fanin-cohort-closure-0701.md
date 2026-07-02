# Tasks #6+#7 closure evidence — fan-out latency + fan-in cohort one-hop fix (0701)

Status: support evidence for tasks #6 and #7 (finding docs
`brick-6-fanout-node-latency-not-recorded-finding-0701.md` and
`brick-6-fan-in-cohort-reverify-one-hop-blindspot-finding-0701.md`). Not
source truth, success judgment, quality judgment, or Movement authority.

## Result

Single Building launch, clean on the first try (no launch-method mistakes
this time -- the lessons from task #8's saga, now in
`brick-build-launch-playbook-0701`, held). `frontier_kind=complete`.

- Declaration commit: (this Building's graph packet)
  `brick-6-fanout-latency-and-fanin-cohort-fix-0701a.json`.
- Sandbox output commit: `5a2400310d04e9e679f7dd57f0da4c83994f24d9`.
- Adopted to main as: `4f0d147`.
- Changed files: `support/operator/walker_kernel.py`,
  `support/operator/walker_fan_in.py`,
  `support/checkers/check_adapter_usage_meter.py`,
  `support/checkers/check_bounded_agent_proposed_routing_loop0.py`.

## FIX A (task #6, fan-out latency)

`walker_kernel.py` now captures live per-node adapter dispatch timing
(`adapter_dispatch_timing`) during fan-out dispatch and persists it both to
a new `raw/adapter-usage.jsonl`-family record
(`_adapter_dispatch_timing_record`, `support_record_role:
"adapter-dispatch-timing"`) and enriches the deferred `step-output.json`
projection after the drain closes
(`_enrich_step_output_with_adapter_dispatch_timing`). This makes real
per-lane duration independently auditable from evidence, not only
inferable from source code, without changing `record_step_output_immediately`
semantics or the drain ordering itself.

New checker-first probe: `check_adapter_usage_meter.py::_assert_dynamic_walker_dispatch_timing_persisted`
-- a static structural pin confirming the required plumbing markers exist
in `walker_kernel.py` (timing capture, record emission, step-output
enrichment). Wired into the profile's `check()`.

**Not addressed in this Building** (explicitly deferred by design per the
task statement's optional framing): the `changed_files` lane-scope half of
the finding -- whether fan-out lanes' `changed_files` reporting should be
scoped to each lane's own diff/write_scope rather than the current shared-
sandbox snapshot. This remains open; see finding doc.

## FIX B (task #7, fan-in cohort one-hop blind spot)

`walker_fan_in.py::_fan_in_cohort_replay_plan` no longer only checks the
reroute's landing node for fan-in-source membership. It now walks
`trigger_step_refs = [target_step_ref, *already_scoped_step_refs]` (the
landing node plus its declared replay scope) and checks EACH for fan-in-
source membership. If any node in that chain is a fan-in source, the
existing cohort-reverify-or-vouch logic now applies against that node (the
"trigger"), distinct from the reroute landing itself. Evidence records now
carry both `reroute_landing_step_ref` and `cohort_trigger_step_ref` so the
distinction is auditable, not collapsed.

New checker-first probe: `check_bounded_agent_proposed_routing_loop0.py`
"knot3-cohort-e" -- directly reproduces the exact blind-spot shape from the
finding (a `rs-work-docs` reroute landing one hop above the real fan-in
source `rs-docs-lane-qa`, with unvouched sibling `rs-checker-lane-qa`) and
asserts: (1) the unvouched sibling IS now re-verified, (2) the already-
scoped fan-in source is not re-appended, (3) records distinguish trigger
from landing. A second case (`knot3-cohort-e-vouch`) confirms
`sibling_independence` still correctly skips when declared.

## Independent verification performed before adoption (Claude, detached worktree)

Clean on the first pass this time (prior worktree-contamination lessons
applied: fresh isolated `/tmp/verify-fanout-fanin-0701` path, pre-check
`git status --short` before running):

```text
py_compile (all 4 changed files): PASS
check_profile.py --profile adapter_usage_meter.yaml: PASS
check_profile.py --profile bounded_agent_proposed_routing_loop.yaml: PASS
  (kernel_check=bounded_agent_proposed_routing_loop, 40.6s -- includes the
   new knot3-cohort-e/e-vouch cases)
git diff --check: PASS
check_profile.py --all: DIRECT_EXIT=0, 30/30 profiles passed to completion,
  including pin_estate_integrity ("0 history-doc pin block(s)") and
  tier-a-three-axis-conformance (last profile in the sweep)
Re-verified again after cherry-pick onto current main: py_compile PASS,
  focused profile PASS, git diff --check PASS
```

## Narrowly proven

- Fan-out dispatch now records live per-node adapter timing as independently
  auditable evidence.
- A reroute landing one hop above a declared fan-in source now correctly
  triggers cohort re-verification of unvouched siblings (previously silently
  skipped).
- `sibling_independence` vouching still functions correctly for the
  replay-scope-triggered case.

## Not proven

- `changed_files` lane-scope (deferred half of task #6, still open).
- Whether the replay_scope walk covers every possible multi-hop topology
  beyond the one-hop case reproduced in the probe.
- Task #9 (dual plan-materialization producer reconciliation) remains
  entirely open and untouched by this Building.
- P8 ship safety, P9 dynamic customer replay, fresh-machine install,
  real-provider reliability, customer comprehension.

## Next Movement candidate

Tasks #6 and #7 are closed (the changed_files lane-scope half of #6 stays
open as a known, explicitly-recorded gap, not silently dropped). Proceed to
task #9 (dual-producer reconciliation, needs its own feature-parity
investigation before a Building can even be scoped), then P8.
