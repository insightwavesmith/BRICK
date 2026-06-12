# postmortem-fleet preset + step_alias node identity (6-lens mixed-provider chain)

## Operator pre-analysis (VERIFIED — the design is PRESCRIBED; design step CONFIRMS, not explores)
Read ONLY these exact locations:
1. support/operator/composition.py — _materializer_graph_declaration: the node loop builds
   `kind_slug = _materializer_step_template_slug(step_template_ref)` then
   `node_id = f"{building_slug}-{kind_slug}"` (operator-verified ~line 1568-1570).
   CONSEQUENCE (verified): declaring the SAME step_template_ref twice in one preset
   yields DUPLICATE node_ids (silent collision today).
2. support/operator/plan_rendering.py — _chain_presets_from_presets (~965): preset
   frontmatter keys pass VERBATIM including steps[] rows (operator-verified), so a new
   optional row key flows through without loader changes.
3. brick/templates/presets/recon-fleet.md — the model preset to mirror.
4. support/checkers/lib/kernel_checks.py — the catalog/template checker family
   (brick_template_catalog_restructure) + structure-template-integrity profile wiring.
Do NOT survey other modules. Do NOT redesign the graph machinery.

## Objective (invariant)
A chain preset may declare the same step template on multiple rows IFF each such row
carries a distinguishing alias; node identity stays unique or materialization fails LOUD.

## Deliverables (prescribed design — implement exactly, justify only deviations)
1. OPTIONAL preset step row key `step_alias` (plain slug text):
   in _materializer_graph_declaration, `kind_slug = _composition_slug(step_alias)` when
   present, else the template slug (today's behavior). After the node loop, if any
   node_id appears twice -> raise loud ValueError naming the colliding rows (fail-closed
   replaces today's silent collision). Aliases affect node identity/labels ONLY;
   template/brick resolution stays by step_template_ref.
2. brick/templates/presets/postmortem-fleet.md — mirror recon-fleet frontmatter/gates:
   inspect(parallel_recon, codex) ->
   code-attack-qa x2 (step_alias: code-lens-codex / code-lens-claude;
     selected_adapter_ref adapter:codex-local / adapter:claude-local),
   axis-attack-qa x2 (axis-lens-codex / axis-lens-claude, same adapter split),
   evidence-integrity x2 (evidence-lens-codex / evidence-lens-claude, same split),
   all six target_word fan_in_final_gate -> closure(codex).
   gate_concept_profile strict-evidence + fan-in-wait-all; node_reroute_budgets
   inspect: 1; closure_transition_target_policy mirror recon-fleet; proof_limits mirror
   recon-fleet (+ mixed-provider lens note). Comply with the C1 repeat-lane rule the
   compliant presets follow.
3. Checker pins (extend existing families, no weakening):
   a. duplicate template WITHOUT step_alias (or colliding aliases) -> loud reject
      (fixture must observe the ValueError; mutation probe: collision check removed -> RED).
   b. postmortem-fleet materialize smoke: 8 distinct node_ids; per-node adapter refs
      show the codex/claude split (observed table in evidence).
   c. catalog checkers stay green with the new preset document.

## Proof required (run yourself, report honestly — claims only from execution)
- compileall + git diff --check.
- Materialize smoke: materialize_building_intent(chain_preset_ref=
  building-chain-preset:postmortem-fleet, 2-line inline statement, temp building_id)
  -> show node_id + adapter table (8 nodes). NO walk.
- Focused checker green + collision mutation RED (show both).
- Full gate in TEMP SOURCE COPY (bake first, --all exit 0, state copy path).

## Hard constraints (law)
- write_scope brick/templates/* + support/* ONLY; forbidden link/*, agent/*, project/*,
  brick/building.py, brick/building.yaml, brick/work.py, brick/work.yaml,
  brick/comparison.py, brick/comparison.yaml, .git/*, AGENTS.md, pyproject.toml, uv.lock.
- No pin weakening; append-only; no scheduler; no new deps; no packet echo; no npm/node.
