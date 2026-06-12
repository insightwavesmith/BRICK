---
preset_ref: building-chain-preset:recon-fleet
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Read-only reconnaissance fleet with parallel survey lenses and fan-in closure synthesis.
selection_hint: Use when the task needs several read-only repository or evidence surveys before a closure synthesis.
steps:
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick/templates/bricks/inspect/brick.md
    target_word: parallel_recon
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:evidence-integrity
    brick_spec_ref: brick/templates/bricks/evidence-integrity/brick.md
    target_word: fan_in_final_gate
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
    selected_adapter_ref: adapter:codex-local
    selected_model_ref: model:default
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
  - fan-in closure synthesis is support evidence, not success or quality judgment
  - provider/model selection remains declared data, not provider availability proof
  - preset is not runtime parallel execution
---

# recon-fleet

## Route

Read-only reconnaissance route: inspect the survey boundary, fan out code, axis, and evidence-integrity survey lenses, then fan in to closure synthesis. The fleet declares graph shape only; the engine may still walk the declared graph sequentially.
