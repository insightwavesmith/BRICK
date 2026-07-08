---
preset_ref: building-chain-preset:review-fleet
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Tier/lens adversarial review fleet with fan-in closure synthesis.
selection_hint: Use when a completed design or implementation needs several read-only adversarial review lenses before closure synthesis.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick_protocol/brick/templates/bricks/design/brick.md
    target_word: parallel_review
    casting_tier_ref: casting-tier:plan
    casting_lens_ref: casting-lens:deep-design
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
  - step_template_ref: building-step-template:evidence-integrity
    brick_spec_ref: brick_protocol/brick/templates/bricks/evidence-integrity/brick.md
    target_word: fan_in_final_gate
    casting_tier_ref: casting-tier:light
    casting_lens_ref: casting-lens:evidence-integrity
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
    casting_tier_ref: casting-tier:standard
    casting_lens_ref: casting-lens:closure
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
node_reroute_budgets:
  building-step-template:design: 1
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:design
  verification_gap:
    action: hold
proof_limits:
  - adversarial review fleet only
  - review synthesis is support evidence, not success or quality judgment
  - declared review lenses use provider-neutral tier/lens refs resolved through providers.yaml; concrete selected_* literals remain available by launch-time override
  - preset is not runtime parallel execution
anti_hint: Do not use before a completed design or implementation exists, or when one read-only review lens is enough.
blocks:
  - B2
  - B4
---

# review-fleet

## Route

Tier/lens review route: design the review boundary, fan out code, axis, and evidence-integrity adversarial lenses, then fan in to closure synthesis. The tier/lens selections are declared per-step defaults, not provider availability proof.
