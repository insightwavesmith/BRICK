---
preset_ref: building-chain-preset:brick-protocol-post-d-cleanup
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:high-risk-change-inspected
selected_shape_ref: building-shape:parent-goal
intent: Brick Protocol post-D surface recompilation and cleanup with parallel cleanup lanes, fan-in final gate, and strict closure.
selection_hint: Use before Brick Protocol E surfaces such as reporter, notification, dashboard expansion, fine-tuning data, or multi-human gate.
steps:
  - step_template_ref: building-step-template:inspect
    brick_spec_ref: brick_protocol/brick/templates/bricks/inspect/brick.md
    target_word: parallel_cleanup_lanes
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick_protocol/brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:evidence-integrity
    brick_spec_ref: brick_protocol/brick/templates/bricks/evidence-integrity/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
  - coo-review
node_reroute_budgets:
  building-step-template:inspect: 1
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:inspect
  verification_gap:
    action: hold
proof_limits:
  - this is a Brick Protocol dogfood variant over common templates
  - cleanup classification is not deletion authorization
  - no new feature or runtime opens from this preset
anti_hint: Do not use for a bounded single-surface cleanup where the file set and final graph are already known.
blocks:
  - B1
  - B2
  - B4
  - B7
  - B8
---

# brick-protocol-post-d-cleanup

## Route

Brick Protocol dogfood route for post-D surface recompilation and cleanup: an inspect step into parallel cleanup lanes, then axis-attack and evidence-integrity QA that fan in to a final gate before strict closure.
