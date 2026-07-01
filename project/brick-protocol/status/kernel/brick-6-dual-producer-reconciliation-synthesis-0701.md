# Task #9 / Global Operating Rule 9 — final synthesis (0701)

Status: COO synthesis of two independent investigations. Not source truth,
success judgment, quality judgment, or Movement authority. This document
records the DECISION recommendation only; no source code was mutated by
either investigation.

## Two independent sources, same conclusion

1. **Building `brick-6-dual-producer-reconciliation-design-0701a`** (dual-design
   fan-out: Codex code-surface lane + Claude architecture/risk lane, synthesized,
   Gemini design-QA attacked it with its own live reproduction probe).
   `frontier_kind=complete`, evidence root
   `/Users/smith/.brick/project/brick-protocol/buildings/brick-6-dual-producer-reconciliation-design-0701a`.
2. **Independent research workflow** (`dual-producer-reconciliation-research-0701`,
   35 agents, 4 investigation angles each adversarially re-verified by a
   separate agent that tried to refute it before inclusion). Report:
   `godmodule`-sibling doc pattern, full text below.

Both were run in parallel, neither read the other's output before concluding.

## Recommendation (both sources agree)

**Declare `compose_building()` permanently canonical. Do not migrate the CLI
to `assemble()`.**

## Why (structural finding, independently confirmed twice)

`assemble()` is not a second engine. It is a Python-authoring DSL
(`chain`/`fan_out`/`fan_in`/`converge`/`build`/`brick`) that lowers to raw
node/edge/group dicts and then calls `compose_building()` itself
(`assembly.py:727`) to actually produce the plan. `compose_building(` appears
exactly once in `assembly.py`'s 1469 lines. "Migrate the CLI to `assemble()`,
retire `compose_building()`" is structurally impossible as literally stated
in Rule 9 -- you cannot migrate *to* a wrapper *away from* the thing it
wraps. Every real execution path (preset route, `--graph` route, and
`assemble()`'s own internal call) bottoms out in the same function.

## What "declare canonical" concretely requires (small, editorial)

1. `support/checkers/check_assembly_equivalence.py:2` (module docstring) and
   `:2011` (argparse `--help` text) -- retire "future assembly.py lowering"
   framing.
2. `support/checkers/profiles/assembly_equivalence.yaml:3` -- carries the
   identical stale phrase (found by the independent workflow; the Building's
   own design lanes missed this file).
3. Global Operating Rule 9 itself in the goal doc -- needs a dated resolution
   addendum, not deletion (keep the history).
4. **New, not previously known**: reconcile a live documentary conflict --
   `agent/skills/brick-task-author/SKILL.md` recommends `assemble()`/`build()`
   as the "primary zero-ritual launch surface" with `--graph` as a demoted
   fallback; a same-day, more current doc
   (`support/docs/references/launch-guide.md`) says the opposite (`--graph`
   is the customer surface, `assemble()`/`build()` are internal operator
   helpers). This contradiction predates and is independent of this
   investigation, but the canonical-producer decision is the natural place
   to force it closed, since it's the same underlying question.

No deletion of `assembly.py`'s runtime, no CLI rewiring, no checker-seal
rewrite (`check_driver_public_intake_seal.py` already correctly encodes the
current split and needs zero changes under this branch).

## Real findings this investigation surfaced, not previously known

- **A third plan-materialization mechanism exists**: `support/operator/plan_rendering.py::render_declared_building_plan()`
  is a fully independent, live, checker-exercised materializer with zero
  dependency on `compose_building()`. It is NOT wired to any currently-
  reachable CLI/customer entry point today. Rule 9 only ever named two
  producers; this is a third that the "permanent canonical" declaration
  should explicitly scope in or out, not leave implicit.
- **`sibling_independence` is a real, confirmed gap in `assemble()`'s DSL**
  (`GroupSpec` has only 2 fields, no extension point) -- but scoped narrowly:
  the live `--graph` route never calls `assemble()` at all, so this does not
  block declaring `compose_building()` canonical. It only matters if
  `assemble()`'s DSL is later pushed as a customer-facing authoring surface.
- **One initial concern was directly refuted by live execution**: whether
  `assemble()`-authored graphs silently lose route-policy provenance
  stamping. They do not -- `assemble()` feeds into `compose_building()` in
  the same call, and `check_assembly_equivalence.py`'s own green run proves
  byte-identical provenance output.
- **The write_scope default-on-omission gap (task #8, commit 6c3c73e) was
  real evidence that Rule 9's underlying worry was not hypothetical** -- a
  genuine divergence existed and had to be patched. The independent
  workflow's own investigation confirmed `assembly.py` already handled this
  correctly via an older pre-lowering step (commit 4302473, predating
  6c3c73e) -- so this specific gap is now closed on both producers, but the
  declaration should say so explicitly rather than only relabeling.

## What this document does NOT do

- Does not implement anything. No source file was edited.
- Does not close task #9. This is the design/recommendation phase; a
  follow-on implementation Building is required to actually make the edits
  listed above.
- Does not resolve the `render_declared_building_plan()` question (scope
  in or out) -- that needs an explicit COO decision, recorded separately.

## Next Movement candidate

Pending Smith's ratification of the recommendation above: declare a small,
narrowly-scoped follow-on implementation Building (checker-first) covering
the 3 stale-language edits, the launch-guide/SKILL.md reconciliation, and an
explicit disposition for `render_declared_building_plan()`. Then task #9 and
Global Operating Rule 9 close, and P8 can begin.
