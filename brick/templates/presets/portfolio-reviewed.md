---
preset_ref: building-chain-preset:portfolio-reviewed
catalog_scope: common
selected_shape_ref: building-shape:parent-goal
intent: Multiple declared Buildings or work boundaries are walked under a finite declared portfolio policy, with a read-only review that cross-checks the aggregated child returns before portfolio closure.
selection_hint: Use only when finite child Building refs and portfolio policy are already declared by caller / COO, AND a roll-up cross-check of the child returns is wanted before parent closure.
steps:
  - step_template_ref: building-step-template:plan
    brick_spec_ref: brick/templates/bricks/plan/brick.md
    target_word: child_building_runs
  - step_template_ref: building-step-template:review
    brick_spec_ref: brick/templates/bricks/review/brick.md
    target_word: portfolio_closure
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
  - review reads and cross-checks the declared child returns only; it observes and reports, never mutates child evidence or judges success
  - bare default-transition must not select among multiple candidates
anti_hint: Do not use when finite child Building refs are missing or when no roll-up cross-check of child returns is wanted.
blocks:
  - B5
  - B2
---

# portfolio-reviewed

## Route

Walk multiple declared Buildings or work boundaries under a finite declared portfolio policy, then roll them up with a read-only review before closing: a plan step over the declared child Building runs, a review step that reads and cross-checks the aggregated child returns, then portfolio closure that records the portfolio delta. Use it only when finite child Building refs and portfolio policy are already declared and a final cross-check of the child deltas is wanted before declaring the parent done. The review is read-only (it observes and reports, never mutates), so it stays within portfolio policy without a write scope or a reroute budget. Per-step provider/model is a swappable launch-time knob (step_selection_overrides), not part of this shape: the weekend recommended defaults are codex-local for the plan and closure work and gemini-local for the review lens; claude-local remains an override option when available.
