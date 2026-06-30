# Customer-Ready Release Pruning — Export Operator-Literal Scrub — 0630

Status: FORWARD candidate / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

## Scope

This is a narrow customer release-pruning expansion after the first release
pruning slice and the durable `product_no_smith_residue` guard.

Goal: the clean release export should not contain raw Smith-local operator
literals outside the README working-example allowance. The checker logic may
still synthesize the same forbidden strings at runtime for FIRE probes, but the
source tree should not ship those raw literals in comments or probe strings.

## Composition note

This turn was direct operator maintenance, not a new official Building run. That
is a proof limit: no Building frontier, raw Agent returns, or sandbox commit were
created for this slice. The next code-bearing release-pruning or FINAL
architecture slice should return to a declared Building graph (work -> fan-in QA
-> closure/route disposition) unless Smith explicitly keeps it as operator
maintenance.

## Changed files

```text
support/checkers/lib/kernel_checks.py
support/checkers/check_profile.py
support/checkers/check_package_path_admission.py
```

Changes:

- `kernel_checks.py` now constructs the Smith user-home and GitHub-org probe
  literals from symbolic parts before injecting them into FIRE probes.
- Product-residue detection still checks for the concrete forbidden strings at
  runtime; the raw source no longer carries the concrete operator-local strings.
- Checker/profile comments were reworded so they describe the forbidden family
  without embedding a raw operator-local path/org literal.
- The README working-example `insightwavesmith/BRICK` line remains the sole
  raw occurrence outside `project/`, by design and by existing allowance.

## Verification performed

```bash
PYTHONPATH=support/import_identity:. python3 -m compileall -q \
  support/checkers/lib/kernel_checks.py \
  support/checkers/check_profile.py \
  support/checkers/check_package_path_admission.py

git diff --check

PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py \
  --profile support/checkers/profiles/read_side_projection_boundary.yaml

PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --all

git grep -n '/Users/smith\|insightwavesmith' -- ':!project/**' ':!README.md' ':!*.pyc'

sh support/onboarding/release_export.sh --output <tmp>/export
(cd <tmp>/export && git grep -n '/Users/smith\|insightwavesmith' -- ':!README.md' ':!*.pyc')
```

Observed:

```text
compileall: PASS
git diff --check: PASS
read_side_projection_boundary: PASS
check_profile.py --all: PASS
repo grep outside README/project/pyc: empty
release export: copied files 380, excluded path matches 4299, project/ omitted
release export grep outside README: empty
```

`product_no_smith_residue` still reported its FIRE probes green: temp-copy probes
for the user-home family and Smith GitHub-org family fired RED, including the
`agent/skills` and `brick/templates/skills` surfaces.

## Narrowly proven

- The non-`project/` source tree no longer has raw `/Users/smith` or raw
  `insightwavesmith` literals outside README.md.
- A clean release export no longer has those raw operator literals outside
  README.md.
- The existing no-Smith checker still detects concrete forbidden strings at
  runtime via its FIRE probes.
- `project/` and `brick_protocol.egg-info/` remain excluded from release export.

## Not proven / caveats

- This was not run as a Building; no frontier/evidence spine exists for this
  slice.
- This does not prove customer comprehension or final public-release readiness.
- The README working example still contains `insightwavesmith/BRICK` by explicit
  current allowance.
- Future provider reliability and future release export parity remain not_proven.

## Next Movement candidate

Forward this narrow release-pruning cleanup after Smith/COO review, then continue
either:

1. customer release pruning expansion (export/readme/customer-comprehension
   review), or
2. FINAL architecture cleanup next leaf under conservation-ledger + mutation-RED
   + net-negative LOC.
