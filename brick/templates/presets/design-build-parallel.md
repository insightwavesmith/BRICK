---
preset_ref: building-chain-preset:design-build-parallel
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Task-first design, implementation, parallel code/axis QA, and closure.
selection_hint: Use when task.md is clear but implementation needs design before work and parallel attack review after work.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick/templates/bricks/design/brick.md
    target_word: work
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: parallel_qa
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
gate_concept_profile:
  - default-transition
  - strict-evidence
  - fan-in-wait-all
node_reroute_budgets:
  building-step-template:design: 1
  building-step-template:work: 1
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:work
  verification_gap:
    action: hold
proof_limits:
  - parallel/fan-in semantics require an explicit Building Plan graph
  - preset does not create fan-out or target selection by itself
  - model review is support evidence only
---

# design-build-parallel

## Route

Task-first design, then implementation, then parallel code-attack and axis-attack QA that fan in to a final gate before closure. Use it when the task is clear but implementation needs design before work and parallel attack review after work.
