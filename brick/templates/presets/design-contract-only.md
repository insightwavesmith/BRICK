---
preset_ref: building-chain-preset:design-contract-only
catalog_scope: common
intent: Produce a design contract and have it checked, with no implementation step.
selection_hint: Use when only the design boundaries are wanted now and implementation is a later building.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick/templates/bricks/design/brick.md
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
  - design output stays a proposal; nothing is implemented or admitted from this route
anti_hint: Do not use when source mutation is required in the same Building or when the design question is already settled.
blocks:
  - B3
---

# design-contract-only

## Route

Design-only route: design turns the task into proposed architecture, data, or protocol boundaries, review checks that design contract against the declared work and return shape, closure records the reviewed contract and the open implementation delta. No work step exists, so nothing is implemented and no caller write_scope is required.
