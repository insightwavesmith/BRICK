---
preset_ref: building-chain-preset:repair-loop
catalog_scope: common
selected_shape_ref: building-shape:repairable-work
intent: Task-first repair route that declares its replay target up front, attacks QA, and sends a failed implementation_gap back to the budgeted work Brick for a bounded repair loop instead of an immediate hold.
selection_hint: Use when task.md is a clear repair and you want a failed QA to drive a bounded, pre-declared loop back to work rather than holding.
steps:
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: code_attack_qa
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
node_reroute_budgets:
  building-step-template:work: 5
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:work
  verification_gap:
    action: hold
proof_limits:
  - task source is pre-run input evidence, not an automatic plan selector
  - chain preset is a caller / COO selection candidate only
  - reroute target and budget are declared inputs; the engine, not the preset, executes the bounded replay
  - not automatic shape selection
  - not Building Plan authoring from task text
---

# repair-loop

## Route

Task-first repair route that declares its replay target up front: direct work, code-attack QA, then closure whose closure_transition_target_policy sends an implementation_gap back to the budgeted work Brick under its node_reroute_budget for a bounded repair loop, while a verification_gap holds. Use it when the task is a clear repair and you want a failed QA to drive a declared, budgeted loop back to work instead of an immediate hold.
