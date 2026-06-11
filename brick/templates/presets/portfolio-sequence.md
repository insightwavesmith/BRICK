---
preset_ref: building-chain-preset:portfolio-sequence
catalog_scope: common
selected_shape_ref: building-shape:parent-goal
intent: Multiple declared Buildings or work boundaries are walked under a finite declared portfolio policy.
selection_hint: Use only when finite child Building refs and portfolio policy are already declared by caller / COO.
steps:
  - step_template_ref: building-step-template:plan
    brick_spec_ref: brick/templates/bricks/plan/brick.md
    target_word: child_building_runs
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: portfolio_closure
gate_concept_profile:
  - portfolio-policy
  - coo-review
  - human-review
proof_limits:
  - portfolio walker consumes declared Building refs only
  - portfolio walker does not invent Buildings, choose Movement, judge success, or rewrite child evidence
  - bare default-transition must not select among multiple candidates
---

# portfolio-sequence

## Route

Walk multiple declared Buildings or work boundaries under a finite declared portfolio policy: a plan step over the declared child Building runs, then portfolio closure. Use it only when finite child Building refs and portfolio policy are already declared.
