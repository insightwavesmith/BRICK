# Godmodule + Checker Cleanup — Synthesized Plan

Baseline: main HEAD `201cec0` (2026-07-02). All numbers below are current,
independently re-verified (`wc -l` / `grep -c` / direct file reads) as of this
baseline. Treat any figure in an older doc (0625/0626/0628/0630 cluster, or
this doc's own earlier 0701/0702 drafts) as stale unless re-stated here. This
doc supersedes the file-shape numbers in all prior sources; it does not
re-litigate their design reasoning where that reasoning still holds.

**Standing rule, proven twice now (0701→0702 drift, then again this pass):**
line numbers in this codebase rot fast — every single coordinate cited by the
0625/0626/0628 docs had drifted by 0701, and most of 0701's own coordinates
had drifted again by 0702. Re-derive every cited line at implementation time.
Only the *existence* of a symbol/pin/import is durable; its line number is
not.

---

## 1. 확정 필요 (Confirmed still-needed)

Organized by target file.

### `support/checkers/lib/kernel_checks.py` — 10141 LOC
- Still monolithic, still the single largest checker file by a wide margin.
  Has shed 8 leaf modules since 0626/0628 (`no_smith_residue_check.py`,
  `install_release_export_lint_check.py`, `provider_preflight_check.py`,
  `design_ai_text_seams_check.py`, `codex_connect_stall_classification_check.py`,
  `onboard_smoke_check.py`, `gemini_local_only_adapter_check.py`,
  `graph_topology_fan_barrier.py`) — all 8 confirmed on disk with real
  extraction commit history. `kernel_checks.py` still re-exports several of
  these back in via `from ... import` (facade pattern, intentional, keeps
  `check_profile.py`'s import block byte-identical).
- `grep -nE '^def run_'` = 16 public entrypoints (not the 23/24 cited in 0626
  — extraction has since removed 8).
- `check_profile.py` (1397 lines) is the sole importer. Import block is 27
  names total (26 `run_*`/utility names + `call_main`) — earlier docs'
  "~17 + call_main" was a material undercount.
- 3 axis-vocab self-allowlist pins present (`_AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST`,
  `_AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST`, `_AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST`,
  currently lines 119/130/138) — these must relocate with whatever module
  re-encodes the enum literals, or `run_axis_vocab_drift`
  (`KERNEL_DISPATCH["axis_vocab_drift"]`, wired via `core.yaml:5` and
  `module_registry.yaml:645`) goes RED. This consequence is real, confirmed
  wired.
- No `kernel_common.py` or `kernel_checks_*.py` split-module naming exists —
  none of the earlier proposed module names were adopted. The 8 extractions
  used flat domain-named siblings instead (`support/checkers/lib/<domain>_check.py`),
  with a minor naming nuance: 6 of 8 follow the exact suffix pattern; 2 of 8
  deviate (`install_release_export_lint_check.py` has a compound domain name;
  `graph_topology_fan_barrier.py` has no `_check` suffix at all). Any future
  split should follow the established convention, noting it isn't 100%
  uniform today.

### `support/checkers/lib/case_runners.py` — 8512 LOC
- Partially split since 0628: 8 extraction commits pulled out
  `preset_completion_fixture.py`, `gate_evidence_readers.py`,
  `plan_fixture_helpers.py`, `materialized_plan_observers.py`,
  `materialize_reject_scaffold.py`, `adapter_capability_checks.py`,
  `materialized_return_shape_guards.py`, `casting_node_carry_check.py` — all
  flat siblings in `support/checkers/lib/`, all confirmed on disk.
- Still the second-largest checker file (ranking: kernel_checks.py 10141 >
  case_runners.py 8512 > check_bounded_agent_proposed_routing_loop0.py 7176).
  Not "done", just further along than any prior doc recorded.
- `grep '^def run_.*_case'` = 28 public case functions remain in-file.
- Cross-module private-helper imports still constrain any further split:
  `kernel_checks.py` imports `_preset_completion_command_runner` at **two**
  sites (lines 3429 and 3635 — only one was ever previously cited).
  `check_building_operator_driver0.py:75` imports
  `_graph_test_plan_from_linear`. Re-derive exact lines before touching —
  this coordinate alone has moved 4+ times across successive docs.
- **Correction to a standing error in prior docs:** `RULE_RUNNERS` (50 keys)
  does **not** live in `support/checkers/lib/rule_runners.py`. The dict
  literal itself is defined in `support/checkers/check_profile.py:235`
  (through line 286). `rule_runners.py` (635 LOC) holds the 15 individual
  rule-runner *functions* the dict dispatches to (`run_path_exists`,
  `run_path_absent`, `run_path_absent_glob`, `run_path_allowlist`,
  `text_rule`, `run_yaml_literal_set`, `run_json_required_paths`,
  `run_json_value_paths`, `run_agent_resource_boundary`,
  `run_agent_preferred_adapter_rejects`,
  `run_agent_resource_retired_ref_rejects`, `run_building_plan_boundary`,
  `run_route_policy_boundary`, plus 2 validator helpers) — not the dict
  itself; its own `RULE_RUNNERS` mention (line 6) is a docstring reference
  only. Any split must keep the 50-key set byte-identical; the dict's home
  is `check_profile.py`, not either lib file.
- `check_profile.py`'s import block for `case_runners.py` (starting line 86)
  contains exactly 33 `run_*` names — not "~37" as earlier docs stated (that
  figure conflated this block with the separate `rule_runners.py` import
  block, 15 names starting line 69). 33 + 15 = 48; the remaining 2 of the 50
  `RULE_RUNNERS` keys are inline `text_contains`/`text_absent` lambdas
  defined directly in `check_profile.py` (lines 240-241).

### `support/checkers/check_bounded_agent_proposed_routing_loop0.py` — 7176 LOC
- Third-largest checker file (behind kernel_checks.py and case_runners.py —
  a prior doc's "the largest checker file" framing is imprecise; correct
  either as "3rd-largest overall" or "largest among files with zero
  decomposition analysis," since the top two do have partial extraction work).
  Still wired via `_CallMainKernel` from `check_profile.py`'s `KERNEL_DISPATCH`.
- No prior plan proposes a concrete split shape for this file anywhere —
  zero function-level cluster map, family breakdown, or split-shape proposal
  in any source doc. Every mention is a bare filename, a LOC fact, or a
  passing cross-reference to one symbol.
- Needs its own read-first pass before any split proposal exists — this is
  the missing first step, blocked on nothing.

### `support/operator/walker_kernel.py` — 2479 LOC
- **First split already landed and is done** (commit `f0b4679`, 2026-06-26):
  5 leaf modules extracted (`walker_carry.py` 669L, `walker_frontier_driver.py`
  186L, `walker_report_events.py` 296L, `walker_resume_seed.py` 400L,
  `walker_runtime_mail.py` 237L), `walker_kernel.py` kept as slim orchestrator
  + re-export facade for 10 externally-imported names. Verified at landing
  time via a 4-dimension adversarial workflow (byte-identity, `check_profile.py
  --all` exit 0, sha256-equal `_run_dynamic_graph_walker`, registry/admission
  complete).
- `_run_dynamic_graph_walker` remains intact, unsplit — HOLD still honored, no
  extraction has touched it since 0628. Re-derive its exact current line
  before any implementation work touches it (do not trust any cached
  coordinate for this function specifically).
- Do-not-split reasoning still applies: ~30 shared mutable locals, 7 nested
  closures, no `WalkerState` dataclass exists yet. Any future split needs P4
  resume-preservation proof plus a `WalkerState`-gated design — unchanged,
  still the correct gate.

### `support/checkers/module_registry.yaml` — 2072 LOC / 164 rows
- Growing in lockstep with every leaf extraction (each new lib module = 1 new
  row). Expected mechanical growth, not drag — do not target for reduction.
  `support/operator/*.py` census = 63 files / 63 registry rows (exact match).
  `support/checkers/lib/*.py` census = 20 files, all 20 with matching rows.
  (Counting note: the correct row pattern is `^  - module:` = 164; a naive
  `grep -c "module:"` returns 166 because 2 extra hits live inside an
  unrelated `decomposition_ceilings:` block at file-end, not real rows.)
- Carries a phantom `checker_strict_validation` profile reference at 3 lines
  (78, 533, 545), with no corresponding `.yaml` profile file on disk.
  **This is confirmed harmless stale prose, not a functional defect** — no
  code anywhere in the repo reads or dereferences the `pinned_by:` field
  (repo-wide grep = zero hits); it is a human-readable annotation only. The
  validation coverage `checker_strict_validation` used to represent was
  folded into the live profile `structure_template_integrity.yaml` (its own
  `description:` field states it is a "PASS-2 fold of
  brick_template_catalog_restructure, checker_strict_validation,
  current_context_prune"). What actually validates `module_registry.yaml`
  structurally is `check_package_path_admission.py` and
  `check_axis_crossing_elegance.py` (G4 bidirectional disk/registry-row
  existence — unrelated to `pinned_by` content). The registry's own
  `not_proven:` section (lines 2070-2072) self-declares `pinned_by` as
  descriptive only. Item 5 below remains a valid cleanup, but as a
  documentation-accuracy fix, not a dead-dependency repair.

### `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml` — 4237 LOC
- Still the checker-diet target, still not thinned (B2b never ran) — LOC
  unchanged across the most recent touching commit.
- Current label count: 99 `label:` rows.
- 3 staged split copies exist and are registered in `core.yaml`
  `path_allowlist` (lines 76-79) alongside the original:
  - `building_skill_preset_builder_composition.yaml` — 320 LOC, 8 labels
    (all 8 overlap with original).
  - `building_skill_preset_intake_adapter_gate.yaml` — 131 LOC, 4 labels
    (all 4 overlap with original).
  - `building_skill_preset_agent_resource_boundary.yaml` — 259 LOC, 1 label
    (`agent-resource-digest-sentinel-materialized-fast-fix`, genuinely
    non-overlapping with the original's 99).
- Conservation math: 12 labels duplicated (8+4) / 87 labels carried ONLY by
  the original (99 − 12). Confirmed via `comm -12`/`comm -23` set operations.
- `check_profile.py` has no extends/include/inherit/facade primitive — a
  delegating facade is structurally impossible here; diet must be
  complete-the-split-then-delete, not facade-preserving.
- Must use `support/checkers/lib/yaml_subset.py`'s loader for any inventory
  work: PyYAML cannot parse `module_registry.yaml` (`ScannerError: mapping
  values are not allowed here`, line 400 col 251) or this profile file itself
  (`ScannerError`, line 3690 col 51 — an unquoted scalar with an embedded
  colon: `expected_message: preferred_model_ref rejected: selected_model_ref
  provider must match selected adapter`).

### `support/checkers/profiles/*.yaml` — 31 live profiles
- Growth trail: 24 (0625) → 28 (0628/0630) → 30 (0701) → 31 (now). Newest
  additions since 0628: `graph_topology_fan_barrier.yaml`,
  `provider_registry_ladder.yaml`, `raw_evidence_stream_scrub.yaml`. Docs must
  stop hardcoding this number (§2 already fixed the 2 worst offenders).
- `RULE_RUNNERS` = 50 keys (stable since 0625); dict lives in
  `check_profile.py:235` (see case_runners.py section above).
- `KERNEL_DISPATCH` = 67 keys (growth trail: 62 → 63 → 65 → 67), no
  duplicates, confirmed via two independent counting methods.

### Checker-system-wide structural facts
- **`.github/workflows/release-gate.yaml` exists** (612 bytes, commit
  `60b46b9`, 2026-07-01, "P8 ship safety" Building output) — a real CI gate
  now runs on `pull_request`/`push to main`/`workflow_dispatch`: checkout,
  Python 3.11 + `uv` setup, `uv sync --locked`, then `sh
  support/onboarding/release_gate.sh`. Any prior claim of "no CI/release gate
  exists at all" is stale. This directly changes §4 item 8's scope — see
  there. (A second, irrelevant `.github/workflows` also exists under vendored
  `support/dashboard/node_modules/reusify/` — not part of this repo's CI.)
- `check_profile.py --all` sweeps are not strictly read-only:
  `case_runners.py:1930` creates a fixture vessel under
  `repo/project/<vessel_id>`, and a second fixed-vessel-id
  `checker-projection-fixture-vessel` function (lines 7767-8029, pinned by
  `read_side_projection_boundary.yaml:488`) does the same. Cleanup is
  `finally`-only (`shutil.rmtree(vessel_dir, ignore_errors=True)`, no
  `atexit`/signal-handler guard) — a SIGKILL mid-run leaves an orphan
  directory that hard-RUDs the next `--all` run (the code refuses to
  reuse/remove a pre-existing fixture dir it did not just create). Ordinary
  sweeps are non-reentrant under interruption.
- `check_adapter_usage_meter.py` exposes `--probe-mutation-red` (function at
  line 1021, flag registration at line 1159) which mutates the live
  `support/connection/adapter_local_cli.py` in place (backs up via `cp`,
  writes in place, re-runs as subprocess, restores) — an out-of-band probe
  that writes inside the inspected repo. Its help text (line 1162) names
  `agent_adapter.py` — that file is not deleted/renamed, it's a real,
  different, still-existing file from the actual mutation target
  (`adapter_local_cli.py`); the help text just names the wrong existing file,
  not a nonexistent one.
- `validate_profile()` (`check_profile.py:1104`) and `assert_registry_closure()`
  (lines 1068-1094) enforce schema/profile-ID presence and known-kernel-ID
  membership only — no requirement for non-empty `description`,
  `proof_limits`, `not_proven`, or at least one active tooth. A profile can
  be schema-valid and toothless today.

---

## 2. 이미 해결됨 / 낡음 (Resolved or stale)

- **`support/operator/walker_kernel.py` split (clusters A-E)** — done,
  commit `f0b4679` (2026-06-26), predates most source docs that still
  describe it as pending. Do not re-propose.
- **Dead pytest declaration in `pyproject.toml`** — fixed, commit `40ea12d`
  ("P6: correct verification surface honesty", 2026-07-01). The
  `[tool.pytest.ini_options]` / `testpaths = ["support/checkers"]` block was
  removed entirely; a regression guard (`brick_cli_entrypoint.yaml`
  `text_absent` rule, line 96) fails if it reappears. (Stray `def test_*`-named
  helper functions still exist inside `check_adapter_usage_meter.py`, now
  lines 312/978 — harmless now that pytest isn't pointed at the directory;
  not worth separate action.)
- **`setup.md` hardcoded "24 profiles"** — fixed, commit `40ea12d`. Text now
  instructs `find support/checkers/profiles -maxdepth 1 -name '*.yaml' | wc
  -l` instead of a fixed number.
- **`checker-profile-map.md` hardcoded "24 profiles / 54 kernel_checks"** —
  fixed, same commit. Replaced with a "measured checkout fact, not a
  constitutional constant" framing plus a dated observation block. Superseded
  the ADD-13 finding from the 0630 audit.
- **0626/0628 kernel_checks.py and case_runners.py line-coordinate tables** —
  every cited coordinate across those docs has drifted at least once, several
  multiple times. Only the *existence* of the pins/imports/allowlists is
  reliable; re-derive positions fresh at implementation time. This pattern
  has now repeated across three successive doc generations (0625→0626→0628
  drift, then 0701→0702 drift on this very document) — "line numbers rot
  fast in this repo" is an ongoing, currently-active property, not a
  one-time observation.
- **0626 proposed module names for kernel_checks split**
  (`kernel_common.py`, `kernel_checks_axis_vocab.py`, etc.) — never adopted,
  confirmed absent. The 8 extractions that actually happened used a
  different, already-established flat-domain-name convention. Moot.
- **"kernel_checks unchanged surfaces" claim (0626 decision table)** —
  refuted by its own quality-judge pass at the time, and further superseded
  since: the file's dispatch surface has changed substantially via 8
  subsequent extractions.
- **`archive/0702-doc-archive/research-0626/godmodule-decision-merged-0626.md` and
  `archive/0702-doc-archive/research-0626/godmodule-decomposition-decision-table-0626.md` LOC/coordinate tables** —
  superseded wholesale by the 0628 doc, which is itself superseded by this
  document. Keep only for historical trail, not for coordinates.
- **0630 audit's S4-F8 line citation (`kernel_checks.py:8541`)** — the
  underlying `.brick/builds` guard message still exists but has moved
  repeatedly, now at lines 8574 and 8829. The finding's substance (a
  negative-guard string inside a `text_absent`/guard-check pattern, not a
  live default path) is still correct on inspection.

---

## 3. 미검증 의견 (Unverifiable recommendations)

Kept for human judgment — these are design/process opinions, not
re-measurable facts.

- Facade-preserving split is the right default shape for kernel_checks.py /
  case_runners.py (vs. a clean break with re-pointed importers). Consensus
  across prior docs, never adjudicated against actual implementation cost.
- A green split-copy profile proves only what it carries — every moved
  label/assertion needs a **mutation-RED probe** (deliberately break the
  behavior, confirm the checker catches it) before it can be called
  "conserved." No such probes exist yet for any of the 12 currently-
  duplicated checker-diet labels; no mutation-RED probe mechanism found
  anywhere in the repo.
- `path_allowlist` cannot serve as a deletion-safety oracle (it rejects
  unexpected files, not missing expected ones) — cannot prove a profile
  deletion is safe by itself.
- Checker complexity should be hidden behind a customer-facing product-status
  translation layer (state/reason/next-action/evidence-refs) rather than
  exposed as raw checker/profile vocabulary. No implementation attempt yet;
  no matching translation-layer code found anywhere in `support/`.
- Profile schema should require non-empty `description`/`proof_limits`/
  `not_proven` and at least one active tooth (anti-toothless-profile guard).
  Confirmed gap, unimplemented — whether to gate future profile authoring on
  this is a judgment call, not a fact.
- `check_bounded_agent_proposed_routing_loop0.py`'s `0`-suffix naming should
  not be assumed "retired/dead" by default — some `0`-suffixed / `--large`
  style names are intentional negative guards. Applies caution to any future
  pruning pass on this file.
- Whether `_ensure_import_identity` fan-out is still a real cross-cutting
  constraint post-extraction: still open. Data point — 5 call sites remain
  inside `kernel_checks.py` itself, and 5 of the 8 extracted domain files
  also call it (~10 call-site locations total, roughly matching but not
  exactly the originally-cited "9 domains" figure, which used a
  semantic-domain grouping not re-derived here). Not resolved either way.

---

## 4. 제안 범위 (Proposed scope)

**Sequencing precondition satisfied:** this scope was explicitly sequenced to
start only after `brick-6-surface-audit-repair`'s P9 (final dynamic proof)
closes. P9 closed 2026-07-01 19:57 via a two-attempt Building sequence with
attempt 2 adopted (commit `46d02e4`; see
`archive/0702-doc-archive/brick-6-p9-dynamic-proof-closure-disposition-0701.md`, which concludes "P9's
live dynamic proof is demonstrated and adopted"). Note: that disposition doc
itself says P9 closure does not by itself declare the entire P0-P9 goal
complete — a separate final COO/Smith review across all phases plus Rules
8/9/10 was still pending at that time (since independently closed and
pushed — see `archive/0702-doc-archive/brick-6-goal-completion-definition-final-audit-0701.md`). None
of this scope folds into that goal's own P0-P9. This is the P6-class "engine
cleanup / godmodule decomposition" work the 0628 doc already scoped as
post-customer-path.

1. **Split `support/checkers/lib/kernel_checks.py` (10141 LOC) by domain,
   flat-sibling shape.**
   Follow the convention already established by the 8 completed extractions
   (`<domain>_check.py`, noting 2 of 8 deviate slightly — see §1), not the
   older `kernel_checks_*.py` proposal. Blocked on: fresh re-derivation of
   the 16 remaining `run_*` entrypoint boundaries, the 3 axis-vocab
   self-allowlist relocations, and confirming whether any profile
   `text_contains` pin targets a private helper body inside this file (would
   need to move with its function, not stay in a re-export shell). Gate:
   `check_profile.py --all` exit 0 + `module_registry.yaml` row per new leaf
   + G5 forbidden-ownership echo per leaf.

2. **Split `support/checkers/lib/case_runners.py` (8512 LOC) by
   support-surface family, flat-sibling shape.**
   Already 8 leaves extracted; remaining 28 `run_*_case` functions plus
   private helpers need re-clustering by family (adapter/materialize/
   intake/drain/link, or whatever grouping the current file content actually
   supports — re-derive, don't reuse an old line-based guess). Blocked on:
   re-deriving exact current lines for the two known cross-module
   private-helper imports (`_preset_completion_command_runner` from
   `kernel_checks.py`, now two sites; `_graph_test_plan_from_linear` from
   `check_building_operator_driver0.py`), and an explicit decision on
   facade-vs-direct-importer-update for the `check_profile.py` import block
   (33 names from case_runners.py + 15 from rule_runners.py — see §1 for the
   `RULE_RUNNERS` location correction).

3. **First-ever read-first inspection of
   `support/checkers/check_bounded_agent_proposed_routing_loop0.py` (7176
   LOC) for split feasibility.**
   No prior doc has produced a cluster map for this file — third-largest
   checker file, zero decomposition analysis done anywhere. Blocked on
   nothing — this is the missing first step; should happen before or
   alongside item 1/2 since it may share fixture/helper machinery with
   `case_runners.py`.

4. **Complete checker-diet on
   `building_skill_preset_agent_tool_hardening.yaml` (4237 LOC, 99 labels).**
   Confirmed no facade primitive exists — must be complete-the-split then
   delete, not thin-in-place. 87 labels currently have no split home; 12 are
   duplicated with no drift check. Blocked on: (a) mutation-RED probe per
   moved/duplicated label before any deletion, (b) an explicit disposition
   for the 5 concern families with no matching split target (p5/p6
   source-fact-carry, gate-sequence, hard-graph, multi-leader,
   governance-hint), (c) removing the corresponding `core.yaml`
   `path_allowlist` entry in the *same* change as any file deletion.

5. **Repair `module_registry.yaml` phantom `checker_strict_validation`
   row(s)** (lines 78, 533, 545) — either author the missing profile or
   remove the dead reference. **This is a documentation-accuracy fix, not a
   functional-dependency repair** (§1 confirms: no code reads `pinned_by:`,
   and the underlying validation coverage already lives on in
   `structure_template_integrity.yaml`). Small, independent, no blockers —
   could land before or during item 4. Also touch the matching stale comment
   at `check_profile.py:34`.

6. **Add anti-toothless-profile schema guard** to `validate_profile()`
   (line 1104) / `assert_registry_closure()` (lines 1068-1094): require
   non-empty `description`, `proof_limits`, `not_proven`, and at least one
   active tooth. Confirmed still fully unimplemented. Independent of the
   split work; should land before item 4's checker-diet deletion so the
   diet's own split-copy profiles are held to the new standard.

7. **Isolate/harden `check_profile.py --all` fixture writes.**
   Two known non-reentrant fixed-path fixture vessels
   (`case_runners.py:1930`, and `checker-projection-fixture-vessel` at lines
   7767-8029) both rely on `finally`-only cleanup and hard-raise if a stale
   directory exists from an interrupted prior run. Move to temp-root
   isolation or add a startup self-heal. Independent of the split work.

8. **Verify/complete the CI release gate.**
   `.github/workflows/release-gate.yaml` now exists (commit `60b46b9`,
   2026-07-01) — the original framing of this item ("add a CI/release gate,
   currently none exists") is overtaken. **Re-scoped**: verify whether
   `release_gate.sh` already covers `compileall`, `check_profile.py --all`,
   `brick verify`, dashboard build, and release-export negative probes, or
   whether it's a narrower stub still needing the full checklist. Not yet
   verified — do that first, then close any gap found. Sequence after items
   1-4 so the gate isn't immediately broken by in-flight splits.

9. **Retire `check_adapter_usage_meter.py --probe-mutation-red`'s
   live-source mutation pattern** — convert to a temp-copy probe, and fix its
   help-text reference (line 1162) to point at the correct file
   (`adapter_local_cli.py`, not `agent_adapter.py` — see §1 for why this is
   "wrong target," not "dead reference"). Small, independent.

**Explicit non-goals for this scope:** splitting `_run_dynamic_graph_walker`
(HOLD stands until P4 resume-preservation is proven with focused checker
evidence — do not revisit without that proof), and any work that changes
Brick/Agent/Link axis meaning — this is structural-drag cleanup only, per the
0628 doc's own framing, which still holds.
