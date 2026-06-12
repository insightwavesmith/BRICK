# D (attempt 2): Provider ladder + fleet presets — per-step LLM selection and mixed-provider fleets

PRIOR ATTEMPT NOTE (provider-ladder-fleet-presets-0612, voided): the work step ran the FULL
checker gate INSIDE the working tree; the notification auto-wiring rang during checker fixture
runs and wrote a bell packet into the tree's project/status/inbox — the write observation voided
the step (F12, queued separately). THIS attempt: run check_profile.py --all ONLY in a TEMP SOURCE
COPY outside the repo (the established pattern; say which copy). Never execute the full gate in
the working tree. Focused single-profile runs in-tree are fine IF they write nothing.

## Objective
Open the BUILDER-side path for per-step provider/model selection (the ENGINE already honors
step-level selected_adapter_ref/selected_model_ref — plan_validation.py:156-163 falls back
step->plan; verified) and add fleet presets so recon/review fan-outs run as buildings with mixed
lanes.

## Deliverables
1. Intake/preset per-step declaration: a preset step entry (and/or intent override keyed by
step_template_ref) may declare selected_adapter_ref and selected_model_ref; the materializer
(support/operator/composition.py — today stamps ONE building-wide adapter, ~line 280) stamps
them per-step. Building-wide value stays default for undeclared steps. Capability law unchanged:
a step's lane must declare that adapter in its agent object adapter_refs (keep the loud reject;
add a FIRE case for a per-step adapter the lane does not declare).
2. Lane preference (optional): agent objects may declare ONE preferred_adapter_ref
(agent/objects/*.yaml — additive key); ladder: step declaration > lane preference > building
default. Preference must be within the lane's adapter_refs (loud reject otherwise). Update
projection checkers if they pin the agent yaml key set.
3. Fleet presets (brick/templates/presets/): 'recon-fleet' — fan-out N read-only survey steps
(reviewer/inspector lanes, read tier) -> fan-in synthesis -> closure; 'review-fleet' — fan-out
adversarial review lenses -> fan-in verdict synthesis -> closure. Graph-shaped, gate profiles
matching the compliant presets (fan-in-wait-all + strict-evidence; C1 rule: inspection gates =>
declared repeat lanes). Default lanes codex; ONE lens in review-fleet declares
adapter:claude-local per-step as the ladder example (provider policy: claude = review lens only).
4. Pins + FIRE: per-step adapter stamped into declared plan (mutated materializer ignoring step
declaration -> RED); undeclared-capability per-step adapter -> loud reject; preference outside
adapter_refs -> reject; fleet presets pass catalog checkers; C1 rule holds.
5. Full gate in TEMP COPY -> exit 0.

## Constraints
Write scope: support/*, brick/templates/*, brick/building_plans/*, agent/objects/* (additive key
only). No link/ edits; no new Link vocabulary; no scheduler. Sequential walking accepted. No pin
weakening. Plain-text refs only in returns (no packet echo).
