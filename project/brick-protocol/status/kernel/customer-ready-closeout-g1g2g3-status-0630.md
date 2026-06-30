# Customer-Ready Closeout — G1/G2/G3 Live Status Measurement — 0630

Status: support evidence only / operator measurement. Not source truth, not
success judgment, not quality judgment, not Link Movement authority.

Goal of record: `customer-ready-closeout-goal-0630.md` (G1 route-default,
G2 release pruning finalization, G3 FINAL architecture cleanup).

This doc records a LIVE re-measurement of all three tracks against current main,
because the prior route-track plan (`customer-ready-fanin-route-link-track-0629.md`)
was written on a different line (commit 4e335bf, 0629) and main has advanced
since (`ca79c12`).

## Measurement base

```text
branch = main
HEAD = ca79c12 (local; origin/main = b9d193d, ahead 2 unpushed goal docs)
worktree = clean before this doc
```

## G1 route-default policy — engine behavior MEASURED GREEN

The 0629 route-track doc carried two engine bugs as "수리 중":

```text
#1 fluent fan-in concern adoption rejected
#3 reroute redo carry crash (walker_kernel.py:525)
```

LIVE measurement on current main contradicts those still being open:

- `link/route_policies/basic_qa_repair.yaml` is intact: implementation_gap ->
  dev (replay [qa]), design_gap -> design (replay [work,qa], human_gate_required),
  verification_gap intentionally non-reroute.
- `support/operator/walker_kernel.py` line ~525 is now a structured
  `_build_fan_in_wait_all_hold(...)` path with `cascade_depth` tracking, not a
  bare crash. The 0629 line:525 crash reference is STALE.
- `building-operator-driver0` profile PASSES, including case
  `live_qa_reroute_to_work_n2`: a real dynamic fan-in graph where a code-attack-qa
  brick emits ONE `implementation_gap` transition_concern_evidence targeting the
  upstream work brick, default-transition ADOPTS it, and the dynamic walker
  records a SECOND work attempt before closure. Recorded brick instance sequence:
  `brick-qa-reroute-work -> brick-qa-reroute-code-attack-qa -> brick-qa-reroute-work
  -> brick-qa-reroute-closure`.
- Same profile also proves fan-in receipt closure (`live_dynamic_fan_in_n3`):
  the fan-in closure consumer receipt carries all three upstream QA step-output
  addresses.

Interpretation (narrowly_proven): the ENGINE mechanism for "user draws a fan-in
graph, a QA concern is emitted, Link adopts it as a reroute, the walker replays
work" is live and green on main. The two bugs that blocked it are no longer
reproducing.

G1 policy-doc follow-up landed as operator-maintenance candidate:
`customer-ready-g1-no-link-policy-docs-skill-sync-0630.md` updates the customer/operator skill chain so it teaches the no-link/materialized-forward distinction.

NOT proven / remaining G1 work after that docs/skill sync:

```text
- Deep L2 cascade replay beyond the measured n2 single-reroute case remains
  not_proven.
- Fresh customer reading-comprehension of the updated docs/skills is not proven.
- The docs/skill sync was direct operator maintenance, not a Building-produced
  patch; next implementation slice should return to Building-first operation.
```

## G2 customer release pruning — export MEASURED CLEAN

Fresh `release_export.sh` run on current checkout:

```text
copied files: 380
excluded roots: project/, brick_protocol.egg-info/
excluded path matches: 4301
top-level: AGENTS.md README.md agent/ brick/ link/ pyproject.toml support/
operator-literal grep outside README: clean (no /Users/smith, no insightwavesmith)
```

G2 fresh-export CLI smoke follow-up landed as operator-maintenance candidate:
`customer-ready-g2-fresh-export-cli-smoke-0630.md` measures a fresh export, `uv sync`, import, CLI help, and `brick verify` GREEN. It also found and corrected an over-green docs claim: provider-free `brick build --adapter adapter:local` with verdict-bearing design/review/closure currently returns `agent_incomplete`/`not_ready`, not complete.

NOT proven / remaining G2 work after that docs/measurement sync:

```text
- A real provider-backed fresh export build reaching frontier_kind=complete was
  not re-run here.
- Full customer comprehension remains not_proven.
- release export parity (byte-for-byte across runs) not asserted.
- The docs/measurement sync was direct operator maintenance, not a Building-produced patch.
```

## G3 FINAL architecture cleanup — current target re-measured

LOC on current main (live):

```text
support/checkers/lib/kernel_checks.py   11452  <- now the LARGEST godmodule
support/checkers/lib/case_runners.py     8503
support/checkers/check_bounded_agent_proposed_routing_loop0.py  6923
support/recording/spine_projection.py    2902
support/operator/onboard.py              2849
```

Correction to the 0628 plan: the FINAL-architecture leaf series so far targeted
`case_runners.py` (8 leaves landed). On current main `kernel_checks.py` (11452)
is the bigger godmodule and is the higher-value next decomposition target. The
0628 plan's LOC coordinates are stale; live measurement governs.

G3 first kernel_checks.py leaf LANDED (0630): the product no-Smith-residue scan
cluster moved VERBATIM to `support/checkers/lib/no_smith_residue_check.py`
(kernel_checks.py 11452 -> 11325, net -127). Ledger=
`customer-ready-final-architecture-no-smith-residue-ledger-0630.md`, proof=
`customer-ready-final-architecture-no-smith-residue-proof-0630.md`. Verified:
re-export + dispatch identity, live inspected=39, mutation-RED, REAL HOME --all GREEN.

NOT proven / remaining G3 work:

```text
- more kernel_checks.py leaves remain (11325 still the largest godmodule).
- agreed stop condition for "final architecture cleanup" is not yet declared;
  remaining debt must be named at stop.
```

## Verification of this measurement turn

```text
building-operator-driver0 profile: PASS (rc=0)
release_export.sh: ran, export clean
git diff --check: (run at commit time)
REAL HOME check_profile.py --all: (run at commit time)
```

## Disposition (COO)

```text
G1 = engine route/reroute behavior PROVEN green on main; remaining = no-link
     default POLICY + customer docs/skills (not engine repair). 0629 "수리 중"
     bug flags are STALE.
G2 = export literal/structure CLEAN; remaining = comprehension + fresh-machine.
G3 = first kernel_checks.py leaf LANDED after this measurement base;
     no_smith_residue extraction is narrowly proven, but more leaves and a stop
     condition remain.
```

This is forward measurement, not closeout. The goal stays ACTIVE.
