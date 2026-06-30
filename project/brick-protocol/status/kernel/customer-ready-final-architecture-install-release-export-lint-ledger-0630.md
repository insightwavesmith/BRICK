# FINAL architecture — conservation ledger: install/release-export lint leaf extraction (kernel_checks.py) — 0630

Status: DESIGN / conservation contract. Support evidence only. Not source truth,
not success judgment, not quality judgment, not Link Movement authority.

## Context

Closeout G3 shrinks godmodules. After the no_smith_residue leaf landed
(`a779a2c`), `kernel_checks.py` was 11325 LOC and still the LARGEST godmodule.
This is the SECOND kernel_checks.py leaf, applying the same proven pattern
(case_runners leaf series + no_smith_residue leaf).

## Composition-first note

Per the goal anchor COMPOSITION-FIRST rule, this is recorded as direct operator
maintenance (a byte-identical relocation with mechanical verification), not a
fixed work->QA->closure line. A heavier Building shape is the right vehicle when
a leaf carries behavior risk; a pure byte-identical relocation with mutation-RED
+ REAL HOME --all is the minimal honest proof and is recorded as an exception
here. Next implementation slice should return to Building-first operation.

## Leaf chosen (pure leaf)

Extract the onboarding install-script lint + release-export exclusion lint
cluster from `support/checkers/lib/kernel_checks.py` into ONE new flat sibling
module `support/checkers/lib/install_release_export_lint_check.py`. Flat sibling,
no new folder, no new module family. kernel_checks keeps a thin re-export and
behavior stays byte-identical. This cluster also serves G2 (the customer release
surface lints), so co-locating them is a clean boundary.

### Exact symbols moved (live spans, kernel_checks.py before move)

```text
_INSTALL_SCRIPT_REL                     const @ 4259
_RELEASE_EXPORT_REL                     const @ 4260
_RELEASE_EXPORT_REQUIRED_EXCLUSIONS     const @ 4261-4264
_INSTALL_SCRIPT_SECRET_PATTERNS         const @ 4270-4280
run_install_script_lint                 def   @ 4282-4377
_release_export_exclusions              def   @ 4379-4384
_release_export_exclusion_violations    def   @ 4386-4401
_release_export_exclusion_fire_probe    def   @ 4403-4412
run_release_export_exclusion            def   @ 4414-4448
```

### Dependency audit (why this is a true leaf)

- AST scan over kernel_checks.py top-level symbols: the cluster references NO
  other top-level symbol of kernel_checks (ext_from = []).
- AST scan: NO top-level symbol outside the cluster references any cluster
  symbol (ext_to = {}).
- The span uses only stdlib + shared imports already available to a sibling:
  `re`, `Path` (pathlib), and `KernelResult`, `ProfileError` from
  `support.checkers.lib.yaml_subset` (same source kernel_checks imports).
- `run_install_script_lint` and `run_release_export_exclusion` are imported by
  `check_profile.py` and dispatched as kernel checks `install_script_lint` /
  `release_export_exclusion`. The re-export preserves those public import paths
  byte-for-byte.

### Move mechanics (conservation = byte-identical bodies)

```text
1. Create support/checkers/lib/install_release_export_lint_check.py with:
   - module docstring + from __future__ import annotations
   - imports: re; pathlib Path
   - from support.checkers.lib.yaml_subset import KernelResult, ProfileError
   - the four consts + five function bodies moved VERBATIM (no body text edits)
2. In kernel_checks.py, delete the moved consts + defs and add ONE re-export
   block importing the nine names from the sibling.
3. Add one module_registry.yaml checker-lib row for the sibling.
```

### Profile / registry pin audit

- `install_script_lint` and `release_export_exclusion` are pinned by
  `read_side_projection_boundary.yaml` as kernel_check IDs; the IDs are unchanged
  (dispatched through check_profile, which imports the same names).
- No profile text-pins any moved symbol name against a specific module path
  (grep over profiles + module_registry => none).
- A new `module_registry.yaml` row is added for the sibling, mirroring the
  no_smith_residue / case_runners leaf rows (role checker-lib, owns_crossings []).

## Conservation invariants asserted by the follow-up verification

```text
byte-identical bodies (the moved text is unchanged; diff vs HEAD span = empty)
public name compatibility (check_profile import + dispatch unchanged)
re-export keeps in-file consumers working (none outside the cluster)
net-negative LOC in kernel_checks.py (11325 -> 11151, net -174)
no new module family / no axis import / support-only
mutation-RED: tampered install.sh (/Users/ literal) and release_export.sh
  (missing project/ exclusion) still fire RED
REAL HOME check_profile.py --all GREEN
```

## Not proven

```text
- Future provider behavior / future Building correctness.
- Source truth / success / quality / Movement authority.
- This is one leaf; kernel_checks.py (11151) remains the largest godmodule.
```
