---
preset_ref: building-chain-preset:governed-change-review
catalog_scope: common
selected_shape_ref: building-shape:reviewable-work
intent: Governed contract, policy, permission, or public-control change with design, axis attack, code attack, and closure.
selection_hint: Use when the requested work changes active instructions, public contracts, review policy, permissions, or authority boundaries.
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
proof_limits:
  - human-review remains exceptional and explicitly declared when needed
  - change wording is not active until admitted by the governing Building
  - no support surface becomes authority
---

# governed-change-review

## Route

Governed change route for contract, policy, permission, or public-control changes: design, axis-attack QA, code-attack QA, then closure under a strict-evidence / COO / human-review gate profile. The change wording is not active until the governing Building admits it.
