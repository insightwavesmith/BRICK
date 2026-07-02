# FINAL architecture — conservation ledger: no_smith_residue leaf extraction (kernel_checks.py) — 0630

Status: DESIGN / conservation contract. Support evidence only. Not source truth,
not success judgment, not quality judgment, not Link Movement authority.

## Context

The closeout G3 track shrinks godmodules. Live LOC re-measurement
(`customer-ready-closeout-g1g2g3-status-0630.md`) shows `kernel_checks.py`
(11452 LOC) is now the LARGEST godmodule, exceeding `case_runners.py` (8503).
The case_runners leaf series proved the safe pattern; this leaf applies the same
pattern to kernel_checks.py for the first time.

## Composition-first note

Per the goal anchor COMPOSITION-FIRST rule, this is recorded as direct operator
maintenance (a byte-identical relocation with mechanical verification), not a
fixed work->QA->closure line. A heavier Building shape (Codex work + dual QA
fan-in) is the right vehicle when a leaf carries behavior risk; a pure
byte-identical relocation with mutation-RED + REAL HOME --all is the minimal
honest proof and is recorded as an exception here.

## Leaf chosen (pure leaf)

Extract the product no-Smith-residue scan cluster from
`support/checkers/lib/kernel_checks.py` into ONE new flat sibling module
`support/checkers/lib/no_smith_residue_check.py`. Flat sibling, no new folder,
no new module family. Mirrors the admitted MODULE-SEP precedent: kernel_checks
keeps a thin re-export and behavior stays byte-identical.

### Exact symbols to move (live spans, kernel_checks.py)

```text
_SMITH_USER_HOME_LITERAL          const @ 4451
_SMITH_GITHUB_ORG_LITERAL         const @ 4452
_SMITH_GITHUB_REPO_LITERAL        const @ 4453
_NO_SMITH_RESIDUE_SURFACES        const @ 4455-4462
_no_smith_residue_text_paths      def   @ 4465-4479
_no_smith_residue_allowed_org_line def  @ 4482-4487
_collect_no_smith_residue_violations def @ 4490-4501
_copy_no_smith_residue_surfaces   def   @ 4504-4514
_no_smith_residue_fire_probe      def   @ 4517-4564
run_product_no_smith_residue      def   @ 4567-4594
```

### Dependency audit (why this is a true leaf)

- External module-level references FROM the span: NONE (AST load-name scan).
- The span uses only stdlib + shared imports already available to a sibling:
  `Path` (pathlib), `shutil`, `tempfile`, `to_posix`, `KernelResult`,
  `ProfileError`. `to_posix`, `KernelResult`, `ProfileError` come from
  `support.checkers.lib.yaml_subset` (same source kernel_checks imports).
- External references TO the moved symbols, outside the span: exactly ONE —
  `_SMITH_USER_HOME_LITERAL` is used at kernel_checks.py:8058 (dashboard
  productization probe). The re-export keeps that call site working unchanged.
- `run_product_no_smith_residue` is imported by `check_profile.py` (line 138)
  and dispatched as kernel check `product_no_smith_residue` (line 713). The
  re-export preserves that public import path byte-for-byte.

### Move mechanics (conservation = byte-identical bodies)

```text
1. Create support/checkers/lib/no_smith_residue_check.py with:
   - from __future__ import annotations
   - imports: shutil; tempfile; pathlib Path
   - from support.checkers.lib.yaml_subset import KernelResult, ProfileError, to_posix
   - the four consts + six function bodies moved VERBATIM (no body text edits)
2. In kernel_checks.py, delete the moved consts + defs and add ONE re-export
   block near the other lib imports:
     from support.checkers.lib.no_smith_residue_check import (
         _SMITH_USER_HOME_LITERAL,
         _SMITH_GITHUB_ORG_LITERAL,
         _SMITH_GITHUB_REPO_LITERAL,
         _NO_SMITH_RESIDUE_SURFACES,
         _no_smith_residue_text_paths,
         _no_smith_residue_allowed_org_line,
         _collect_no_smith_residue_violations,
         _copy_no_smith_residue_surfaces,
         _no_smith_residue_fire_probe,
         run_product_no_smith_residue,
     )
```

### Profile / registry pin audit

- `product_no_smith_residue` is pinned by `read_side_projection_boundary.yaml`
  as a kernel_check ID; the ID stays the same (the check is dispatched through
  check_profile, which still imports the same name).
- No profile text-pins any of the moved symbol names against a specific module
  path (grep over profiles + module_registry => the only kernel_checks.py
  text-pin set is the chat_session/codex needles, none of which move).
- A new `module_registry.yaml` row is added for the sibling, mirroring the
  case_runners leaf rows (role checker-lib, owns_crossings []).

## Conservation invariants asserted by the follow-up verification

```text
byte-identical bodies (the moved text is unchanged)
public name compatibility (check_profile import + dispatch unchanged)
re-export keeps in-file call site (8058) working
net-negative LOC in kernel_checks.py
no new module family / no axis import / support-only
mutation-RED: a tampered scan must still fire RED
REAL HOME check_profile.py --all GREEN
```

## Not proven

```text
- This ledger does not itself move code; the relocation + verification follow.
- Future provider behavior / future Building correctness.
- Source truth / success / quality / Movement authority.
```
