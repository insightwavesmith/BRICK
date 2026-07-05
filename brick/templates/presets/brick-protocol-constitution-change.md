---
preset_ref: building-chain-preset:brick-protocol-constitution-change
catalog_scope: brick_protocol_dogfood
common_basis_ref: building-chain-preset:governed-change-review
selected_shape_ref: building-shape:reviewable-work
intent: Brick Protocol AGENTS.md, current packet, projection policy, Link-gate policy, or checker-governance change.
selection_hint: Use for Brick Protocol constitutional or active-control wording changes.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick/templates/bricks/design/brick.md
    target_word: axis_attack_qa
  - step_template_ref: building-step-template:axis-attack-qa
    brick_spec_ref: brick/templates/bricks/axis-attack-qa/brick.md
    target_word: code_attack_qa
  - step_template_ref: building-step-template:code-attack-qa
    brick_spec_ref: brick/templates/bricks/code-attack-qa/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick/templates/bricks/closure/brick.md
    target_word: closure
gate_concept_profile:
  - strict-evidence
  - coo-review
  - human-review
node_reroute_budgets:
  building-step-template:design: 5
proof_limits:
  - this is a Brick Protocol dogfood variant over common templates
  - human-review remains exceptional and explicitly declared when needed
  - no support surface becomes authority
anti_hint: Do not use for ordinary implementation or docs edits that do not mutate active constitutional or packet authority wording.
blocks:
  - B3
  - B2
  - B6
---

# brick-protocol-constitution-change

## Route

Brick Protocol dogfood variant of the governed-change route: design, axis-attack QA, code-attack QA, then closure, under a strict-evidence / COO / human-review gate profile. Use it for AGENTS.md, current-packet, projection-policy, Link-gate-policy, or checker-governance wording changes.
