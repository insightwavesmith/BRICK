# FINAL architecture — conservation ledger: first safe case_runners.py leaf extraction (0630)

Status: DESIGN / not_proven. This is the conservation contract a follow-up
implementation Building consumes. No source mutation has happened. It closes the
gap the baseline measurement (customer-ready-final-architecture-baseline-0630.md)
HOLD'd for: the baseline link_paused because no conservation ledger existed yet.
This doc is evidence only; the move itself must run through an official Building.

## Composition-first note (operating principle)

Per the goal anchor COMPOSITION-FIRST rule, the implementation Building must be
composed for THIS task, not stamped as a fixed work->QA->closure line. Proposed
shape: Codex work (write=True, bounded write_scope over support/checkers/lib/)
-> Codex code-attack QA (byte-identical + pin-survival) -> Gemini axis-attack QA
(no new module family / no axis leak / support-only) -> Codex closure. fan-in on
the two QA lenses, mirroring the proven P8 shape.

## Leaf chosen (narrowest safe first move)

Extract the self-contained fake-CLI completion fixture cluster from
support/checkers/lib/case_runners.py into ONE new flat sibling module
support/checkers/lib/preset_completion_fixture.py (flat sibling, no new folder,
no new module family). Mirrors the admitted MODULE-SEP 0621 precedent
(agent_adapter facade + pure relocation siblings): case_runners keeps a thin
re-export and behavior stays byte-identical.

### Exact helper symbols to move (live spans, case_runners.py)

    _preset_completion_command_runner        def @ 3394
    _preset_completion_prompt_from_cli_args  def @ 3475
    _is_gemini_json_invocation               def @ 3488
    _output_last_message_path                def @ 3496
    _deterministic_completion_list           def @ 3575
    _return_labels_from_cli_prompt           def @ 3583

Contiguous span measured: lines 3394-3595 = 202 lines (six defs + interleaving
blanks/comments). Dependency audit: cluster imports nothing case_runners-private;
uses only stdlib (json) plus a caller-passed completed_cls parameter
(LocalCliCompleted / agent_adapter.LocalCliCompleted supplied by callers). Does
NOT call _case_slug / _preset_slug / profile loaders. => true leaf.

### Move mechanics (conservation = byte-identical bodies)

    1. Create support/checkers/lib/preset_completion_fixture.py with:
       - from __future__ import annotations
       - imports: json; collections.abc Callable/Sequence; pathlib Path; typing Any
       - the six function bodies moved VERBATIM (no body text edits)
    2. In case_runners.py, delete the six defs and add ONE re-export block near
       the other lib imports:
         from support.checkers.lib.preset_completion_fixture import (
             _preset_completion_command_runner,
             _preset_completion_prompt_from_cli_args,
             _is_gemini_json_invocation,
             _output_last_message_path,
             _deterministic_completion_list,
             _return_labels_from_cli_prompt,
         )
       (re-export keeps all in-file call sites working unchanged)

## Affected RULE_RUNNERS labels

None directly. The six symbols are PRIVATE helpers (underscore). They are not
entries in check_profile.RULE_RUNNERS and not in the case_runners public import
block of check_profile.py (that block imports only run_* case/reject entry
points). All callers (1215/1437/1686/2111/2430/4172/10225, plus prompt/output
helpers at 1442/1443/3405/3406/3420/3437/3455/10464/1333) live inside run_*_case
bodies and reach the symbols through the re-export => every RULE_RUNNERS-
dispatched case keeps identical behavior.

## Profile path / text / json pins referencing moved bodies

Audited every profile + module_registry. NONE of the six moved symbol names are
text-pinned anywhere (grep over support/checkers/profiles/ +
module_registry.yaml => empty). Profiles DO pin the PATH
support/checkers/lib/case_runners.py (agent_axis_behavioral L68/L203,
native_dispatch_brick_backstop L22, building_skill_preset_agent_tool_hardening
L183) but the pinned TEXTS are OTHER needles
(run_adapter_capability_rehome_case, ok_all_four,
_assert_native_dispatch_pos_a_shape, _POS_A_*, agent_object_hashes_unchanged,
_agent_object_file_digests) — all stay in case_runners.py and are NOT moved. The
path pins survive untouched.

## Private helper / probe text pins

The moved cluster carries no probe text needle that any profile asserts. The
only private-name pins on case_runners.py are the native-dispatch _POS_A_* /
_assert_native_dispatch_pos_a_shape set and _agent_object_file_digests, none in
the moved cluster. No probe pin moves.

## module_registry rows

module_registry.yaml has one row for support/checkers/lib/case_runners.py (@537).
The new sibling needs ONE row added directly after it:

    - module: support/checkers/lib/preset_completion_fixture.py
      layer: checkers/lib
      role: checker-lib
      owns_crossings: []
      consumes_crossings: []
      imports_axis: []
      forbidden_ownership: [movement_author, target_selector, success_judge, quality_judge, route_invent]
      decomposition_target: ""
      pinned_by: pure-relocation sibling of case_runners (fake-CLI completion fixture; homes no crossing mechanics, imports no axis)

The existing case_runners row stays; owns/consumes/imports stay [] (no crossing
ownership moves).

## Mutation-RED probes per moved label/assertion

Conservation is proven by the EXISTING profile suite, which exercises these
symbols transitively through their run_*_case callers
(run_preset_building_completion_case, run_building_intake_seam_case,
run_onboard_seam_case, run_intake_project_vessel_case, run_compose_building_case).
Required checks for the implementation Building:

    1. Pre-move:  check_profile.py --all => GREEN (baseline captured).
    2. Post-move: --all => GREEN unchanged (byte-identical behavior).
    3. Mutation-RED A: break one moved body (flip _is_gemini_json_invocation to
       always return False) => preset/onboard completion cases go RED. Proves the
       moved code is still LIVE on the dispatch path, not dead.
    4. Mutation-RED B: remove the re-export line => ImportError/NameError at call
       sites => proves the seam is load-bearing.
    5. import smoke: importing support.checkers.lib.case_runners still exposes all
       six names (re-export contract).

No NEW standalone check_*.py is admitted; conservation rides existing coverage
(matches the checker-direction rule to avoid new standalone checkers).

## Expected byte-identical behavior

Bodies move verbatim; call sites resolve through the re-export, so every
run_*_case yields identical KernelResult/int outcomes and identical evidence.
check_profile.py --all output is unchanged. No axis crossing, no Movement, no
judgment changes — support mechanics relocation only.

## Net-negative LOC basis

    removed from case_runners.py:   ~202 lines (six defs, span 3394-3595)
    added to case_runners.py:       ~8 lines (one re-export import block)
    new sibling file:               ~202 moved + ~6 imports + module docstring
    net repo LOC:                   roughly +6..+14 (import/docstring overhead)
    god-module LOC (the metric):    case_runners.py 10907 -> ~10713 (-~194)

The goal metric is god-module shrinkage, not whole-repo line golf. case_runners
drops ~194 lines into a named, single-purpose, pin-free sibling. Smallest safe
first move; does NOT touch kernel_checks split, walker/run split, profile
thinning, or any new module family — all out of scope per the FINAL plan.

## Disposition

next Movement candidate: declare + fire ONE official leaf-extraction Building
(brick build --graph) with the composition above, gated on the five checks.
narrowly proven: the conservation map (symbols, pins, registry, callers) is
measured against live HEAD. not_proven: the move itself + byte-identical run,
until the Building lands frontier=complete with --all GREEN on REAL HOME.
