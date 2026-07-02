# Customer-Ready G2 — release export payload parity proof — 0630

Status: FORWARD candidate / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

## Purpose

Close one explicit remaining G2 gap from `customer-ready-closeout-g1g2g3-status-0630.md`:

```text
release export parity (byte-for-byte across runs) not asserted
```

This proof measures deterministic exported PAYLOAD parity across two fresh runs of
`support/onboarding/release_export.sh` from the current checkout. It intentionally
excludes `.git/` metadata from the parity claim because each export creates a new
initial commit and therefore has distinct commit timestamps / commit IDs even when
the payload is identical.

## Measurement base

```text
source checkout = /Users/smith/projects/BRICK
branch = main
HEAD before proof = c3d8e03 (plus local ahead-of-origin closeout commits)
command A = sh support/onboarding/release_export.sh --output /Users/smith/.brick/tmp/g2-parity-0630/export-a
command B = sh support/onboarding/release_export.sh --output /Users/smith/.brick/tmp/g2-parity-0630/export-b
```

The script is support mechanics only. It creates an output tree and local git
repo; it does not push, tag, choose Movement, judge release quality, or prove
customer comprehension.

## Observed export outputs

```text
export-a copied files: 382
export-a excluded paths matched: 4308
export-a excluded roots: project/, brick_protocol.egg-info/
export-a initial commit: 0085e73

export-b copied files: 382
export-b excluded paths matched: 4308
export-b excluded roots: project/, brick_protocol.egg-info/
export-b initial commit: 38d2961
```

The initial commit IDs differ as expected; that is outside the payload parity
claim.

## Payload parity method

For each export:

```text
cd <export>
git ls-files -z | sort -z | xargs -0 shasum -a 256 > ../<export>.sha256
```

Then compare:

```text
diff -u export-a.sha256 export-b.sha256
```

Observed:

```text
PAYLOAD_PARITY_OK
FILELIST_PARITY_OK
manifest_a = 2d152bc663ce9b040722ee62bb2041abcc3dacb836d2c078c76c313390c231f8
manifest_b = 2d152bc663ce9b040722ee62bb2041abcc3dacb836d2c078c76c313390c231f8
```

## Release-pruning checks repeated during parity proof

```text
export-a files = 382
export-b files = 382
export-a no project/ = OK
export-b no project/ = OK
export-a no brick_protocol.egg-info/ = OK
export-b no brick_protocol.egg-info/ = OK
export-a top-level = .gitignore AGENTS.md README.md agent brick link pyproject.toml support
export-b top-level = .gitignore AGENTS.md README.md agent brick link pyproject.toml support
export-a local_literal_violations_outside_README = 0
export-b local_literal_violations_outside_README = 0
```

The local-literal check searched exported files outside `.git/` and outside the
README working-example allowance for:

```text
/Users/smith
insightwavesmith
```

## Three-axis attribution

```text
Brick evidence: G2 release-pruning work asks whether the customer export surface
  is deterministic and excludes internal/local evidence.
Agent evidence: no Agent performer work; this is direct operator measurement,
  recorded as support evidence.
Link evidence: no Movement authored; export parity is not a route target or
  success judgment.
Support surface: support/onboarding/release_export.sh plus normalized export
  file manifests.
Rejected shortcut: do not call G2 complete from script exit alone; compare the
  exported payload manifests and repeat the exclusion/local-literal checks.
```

## Narrowly proven

- Two fresh release exports from the same checkout produce the same git-tracked
  payload file list and SHA-256 file-content manifest.
- The exported payload excludes `project/` and `brick_protocol.egg-info/` in both
  runs.
- The exported payload carries no `/Users/smith` or `insightwavesmith` literal
  outside the README allowance in either run.

## Not proven / remaining G2 caveats

```text
- `.git/` metadata byte parity is not asserted; initial commit hashes differ by
  construction and are outside the customer payload claim.
- A real provider-backed fresh export build reaching frontier_kind=complete was
  not re-run here.
- Full customer comprehension remains not_proven.
- Future exports after future commits must be re-measured.
- Source truth / success / quality / Movement authority remain not_proven.
```

## Next Movement candidate

Forward this G2 parity proof. Remaining G2 closeout candidates are:

```text
1. provider-backed fresh export build reaching frontier_kind=complete
2. customer reading-comprehension / first-run UX validation
```
