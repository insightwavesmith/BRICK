---
preset_ref: building-chain-preset:high-risk-change-inspected
catalog_scope: common
selected_shape_ref: building-shape:design-needed
intent: Hard path for shared contract, automation, integration, data, security-sensitive, or high-blast-radius changes.
selection_hint: Use when normal path, negative probes, regression checks, and evidence integrity review are required.
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
  - negative probes and frontier visibility must be proven by the declared Building Plan
  - checker green is support evidence only
  - preset is not runtime automation
anti_hint: Do not use for narrow high-trust work with a small blast radius and no shared contract, security, data, or automation impact.
blocks:
  - B3
  - B2
  - B4
  - B6
---

# high-risk-change-inspected

## Route

Hard route for shared-contract, automation, integration, data, security-sensitive, or high-blast-radius changes: design, DEV work, then parallel code-attack / axis-attack / evidence-integrity QA that fan in to a final gate before closure.
