---
preset_ref: building-chain-preset:review-fleet
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Mixed-provider adversarial review fleet with fan-in closure synthesis.
selection_hint: Use when a completed design or implementation needs several read-only adversarial review lenses before closure synthesis.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick/templates/bricks/design/brick.md
    target_word: parallel_review
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
    selected_model_ref: model:claude:sonnet
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:evidence-integrity
    brick_spec_ref: brick/templates/bricks/evidence-integrity/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
    selected_adapter_ref: adapter:codex-local
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
  - one declared review lens may use adapter:claude-local under provider policy
  - preset is not runtime parallel execution
---

# review-fleet

## Route

Mixed-provider review route: design the review boundary, fan out code, axis, and evidence-integrity adversarial lenses, then fan in to closure synthesis. The Claude lens is a declared per-step provider/model selection example, not a provider availability proof.
