---
preset_ref: building-chain-preset:brick-protocol-engine-feature-hard
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:high-risk-change-inspected
selected_shape_ref: building-shape:design-needed
intent: Brick Protocol runner, driver, checker, Link gate, adapter, recording, or automation surface change.
selection_hint: Use for Brick Protocol support/operator, checker, gate, adapter, recording, or automation work requiring negative probes.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick/templates/bricks/design/brick.md
    target_word: work
  - step_template_ref: building-step-template:work
    brick_spec_ref: brick/templates/bricks/work/brick.md
    target_word: hard_parallel_qa
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:evidence-integrity
    brick_spec_ref: brick/templates/bricks/evidence-integrity/brick.md
    target_word: fan_in_final_gate
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
gate_concept_profile:
  - strict-evidence
  - fan-in-wait-all
  - coo-review
  - human-review
gate_sequence_policy:
  - policy_ref: link-gate-sequence-policy:brick-protocol-engine-feature-hard-design-to-work
    sequence:
      - declared_link_gate: link-gate:default-transition
        on_missing_required_facts:
          action: reroute
          reason_refs:
            - observation:default-transition-missing-required-facts
          required_target_budget: true
          target_basis: source_brick
        on_sufficient:
          action: next
          next_gate_ref: link-gate:coo
      - declared_link_gate: link-gate:coo
        on_missing_required_facts:
          action: HOLD
          pending_target_basis: target_brick
          reason_refs:
            - observation:coo-gate-missing-required-facts
          required_disposition_owner: coo
        on_sufficient:
          action: forward
    source_step_template_ref: building-step-template:design
    target_step_template_ref: building-step-template:work
node_reroute_budgets:
  building-step-template:design: 1
  building-step-template:work: 1
closure_transition_target_policy:
  implementation_gap:
    action: target
    target_step_template_ref: building-step-template:work
  verification_gap:
    action: hold
proof_limits:
  - this is a Brick Protocol dogfood variant over common templates
  - checker green is support evidence only
  - preset is not runtime automation
---

# brick-protocol-engine-feature-hard

## Route

Brick Protocol dogfood hard route for runner, driver, checker, Link-gate, adapter, recording, or automation changes: design, DEV work, then parallel code-attack / axis-attack / evidence-integrity QA that fans in to a final gate before closure. It also declares a design-to-work gate-sequence policy and a fan-in-wait-all gate profile.
