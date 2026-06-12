# D: Provider ladder + fleet presets — per-step LLM selection and mixed-provider fleets

## Objective
Open the BUILDER-side path for per-step provider/model selection (the ENGINE already honors step-level selected_adapter_ref/selected_model_ref — plan_validation.py:156-163 falls back step->plan; verified) and add fleet presets so recon/review fan-outs run as buildings with mixed lanes.

## Deliverables
1. **Intake/preset per-step declaration**: a preset step entry (and/or intent override keyed by step_template_ref) may declare selected_adapter_ref and selected_model_ref; the materializer (support/operator/composition.py — today it stamps ONE building-wide adapter, ~line 280) stamps them per-step. Building-wide value stays the default for undeclared steps. Capability law unchanged: a step's lane must declare that adapter in its agent object adapter_refs (the existing loud reject — keep it biting; add a FIRE case for a per-step adapter the lane does not declare).
2. **Lane preference (optional tier)**: agent objects may declare ONE preferred_adapter_ref (agent/objects/*.yaml — additive key); resolution ladder: step declaration > lane preference > building default. Validate preference is within the lane's declared adapter_refs (loud reject otherwise). Update the projection checkers if they pin the agent yaml closed key set.
3. **Fleet presets** (brick/templates/presets/): 'recon-fleet' — fan-out N read-only survey steps (reviewer/inspector lanes, read tier) -> fan-in synthesis step -> closure; 'review-fleet' — fan-out adversarial review lenses -> fan-in verdict synthesis -> closure. Both graph-shaped with gate profiles consistent with house compliant presets (fan-in-wait-all + strict-evidence; reroute lanes per C1 rule: any preset declaring inspection gates must declare repeat lanes — follow the 4 compliant presets' shape). Default lanes codex; one lens MAY be claude-local per the provider policy (declare it in the preset as the example of per-step selection).
4. **Pins + FIRE**: per-step adapter stamped into the declared plan (mutated materializer ignoring step declaration -> RED); undeclared-capability per-step adapter -> loud reject; preference outside adapter_refs -> reject; fleet presets pass the catalog/restructure checkers; C1 rule holds for the new presets.
5. Full gate -> exit 0 (say which checkout/copy).

## Constraints
Write scope: support/*, brick/templates/*, brick/building_plans/*, agent/objects/* (additive key only). No link/ edits; no new Link vocabulary; no scheduler. Engine walk order unchanged (sequential walking accepted; no parallel runtime). No pin weakening. Provider policy context: builds default codex; claude reserved for at most one review lens.
