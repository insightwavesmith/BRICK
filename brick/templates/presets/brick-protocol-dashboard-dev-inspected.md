---
preset_ref: building-chain-preset:brick-protocol-dashboard-dev-inspected
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:app-feature-inspected
selected_shape_ref: building-shape:design-needed
intent: Brick Protocol higher-risk dashboard path with axis inspection before closure.
selection_hint: Use when Brick Protocol dashboard work touches protocol surfaces, evidence, Link gates, provider projections, or public status.
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
    target_word: inspect
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick/templates/bricks/inspect/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
proof_limits:
  - this is a Brick Protocol dogfood variant over common templates
  - not automatic shape selection
  - not Building Plan authoring from task text
anti_hint: Do not use when dashboard work does not touch protocol surfaces, evidence, Link gates, projections, or public status.
blocks:
  - B3
  - B2
  - B6
---

# brick-protocol-dashboard-dev-inspected

## Route

Brick Protocol dogfood variant of the inspected app-feature route for higher-risk dashboard work that touches protocol surfaces, evidence, Link gates, provider projections, or public status; it adds an axis-inspection step before closure.
