# BRICK 6-Surface Architecture Audit - S1 Brick Axis - 2026-06-30

## Surface

- Surface: Brick axis.
- Target checkout: `/Users/smith/projects/BRICK`.
- Commit: `17eaade696998cd0de7bbd85ceb7525f349588e9`.
- Mode: audit only. No source repair was performed.
- Verdict: `ISSUE`.

## Map

Brick owns work contracts, Building Plan composition, Brick templates, required return shapes, comparison facts, write NEED interpretation, and declared work authoring vocabulary.

Primary Brick-owned surfaces inspected:

- `brick/work.py`
- `brick/building.py`
- `brick/comparison.py`
- `brick/spec.py`
- `brick/templates/bricks/*/brick.md`
- `brick/templates/bricks/*/return.yaml`
- `brick/templates/shapes/catalog.yaml`
- `brick/templates/shapes/shapes.yaml`
- `brick/templates/presets/*.md`
- `brick/building_plans/*.yaml`

Observed Brick flow:

1. A caller/COO declares task, preset, graph, or node kind.
2. Support loads `brick/templates/shapes/catalog.yaml`.
3. Step templates are materialized from `brick/templates/bricks/<kind>/brick.md`.
4. Primary return shape and carry fields are read from `brick/templates/bricks/<kind>/return.yaml`.
5. Support emits a declared Building Plan row and then walks that road.

Support surfaces inspected as consumers, not source truth:

- `support/operator/plan_rendering.py`
- `support/operator/composition_compose.py`
- `support/operator/composition_graph_emit.py`
- `support/operator/driver.py`
- `support/operator/assembly.py`
- `support/operator/run.py`
- `support/checkers/check_assembly_equivalence.py`
- `support/checkers/check_building_operator_driver0.py`
- `support/checkers/lib/kernel_checks.py`

## Evidence

Parallel attack review used 9 lanes:

- `S1-map`
- `S1-godmodule`
- `S1-dup-dead`
- `S1-axis-leak`
- `S1-contract`
- `S1-runtime`
- `S1-checker`
- `S1-simplicity`
- `S1-adversarial`

Codex operator direct checks:

- `git rev-parse HEAD`
- `git status --branch --short --untracked-files=no`
- `find brick/templates/presets -maxdepth 1 -type f -name '*.md' | wc -l`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_skill_preset_builder_composition`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_skill_preset_agent_tool_hardening`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile building_skill_preset_intake_adapter_gate`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile assembly_equivalence`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile structure_template_integrity`
- `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=support/import_identity:. python3 support/checkers/check_profile.py --profile brick_cli_entrypoint`
- Targeted repros of customer graph fan-in source `required_return_shape` override.
- Targeted repro of `assembly.build([... fan([...]), closure])` fan-in source shape lowering.

Direct green evidence:

- `building_skill_preset_builder_composition` passed.
- `building_skill_preset_agent_tool_hardening` passed.
- `building_skill_preset_intake_adapter_gate` passed.
- `assembly_equivalence` passed.
- `structure_template_integrity` passed.
- `brick_cli_entrypoint` passed.
- Active `support/operator` code has no live `--large` or `_p3_easy_large` route. The remaining `--large` references are negative guards.
- All 10 active Brick kind folders have resolvable `brick.md` frontmatter and primary `return.yaml` files.

Proof limit: checker green is support evidence only. It does not prove source truth, provider behavior, quality, success, Movement authority, semantic fitness of future presets, or complete future coverage.

## Findings

### S1-F1 - Fan-in source return shape can still be shrunk outside the template truth path

- Severity: high.
- Axis attribution: Brick return contract, with Link carry/filter concern and support graph admission.
- Evidence:
  - `driver.py:82-89` marks `required_return_shape` as a customer graph template-authority field.
  - `driver.py:220-237` creates a narrow exception for fan-in source nodes and skips rejection of `required_return_shape`.
  - `composition_compose.py:853-919` lets an author-supplied `required_return_shape` override the template default.
  - Direct repro result: `override_filter=ACCEPTED`, `compose=ACCEPTED`, and `qa1_required_return_shape=observed_evidence, not_proven`.
  - The same repro kept the other QA source on its template-derived full shape, proving mixed behavior in one fan-in graph.
  - `code-attack-qa/return.yaml:7-17` declares the full return shape including `transition_concern_evidence`.
- Meaning: the broad claim "Brick return shape always comes from `return.yaml`" is false for this accepted path. The design intent appears to be "QA fan-in sources should not expose Link-facing concern fields before closure", but the mechanism shrinks the Brick return contract instead of preserving full return and filtering carry at Link/closure handoff.
- Proof status: confirmed by code inspection and direct repro.

### S1-F2 - `assembly.py` easy graph path deliberately strips `transition_concern_evidence` from fan-in source shapes

- Severity: high.
- Axis attribution: support authoring sugar crossing Brick return shape and Link carry semantics.
- Evidence:
  - `assembly.py:447-468` derives fan branch returns from the template shape and strips `transition_concern_evidence`.
  - `assembly.py:1103-1112` lowers fan-in source nodes with the stripped shape.
  - `assembly.py:1229-1232` rejects fan-in source shapes that still carry `transition_concern_evidence`.
  - `check_building_operator_driver0.py:837-856` pins the expectation that fluent fan-in sources omit `transition_concern_evidence`.
  - `check_assembly_equivalence.py:1863-1869` fails if fan-in source return shapes still carry `transition_concern_evidence`.
  - Direct repro of `assemble(build([fan([code-attack-qa, axis-attack-qa]), closure]))` produced QA source shapes without `transition_concern_evidence`.
- Meaning: current green checkers preserve the older shrink-return behavior. That is not a runtime engine bug; it is a Brick/Link boundary design issue pinned by support checkers.
- Proof status: confirmed by code inspection, direct repro, and checker source.

### S1-F3 - Brick templates and presets carry live Agent and Link selection metadata

- Severity: medium-high.
- Axis attribution: Brick template origin, Agent/Link selection metadata, support materialization.
- Evidence:
  - Brick kind frontmatter carries `performer_lane_need`, `agent_object_hint_ref`, and `link_movement_literal`.
  - `plan_rendering.py:1055-1084` resolves Agent and Link metadata from those template rows.
  - `composition_graph_emit.py` materializes preset gate/adoption policy from preset frontmatter.
  - `four-llm-standard-graph.md:12-31` declares Codex/Gemini/Codex adapter choices.
  - `four-llm-standard-graph.md:82-88` correctly marks this as proof-limited declared routing data.
- Meaning: this may be admitted metadata rather than an immediate violation, but it is not a clean Brick-only surface. Future repair should clarify which metadata is Brick NEED, Agent selection hint, and Link row declaration.
- Proof status: confirmed co-location. Hidden Movement chooser, success judge, or quality judge not proven.

### S1-F4 - Brick-side skills contain role/provider/verdict wording that contradicts axis boundaries

- Severity: medium-high.
- Axis attribution: Brick projection/authoring text leaking Agent and Link authority language.
- Evidence:
  - `building-sizing-method/SKILL.md:21-29` says KIND brings the Agent and role/provider/write/verdict are automatically determined.
  - `brick-task-author/SKILL.md:254-258` uses weekend adapter defaults and "verdict-bearing" language for design/closure/review/inspect.
  - `make-an-agent` and `make-a-gate` skills live under `brick/templates/skills/` while describing Agent and Link resource creation.
- Meaning: these may be useful operator recipes, but under Brick templates they can teach future operators that Brick kind owns provider, Agent role, or verdict authority.
- Proof status: confirmed text/projection issue. Runtime break not proven.

### S1-F5 - `brick/spec.py` is a Brick-axis godmodule candidate and imports Agent private casting helpers

- Severity: medium.
- Axis attribution: Brick authoring API with Agent coupling.
- Evidence:
  - `brick/spec.py:9-31` lists several responsibilities: Brick row keys, write scope, derived worktree scope, write NEED, and authoring.
  - `brick/spec.py:66-74` imports `_CASTING_KWARG_BY_NAME` and `_build_casting_bag` from `agent/spec.py`.
  - Claude review C1 corrected this locator: `brick/spec.py:522-576`
    covers the intro comment, `def brick(` at line 569, and the AgentSpec
    parameter at line 576.
- Meaning: no runtime cycle or authority leak is proven, but the module is now a public import magnet with Brick schema, write policy, return completeness, and Agent casting concerns.
- Proof status: confirmed godmodule/coupling candidate. Safe split not proven.

### S1-F6 - Active Brick template docs and fixtures contain stale or confusing projections

- Severity: medium.
- Axis attribution: Brick docs/status/support fixture drift.
- Evidence:
  - Live preset count is 28, but `brick/templates/README.md:11` says 17 chain presets.
  - `support/docs/references/checker-profile-map.md:19` and `project/brick-protocol/status/kernel/p9-b1-six-family-module-map-reference-0625.md:24` say 28 presets.
  - Retired old physical template directories are still package-admitted in `check_package_path_admission.py`.
  - GOAL graph packets under `project/brick-protocol/status/kernel/GOAL/` contain non-catalog `selected_shape_ref` values, while current compose intentionally treats `selected_shape_ref` as an optional tag.
  - Claude review C19 quantified this drift: 8 of 10 distinct GOAL
    `selected_shape_ref` values are non-catalog; only `design-needed` and
    `reviewable-work` are catalog shapes.
  - `development` Brick exists as CTO assignment, but no active preset uses `step_template_ref: building-step-template:development`; some preset prose still says CTO assignment.
- Meaning: most of this is projection/status drift rather than runtime failure, but it weakens the customer-ready authoring surface.
- Proof status: confirmed drift. Runtime break not proven.

### S1-F7 - `brick/comparison.py` mixes write-scope path comparison and Agent-return contract comparison

- Severity: low-medium.
- Axis attribution: Brick comparison domain.
- Evidence:
  - `brick/comparison.py:34-89` compares changed paths to write scope.
  - `brick/comparison.py:92-140` defines `BrickComparisonFact` for required-return and comparison evidence.
  - `_OBSERVED_MATCH_KINDS` uses `matched/missing/mismatched/unknown`.
- Meaning: still Brick-owned comparison evidence, not success/quality judgment. The risk is readability and future overclaiming, not an observed authority leak.
- Proof status: confirmed mixed measurement domain. Success/quality leak not proven.

## External Review Incorporation

Claude review and Smith/operator follow-up sharpened S1 in five ways.

1. Return-shape truth remains the S1 center of gravity.
   - Existing S1-F1/S1-F2 already proved the fan-in source shrink path.
   - Claude ADD-4 adds that `brick/work.py::parse_required_return_shape` was
     in scope but not inspected. It tokenizes differently from support
     materializer stripping: comma/slash split, dash normalization, and JSON-like
     shape rejection in Brick versus narrower comma/token matching in support.
   - Claude ADD-16 adds that `assembly.py`'s fan-in guard uses a substring
     style check that the codebase's own composition helper warns can
     false-match superstrings.
   - Final S1 rule: template `return.yaml` is the Brick contract; any fan-in
     filtering must be Link carry / closure synthesis policy, not Brick
     return-shape shrink.

2. Fan-in classification itself needs a negative probe.
   - Claude ADD-6 notes that `_customer_graph_fan_in_source_node_ids` is the
     switch that decides whether a graph node can use the fan-in
     `required_return_shape` exception.
   - Malformed or misclassified fan groups can therefore become a Brick/Support
     authority seam: an intended fan-in source may lose the exception, while a
     misclassified source may gain it.
   - This remains a coverage gap, not a proven exploit.

3. Brick-owned parser and BuildingWork edges need coverage.
   - Claude ADD-17 notes that `brick/building.py` was named in scope but its
     empty-fact / non-text error paths were not inspected.
   - This should be folded into the S1 checker set when return-shape repair is
     declared.

4. GOAL/status drift is broader than first stated.
   - C19 strengthens S1-F6: the non-catalog shape drift is the bulk of current
     GOAL shape refs, not a few edge cases.
   - This does not mean GOAL evidence is invalid; it means old materialized
     graph/status records must remain historical/support evidence unless
     regenerated or explicitly admitted.

5. Smith's correction on P3 is binding for S1 repair direction.
   - Do not revive `--large`.
   - Do not hand-author `required_return_shape` or return-field shrinkage in
     operator graph packets.
   - Easy Building belongs in a declaration layer over the official route, with
     Brick template refs and `return.yaml` materialization preserved.

## Rejected Shortcuts

- "This is an engine bug" was rejected. The confirmed return-shape issue originates in Brick return contract handling and Link carry/filter design, then is materialized by support.
- "Checker green closes S1" was rejected. Relevant profiles passed while also pinning the fan-in source shape shrink.
- "`--large` is still the active P3 problem" was rejected. Active operator code no longer exposes `--large`; remaining hits are negative guards.
- "Support invented all return shapes" was rejected. The normal materializer path derives return shapes from `return.yaml`; the issue is a fan-in source exception and assembly sugar path.
- "Brick presets are Movement authority" was rejected. Presets carry declared/proof-limited Link row data, but hidden Link Movement choice was not proven.
- "Delete development Brick" was rejected. It is unused by active presets, but manual graph/caller declaration use remains not proven.

## Verdict

`ISSUE`.

The Brick axis core is strong enough to map and run: the split catalog exists, active Brick kind templates resolve, primary `return.yaml` files materialize normal return shapes, write NEED admission is strict, and the retired `--large` path is guarded as negative. The surface is not clear because fan-in source paths can still shrink Brick return contracts, the easy assembly path and checkers pin that behavior, Brick templates/presets co-locate Agent/Link/provider metadata, Brick-side skills carry verdict/provider language, and several docs/status fixtures are stale.

Readiness tuple: use `brick-6-surface-audit-readiness-tuples-0630.md` for implementation priority. S1 is `core_sound: partial`, `axis_integrity_blockers: 4`, `ship_safety_blockers: 1`, `dynamic_runtime_not_proven: yes`, and `worst_severity: high`. The flat `ISSUE` label is only a findings-inventory label.

## Next Work Candidates

1. Checker-first repair: preserve full Brick `return.yaml` shape for fan-in source Bricks, and move field reduction to Link carry / closure synthesis filtering.
2. Update `assembly.py` and the pinned checkers so they no longer require fan-in source Brick return shapes to drop `transition_concern_evidence`.
3. Add a customer graph negative probe proving fan-in source `required_return_shape` injection is rejected or materialized back to the template full shape.
4. Add return-shape tokenizer equivalence coverage between `brick/work.py`,
   support materialization, and assembly guards.
5. Add fan-in classification negative probes for malformed groups and
   misclassified fan-in sources.
6. Clarify Brick template frontmatter into Brick NEED, Agent hint, and Link row declaration fields without implying Brick owns Agent identity or Link Movement.
7. Move or mark `brick/templates/skills/*` as operator projection/recipe rather than Brick-axis contract truth, especially skills that create Agent/Link resources.
8. Refresh stale Brick template docs and status counts after repair.
9. Treat `brick/spec.py` decomposition as later cleanup only, with facade-preserving split and checker conservation.

## Not Proven

- Semantic fitness of any future preset or selected shape.
- Provider behavior or model quality.
- Runtime correctness of every customer graph.
- Safe deletion of old template fixture paths or unused Brick kinds.
- Complete absence of future support-authority leaks.
- Whether Brick/Agent/Link metadata co-location should be split physically or only renamed and guarded.
