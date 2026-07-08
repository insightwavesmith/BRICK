---
preset_ref: building-chain-preset:docs-simple-review
catalog_scope: common
selected_shape_ref: building-shape:reviewable-work
intent: Plan, work, review, and closure for narrow documentation or status updates.
selection_hint: Use when no design Brick or CTO assignment is needed.
steps:
  - step_template_ref: building-step-template:plan
    brick_spec_ref: brick_protocol/brick/templates/bricks/plan/brick.md
    target_word: work
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick_protocol/brick/templates/bricks/work/brick.md
    target_word: review
  - step_template_ref: building-step-template:review
    brick_spec_ref: brick_protocol/brick/templates/bricks/review/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
proof_limits:
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
anti_hint: Do not use for constitutional, contract, customer-facing, or multi-area documentation that needs a human gate or fan review.
blocks:
  - B5
  - B2
---

# docs-simple-review

## Route

A short plan, work, review, closure route for narrow documentation or status updates where no design Brick or CTO assignment is needed.
