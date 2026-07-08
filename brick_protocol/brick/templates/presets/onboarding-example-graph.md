---
preset_ref: building-chain-preset:onboarding-example-graph
catalog_scope: common
intent: Onboarding LOCAL example route -- design contract, review, and closure as a minimal graph so the example walks the dynamic walker.
selection_hint: Use only for the onboarding adapter:local example; it is the design-contract-only forward shaped as a graph (carries node_reroute_budgets) so the example routes through the dynamic walker instead of the linear runner.
steps:
  - step_template_ref: building-step-template:design
    brick_spec_ref: brick_protocol/brick/templates/bricks/design/brick.md
    target_word: review
  - step_template_ref: building-step-template:review
    brick_spec_ref: brick_protocol/brick/templates/bricks/review/brick.md
    target_word: closure
  - step_template_ref: building-step-template:closure
    brick_spec_ref: brick_protocol/brick/templates/bricks/closure/brick.md
    target_word: closure
node_reroute_budgets:
  building-step-template:design: 5
proof_limits:
  - chain preset is a caller / COO selection candidate only
  - not automatic shape selection
  - not Building Plan authoring from task text
  - design output stays a proposal; nothing is implemented or admitted from this route
  - onboarding-only graph variant of design-contract-only; the shared design-contract-only preset is unchanged
anti_hint: Do not use for real customer work or non-onboarding runs; it is only the adapter:local example graph.
blocks:
  - B5
---

# onboarding-example-graph

## Route

Onboarding LOCAL example route: the same design-only forward as design-contract-only (design turns the task into proposed architecture, data, or protocol boundaries, review checks that design contract against the declared work and return shape, closure records the reviewed contract and the open implementation delta), but carrying node_reroute_budgets so it materializes as a graph and the onboarding example walks the dynamic walker. No work step exists, so nothing is implemented and no caller write_scope is required. This preset is for the onboarding adapter:local example only; the shared design-contract-only preset (checker profiles, quickstart, hardening tests) stays untouched.
