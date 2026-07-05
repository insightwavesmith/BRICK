---
preset_ref: building-chain-preset:brick-protocol-portfolio-driver
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:portfolio-sequence
selected_shape_ref: building-shape:parent-goal
intent: Brick Protocol declared multi-Building portfolio driver path under declared Link/portfolio policy.
selection_hint: Use only when finite Brick Protocol child Building refs and portfolio policy are already declared by caller / COO.
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
  - this is a Brick Protocol dogfood variant over common templates
  - portfolio driver walks declared Building refs only
  - portfolio driver does not invent Buildings, choose Movement, judge success, or rewrite child evidence
  - bare default-transition must not select among multiple candidates
anti_hint: Do not use when child Building refs or portfolio policy are not already declared by caller or COO.
blocks:
  - B5
  - B6
---

# brick-protocol-portfolio-driver

## Route

Brick Protocol dogfood variant of the portfolio route: a plan step that walks declared child Building refs and a closure step, under a declared portfolio policy. Use it only when finite child Building refs and portfolio policy are already declared.
