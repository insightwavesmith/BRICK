---
preset_ref: building-chain-preset:app-feature-inspected
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Plan, design, CTO assignment, DEV work, QA review, axis inspection, and closure for higher-risk product or app feature work.
selection_hint: Use when feature work touches shared contracts, evidence, policy, provider projections, public status, security, or authority boundaries.
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
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
---

# app-feature-inspected

## Route

The basic app-feature route with one extra axis-inspection step before closure. Use it when feature work touches shared contracts, evidence, policy, provider projections, public status, security, or authority boundaries.
