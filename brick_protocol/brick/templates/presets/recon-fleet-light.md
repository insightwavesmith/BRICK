---
preset_ref: building-chain-preset:recon-fleet-light
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Lightweight read-only reconnaissance fleet with two survey lenses and fan-in closure synthesis.
selection_hint: Use when a read-only task has only two distinct attack surfaces (correctness + conformance) and the evidence-integrity lens is overkill — a cheaper recon than recon-fleet.
steps:
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick_protocol/brick/templates/bricks/inspect/brick.md
    target_word: parallel_recon
    casting_tier_ref: casting-tier:standard
    casting_lens_ref: casting-lens:review
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick_protocol/brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
    casting_tier_ref: casting-tier:standard
    casting_lens_ref: casting-lens:code-attack
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick_protocol/brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
    casting_tier_ref: casting-tier:light
    casting_lens_ref: casting-lens:axis-attack
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
    casting_tier_ref: casting-tier:standard
    casting_lens_ref: casting-lens:closure
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
node_reroute_budgets:
  building-step-template:inspect: 1
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:inspect
  verification_gap:
    action: hold
proof_limits:
  - read-only survey fleet only
  - two-lens fan-in closure synthesis is support evidence, not success or quality judgment
  - per-step tier/lens selection is a swappable launch knob, not a provider availability proof
  - preset is not runtime parallel execution
anti_hint: Do not use when evidence integrity is a separate risk or when more than two read-only attack surfaces exist.
blocks:
  - B1
  - B2
---

# recon-fleet-light

## Route

Lightweight read-only reconnaissance route: inspect the survey boundary, fan out a code-attack lens and an axis-attack lens, then fan in to closure synthesis. This is the two-lens (correctness + conformance) recon for narrow surfaces where the evidence-integrity lens is overkill; fan-in width is the cost knob, so dropping that third lens is the genuinely smaller config. The fleet declares graph shape only; the engine may still walk the declared graph sequentially. The tier/lens selections are declared per-step defaults, swappable at launch via step_selection_overrides, not a provider availability proof.
