# BRICK 6 P7c status/build root alignment closure - 2026-07-01

## Scope

- Phase: revised P7 — product route / P3 Easy Building surface.
- Building: `brick-6-p7-status-build-root-alignment-0701c`.
- Graph declaration: `ff47067 P7: declare status/build root alignment graph`.
- Official build route: `uv run brick build --non-interactive --json --graph project/brick-protocol/status/kernel/GOAL/brick-6-p7-status-build-root-alignment-0701c.json --timeout 1200`.
- Evidence root: `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-p7-status-build-root-alignment-0701c`.
- Building frontier: `frontier_kind=complete`, `customer_visible_frontier_state=frontier_complete`.
- Sandbox output commit: `42d3b27 BRICK building output: brick-6-p7-status-build-root-alignment-0701c`.
- Main adoption: `42d3b27` fast-forwarded onto `/Users/smith/projects/BRICK` `main`.

## Graph shape

P7c used the corrected non-linear graph shape:

```text
design -> work -> fan([code-qa, axis-qa, evidence-qa]) -> closure
```

Recorded step outputs:

```text
work/step-outputs/brick-6-p7-status-build-root-alignment-0701c-design-attempt-1/step-output.json
work/step-outputs/brick-6-p7-status-build-root-alignment-0701c-work-attempt-1/step-output.json
work/step-outputs/brick-6-p7-status-build-root-alignment-0701c-code-qa-attempt-1/step-output.json
work/step-outputs/brick-6-p7-status-build-root-alignment-0701c-axis-qa-attempt-1/step-output.json
work/step-outputs/brick-6-p7-status-build-root-alignment-0701c-evidence-qa-attempt-1/step-output.json
work/step-outputs/brick-6-p7-status-build-root-alignment-0701c-closure-attempt-1/step-output.json
```

QA lanes returned no Link-facing `transition_concern_evidence`; closure returned no Link-facing transition concern.

## Observed evidence

P7c directly targeted the P7b closure blocker `status-build-root-drift`.

Changes adopted on main:

```text
support/operator/cli.py
support/checkers/lib/kernel_checks.py
support/checkers/profiles/brick_cli_entrypoint.yaml
support/docs/references/quickstart.md
```

Observed closure/adoption evidence:

- `brick status` / bare `brick` status evidence now reports `default_evidence_root` and `default_builds_root` as the same caller-local Building evidence root.
- The status packet records `default_build_root_basis: same ref-less Building evidence root used by brick build when --output-root is omitted`.
- Invalid graph packet plain CLI error now uses product-safe taxonomy (`graph_packet_invalid`) rather than raw path / traceback / exception class as the operator-facing line.
- `brick_cli_entrypoint` focused checker pins:
  - no legacy `~/.brick/builds` revival for build/status root wording;
  - no onboard-module/internal route as public customer route;
  - no raw `str(exc)` / traceback / raw path leak in plain CLI error;
  - no `--large` / new-engine public build mode revival.
- P7b public route surface remains bounded to `brick init`, `brick status` / bare `brick`, `brick doctor`, `brick build`, and `brick build --graph`.

## Main verification after adoption

Executed from `/Users/smith/projects/BRICK` after fast-forward to `42d3b27`:

```text
PYTHONPATH=support/import_identity python3 -m py_compile support/operator/cli.py support/checkers/lib/kernel_checks.py
# rc 0

PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --profile brick_cli_entrypoint
# rc 0

python3 support/operator/cli.py status --json
# rc 0
# default_evidence_root=/Users/smith/.brick/project/brick-protocol/buildings
# default_builds_root=/Users/smith/.brick/project/brick-protocol/buildings
# default_build_root_basis=same ref-less Building evidence root used by brick build when --output-root is omitted

python3 support/operator/cli.py build --graph /path/that/must/not/exist.json
# rc 1
# stderr begins: brick command rejected evidence: graph_packet_invalid: graph packet rejected; provide a declared JSON graph packet with required fields
# no raw missing path / traceback as the primary operator-facing line

git diff --check
# rc 0

PYTHONPATH=support/import_identity python3 support/checkers/check_profile.py --all
# rc 0
```

## Narrowly proven

- The P7b `status-build-root-drift` blocker is closed on current main evidence.
- The P7c Building ran through the official `brick build --graph` route with real QA fan-out/fan-in and reached `frontier_kind=complete`.
- The sandbox output commit was adopted onto main by fast-forward, not reimplemented directly.
- Focused P7 CLI/product-route checks and full `check_profile.py --all` are green on current main after adoption.

## Not proven

- Whole P7 is not complete merely from P7c if full Easy-Building dynamic design ergonomics (S6-F4) remains required rather than explicitly deferred.
- P8 ship safety / release / dashboard / provider / CI hardening remains not proven.
- P9 dynamic customer replay / self-dogfood proof remains not proven.
- Fresh-machine customer install/run, real-provider repeated reliability, and customer comprehension remain not proven.
- Checker/profile green is support evidence only; it is not source truth, success judgment, quality judgment, or Movement authority.

## Next Movement candidate

Proceed to the next declared Building only after carrying this closure boundary:

1. If full Easy-Building dynamic design ergonomics (S6-F4) is still in P7 scope, declare a separate P7d Building for the large-work route shape:

```text
task intake -> fan([design-codex, design-qa/axis-qa as declared]) -> design synthesis/plan confirm -> parallel dev lanes -> lane QA -> fan-in -> final code/axis/evidence QA -> closure
```

2. If Smith/COO explicitly defers S6-F4, advance to P8 ship-safety hardening.

Do not claim whole customer-ready closeout complete.
Do not push without Smith OK.
