---
preset_ref: building-chain-preset:one-brick-do
catalog_scope: common
selected_shape_ref: building-shape:one-brick
intent: Smallest WRITE building, one work step then closure.
selection_hint: Use when one implementation step is enough and no QA, design, or portfolio shaping is needed.
steps:
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
proof_limits:
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
  - the work step carries write need, so the caller must declare write_scope
anti_hint: Do not use when QA, design, portfolio shaping, human review, or multi-file risk needs a separate Brick boundary.
blocks:
  - B5
---

# one-brick-do

## Route

Smallest possible WRITE building: a single work Brick performs the declared implementation inside its write scope and returns the requested artifact, then closure records the parent delta. The work step runs first, so its input is the task source itself rather than a prior Brick's report. The work step carries write need, so the route materializes only when the caller declares write_scope; closure writes no files. The write-side sibling of quick-check.
