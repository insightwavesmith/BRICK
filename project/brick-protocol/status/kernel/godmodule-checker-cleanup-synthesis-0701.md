# Godmodule + Checker Cleanup — Synthesized Plan (0701)

Baseline: main HEAD `62a02c2` (2026-07-01). All numbers below are the operator's
fresh measurements taken moments ago, cross-checked against `wc -l` /
`grep -c` re-runs during verification. Treat every LOC/count figure in any
prior doc (0625/0626/0628, and the 0630 audit cluster) as stale unless
re-stated here. This doc supersedes the file-shape numbers in all 8 source
docs; it does not re-litigate their design reasoning where that reasoning
still holds.

---

## 1. 확정 필요 (Confirmed still-needed)

Organized by target file. Numbers are current (0701), not the stale figures
carried in the source docs.

### `support/checkers/lib/kernel_checks.py` — 10201 LOC
- Still monolithic. Has already shed 8 leaf modules since 0626/0628
  (`no_smith_residue_check.py`, `install_release_export_lint_check.py`,
  `provider_preflight_check.py`, `design_ai_text_seams_check.py`,
  `codex_connect_stall_classification_check.py`, `onboard_smoke_check.py`,
  `gemini_local_only_adapter_check.py`, `graph_topology_fan_barrier.py`) but
  is still the single largest checker file by a wide margin.
- `grep -nE '^def run_'` today = 16 public entrypoints (not the 23/24 cited
  in 0626 docs — those were correct for their own snapshot, extraction has
  since removed 8).
- `check_profile.py` (1391 lines) is still the sole importer, import block
  now ~17 names + `call_main`.
- 3 axis-vocab self-allowlist pins still present (`_AXIS_VOCAB_MOVEMENT_ENUM_ALLOWLIST`,
  `_AXIS_VOCAB_DISPOSITION_ENUM_ALLOWLIST`, `_AXIS_VOCAB_ADAPTER_ENUM_ALLOWLIST`)
  at current lines 118/129/137 — these must relocate with whatever module
  re-encodes the enum literals, or `axis_vocab_drift` goes RED.
  **All prior line-number citations for this file (0625/0626/0628) are dead —
  re-derive at implementation time, do not trust any cached coordinate.**
- Still no `kernel_common.py` or `kernel_checks_*.py` split-module naming
  exists — none of the earlier proposed module names were adopted; the 8
  extractions that did happen used flat domain-named siblings instead
  (`support/checkers/lib/<domain>_check.py`). Any future split should follow
  that already-established naming convention, not the old proposal's names.

### `support/checkers/lib/case_runners.py` — 8507 LOC
- Partially split since 0628: 8 extraction commits pulled out
  `preset_completion_fixture.py`, `gate_evidence_readers.py`,
  `plan_fixture_helpers.py`, `materialized_plan_observers.py`,
  `materialize_reject_scaffold.py`, `adapter_capability_checks.py`,
  `materialized_return_shape_guards.py`, `casting_node_carry_check.py` — all
  flat siblings in `support/checkers/lib/`, all with `module_registry.yaml`
  rows.
- Still 8507 LOC — still the second-largest checker file. Not "done", just
  further along than any prior doc recorded.
- `grep '^def run_.*_case'` = 28 public case functions remain in-file.
- Cross-module private-helper imports still exist and still constrain any
  further split: `kernel_checks.py:3427` imports
  `_preset_completion_command_runner`; `check_building_operator_driver0.py:75`
  imports `_graph_test_plan_from_linear`. **Re-derive exact line before
  touching — this number has moved at least 3 times across the source docs
  (4401/5276 → 3978/4853 → 3427) and will move again.**
- `RULE_RUNNERS` (50 keys) now lives in `support/checkers/lib/rule_runners.py`,
  not in `case_runners.py` — any split must keep this keyset byte-identical
  but does not need to co-locate it.
- `check_profile.py` import block for this file: ~37 `run_*` names starting
  at line 86; `RULE_RUNNERS` dict itself at `check_profile.py:234`.

### `support/checkers/check_bounded_agent_proposed_routing_loop0.py` — 7087 LOC
- Not touched by any split work in any source doc. Third-largest checker
  file, growing (was 6923 at the 0630 audit, +164 lines since). Still wired
  via `_CallMainKernel` from `check_profile.py`'s `KERNEL_DISPATCH`.
- No prior plan proposes a concrete split shape for this file — it is a
  gap in all 8 source docs, not just a stale-number problem. Needs its own
  read-first pass before any split proposal exists.

### `support/operator/walker_kernel.py` — 2306 LOC
- **First split already landed and is done** (commit `f0b4679`, 2026-06-26):
  5 leaf modules extracted (`walker_carry.py` 669L, `walker_frontier_driver.py`
  186L, `walker_report_events.py` 296L, `walker_resume_seed.py` 400L,
  `walker_runtime_mail.py` 237L), `walker_kernel.py` kept as slim
  orchestrator + re-export facade for 10 externally-imported names.
  Verified via 4-dimension adversarial workflow at landing time
  (byte-identity, `check_profile.py --all` exit 0, sha256-equal
  `_run_dynamic_graph_walker`, registry/admission complete).
- `_run_dynamic_graph_walker` remains intact, unsplit, at current line 805,
  spanning to end-of-file (~1500 LOC). **HOLD confirmed still honored** — no
  further extraction has touched this function since 0628 (only one
  incidental commit, `0fa3a34`, added code around it).
- Do-not-split reasoning still applies as originally stated: ~30 shared
  mutable locals, 7 nested closures, no `WalkerState` dataclass exists yet.
  Any future split needs P4 resume-preservation proof plus a
  `WalkerState`-gated design — this is unchanged and still the correct gate.

### `support/checkers/module_registry.yaml` — 2052 LOC / 162 rows
- Growing in lockstep with every leaf extraction (each new lib module = 1
  new row). This is expected mechanical growth, not drag — do not target
  for reduction.
- Confirmed live: `support/operator/*.py` census = 61 files / 61 registry
  rows (exact match, unchanged since 0628). `support/checkers/lib/*.py`
  census = 20 files, all 20 with matching registry rows.
- Still carries a phantom `checker_strict_validation` profile reference at
  3 lines (78, 523, 535) with no corresponding
  `support/checkers/profiles/checker_strict_validation.yaml` file on disk.
  This is real registry drift, confirmed by direct grep, not yet repaired
  by any landed commit.

### `support/checkers/profiles/building_skill_preset_agent_tool_hardening.yaml` — 4237 LOC
- Still the checker-diet target. Still not thinned (B2b never ran).
- Current label count: **99** `label:` rows (drifted up from 97 cited in
  0626/0628 — 2 labels were added since).
- 3 staged split copies exist and are registered in `core.yaml`
  `path_allowlist` (lines 76-79) alongside the original:
  - `building_skill_preset_builder_composition.yaml` — 320 LOC, 8 labels
    (all 8 overlap with original)
  - `building_skill_preset_intake_adapter_gate.yaml` — 131 LOC, 4 labels
    (all 4 overlap with original)
  - `building_skill_preset_agent_resource_boundary.yaml` — 259 LOC, **1**
    label (drifted from the 0 originally recorded — a label was added since
    the split)
- Current conservation math: 12 labels duplicated (8+4, the
  `agent_resource_boundary` label does not overlap with original) / **87**
  labels carried ONLY by the original (99 − 12), not the 85 cited earlier.
- `check_profile.py` confirmed to have **no** extends/include/inherit/facade
  primitive — a delegating facade is structurally impossible; diet must be
  complete-the-split-then-delete, not facade-preserving.
- Must use `support/checkers/lib/yaml_subset.py`'s loader for any inventory
  work — directly reproduced that PyYAML cannot parse this file
  (`ScannerError` at line 390 of `module_registry.yaml`, and likely similar
  issues in this profile file — same repo-wide constraint).

### `support/checkers/profiles/*.yaml` — 30 live profiles
- Confirmed current count (was 24 at 0625, 28 at 0628/0630-audit, now 30).
  New since 0628: `graph_topology_fan_barrier.yaml` (commit `2405a9d`) plus
  the 3 checker-diet split copies above (already counted). Docs must stop
  hardcoding this number — see §2, already partly fixed.
- `RULE_RUNNERS` = 50 keys (stable across every measurement window, confirmed
  unchanged since 0625).
- `KERNEL_DISPATCH` = 65 keys (drifted from 62 at 0625, 63 at 0626 — grew by
  3 via the same extraction commits).

### Checker-system-wide structural facts (still true, not file-specific)
- No `.github/workflows/` directory exists anywhere in the repo — no
  CI/branch-protection release gate exists at all. Confirmed by direct
  listing. This is independent of any godmodule work.
- `check_profile.py --all` sweeps are not strictly read-only:
  `case_runners.py` creates fixture vessels under `repo/project/<vessel_id>`
  (confirmed at current line 1930, and a second fixed-vessel-id pattern at
  ~7813-8020 for `checker-projection-fixture-vessel`, pinned by
  `read_side_projection_boundary.yaml:479`). Cleanup is `finally`-only —
  a SIGKILL mid-run leaves an orphan directory that hard-RUDs the next
  `--all` run. This makes ordinary sweeps non-reentrant under interruption.
- `check_adapter_usage_meter.py` still exposes `--probe-mutation-red`
  (function at line 978, flag at 1115) which mutates the live
  `support/connection/adapter_local_cli.py` in place and restores via `cp`
  — an out-of-band probe that writes inside the inspected repo. Its help
  text at line 1118 still references the older `agent_adapter.py` surface
  name (stale reference, separate from the mutation-write concern).
- `validate_profile()` (`check_profile.py:1098`) and `assert_registry_closure()`
  (lines 1061-1085) enforce schema/profile-ID presence and known-kernel-ID
  membership only — no requirement for non-empty `description`,
  `proof_limits`, `not_proven`, or at least one active tooth. A profile can
  be schema-valid and toothless today. Confirmed by direct read, unchanged.

---

## 2. 이미 해결됨 / 낡음 (Resolved or stale)

- **`support/operator/walker_kernel.py` split (clusters A-E)** — done,
  commit `f0b4679` (2026-06-26), predates most of the source docs that still
  describe it as pending. Do not re-propose.
- **Dead pytest declaration in `pyproject.toml`** — fixed same-day, commit
  `40ea12d` ("P6: correct verification surface honesty", 2026-07-01). The
  `[tool.pytest.ini_options]` / `testpaths = ["support/checkers"]` block was
  removed entirely; current `pyproject.toml` has no pytest section. A
  regression guard was added (`brick_cli_entrypoint.yaml` `text_absent`
  rule) that fails if the declaration reappears. (Stray `def test_*`-named
  helper functions still exist inside `check_adapter_usage_meter.py` at
  lines 311/935 — those are unchanged and harmless now that pytest isn't
  pointed at the directory; not worth separate action.)
- **`setup.md` hardcoded "24 profiles"** — fixed same-day, commit `40ea12d`.
  Text now instructs `find support/checkers/profiles -maxdepth 1 -name
  '*.yaml' | wc -l` instead of a fixed number.
- **`checker-profile-map.md` hardcoded "24 profiles / 54 kernel_checks"** —
  fixed same commit `40ea12d`. Replaced with "measure at runtime" plus a
  dated observation, superseding the ADD-13 finding from the 0630 audit.
- **0626/0628 kernel_checks.py and case_runners.py line-coordinate tables**
  (function line numbers, cross-import line numbers, self-allowlist line
  numbers) — every single cited coordinate across all three 0626/0628 docs
  has drifted at least once, several multiple times. None are usable as-is.
  Only the *existence* of the pins/imports/allowlists is reliable; re-derive
  positions fresh at implementation time.
- **0626 proposed module names for kernel_checks split**
  (`kernel_common.py`, `kernel_checks_axis_vocab.py`, etc.) — never adopted.
  The 8 extractions that actually happened used a different, already-
  established flat-domain-name convention. Proposed names are moot.
- **"kernel_checks unchanged surfaces" claim (0626 decision table)** —
  refuted by its own quality-judge pass at the time, and further superseded
  since: the file's dispatch surface has changed substantially via 8
  subsequent extractions.
- **`godmodule-decision-merged-0626.md` and
  `godmodule-decomposition-decision-table-0626.md` LOC/coordinate tables** —
  superseded wholesale by the 0628 doc, which is itself now superseded by
  this document. Keep only for historical trail, not for coordinates.
- **0630 audit's S4-F8 line citation (`kernel_checks.py:8541`)** — the
  underlying `.brick/builds` guard message still exists but has moved to
  lines 8489 and 8728 due to file growth. The finding's substance (it's a
  negative-guard string, not a live default path) is still correct.

---

## 3. 미검증 의견 (Unverifiable recommendations)

Kept for human judgment — these are design/process opinions, not
re-measurable facts. Listed once, de-duplicated across sources.

- Facade-preserving split is the right default shape for kernel_checks.py /
  case_runners.py (vs. a clean break with re-pointed importers). Consensus
  across 0626/0628 docs, never adjudicated against actual implementation
  cost.
- A green split-copy profile proves only what it carries — every moved
  label/assertion needs a **mutation-RED probe** (deliberately break the
  behavior, confirm the checker catches it) before it can be called
  "conserved." No such probes exist yet for any of the 12 currently-
  duplicated checker-diet labels.
- `path_allowlist` cannot serve as a deletion-safety oracle (it rejects
  unexpected files, not missing expected ones) — so it cannot prove a
  profile deletion is safe by itself.
- Checker complexity should be hidden behind a customer-facing product-
  status translation layer (state/reason/next-action/evidence-refs) rather
  than exposed as raw checker/profile vocabulary. No implementation attempt
  yet in any reviewed closure.
- Profile schema should require non-empty `description`/`proof_limits`/
  `not_proven` and at least one active tooth (anti-toothless-profile guard).
  Confirmed gap, unimplemented; whether to gate future profile authoring on
  this is a judgment call, not a fact.
- `check_bounded_agent_proposed_routing_loop0.py`'s `0`-suffix naming should
  not be assumed "retired/dead" by default — some `0`-suffixed / `--large`
  style names are intentional negative guards. Applies caution to any future
  pruning pass on this file.
- Whether `_ensure_import_identity` fan-out (originally cited as touching 9
  domains inside kernel_checks.py) is still a real cross-cutting constraint
  post-extraction was not independently re-confirmed this round — treat as
  open until re-derived.

---

## 4. 제안 범위 (Proposed scope)

**Explicitly sequenced to start only after the current
brick-6-surface-audit-repair goal's P9 (final dynamic proof) closes.** None
of this folds into that goal's P0-P9. This is the P6-class "engine cleanup /
godmodule decomposition" work the 0628 doc already scoped as post-customer-
path — that framing still holds and is reinforced here.

1. **Split `support/checkers/lib/kernel_checks.py` (10201 LOC) by domain,
   flat-sibling shape.**
   Follow the naming convention already established by the 8 completed
   extractions (`<domain>_check.py` under `support/checkers/lib/`), not the
   older `kernel_checks_*.py` proposal. Blocked on: fresh re-derivation of
   the 16 remaining `run_*` entrypoint boundaries, the 3 axis-vocab
   self-allowlist relocations, and confirming whether any profile
   `text_contains` pins target private helper bodies inside this file
   (would need to move with their function, not stay in a re-export shell).
   Gate: `check_profile.py --all` exit 0 + `module_registry.yaml` row per
   new leaf + G5 forbidden-ownership echo per leaf.

2. **Split `support/checkers/lib/case_runners.py` (8507 LOC) by
   support-surface family, flat-sibling shape.**
   Already 8 leaves extracted; remaining 28 `run_*_case` functions plus
   private helpers need re-clustering by family (adapter/materialize/
   intake/drain/link, or whatever grouping the current file content
   actually supports — re-derive, don't reuse 0626's line-based guess).
   Blocked on: re-deriving the exact current line for the two known
   cross-module private-helper imports (`_preset_completion_command_runner`
   from `kernel_checks.py`, `_graph_test_plan_from_linear` from
   `check_building_operator_driver0.py`), and an explicit decision on
   facade-vs-direct-importer-update for the ~37-name `check_profile.py`
   import block.

3. **First-ever read-first inspection of
   `support/checkers/check_bounded_agent_proposed_routing_loop0.py` (7087
   LOC) for split feasibility.**
   No prior doc has produced a cluster map for this file — it is the
   largest checker file with zero decomposition analysis done anywhere in
   the 8 sources. Blocked on: nothing (this is the missing first step);
   should happen before or alongside item 1/2 since it may share fixture/
   helper machinery with `case_runners.py`.

4. **Complete checker-diet on
   `building_skill_preset_agent_tool_hardening.yaml` (4237 LOC, 99 labels).**
   Confirmed no facade primitive exists — this must be complete-the-split
   then delete, not thin-in-place. 87 labels currently have no split home;
   12 are duplicated with no drift check. Blocked on: (a) mutation-RED probe
   per moved/duplicated label before any deletion, (b) an explicit
   disposition for the 5 concern families that currently have no matching
   split target (p5/p6 source-fact-carry, gate-sequence, hard-graph,
   multi-leader, governance-hint), (c) removing the corresponding
   `core.yaml` `path_allowlist` entry in the *same* change as any file
   deletion.

5. **Repair `module_registry.yaml` phantom `checker_strict_validation`
   row(s)** (3 lines: 78, 523, 535) — either author the missing profile or
   remove the dead reference. Small, independent, no blockers — could land
   before or during item 4 without waiting on it.

6. **Add anti-toothless-profile schema guard** to `validate_profile()` /
   `assert_registry_closure()`: require non-empty `description`,
   `proof_limits`, `not_proven`, and at least one active tooth. Independent
   of the split work; should land before item 4's checker-diet deletion so
   the diet's own split-copy profiles are held to the new standard.

7. **Isolate/harden `check_profile.py --all` fixture writes.**
   Two known non-reentrant fixed-path fixture vessels
   (`case_runners.py:~1930` repo/project vessel, and the
   `checker-projection-fixture-vessel` pinned at
   `read_side_projection_boundary.yaml:479`) both rely on `finally`-only
   cleanup and hard-raise if a stale directory exists from an interrupted
   prior run. Move to temp-root isolation or add a startup self-heal.
   Independent of the split work.

8. **Add CI/release gate** (GitHub Actions or equivalent) wiring
   `compileall`, `check_profile.py --all`/targeted profiles, `brick verify`,
   dashboard build, and release-export negative probes into a required
   branch-protection check. Currently zero `.github/workflows/` exist.
   Large, independent of the god-module work — sequence after items 1-4 so
   the gate isn't immediately broken by in-flight splits.

9. **Retire `check_adapter_usage_meter.py --probe-mutation-red`'s
   live-source mutation pattern** — convert to a temp-copy probe, and fix
   its stale `agent_adapter.py` help-text reference. Small, independent.

**Explicit non-goals for this scope:** splitting `_run_dynamic_graph_walker`
(HOLD stands until P4 resume-preservation is proven with focused checker
evidence — do not revisit without that proof), and any work that changes
Brick/Agent/Link axis meaning — this is structural-drag cleanup only, per
the 0628 doc's own framing, which still holds.
