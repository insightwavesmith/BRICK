---
preset_ref: building-chain-preset:postmortem-fleet
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Tier/lens postmortem fleet with code-attack plus axis/evidence attack lenses and fan-in closure synthesis.
selection_hint: Use when a completed incident, repair wave, or decision chain needs code-attack plus axis/evidence postmortem lenses before closure synthesis.
steps:
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick/templates/bricks/inspect/brick.md
    target_word: parallel_recon
    casting_tier_ref: casting-tier:standard
    casting_lens_ref: casting-lens:review
  - step_template_ref: building-step-template:code-attack-qa
    step_alias: code-attack-lens
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
    casting_tier_ref: casting-tier:standard
    casting_lens_ref: casting-lens:code-attack
  - step_template_ref: building-step-template:axis-attack-qa
    step_alias: axis-attack-lens
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
    casting_tier_ref: casting-tier:light
    casting_lens_ref: casting-lens:axis-attack
  - step_template_ref: building-step-template:evidence-integrity
    step_alias: evidence-integrity-lens
    brick_spec_ref: brick/templates/bricks/evidence-integrity/brick.md
    target_word: fan_in_final_gate
    casting_tier_ref: casting-tier:light
    casting_lens_ref: casting-lens:evidence-integrity
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
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
  - read-only postmortem fleet only
  - fan-in closure synthesis is support evidence, not success or quality judgment
  - tier/lens code-attack plus axis/evidence attack casting is declared routing data, not provider availability proof
  - preset is not runtime parallel execution
anti_hint: Do not use for active implementation or when the incident evidence is too small for multiple postmortem lenses.
blocks:
  - B2
  - B4
  - B8
---

# postmortem-fleet

## Route

Tier/lens postmortem route: inspect the postmortem boundary, fan out one code-attack lens plus axis and evidence-integrity lenses, then fan in to closure synthesis. The fleet declares graph shape only; the engine may still walk the declared graph sequentially.
