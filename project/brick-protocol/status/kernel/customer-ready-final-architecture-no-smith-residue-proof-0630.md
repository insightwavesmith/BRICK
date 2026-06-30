# Customer-Ready FINAL Architecture — no_smith_residue leaf extraction proof — 0630

Status: FORWARD candidate / support evidence only. Not source truth, not success
judgment, not quality judgment, and not Link Movement authority.

## What moved

First `kernel_checks.py` godmodule leaf (the prior FINAL leaves all targeted
`case_runners.py`). The product no-Smith-residue scan cluster moved VERBATIM into
a new flat checker-lib sibling:

```text
support/checkers/lib/no_smith_residue_check.py   (new, 165 lines)
```

Ledger: `customer-ready-final-architecture-no-smith-residue-ledger-0630.md`.

## Conservation result

```text
kernel_checks.py: 11452 -> 11325 LOC (net -127)
no_smith_residue_check.py: new flat sibling, byte-identical bodies
case_runners.py: unchanged (8503)
```

Moved symbols (consts + funcs):

```text
_SMITH_USER_HOME_LITERAL, _SMITH_GITHUB_ORG_LITERAL, _SMITH_GITHUB_REPO_LITERAL,
_NO_SMITH_RESIDUE_SURFACES,
_no_smith_residue_text_paths, _no_smith_residue_allowed_org_line,
_collect_no_smith_residue_violations, _copy_no_smith_residue_surfaces,
_no_smith_residue_fire_probe, run_product_no_smith_residue
```

kernel_checks.py keeps a re-export block so:

- `check_profile.py` import of `run_product_no_smith_residue` is unchanged;
- the in-file `_SMITH_USER_HOME_LITERAL` call site (dashboard productization
  probe) keeps working;
- `module_registry.yaml` gains one checker-lib row for the sibling.

## Verification (all measured this turn)

```text
compileall kernel_checks.py + no_smith_residue_check.py: PASS
git diff --check: PASS
re-export identity: kc.run_product_no_smith_residue IS ns.run_product_no_smith_residue: True
dispatch identity: KERNEL_DISPATCH['product_no_smith_residue'] IS the sibling fn: True
literal re-export: kc._SMITH_USER_HOME_LITERAL == ns._SMITH_USER_HOME_LITERAL == '/Users/smith': True
live run on repo: check_id=product_no_smith_residue, inspected=39 (== pre-move)
mutation-RED (collector neutered): ProfileError fired (FIRE probe RED)
mutation restore: GREEN
REAL HOME check_profile.py --all: rc=0, 28 profiles passed
```

## Three-axis attribution

```text
Brick evidence: declared leaf-extraction work; module/file boundary only.
Agent evidence: this was direct operator maintenance (byte-identical relocation),
  recorded as an exception per the composition-first note in the ledger.
Link evidence: no Movement authored; checker dispatch and re-export are support
  mechanics, not Link rows.
Support surface: checker-lib module + registry; support records facts only.
Rejected shortcut: do not blame/relocate by module name alone — the move is
  admitted because the AST dependency audit proved a true leaf (zero external
  module-level refs; one re-exported call site).
```

## Narrowly proven

- The product no-Smith-residue scan behaves identically after the move
  (inspected count, dispatch identity, FIRE probe, mutation-RED).
- kernel_checks.py is net-negative LOC with no new module family and no axis
  import.
- REAL HOME `--all` is GREEN.

## Not proven / caveats

- This is one leaf; kernel_checks.py (11325) remains the largest godmodule and
  more leaves remain for G3.
- Direct operator maintenance, not a Building-produced patch (byte-identical
  relocation exception).
- Future provider behavior / future Building correctness / source truth /
  success / quality / Movement authority remain not_proven by this slice.

## Next Movement candidate

Forward this leaf, then continue G3 with the next kernel_checks.py leaf (e.g.
the install-script-lint cluster or the dashboard_productization cluster), each
under the same conservation-ledger + byte-identical + mutation-RED discipline.
