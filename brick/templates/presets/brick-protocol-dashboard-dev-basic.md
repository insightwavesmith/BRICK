---
preset_ref: building-chain-preset:brick-protocol-dashboard-dev-basic
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:app-feature-basic
selected_shape_ref: building-shape:design-needed
intent: Brick Protocol dashboard feature path with plan, design, CTO assignment, DEV work, QA review, and closure.
selection_hint: Use when Brick Protocol asks for a dashboard or app feature that needs design and implementation.
steps:
  - step_template_ref: building-step-template:plan
    brick_spec_ref: brick/templates/bricks/plan/brick.md
    target_word: design
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick/templates/bricks/design/brick.md
    target_word: work
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: review
  - step_template_ref: building-step-template:review
    brick_spec_ref: brick/templates/bricks/review/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
proof_limits:
  - this is a Brick Protocol dogfood variant over common templates
  - not automatic shape selection
  - not Building Plan authoring from task text
anti_hint: Do not use when the dashboard request is a narrow copy or style repair that needs no design lane or implementation sequence.
blocks:
  - B3
  - B5
---

# brick-protocol-dashboard-dev-basic

## Route

Brick Protocol dogfood variant of the basic app-feature route for dashboard work: plan, design, CTO assignment, DEV work, QA review, and closure.
