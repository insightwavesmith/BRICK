---
preset_ref: building-chain-preset:quick-check
catalog_scope: common
intent: Smallest read-only building, one assessment step then closure.
selection_hint: Use when one read-only look at a narrow target is enough before closing.
steps:
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
  - no write-need step exists on this route, so no caller write_scope is required
anti_hint: Do not use when the target is broad, requires source mutation, or needs more than one read-only assessment lens.
blocks:
  - B5
---

# quick-check

## Route

Smallest possible building: a single read-only review assesses the declared target against the task source, then closure records what was observed. The review step runs first, so its input is the task source itself rather than a prior Brick's report. No step carries write need anywhere on this route.
