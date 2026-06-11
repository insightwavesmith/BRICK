---
preset_ref: building-chain-preset:fast-fix
catalog_scope: common
selected_shape_ref: building-shape:reviewable-work
intent: Task-first narrow implementation or documentation repair with direct work, attack QA, and closure.
selection_hint: Use when task.md is clear and no design, portfolio split, or admission-risk shaping is needed.
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
proof_limits:
  - task source is pre-run input evidence, not an automatic plan selector
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
---

# fast-fix

## Route

Task-first narrow route: direct work, code-attack QA, then closure. Use it when the task is clear and no design, portfolio split, or admission-risk shaping is needed.
