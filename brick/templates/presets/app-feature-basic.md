---
preset_ref: building-chain-preset:app-feature-basic
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Plan, design, CTO assignment, DEV work, QA review, and closure for a product or app feature.
selection_hint: Use when the task asks for an app, dashboard, website, product, or user-facing feature that needs design and implementation.
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
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
anti_hint: Do not use when the app change is a one-file cosmetic fix with no design decision or QA-relevant behavior change.
blocks:
  - B3
  - B5
---

# app-feature-basic

## Route

Plan first, then design, then a CTO assignment, DEV work, a QA review, and closure. Use this linear route when a user-facing feature needs design before implementation but carries no shared-contract or high-blast-radius risk.
