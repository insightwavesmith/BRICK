# Customer-Ready FINAL Architecture — install/release-export lint leaf extraction proof — 0630

Status: FORWARD candidate / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

## What moved

Second `kernel_checks.py` godmodule leaf (first was no_smith_residue). The
onboarding install-script lint + release-export exclusion lint cluster moved
VERBATIM into a new flat checker-lib sibling:

```text
support/checkers/lib/install_release_export_lint_check.py   (new, 213 lines)
```

Ledger: `customer-ready-final-architecture-install-release-export-lint-ledger-0630.md`.

## Conservation result

```text
kernel_checks.py: 11325 -> 11151 LOC (net -174)
install_release_export_lint_check.py: new flat sibling, byte-identical bodies
no_smith_residue_check.py: unchanged (165)
case_runners.py: unchanged (8503)
```

Moved symbols (consts + funcs):

```text
_INSTALL_SCRIPT_REL, _RELEASE_EXPORT_REL, _RELEASE_EXPORT_REQUIRED_EXCLUSIONS,
_INSTALL_SCRIPT_SECRET_PATTERNS,
run_install_script_lint,
_release_export_exclusions, _release_export_exclusion_violations,
_release_export_exclusion_fire_probe, run_release_export_exclusion
```

kernel_checks.py keeps a re-export block so:

- `check_profile.py` imports of `run_install_script_lint` and
  `run_release_export_exclusion` are unchanged;
- `module_registry.yaml` gains one checker-lib row for the sibling.

## Verification (all measured this turn)

```text
compileall kernel_checks.py + install_release_export_lint_check.py + check_profile.py: PASS
git diff --check: PASS
byte-identical diff (HEAD span 4259-4448 vs moved bodies): EMPTY (identical)
re-export identity: kc.run_install_script_lint IS sibling fn: True
re-export identity: kc.run_release_export_exclusion IS sibling fn: True
dispatch identity: KERNEL_DISPATCH['install_script_lint'] IS the sibling fn: True
dispatch identity: KERNEL_DISPATCH['release_export_exclusion'] IS the sibling fn: True
const re-export: kc._RELEASE_EXPORT_REQUIRED_EXCLUSIONS == sibling: True
focused profile read_side_projection_boundary: both checks GREEN
mutation-RED install: tampered install.sh (/Users/ literal) -> ProfileError fired
mutation-RED release: release_export.sh missing project/ exclusion -> ProfileError fired
GREEN baseline: real install.sh inspected=1; real release_export inspected=2 (internal FIRE probe)
REAL HOME check_profile.py --all: rc=0, 28 profiles passed, no failure markers
```

## Three-axis attribution

```text
Brick evidence: declared leaf-extraction work; module/file boundary only.
Agent evidence: direct operator maintenance (byte-identical relocation),
  recorded as an exception per the composition-first note in the ledger.
Link evidence: no Movement authored; checker dispatch and re-export are support
  mechanics, not Link rows.
Support surface: checker-lib module + registry; support records facts only.
Rejected shortcut: do not relocate by module name alone — the move is admitted
  because the AST dependency audit proved a true leaf (zero external top-symbol
  refs in both directions).
```

## Narrowly proven

- The install-script and release-export lints behave identically after the move
  (dispatch identity, GREEN baselines, mutation-RED for both).
- kernel_checks.py is net-negative LOC with no new module family and no axis
  import.
- REAL HOME `--all` is GREEN (28 profiles).

## Not proven / caveats

- This is one leaf; kernel_checks.py (11151) remains the largest godmodule and
  more leaves remain for G3.
- Direct operator maintenance, not a Building-produced patch (byte-identical
  relocation exception).
- Future provider behavior / future Building correctness / source truth /
  success / quality / Movement authority remain not_proven by this slice.

## Next Movement candidate

Forward this leaf, then continue G3 with the next kernel_checks.py leaf (e.g.
provider_preflight or onboard_smoke cluster — both audited as near-leaves with a
single shared `_ensure_import_identity` ref to resolve), each under the same
conservation-ledger + byte-identical + mutation-RED discipline. A G3 STOP
CONDITION still needs to be declared with Smith before closing the track.
