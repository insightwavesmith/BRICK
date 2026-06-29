# God-Module Decomposition — Merged Decision Table (0626)

Best-of-both merge of two independent design Buildings against
`struct-surgery-0623` @ HEAD `3d22955`:

- **claude** (`godmodule-design-0626`) — full coverage on all 4 targets, full risk lists.
- **codex** (`godmodule-design-codex-0626`) — pinpoint `file:line` citations (verified line-accurate at HEAD), but **TRUNCATED** on `kernel_checks` (returned only an `output_excerpt`, no decomposition).

Merge rules applied:
- codex citations are authoritative where present (re-spot-checked at HEAD — they match).
- claude full risk lists + coverage used where codex is thin.
- `kernel_checks` was **RE-DERIVED from scratch** against the current file (claude's spans were stale by ~+423 lines; codex had none).
- All line numbers below are current-HEAD unless tagged `(stale)`.

Shared facts across all four targets:
- Established repo precedent for god-module splits is **two-flavored**: facade-kept (e.g. `agent_adapter.py` → thin facade re-exporting 7 siblings; `dynamic_walker`/`building_operation` `__all__` facade) and facade-removed (e.g. `composition.py` split, callers re-pointed at real homes). The facade-vs-no-facade choice is a separable, human-owned decision both designs flag, not a structural blocker.
- Every new `support/checkers/lib/*.py` or `support/operator/*.py` module needs a `module_registry.yaml` row (G4 bidirectional mag-0 tie, `check_axis_crossing_elegance.py:513,527`) and must echo `forbidden_ownership = [movement_author, target_selector, success_judge, quality_judge, route_invent]` (G5).
- Discipline for all four: **behavior-preserving / verbatim move**, gate = `check_profile.py --all` EXIT 0, no axis ownership moves.

---

## 1. kernel_checks — `support/checkers/lib/kernel_checks.py` (RE-DERIVED)

### Re-derivation note (why this section is authored, not merged)
codex TRUNCATED (only an `output_excerpt`; said "9808 lines" then stopped). claude authored against a **stale checkout** ("10232 lines"; its domain spans run ~+423 lines too high — e.g. it placed `run_chat_session_park_seam` at `:6934` and dashboard at `:7300-8415`, neither of which holds at HEAD). This section was re-derived directly: `wc -l` = **9808 lines**, `grep -nE '^def run_'` = **23 `run_*` public entrypoints**, and the shared-infra call sites were re-counted at HEAD.

### Recommendation
**Facade-preserving split** (keep `kernel_checks.py` as a thin re-export facade). Both the recommended option and the re-derivation agree:
- The public surface is exactly **23 `run_*` functions + `call_main`**, imported by name in `check_profile.py:125-150` (confirmed: the import block lists those 24 names). A facade re-export keeps that import block and `KERNEL_DISPATCH` byte-stable → blast radius confined to the `lib/` layer + N new registry rows.
- Natural seam = **one new flat `lib/*.py` module per `run_*` domain** (or per cohesive cluster of small domains), with shared in-file infra extracted FIRST to a new `kernel_common.py`.
- Pure-split (drop the facade, re-point `check_profile.py:125-150`) is the documented alternative; **not** recommended as first cut (enlarges blast radius to the importer + redistributes registry `pinned_by`).

### Grounded citations (current HEAD — RE-DERIVED)
Public `run_*` entrypoints (23), in file order:

| line | run_* domain |
|---|---|
| 582 | run_axis_vocab_drift |
| 650 | run_building_map_graph |
| 710 | run_building_plans_boundary_sweep |
| 1980 | run_agent_adapter_return_shape (MEGA) |
| 2188 | run_provider_preflight |
| 2287 | run_design_ai_text_seams |
| 2606 | run_codex_connect_stall_classification |
| 2966 | run_gemini_api_adapter |
| 3205 | run_onboard_smoke |
| 3365 | run_install_script_lint |
| 3497 | run_release_export_exclusion |
| 3632 | run_product_no_smith_residue |
| 4953 | run_reporter_notification_projection (MEGA) |
| 5195 | run_adapter_error_frontier_manifest_consistency |
| 5286 | run_adapter_error_path_hardening (MEGA) |
| 6511 | run_chat_session_park_seam |
| 7932 | run_dashboard_productization_projection (MEGA) |
| 8762 | run_brick_cli_entrypoint_smoke |
| 8830 | run_mcp_stdio_smoke |
| 8951 | run_connect_config_launch |
| 9067 | run_codex_projection_native |
| 9312 | run_claude_projection_native |
| 9783 | run_agent_session_id_redaction |

Shared in-file infra (extract to `kernel_common.py` FIRST):
- `captured_output` `:606`, `patched_argv` `:614`, `_without_report_grain_env` `:624` (callers `:4001,:4052`), `call_main` `:633` — the in-process subprocess shim.
- `_ensure_import_identity` `:679` — called by **9 domains** at `:1981, :2199, :2304, :2632, :2987, :3223, :4954, :9096, :9342`. **Must be extracted to common first**, else each domain module duplicates it (single-source violation) or imports across domain modules (lib-internal coupling).
- `_minimal_reporter_packet` `:685` (callers `:3850, :4474, :4751, :5024`) — reporter-domain-local; can travel with the reporter module.

Axis-vocab self-allowlist pins naming `kernel_checks.py` at `:114, :122, :129` (`_AXIS_VOCAB_*_ALLOWLIST`) — these must **RELOCATE** to whichever module re-encodes the movement/disposition enum literals (proposed `kernel_checks_axis_vocab.py`), per the documented checker-pin-follows-rehome standard. Leaving them on the facade while the body moves mis-pins the allowlist → `axis_vocab_drift` RED.

Gate / contract surfaces (HEAD):
- `check_profile.py:125-150` — sole Python importer (import block re-confirmed: 23 `run_*` + `call_main`).
- `check_package_path_admission.py:1852-1857` — flat-lib admission: `len(lib_parts) == 4` (a `lib/subdir/foo.py` is NOT admitted → a `lib/` subpackage RED's; **flat-only**).
- `check_axis_crossing_elegance.py:513,520,527` — G4 bidirectional mag-0 tie; `:67` G5 forbidden_ownership restatement.
- `module_registry.yaml:547` — existing `kernel_checks.py` row (stays as the facade row).

### Proposed module grouping (re-derived spans at HEAD)
Domain blocks by current line range:

- `kernel_common.py` — shared shim `:606-648` + `_ensure_import_identity` `:679` + `_minimal_reporter_packet` `:685`.
- `kernel_checks_axis_vocab.py` — axis-vocab constants + helpers + `run_axis_vocab_drift` `:43-605` (**CARRIES the relocated `:114/:122/:129` enum self-allowlist pin**).
- `kernel_checks_building_map.py` — `run_building_map_graph` `:650` + `run_building_plans_boundary_sweep` `:710-811`.
- `kernel_checks_agent_adapter.py` — `run_agent_adapter_return_shape` MEGA `:812-1979` incl. `_agent_effective_write_probe :925`, `_agent_read_tier_probe :1213`, `_artifact_grounding_probe :1514`.
- `kernel_checks_provider_native.py` — `run_provider_preflight :2188`, `run_design_ai_text_seams :2287`, `run_codex_connect_stall_classification :2606`, `run_gemini_api_adapter :2966`, `run_onboard_smoke :3205`, plus the late native/connect cluster `run_brick_cli_entrypoint_smoke :8762`, `run_mcp_stdio_smoke :8830`, `run_connect_config_launch :8951`, `run_codex_projection_native :9067`, `run_claude_projection_native :9312`.
- `kernel_checks_product_release.py` — `run_install_script_lint :3365`, `run_release_export_exclusion :3497`, `run_product_no_smith_residue :3632`, `run_agent_session_id_redaction :9783`.
- `kernel_checks_reporter.py` — `run_reporter_notification_projection` MEGA `:3660-5194` (helpers `_minimal_operator_wake_target :3660` … `_assert_no_scheduler_constructs :4912`, run at `:4953`).
- `kernel_checks_adapter_error.py` — `run_adapter_error_frontier_manifest_consistency :5195` + `run_adapter_error_path_hardening :5286` (MEGA helpers `:5642-6500`).
- `kernel_checks_chat_session.py` — `run_chat_session_park_seam :6511` + **all `_chat_session_*` helpers `:7993-8726`** (RE-CONTIGUOUS them).
- `kernel_checks_dashboard.py` — `_dashboard_*` helpers `:6877-7926` + `run_dashboard_productization_projection :7932`.
- `kernel_checks.py` (facade) — `from .kernel_checks_* import run_*` re-exports preserving the 23 public names + `call_main`.

### Risk union
- **chat_session is NON-contiguous at HEAD** (load-bearing): `run_chat_session_park_seam` is at `:6511`, but its `_chat_session_*` helpers are at `:7993-8726` — **the dashboard block `:6877-7932` is spliced in between**. A naive line-range cut mis-slices. **Move BY SYMBOL, not by line range.** (claude flagged this pattern; the HEAD spans here are the corrected ones.)
- `_ensure_import_identity` fan-out across 9 domains → extract to common FIRST (else duplication or cross-domain import coupling).
- Self-allowlist literals `:114/:122/:129` must relocate WITH the enum-re-encoding body, not stay on the facade.
- Monkeypatch string targets (gemini `urlopen` patch) + `check_id` literals are behavior-bearing — any incidental edit silently breaks the check; verbatim-move only.
- FLAT-ONLY admission: every new module is `support/checkers/lib/<name>.py` (path length 4); a `lib/` subpackage RED's.
- Suggested verifier: byte-identity audit (concatenate moved defs pre/post + sha256, or `git diff -M` move-only) to evidence behavior-preserving movement.

### claude-vs-codex disagreement
None on substance — codex truncated, so there is no competing decomposition to reconcile. claude's *pattern* analysis (facade-preserving, move-by-symbol, extract-common-first, relocate-allowlist) is sound and adopted; only its **line numbers were stale (~+423)** and have been replaced wholesale with HEAD-derived spans above.

---

## 2. case_runners — `support/checkers/lib/case_runners.py`

### Recommendation
**Split by behavior/surface family + extract a shared-helper leaf.** Both designs agree on split-by-surface; they DIFFER on facade and on package shape (see disagreement).
- **claude:** split into ~5 sibling flat leaves + `case_runners_common.py`, and (route-B precedent) **re-point importers/pins** to real new homes rather than keep a re-export facade — facade-kept recorded as the lower-blast-radius fallback.
- **codex:** split-**plus-facade** — keep `case_runners.py` as a compatibility facade re-exporting `run_*`, move clusters into a `case_runners_parts/` private package (or `_case_runners_*` flat siblings), one cluster per pass.

**Merged recommendation:** split by surface into **flat sibling leaves** (claude's flat shape matches the enforced flat-lib admission rule — a `case_runners_parts/` subpackage would need its own admission check; flat is the safer default), extract a `case_runners_common.py` shared leaf, and treat **facade-kept vs facade-removed as the human-owned sub-choice** (both repo precedents exist). Move one cluster per pass, behavior-preserving.

### Grounded citations
codex `file:line` (authoritative, HEAD-accurate) for cluster entrypoints:
`:46` (run_adapter_model_selection_case, first public run_*), `:190` (materialize-building intent), `:515/:716` (materialization helpers), `:1354` (adapter gate shape union), `:1528` (building intake seam), `:3818` (declared step-template), `:3899` (compose-building), `:4286` (native dispatch close), `:5086` (workflow import), `:5660` (shared graph/composition helper island), `:6016` (adapter capability rehome), `:7229` (run_building_once task-source admission), `:7444` (write-scope default exclude), `:7615` (source-fact body carry), `:7943` (wiki carry truncation), `:8111` (step-output drain), `:9439/:9475` (generated projection property tables), `:9997` (link route evidence).

claude full-coverage facts (the consumer/pin surface codex could not see — read scope was this-file-only):
- Primary consumer `check_profile.py:86-124` (imports 38 `run_*` names) + `RULE_RUNNERS` dispatch dict `:231-268` (keys must stay byte-identical).
- **Cross-module PRIVATE-helper imports** (the real coupling that constrains the split): `kernel_checks.py:4401` imports `_preset_completion_command_runner`; `kernel_checks.py:5276` and `check_building_operator_driver0.py:75` import `_graph_test_plan_from_linear`. These three private helpers MUST land in the shared-common leaf or those importers break.
- Symbol→path text-pins in `check_package_path_admission.py:186-191` and `profiles/agent_axis_behavioral.yaml` name specific case symbols at this exact path → must be re-pointed (route-B) on move.
- `module_registry.yaml:527-535` existing `case_runners.py` row.
- File length: claude `10223`, codex `10219` — minor read-boundary delta, both ~10.2k; not load-bearing.

### Risk union
- **Two private helpers cross the module boundary** (`_graph_test_plan_from_linear`, `_preset_completion_command_runner`) — bury them in a surface module and `kernel_checks.py:4401/5276` + `driver0.py:75` break. They belong in the common leaf. (claude — codex missed these, having read only `case_runners.py`.)
- Module-level constant tuples (`_LINK_CASE_*`, `_VESSEL_CASE_*`) referenced only inside their own cluster's functions → must travel WITH that cluster (NameError at call time otherwise). (both)
- Deferred/lazy imports inside functions (`brick_protocol.*`, `support.operator.*`) manage the checker's repo-import-path swap and dual-import identity (codex pins the dual-identity concern at `:4300/:4286`) — keep them lazy in the first pass; flattening to module top changes import timing. (both)
- Circular-import risk: the common leaf must stay dependency-free of surface leaves (shared graph builders are used by both regular clusters and the drain builders). (both)
- Pin-miss risk: route-B (facade removed) + a missed pin → `check_package_path_admission` text-pin RED; facade-kept → a stale re-export can mask a missing move. (claude)
- Monkeypatch helpers mutating `__globals__` are fragile across import paths → move with their cluster and test immediately. (codex)
- `RULE_RUNNERS` lists some non-case-runner rules too (e.g. from `rule_runners`) — the split must not accidentally claim those. (claude)

### claude-vs-codex disagreement
1. **Facade:** codex = keep facade (split-plus-facade); claude = remove facade, re-point importers/pins (route-B), facade-kept only as fallback. → Reconciled as a **human-owned sub-choice**; both repo precedents exist. Merged default leans claude (cleaner long-term, matches most-recent `composition.py` precedent) but records facade-kept as lower-blast-radius.
2. **Package shape:** codex proposes a `case_runners_parts/` subpackage; claude proposes flat `case_runners_*` siblings. → Reconciled toward **flat siblings** — the admission rule (`check_package_path_admission.py:1852-1857`) auto-admits flat `lib/*.py` only; a subpackage adds an admission burden codex couldn't see (it read only the one file).

---

## 3. walker_kernel — `support/operator/walker_kernel.py`

### Recommendation
**Staged split: relocate the cohesive leaf-helper clusters into sibling `walker_*` modules as pure no-op moves; keep the big loop in place.** Both designs strongly agree.
- `_run_dynamic_graph_walker` (`:2357-3803`, ~1450 lines) is a genuine kernel: ~30 shared mutable locals + 7 nested closures over them → **do NOT split now** (would need a `WalkerState` dataclass; high drift risk against a byte-stability-pinned path). Both designs explicitly defer this.
- Move clusters A–E first; `process_one_node` (cluster F) is already arg-threaded (no closure capture) → optionally liftable later with zero rework.
- Facade-vs-no-facade is again the human sub-choice; both flag `walker_kernel.py` staying as the orchestration facade.

### Grounded citations (HEAD — codex line numbers verified accurate; file = 3803 lines)
Cluster boundaries (claude cluster labels + codex pinpoint lines agree closely):

- **A — frontier driver:** `:139` (`_ReadyItemsResult`, `_FrontierDriver`), `:274` (`_fanout_dispatch_pool_size`), pool override `:304`. → `walker_frontier_driver.py`.
- **B — carry / source-fact / wiki:** `:333` (`_source_fact_body_carry_for_step`), `:742/:837/:882/:916` (wiki-carry view + `wiki_carry_summary_text`/`wiki_carry_path_text` parser helpers). → `walker_carry.py` / `walker_carry_context.py`.
- **C — runtime mail:** `:962` (`_runtime_handoff_unresolved_address`), `:1045` (`_step_output_address_escapes_ledger`), `:1108` (`_runtime_concern_handoff_from_ledger`). → `walker_runtime_mail.py`.
- **D — resume support:** `:1186` (`ResumeSeed`), `:1320` (replay/gate live-compute), `:1429/:1446/:1502` (lifecycle/disposition). → `walker_resume_seed.py` / `walker_resume_state.py`.
- **E — report events:** `:1568-1847` (`_emit_brick_*` / `_brick_grain_*` / `_emit_disposition_applied_event` / `_emit_building_event_best_effort` / `_report_repo_root_for_building_root` `:1827`). → `walker_report_events.py`.
- **F — node processing:** `:1847` (`NodeProcessingOutcome`), `:1937` (`process_one_node`, arg-threaded). → optional `walker_node.py`.
- **G — orchestrator (KEEP):** `:2357-3803` `_run_dynamic_graph_walker`; nested closures at `:2564, :2621, :2627, :2660, :2707, :2731, :2743`; high-coupling loop region `:2830, :3049, :3202, :3433`; terminal evidence assembly `:3679-3803`.

Public/cross-module import surface (claude — the consumer map that constrains facade choice):
- `ResumeSeed` ← `run.py:98`, `walker_resume.py:62`; `replay_gate_compute_live_record` ← `run.py:99`.
- `_run_dynamic_graph_walker` ← `walker_resume.py:63`, `dynamic_walker.py:75`.
- `_runtime_handoff_unresolved_address` ← `walker_resume.py:64` **and a checker `check_bounded_agent_proposed_routing_loop0.py:5878`**.
- `wiki_carry_*` / `_source_fact_body_carry_for_step` ← `case_runners.py:7619, 7882, 7976, 8315`.
- Registry: `module_registry.yaml:1374-1382` existing `walker_kernel` row + forbidden_ownership; god-module split precedent `check_package_path_admission.py:158-160, 381-383`.
- Profile gate: `bounded_agent_proposed_routing_loop` profile pins `walker_kernel` → the byte-stability guard.

### Risk union
- `ResumeSeed` relocation needs the `walker_resume.py:62` importer updated or a re-export (facade). (both)
- `_runtime_handoff_unresolved_address` is imported by a **checker** (`...loop0.py:5878`) — its name must resolve post-split. (claude)
- `wiki_carry_*` / `_source_fact_body_carry_for_step` imported by `case_runners.py` at 3-4 sites — a quiet home move breaks the checker harness unless re-exported/updated. (claude)
- `process_one_node` is referenced by `check_charter_injection.py` (project_ref seam) — lifting F needs that checker comment/expectation updated. (claude)
- No import cycle: new homes for `ResumeSeed` / `_runtime_handoff_unresolved_address` must NOT import `walker_resume`/`walker_kernel` back (`walker_resume` currently imports FROM `walker_kernel`). (both)
- Path-traversal / dot-segment / absolute / symlink-escape containment in runtime-handoff refs must keep failing-closed after the mail extraction (`:962/:1045`); HOLD-loud on unresolved ledger addresses (`:951/:1163`). (codex)
- Wiki carry must preserve PATH+NOTE-before-SUMMARY so tail truncation keeps the full-output address (`:837`). (codex)
- Serial vs parallel (`dispatch_pool_size>1`, ThreadPoolExecutor) must stay byte-identical (`case_runners.py:8651` asserts this) — a partial G split could diverge pool=1 vs pool=N. (both)
- Cohort replay is budget-free (`:3537`) — a helper extraction must not start consuming node budget. (codex)
- Every new module needs a `module_registry.yaml` row or `check_package_path_admission` RED. (both)

### claude-vs-codex disagreement
Essentially none — same cluster set, same "keep G, defer the loop, optionally lift F later" verdict. Minor: claude treats facade-vs-no-facade as a fully separable A1/A2 choice with both precedents; codex leans facade-first ("walker_kernel stays the compatibility facade"). Reconciled as the same human-owned sub-choice as the other targets. Module-name spellings differ cosmetically (claude `walker_carry.py` / `walker_resume_seed.py`; codex `walker_carry_context.py` / `walker_resume_state.py`) — non-substantive.

---

## 4. checker-diet — `building_skill_preset_agent_tool_hardening.yaml`

> Note: this target is a **checker-profile conservation** problem, not a Python god-module split. The "decomposition" is splitting a 97-label monolith profile into concern-coherent profiles.

### Recommendation
**Complete-the-split into concern-coherent profiles + thin/delete the original — NOT a facade.** Both designs agree decisively, for the same reason: **`check_profile.py` has NO `extends`/`include`/`inherit`/facade primitive** (grep-negative), so a facade profile cannot delegate assertions — it would have to physically retain all 97 case bodies, defeating the diet. The original is the SOLE home of 85 of its 97 labels and cannot be deleted until every label is re-homed exactly once or explicitly retired.

### Grounded citations (HEAD)
- Original `building_skill_preset_agent_tool_hardening.yaml` — claude: 97 case labels, lines `:257-4157`; codex: `wc` = **4170 lines / 194810 bytes**, label inventory starts `:256`, `rg` = **97 `label:` rows**. (agree)
- Three staged split copies (from B2a `checker-profile-diet-b2a-copy-stage-0625`), all admitted in `core.yaml` path_allowlist `:76-79`:
  - `building_skill_preset_builder_composition.yaml` — codex: 274 lines, **8 labels** (claude: 8, at `:48,86,135,148,161,175,216,249`).
  - `building_skill_preset_intake_adapter_gate.yaml` — codex: 131 lines, **4 labels** (claude: 4, at `:83,91,99,118`).
  - `building_skill_preset_agent_resource_boundary.yaml` — codex: 175 lines, **0 case labels** (claude: conserves the boundary-pin layer, not the 97 case labels).
- **Conservation today = 12/97** label rows preserved across the 3 splits; **85/97 carried ONLY by the original**. (agree)
- `check_profile.py --all` globs `profiles/*.yaml` (claude `:1340/:1059/:1119`; codex top-level key admission `:207-271`) → original + all 3 splits all run; the 12 preserved labels execute **twice** today.
- No include/facade primitive: claude grep-negative; codex `check_profile.py:207-271` admits only `BASE_TOP_LEVEL_KEYS + RULE_RUNNERS`, no taxonomy/facade key.
- `AGENTS.md:636` — prefer `check_profile.py` + profile YAML; avoid new standalone `check_*.py` unless separately admitted. (codex)

### Risk union
- A direct delete after only the 3 current splits **drops ~85 label rows** from active coverage. (both)
- 12 labels duplicated across original + splits can **DRIFT** if one copy is edited and the other is not — no equivalence check binds them today. (claude)
- Deleting the file while leaving its `core.yaml:76` allowlist entry → core RED; removing the allowlist entry while leaving the file → allowlist drift. They must change in the same slice. (both)
- Concern families with **no matching split name** would be orphaned: p5/p6 source-fact-carry & step-close, gate-sequence `c1-*`, hard-graph `c1-*`, declared/bad-step-template, multi-leader, governance-hint. They need an owner split (a 4th/5th profile) or an explicit "retained in residual shell" decision. (both; codex proposes concrete residuals: `route_and_carry`, `declared_step_template`, `agent_selection`, `completion_matrix`.)
- `agent_resource_boundary` carries 0 of the 97 labels → a naive "sum the splits = 12" understates its real (boundary-pin) conservation role. (claude)
- `preset_building_completion_case` is broad live/dogfood fixture coverage → may deserve its own heavy profile rather than mixing into quick/core lanes. (codex)
- **Non-label assertions** (`path_exists`, `path_absent`, `text_contains`, `json_required_paths`, `kernel_checks`, `proof_limits`, `not_proven`) also need conservation mapping — labels are not the whole inventory. (codex)
- Mechanical inventory must use the repo's **YAML subset loader** (`lib/yaml_subset.load_yaml_subset_file`), NOT PyYAML — PyYAML chokes on an unquoted colon-containing scalar near original `:3631`. (codex — important operational gotcha)
- A split passing green proves only ITS carried assertions, not the 85 it never copied → add a **mutation-RED probe per moved label** (B2b gate) so a silent green can't mask a dropped case. (both)

### Deletion gate (merged)
Original may be deleted ONLY when: (a) all 97 labels + non-label assertions resolve to exactly one non-original profile or are explicitly retired-with-reason; (b) `core.yaml:76` allowlist entry removed in the **same** change; (c) a mutation-RED probe passes for every moved label/assertion; (d) selector/status/`checker-profile-map.md` references to the old profile id are swept.

### claude-vs-codex disagreement
None on direction (both: split-and-thin, no facade, gated deletion). codex adds operational depth claude lacks: the **PyYAML-vs-yaml_subset loader** gotcha, **non-label assertion** conservation, concrete **residual profile names**, and the per-`--profile` verifier commands. claude adds the **drift risk on the 12 doubled labels** and the **agent_resource_boundary 0-label** nuance. Merged = union of both.

---

## Cross-target summary

| target | verdict | facade | new modules | the load-bearing risk |
|---|---|---|---|---|
| kernel_checks | split (re-derived) | facade-preserving (recommended) | ~9 flat `kernel_checks_*` + `kernel_common` | chat_session helpers `:7993-8726` non-contiguous from its `run_*` `:6511` → move by symbol |
| case_runners | split by surface | human sub-choice (lean remove) | ~5 flat `case_runners_*` + `_common` | 3 private helpers cross-imported by `kernel_checks`/`driver0` → land in common leaf |
| walker_kernel | staged leaf split, keep loop | facade-first ok | `walker_frontier_driver/carry/runtime_mail/resume/report_events` (+opt `node`) | `_run_dynamic_graph_walker` closures over ~30 locals → do NOT split G now |
| checker-diet | complete split + thin, NO facade | impossible (no include primitive) | residual concern profiles | 85/97 labels original-only; gated deletion + mutation-RED probe |
