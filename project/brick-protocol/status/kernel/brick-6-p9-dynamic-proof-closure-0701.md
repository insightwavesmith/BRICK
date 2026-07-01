# BRICK 6 P9 Dynamic Proof Closure Artifact - 2026-07-01

Status note for phase:P9 live dynamic proof-run Building
`brick-6-p9-dynamic-proof-run-0701b`, attempt 2, under
`goal:brick-6-surface-audit-repair-0630`.

This file is project-local support/status evidence only. It is not source
truth, not a success or quality judgment, and not Link Movement authority.

## Task Source

- Building root:
  `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p9-dynamic-proof-run-0701b`
- Task statement:
  `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p9-dynamic-proof-run-0701b/work/task.md`
- Declared plan copy:
  `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p9-dynamic-proof-run-0701b/work/declared-building-plan.json`
- Goal status source:
  `project/brick-protocol/status/kernel/brick-6-surface-audit-repair-goal-0630.md`

## Run Disposition

This is the P9 live dynamic proof-run Building, attempt 2. It runs through the
normal local-CLI route with the declared local adapters for this Building. It is
not a fresh-machine or customer-credential real-provider proof. Real-provider
availability, fresh-machine install behavior, and repeated customer-run
reliability remain separate not_proven items unless separately recorded.

## Stub vs Real-Provider Disposition (COO-added, resolves a QA-flagged gap)

- **Stub**: this run used the normal local-CLI route (codex-local/claude-local/
  gemini-local role defaults, no adapter override) -- this is the "stub" tier
  in this goal's actual vocabulary. `adapter:local` (the literal built-in
  smoke-test fixture) was tried during attempt 1's construction and rejected
  by `compose_building`'s own validator (`missing_adapter_write_capability`)
  because it cannot write at all -- confirmed live, not assumed.
- **Real-provider**: fresh-machine install, a customer's own credentials, and
  repeated multi-run provider reliability are explicitly NOT proven by this
  run and remain a separate, distinct not_proven item (already listed in the
  goal's "Not Proven At Goal Start" section).

## Attempt History

Attempt 1 (`brick-6-p9-dynamic-proof-run-0701a`) is not adopted for this proof
shape. Its reroute-only artifact repair node had no normal incoming edge, so
the graph root seeding treated it as an immediately executable root and the
intended fan-out/fan-in/barrier sequence was not exercised.

Attempt 2 (`brick-6-p9-dynamic-proof-run-0701b`) uses a normally reachable
reroute target, `p9-customer-run-artifact`, and keeps an explicit
`p9-second-fanout-gate` barrier between the first fan-in target and the second
fan-out source.

## Repo State (COO-recorded at adoption; the final closure node observed but
could not write these back, since closure/QA nodes are probe_write only)

- `git status --short`: `?? project/brick-protocol/status/kernel/brick-6-p9-dynamic-proof-closure-0701.md`
  (this file itself, before being committed).
- `git status --branch --short`: `## HEAD (no branch)` -- detached HEAD, as
  expected for an official-route Building worktree.
- `git rev-parse HEAD`: `0db69209c90481aec7c3d37b96e775d4149c9baf`.
- `git branch --show-current`: (empty -- detached HEAD).
- upstream delta: not applicable, no upstream ref from a detached HEAD.
- This file was committed to the Building's detached worktree and then
  fast-forward merged into main by the COO after independent verification;
  main was not pushed to origin (requires separate Smith authorization).

## Checker-Result Discrepancy (COO disposition, from independent verification)

Three different steps in this Building reported three different results for
what should be the same `check_profile.py --all` command against the same
worktree state, seconds to minutes apart:

- `p9-code-qa`: rc=1, correctly recorded the cause as unestablished/not_proven.
- `p9-axis-qa`: claimed an unhedged "100% green conformance" -- this claim is
  an OUTLIER and is explicitly NOT credited; it is not corroborated by the
  other two lanes and does not match the actual mechanism (see below).
- `p9-final-closure`: rc=1, "No usable temporary directory found".

An independent, adversarial re-run workflow (0701, separate from this
Building) reproduced the real cause: the Building's own sandboxed execution
context lacked a usable `HOME`/tmp directory for this specific command.
Running the identical command correctly (`HOME=$(mktemp -d)
PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py
--all`) in the same worktree state produced a clean **exit 0, 30/30 profiles
passed, 0 failed**. This is the credited, ground-truth result. `p9-axis-qa`'s
"100% green" claim is therefore NOT trusted as independently verified by that
lane (its own environment likely hit the same tmpdir issue, or it did not
actually run the command as described) -- flagging this as an internal
QA-discipline gap for future Buildings: the fan-in barrier layer should
reconcile contradictory QA claims about the same command rather than passing
all three through silently, and this Building's did not.

## Reroute Concern Disposition (COO decision)

`p9-reroute-trigger-qa` emitted a real, non-binding `implementation_gap`
concern naming this artifact's missing dedicated stub-vs-real-provider
disposition section. By this Building's own declared plan
(`fan_in_source_transition_concern_adoption=advisory` for axis-attack-qa-kind
fan-in-source nodes), that concern structurally cannot auto-adopt a reroute --
only the fan-in closure node or an explicit human/COO disposition can. COO
decision: do not fire a third real-provider Building cycle for this. The
missing section is added directly above (Stub vs Real-Provider Disposition)
as a direct COO documentation edit, which resolves the concern's substance.
Lesson for future Buildings: a QA node's own work_statement should not promise
an auto-reroute outcome its declared plan topology forecloses -- if a single-
target auto-reroute is genuinely intended for a specific QA node, it must not
be declared as a `fan_in_source` advisory node.

## Evidence Pointers

- Work step output directory:
  `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p9-dynamic-proof-run-0701b/work/step-outputs/`
- Raw evidence directory:
  `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p9-dynamic-proof-run-0701b/raw/`
- Spine evidence directory:
  `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p9-dynamic-proof-run-0701b/evidence/spine/`
- Prior related closure:
  `project/brick-protocol/status/kernel/brick-6-fanout-latency-and-fanin-cohort-closure-0701.md`
- Derived write-scope closure:
  `project/brick-protocol/status/kernel/brick-6-graph-write-scope-default-closure-0701.md`
- Fan barrier checker closure:
  `project/brick-protocol/status/kernel/brick-6-graph-topology-fan-barrier-checker-closure-0701.md`

## Proof Limits

- This artifact records the P9 proof-run status and bounded evidence pointers
  only.
- Attempt 1 is preserved as a failed proof shape and is not adopted.
- Attempt 2 exercises reroute/replay back to the original work node when a
  declared QA concern is adopted; it does not re-validate task #7's exact
  one-hop fan-in cohort fix.
- Checker green, frontier state, report delivery, and this status artifact are
  support evidence only.
- This artifact does not claim source truth, provider/runtime authority,
  quality judgment, success judgment, Link sufficiency, or Movement choice.

## Not Proven

- Real-provider proof on a fresh machine with customer credentials.
- Repeated provider reliability.
- Task #7's exact one-hop cohort fix in this P9 run.
- Final repo-state closure values, until the final closure node records them.
- Customer-ready status beyond the explicitly recorded local proof slice.
